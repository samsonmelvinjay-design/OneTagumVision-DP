from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404, HttpResponse, JsonResponse
from django.contrib import messages
from projeng.models import Project, ProjectCost, ProjectCostAllocation, ExpenseReceipt
from django.db.models import Sum, Q
from django.db import connection
from collections import defaultdict
from django.db.models.functions import TruncMonth
from django.core.paginator import Paginator
from django.core import signing
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.text import get_valid_filename
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.conf import settings
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.urls import reverse, NoReverseMatch
from pathlib import Path
from uuid import uuid4
from PIL import Image, UnidentifiedImageError
import logging
import base64
import csv
import io
import openpyxl
import calendar

# Import centralized access control functions
from gistagum.access_control import (
    is_finance_manager,
    is_head_engineer,
    is_finance_or_head_engineer,
    finance_manager_required,
    get_user_dashboard_url
)

logger = logging.getLogger(__name__)

MOBILE_RECEIPT_TOKEN_SALT = "finance-mobile-receipt-upload"
MOBILE_RECEIPT_TOKEN_MAX_AGE_SECONDS = getattr(settings, "MOBILE_RECEIPT_TOKEN_MAX_AGE_SECONDS", 600)
MOBILE_RECEIPT_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
MOBILE_RECEIPT_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MOBILE_RECEIPT_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png"}


def _safe_reverse(name: str, fallback: str) -> str:
    try:
        return reverse(name)
    except NoReverseMatch:
        return fallback


def _mobile_receipt_cache_key(nonce: str) -> str:
    return f"finance_mobile_receipt_upload:{nonce}"


def _decode_mobile_receipt_token(token: str):
    if not token:
        return None, "Missing token."
    try:
        payload = signing.loads(
            token,
            salt=MOBILE_RECEIPT_TOKEN_SALT,
            max_age=MOBILE_RECEIPT_TOKEN_MAX_AGE_SECONDS,
        )
    except signing.SignatureExpired:
        return None, "Token expired. Please generate a new QR code."
    except signing.BadSignature:
        return None, "Invalid token."
    if not isinstance(payload, dict):
        return None, "Invalid token payload."
    required_keys = {"project_id", "user_id", "nonce"}
    if not required_keys.issubset(payload.keys()):
        return None, "Invalid token data."
    return payload, None


def _issue_mobile_receipt_token(project_id: int, user_id: int):
    payload = {
        "project_id": int(project_id),
        "user_id": int(user_id),
        "nonce": uuid4().hex,
    }
    token = signing.dumps(payload, salt=MOBILE_RECEIPT_TOKEN_SALT, compress=True)
    cache.set(
        _mobile_receipt_cache_key(payload["nonce"]),
        {
            "project_id": payload["project_id"],
            "user_id": payload["user_id"],
            "uploaded": False,
            "consumed": False,
            "temp_path": "",
            "filename": "",
            "uploaded_at": "",
            "temp_uploads": [],
            "uploaded_count": 0,
            "last_event": "",
            "last_error": "",
            "last_message": "",
            "created_ts": timezone.now().timestamp(),
        },
        timeout=MOBILE_RECEIPT_TOKEN_MAX_AGE_SECONDS,
    )
    return token


def _validate_mobile_receipt_file(uploaded_file):
    if not uploaded_file:
        raise ValueError("Please capture or choose an image first.")
    ext = Path(uploaded_file.name or "").suffix.lower()
    if ext not in MOBILE_RECEIPT_ALLOWED_EXTENSIONS:
        raise ValueError("Only JPG and PNG images are allowed.")
    content_type = (uploaded_file.content_type or "").lower().strip()
    if content_type and content_type not in MOBILE_RECEIPT_ALLOWED_CONTENT_TYPES:
        raise ValueError("Invalid image type. Please upload JPG or PNG.")
    if uploaded_file.size > MOBILE_RECEIPT_MAX_FILE_SIZE_BYTES:
        raise ValueError("Image exceeds 5MB size limit.")

    uploaded_file.seek(0)
    try:
        with Image.open(uploaded_file) as img:
            img.verify()
    except (UnidentifiedImageError, OSError):
        raise ValueError("Uploaded file is not a valid image.")
    finally:
        uploaded_file.seek(0)


def _build_safe_receipt_name(original_name: str, prefix: str = "receipt") -> str:
    suffix = Path(original_name or "").suffix.lower()
    if suffix not in MOBILE_RECEIPT_ALLOWED_EXTENSIONS:
        suffix = ".jpg"
    stem = get_valid_filename(Path(original_name or "receipt").stem)[:40] or "receipt"
    return f"{prefix}_{stem}_{uuid4().hex[:10]}{suffix}"


def _build_qr_data_uri(target_url: str) -> str:
    try:
        import qrcode
    except Exception as exc:
        raise RuntimeError("Missing 'qrcode' package. Install qrcode[pil] to enable QR generation.") from exc

    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(target_url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _attach_mobile_receipt_to_cost(cost, token: str, expected_project_id: int, expected_user_id: int):
    payload, token_error = _decode_mobile_receipt_token(token)
    if token_error:
        return False, token_error
    if int(payload["project_id"]) != int(expected_project_id) or int(payload["user_id"]) != int(expected_user_id):
        return False, "Token does not match this expense entry."

    cache_key = _mobile_receipt_cache_key(payload["nonce"])
    session_data = cache.get(cache_key)
    if not session_data:
        return False, "Upload session expired."
    if session_data.get("consumed"):
        return False, "This mobile receipt token has already been used."
    temp_uploads = list(session_data.get("temp_uploads") or [])
    if not temp_uploads and session_data.get("temp_path"):
        temp_uploads = [
            {
                "path": session_data.get("temp_path"),
                "filename": session_data.get("filename") or "receipt.jpg",
                "uploaded_at": session_data.get("uploaded_at") or "",
            }
        ]
    if not session_data.get("uploaded") or not temp_uploads:
        return False, "No mobile receipt was uploaded yet."
    uploaded_any = False
    first_saved_name = None
    for upload in temp_uploads:
        temp_path = (upload.get("path") or "").strip()
        if not temp_path or not default_storage.exists(temp_path):
            continue
        try:
            with default_storage.open(temp_path, "rb") as temp_file:
                image_bytes = temp_file.read()
        except Exception:
            return False, "Unable to read uploaded receipt."

        safe_name = _build_safe_receipt_name(upload.get("filename") or "receipt.jpg", prefix="mobile")
        if not first_saved_name:
            cost.receipt.save(safe_name, ContentFile(image_bytes), save=False)
            first_saved_name = safe_name

        receipt_row = ExpenseReceipt(expense=cost)
        receipt_row.image.save(safe_name, ContentFile(image_bytes), save=True)
        uploaded_any = True

        try:
            default_storage.delete(temp_path)
        except Exception:
            logger.warning("Could not delete temporary receipt file: %s", temp_path)

    if not uploaded_any:
        return False, "Uploaded receipt file was not found."

    cost.save(update_fields=["receipt"])

    session_data["consumed"] = True
    session_data["temp_path"] = ""
    session_data["filename"] = ""
    session_data["uploaded_at"] = ""
    session_data["temp_uploads"] = []
    session_data["last_message"] = f"Attached {len(temp_uploads)} mobile receipt(s) to the cost entry."
    cache.set(cache_key, session_data, timeout=60)
    return True, ""

@login_required
@finance_manager_required
def finance_reports(request):
    """
    Finance Manager reports landing page (screenshot-based UI).
    This page links to existing export/report endpoints (budget reports + project reports).
    """
    from django.utils import timezone
    year_now = timezone.now().year
    years = list(range(year_now - 5, year_now + 1))
    months = [
        {'value': 1, 'label': 'January'},
        {'value': 2, 'label': 'February'},
        {'value': 3, 'label': 'March'},
        {'value': 4, 'label': 'April'},
        {'value': 5, 'label': 'May'},
        {'value': 6, 'label': 'June'},
        {'value': 7, 'label': 'July'},
        {'value': 8, 'label': 'August'},
        {'value': 9, 'label': 'September'},
        {'value': 10, 'label': 'October'},
        {'value': 11, 'label': 'November'},
        {'value': 12, 'label': 'December'},
    ]

    # Categories based on existing project types for UI dropdown
    categories = []
    try:
        categories = list(
            Project.objects
            .exclude(project_type__isnull=True)
            .values_list('project_type__name', flat=True)
            .distinct()
            .order_by('project_type__name')
        )
        categories = [c for c in categories if c]
    except Exception:
        categories = []

    return render(request, 'finance_manager/finance_reports.html', {
        'years': years,
        'months': months,
        'categories': categories,
        'default_year': year_now,
        'default_month': timezone.now().month,
    })


def _finance_report_period(period, year, month):
    from datetime import date

    today = timezone.now().date()
    try:
        year = int(year)
    except (TypeError, ValueError):
        year = today.year
    try:
        month = int(month)
    except (TypeError, ValueError):
        month = today.month
    month = min(12, max(1, month))
    period = (period or 'monthly').strip().lower()

    if period == 'yearly':
        start = date(year, 1, 1)
        end = date(year, 12, 31)
        label = str(year)
    elif period == 'quarterly':
        quarter = ((month - 1) // 3) + 1
        start_month = ((quarter - 1) * 3) + 1
        end_month = start_month + 2
        start = date(year, start_month, 1)
        end = date(year, end_month, calendar.monthrange(year, end_month)[1])
        label = f"Q{quarter} {year}"
    else:
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        label = start.strftime('%B %Y')
        period = 'monthly'

    return period, start, end, label


def _finance_report_status_label(status):
    labels = {
        'planned': 'Planned',
        'pending': 'Pending',
        'in_progress': 'In Progress',
        'ongoing': 'In Progress',
        'completed': 'Completed',
        'delayed': 'Delayed',
        'cancelled': 'Cancelled',
    }
    return labels.get((status or '').strip().lower(), (status or 'Unknown').replace('_', ' ').title())


@login_required
@finance_manager_required
def finance_report_preview(request):
    from django.utils import timezone

    template_key = (request.GET.get('template') or 'monthly_budget').strip().lower()
    period, start_date, end_date, period_label = _finance_report_period(
        request.GET.get('period'),
        request.GET.get('year'),
        request.GET.get('month'),
    )
    category = (request.GET.get('category') or '').strip()

    title_map = {
        'monthly_budget': 'Monthly Budget Summary',
        'project_status': 'Project Status Report',
        'quarterly_performance': 'Quarterly Performance Report',
        'barangay_allocation': 'Barangay Budget Allocation',
        'over_budget_alert': 'Over Budget Alert Report',
        'annual_summary': 'Annual Summary Report',
    }
    title = title_map.get(template_key, 'Budget Monitoring Report')

    projects = Project.objects.all().select_related('project_type').prefetch_related('assigned_engineers')
    projects = projects.filter(
        Q(start_date__isnull=False) | Q(end_date__isnull=False),
        Q(start_date__isnull=True) | Q(start_date__lte=end_date),
        Q(end_date__isnull=True) | Q(end_date__gte=start_date),
    )
    if category:
        projects = projects.filter(project_type__name=category)
    if template_key == 'project_status':
        projects = projects.filter(Q(status='in_progress') | Q(status='ongoing') | Q(status='delayed'))

    project_rows = []
    status_counts = defaultdict(int)
    barangay_map = defaultdict(lambda: {'barangay': '', 'budget': 0.0, 'spent': 0.0, 'projects': 0})
    totals = {
        'budget': 0.0,
        'spent': 0.0,
        'remaining': 0.0,
        'projects': 0,
        'over': 0,
        'within': 0,
        'under': 0,
        'at_risk': 0,
    }

    for project in projects.order_by('barangay', 'name'):
        costs = ProjectCost.objects.filter(project=project)
        spent = float(costs.aggregate(total=Sum('amount'))['total'] or 0)
        budget = float(project.project_cost or 0)
        remaining = budget - spent
        utilization = (spent / budget * 100.0) if budget > 0 else 0.0
        if budget > 0 and spent > budget:
            budget_state = 'Over'
        elif budget > 0 and utilization >= 80:
            budget_state = 'Within'
        else:
            budget_state = 'Under'

        if template_key == 'over_budget_alert' and budget_state != 'Over':
            continue

        status_label = _finance_report_status_label(project.status)
        status_counts[status_label] += 1
        totals['projects'] += 1
        totals['budget'] += budget
        totals['spent'] += spent
        totals['remaining'] += remaining
        totals[budget_state.lower()] += 1
        if 90 <= utilization <= 100:
            totals['at_risk'] += 1

        barangay_key = project.barangay or 'Unspecified'
        barangay_map[barangay_key]['barangay'] = barangay_key
        barangay_map[barangay_key]['budget'] += budget
        barangay_map[barangay_key]['spent'] += spent
        barangay_map[barangay_key]['projects'] += 1

        engineers = [u.get_full_name() or u.username for u in project.assigned_engineers.all()]
        project_rows.append({
            'prn': project.prn or '',
            'name': project.name or '',
            'barangay': project.barangay or 'Unspecified',
            'status': status_label,
            'start_date': project.start_date.isoformat() if project.start_date else '',
            'end_date': project.end_date.isoformat() if project.end_date else '',
            'engineers': ', '.join(engineers) if engineers else 'Unassigned',
            'budget': round(budget, 2),
            'spent': round(spent, 2),
            'remaining': round(remaining, 2),
            'utilization': round(utilization, 2),
            'budget_state': budget_state,
        })

    barangays = sorted(barangay_map.values(), key=lambda item: item['budget'], reverse=True)
    for item in barangays:
        budget = item['budget']
        item['remaining'] = round(budget - item['spent'], 2)
        item['utilization'] = round((item['spent'] / budget * 100.0) if budget > 0 else 0.0, 2)
        item['budget'] = round(item['budget'], 2)
        item['spent'] = round(item['spent'], 2)

    payload = {
        'title': title,
        'template': template_key,
        'period': period,
        'period_label': period_label,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'category': category or 'All Categories',
        'generated_at': timezone.localtime(timezone.now()).strftime('%b %d, %Y %I:%M %p'),
        'summary': {key: round(value, 2) if isinstance(value, float) else value for key, value in totals.items()},
        'status_counts': [{'label': key, 'value': value} for key, value in sorted(status_counts.items())],
        'barangays': barangays,
        'projects': project_rows,
    }

    return render(request, 'finance_manager/finance_report_preview.html', {'report_payload': payload})

@login_required
@finance_manager_required
def finance_dashboard(request):
    projects = Project.objects.all()
    total_budget = projects.aggregate(total=Sum('project_cost'))['total'] or 0
    total_spent = ProjectCost.objects.aggregate(total=Sum('amount'))['total'] or 0
    remaining = total_budget - total_spent

    # Screenshot-based dashboard metrics
    active_projects_count = projects.filter(status__in=['in_progress', 'ongoing']).count()
    over_budget_count = 0
    near_limit_count = 0
    budget_by_barangay_spent = defaultdict(float)

    # Recent activity (latest cost entries)
    recent_costs = (
        ProjectCost.objects
        .select_related('project')
        .order_by('-date', '-id')[:8]
    )
    recent_activity = []
    for c in recent_costs:
        recent_activity.append({
            'project_id': getattr(c.project, 'id', None) if getattr(c, 'project', None) else None,
            'project_name': getattr(c.project, 'name', '') if getattr(c, 'project', None) else '',
            'barangay': getattr(c.project, 'barangay', '') if getattr(c, 'project', None) else '',
            'amount': float(getattr(c, 'amount', 0) or 0),
            'cost_type': c.get_cost_type_display() if hasattr(c, 'get_cost_type_display') else '',
            'date': getattr(c, 'date', None),
        })

    # Bar Chart: Top 10 projects by budget
    project_financials = []
    budget_watchlist = []
    for project in projects:
        spent = ProjectCost.objects.filter(project=project).aggregate(total=Sum('amount'))['total'] or 0
        project_financials.append({
            'id': project.id,
            'name': project.name,
            'barangay': project.barangay or '',
            'budget': float(project.project_cost or 0),
            'spent': float(spent),
        })
        # Track over-budget / near-limit counts and barangay distribution
        try:
            budget_val = float(project.project_cost or 0)
            spent_val = float(spent or 0)
            if budget_val > 0:
                used_pct = (spent_val / budget_val) * 100.0
                if used_pct > 100.0:
                    over_budget_count += 1
                elif used_pct >= 85.0:
                    near_limit_count += 1
                if used_pct >= 85.0:
                    budget_watchlist.append({
                        'id': project.id,
                        'name': project.name,
                        'barangay': project.barangay or '',
                        'budget': budget_val,
                        'spent': spent_val,
                        'remaining': budget_val - spent_val,
                        'utilization': used_pct,
                        'is_over_budget': used_pct > 100.0,
                    })
            if project.barangay:
                budget_by_barangay_spent[str(project.barangay).strip()] += spent_val
        except Exception:
            pass
    top_projects = sorted(project_financials, key=lambda x: x['budget'], reverse=True)[:10]
    project_names = [p['name'] for p in top_projects]
    project_budgets = [p['budget'] for p in top_projects]
    project_spent = [p['spent'] for p in top_projects]
    # Pie Chart: Spending by cost type
    cost_by_type = defaultdict(float)
    for cost in ProjectCost.objects.all():
        cost_by_type[cost.get_cost_type_display()] += float(cost.amount)
    # Line Chart: Cumulative spending over time (by month)
    monthly_spending = (
        ProjectCost.objects
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )
    months = [m['month'].strftime('%b %Y') if m['month'] else 'Unknown' for m in monthly_spending]
    monthly_totals = [float(m['total']) for m in monthly_spending]
    cumulative = []
    running = 0
    for amt in monthly_totals:
        running += amt
        cumulative.append(running)
    # Doughnut Chart: Budget utilization
    utilization_data = [float(total_spent), float(remaining)]
    utilization_percentage = (float(total_spent) / float(total_budget) * 100) if total_budget > 0 else 0
    available_budget_percentage = max(0, 100 - utilization_percentage)
    at_risk_count = over_budget_count + near_limit_count
    budget_watchlist = sorted(
        budget_watchlist,
        key=lambda x: (x['is_over_budget'], x['utilization']),
        reverse=True
    )[:6]

    # Budget distribution by barangay (Top 6 by spent)
    barangay_items = sorted(
        [{'barangay': k, 'spent': v} for k, v in budget_by_barangay_spent.items() if k],
        key=lambda x: x['spent'],
        reverse=True
    )[:6]
    max_spent = max([i['spent'] for i in barangay_items], default=0) or 0
    for i in barangay_items:
        i['percent'] = round((i['spent'] / max_spent) * 100.0, 2) if max_spent > 0 else 0.0
    context = {
        'total_budget': total_budget,
        'total_spent': total_spent,
        'remaining': remaining,
        'utilization_percentage': utilization_percentage,
        'available_budget_percentage': available_budget_percentage,
        'project_names': project_names,
        'project_budgets': project_budgets,
        'project_spent': project_spent,
        'cost_by_type': dict(cost_by_type),
        'months': months,
        'cumulative': cumulative,
        'utilization_data': utilization_data,
        # New UI data (Finance Manager refreshed layout)
        'active_projects_count': active_projects_count,
        'total_projects_count': projects.count(),
        'over_budget_count': over_budget_count,
        'near_limit_count': near_limit_count,
        'at_risk_count': at_risk_count,
        'budget_watchlist': budget_watchlist,
        'recent_activity': recent_activity,
        'budget_by_barangay': barangay_items,
    }
    return render(request, 'finance_manager/finance_dashboard.html', context)

@login_required
@finance_manager_required
def finance_projects(request):
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from django.db.models import Q
        from django.utils import timezone
        from projeng.models import ProjectProgress
        
        # Filters
        barangay_filter = request.GET.get('barangay')
        status_filter = request.GET.get('status')
        category_filter = (request.GET.get('category') or '').strip()
        prn_filter = (request.GET.get('prn') or '').strip()
        q = (request.GET.get('q') or '').strip()
        projects = Project.objects.all()
        if barangay_filter:
            projects = projects.filter(barangay=barangay_filter)
        if prn_filter:
            projects = projects.filter(prn__icontains=prn_filter)
        if q:
            projects = projects.filter(Q(name__icontains=q))
        if category_filter:
            # Best-effort: Project.project_type FK or project_type string
            try:
                projects = projects.filter(project_type__name=category_filter)
            except Exception:
                try:
                    projects = projects.filter(project_type=category_filter)
                except Exception:
                    pass
        if status_filter:
            
            if status_filter == 'delayed':
                # Include projects with status='delayed' OR projects that are dynamically delayed
                # (overdue projects with status 'in_progress' or 'ongoing' and progress < 98%)
                today = timezone.now().date()
                # Get projects explicitly marked as delayed
                delayed_projects = projects.filter(status='delayed')
                # Get projects that are dynamically delayed (overdue but not yet flagged)
                overdue_projects = projects.filter(
                    Q(status='in_progress') | Q(status='ongoing'),
                    end_date__lt=today
                )
                # Filter overdue projects to only include those with progress < 98%
                dynamically_delayed_ids = []
                for project in overdue_projects:
                    latest_progress = ProjectProgress.objects.filter(project=project).order_by('-date').first()
                    latest_progress_pct = latest_progress.percentage_complete if latest_progress else 0
                    if latest_progress_pct < 98:
                        dynamically_delayed_ids.append(project.id)
                # Combine both sets
                projects = delayed_projects | projects.filter(id__in=dynamically_delayed_ids)
            elif status_filter == 'in_progress':
                # Include both 'in_progress' and 'ongoing' statuses
                projects = projects.filter(Q(status='in_progress') | Q(status='ongoing'))
            else:
                projects = projects.filter(status=status_filter)
        
        # Latest progress (bulk)
        latest_progress_by_project_id = {}
        try:
            progress_qs = (
                ProjectProgress.objects
                .filter(project__in=projects)
                .order_by('project_id', '-date', '-created_at')
            )
            for row in progress_qs:
                pid = row.project_id
                if pid not in latest_progress_by_project_id:
                    latest_progress_by_project_id[pid] = float(row.percentage_complete or 0)
        except Exception:
            pass

        # List of projects with their financials (for pagination / legacy)
        project_financials = []
        today = timezone.now().date()
        project_cards = []
        for project in projects:
            try:
                spent = ProjectCost.objects.filter(project=project).aggregate(total=Sum('amount'))['total'] or 0
                spent_float = float(spent)
                budget_float = float(project.project_cost) if project.project_cost else 0
                remaining_proj = budget_float - spent_float
                
                # Calculate threshold (20% of budget) for color coding
                threshold = budget_float * 0.2
                
                # Determine actual status (check if dynamically delayed)
                actual_status = project.status or 'planned'
                if actual_status in ['in_progress', 'ongoing'] and project.end_date and project.end_date < today:
                    latest_progress = ProjectProgress.objects.filter(project=project).order_by('-date').first()
                    latest_progress_pct = latest_progress.percentage_complete if latest_progress else 0
                    if latest_progress_pct < 98:
                        actual_status = 'delayed'
                
                project_financials.append({
                    'name': project.name,
                    'barangay': project.barangay or '',
                    'budget': budget_float,
                    'spent': spent_float,
                    'remaining': remaining_proj,
                    'status': actual_status,
                    'threshold': threshold,
                })

                # Card data for screenshot layout
                progress_pct = latest_progress_by_project_id.get(project.id, 0.0)
                progress_pct = max(0.0, min(100.0, float(progress_pct)))
                # Use cross-platform date formatting (Windows does not support %-m / %-d).
                start_display = (
                    f"{project.start_date.month}/{project.start_date.day}/{project.start_date.year}"
                    if getattr(project, 'start_date', None) else ''
                )
                end_display = (
                    f"{project.end_date.month}/{project.end_date.day}/{project.end_date.year}"
                    if getattr(project, 'end_date', None) else ''
                )
                date_range = (f"{start_display} - {end_display}" if (start_display or end_display) else '')
                # Assigned engineer / contractor best-effort
                engineer_name = ''
                try:
                    eng = getattr(project, 'assigned_engineer', None)
                    if eng:
                        engineer_name = eng.get_full_name() or eng.username
                except Exception:
                    engineer_name = ''
                contractor = getattr(project, 'contractor', '') if hasattr(project, 'contractor') else ''
                category_name = ''
                try:
                    pt = getattr(project, 'project_type', None)
                    category_name = getattr(pt, 'name', '') if pt else ''
                    if not category_name and isinstance(pt, str):
                        category_name = pt
                except Exception:
                    category_name = ''
                project_cards.append({
                    'id': project.id,
                    'prn': project.prn or '',
                    'status': actual_status,
                    'name': project.name,
                    'barangay': project.barangay or '',
                    'category': category_name,
                    'date_range': date_range,
                    'budget': budget_float,
                    'spent': spent_float,
                    'progress_pct': progress_pct,
                    'engineer_name': engineer_name,
                    'contractor': contractor or '',
                })
            except Exception as e:
                logger.error(f"Error processing project {project.id}: {str(e)}", exc_info=True)
                continue
        
        # Pagination - 25 items per page
        paginator = Paginator(project_financials, 25)
        page_number = request.GET.get('page', 1)
        try:
            page_obj = paginator.get_page(page_number)
        except:
            page_obj = paginator.get_page(1)
        
        # Sort by budget and take top 10 for chart (from all projects, not just current page)
        top_projects = sorted(project_financials, key=lambda x: x['budget'], reverse=True)[:10]
        project_names = [p['name'] for p in top_projects]
        project_budgets = [p['budget'] for p in top_projects]
        project_spent = [p['spent'] for p in top_projects]
        
        # Cost breakdown by type (for pie chart)
        cost_by_type = defaultdict(float)
        try:
            for cost in ProjectCost.objects.filter(project__in=projects):
                cost_by_type[cost.get_cost_type_display()] += float(cost.amount)
        except Exception as e:
            logger.error(f"Error calculating cost breakdown: {str(e)}", exc_info=True)
        
        # Get unique barangays from all projects (normalized)
        barangay_list = Project.objects.exclude(barangay__isnull=True).exclude(barangay='').values_list('barangay', flat=True).distinct()
        all_barangays = sorted(set([b.strip() for b in barangay_list if b and b.strip()]))
        # Fallback to hardcoded list if no projects exist
        if not all_barangays:
            all_barangays = [
                'Apokon', 'Bincungan', 'Busaon', 'Canocotan', 'Cuambogan', 'La Filipina', 'Liboganon',
                'Madaum', 'Magdum', 'Magugpo East', 'Magugpo North', 'Magugpo Poblacion', 'Magugpo South',
                'Magugpo West', 'Mankilam', 'New Balamban', 'Nueva Fuerza', 'Pagsabangan', 'Pandapan',
                'San Agustin', 'San Isidro', 'San Miguel', 'Visayan Village'
            ]
        try:
            all_statuses = [s[0] for s in Project.STATUS_CHOICES if s[0] != 'cancelled']
        except Exception as e:
            logger.error(f"Error getting STATUS_CHOICES: {str(e)}", exc_info=True)
            all_statuses = ['planned', 'in_progress', 'completed', 'delayed']
        
        # Convert to JSON for JavaScript (if needed by template)
        import json
        try:
            project_names_json = json.dumps(project_names)
            project_budgets_json = json.dumps(project_budgets)
            project_spent_json = json.dumps(project_spent)
            cost_by_type_json = json.dumps(dict(cost_by_type))
        except Exception as e:
            logger.error(f"Error converting to JSON: {str(e)}", exc_info=True)
            project_names_json = '[]'
            project_budgets_json = '[]'
            project_spent_json = '[]'
            cost_by_type_json = '{}'
        
        context = {
            'project_financials': list(page_obj.object_list),
            'page_obj': page_obj,
            'project_cards': project_cards,
            'project_names': project_names,
            'project_names_json': project_names_json,
            'project_budgets': project_budgets,
            'project_budgets_json': project_budgets_json,
            'project_spent': project_spent,
            'project_spent_json': project_spent_json,
            'cost_by_type': dict(cost_by_type),
            'cost_by_type_json': cost_by_type_json,
            'all_barangays': all_barangays,
            'all_statuses': all_statuses,
            'selected_barangay': barangay_filter or '',
            'selected_status': status_filter or '',
            'selected_category': category_filter,
            'selected_prn': prn_filter,
            'q': q,
            'categories': sorted(
                [c for c in set([p.get('category') for p in project_cards if p.get('category')])],
                key=lambda x: x.lower()
            ),
        }
        return render(request, 'finance_manager/finance_projects.html', context)
    except Exception as e:
        logger.error(f"Error in finance_projects view: {str(e)}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        # Re-raise the exception so Django's error handling can show the actual error
        raise

@login_required
@finance_manager_required
def finance_cost_management(request):
    import logging
    logger = logging.getLogger(__name__)
    allocation_table_exists = 'projeng_projectcostallocation' in connection.introspection.table_names()
    
    try:
        if request.method == 'POST' and request.POST.get('action') == 'add_cost_entry':
            next_url = (request.POST.get('next') or '').strip() or reverse('finance_cost_management')
            if not next_url.startswith('/'):
                next_url = reverse('finance_cost_management')
            try:
                project = get_object_or_404(Project, id=int(request.POST.get('project_id') or 0))
                cost_type = (request.POST.get('cost_type') or '').strip()
                valid_cost_types = {k for k, _ in ProjectCost.COST_TYPES}
                if cost_type not in valid_cost_types:
                    raise ValueError('Please select a valid cost type.')
                cost_subtype = (request.POST.get('cost_subtype') or '').strip()
                required_subtypes = {
                    'material': dict(ProjectCost.MATERIAL_SUBTYPES),
                    'labor': dict(ProjectCost.LABOR_SUBTYPES),
                }
                subtype_label = ''
                if cost_type in required_subtypes:
                    # Backward compatible: subtype is optional for legacy clients/tests.
                    # Validate only when a subtype value is provided.
                    if cost_subtype:
                        if cost_subtype not in required_subtypes[cost_type]:
                            if cost_type == 'material':
                                raise ValueError('Please select a valid material type (PR or PO).')
                            raise ValueError('Please select a valid labor type.')
                        subtype_label = required_subtypes[cost_type][cost_subtype]
                else:
                    cost_subtype = ''

                amount_raw = (request.POST.get('amount') or '').replace(',', '').strip()
                amount = Decimal(amount_raw)
                if amount <= 0:
                    raise ValueError('Amount must be greater than 0.')

                date_raw = (request.POST.get('date') or '').strip()
                if date_raw:
                    entry_date = datetime.strptime(date_raw, '%Y-%m-%d').date()
                else:
                    from django.utils import timezone
                    entry_date = timezone.now().date()

                description_raw = (request.POST.get('description') or '').strip() or 'No remarks provided.'
                description = f'[{subtype_label}] {description_raw}' if subtype_label else description_raw
                receipt = request.FILES.get('receipt')
                mobile_receipt_token = (request.POST.get('mobile_receipt_token') or '').strip()

                cost_entry = ProjectCost.objects.create(
                    project=project,
                    date=entry_date,
                    cost_type=cost_type,
                    description=description,
                    amount=amount,
                    receipt=receipt,
                    created_by=request.user,
                )

                # If no desktop file was selected, attach scanned mobile receipt (if available).
                if not receipt and mobile_receipt_token:
                    attached, attach_error = _attach_mobile_receipt_to_cost(
                        cost=cost_entry,
                        token=mobile_receipt_token,
                        expected_project_id=project.id,
                        expected_user_id=request.user.id,
                    )
                    if not attached and attach_error:
                        messages.warning(
                            request,
                            f'Cost entry saved, but mobile receipt was not attached: {attach_error}'
                        )
                messages.success(request, f'Cost entry saved for {project.name}.')
            except (ValueError, InvalidOperation) as e:
                messages.error(request, str(e) or 'Invalid amount.')
            except Exception as e:
                logger.error(f"Error adding cost entry: {str(e)}", exc_info=True)
                messages.error(request, 'Unable to save cost entry. Please try again.')
            return redirect(next_url)
        elif request.method == 'POST' and request.POST.get('action') == 'save_cost_allocation':
            next_url = (request.POST.get('next') or '').strip() or reverse('finance_cost_management')
            if not next_url.startswith('/'):
                next_url = reverse('finance_cost_management')
            if not allocation_table_exists:
                messages.error(request, 'Allocation table is not ready yet. Please run database migrations.')
                return redirect(next_url)
            try:
                project = get_object_or_404(Project, id=int(request.POST.get('project_id') or 0))

                def _parse_alloc(field_name):
                    raw_value = (request.POST.get(field_name) or '0').replace(',', '').strip()
                    value = Decimal(raw_value or '0')
                    if value < 0:
                        raise ValueError(f'{field_name.replace("_", " ").title()} cannot be negative.')
                    return value

                allocation_data = {
                    'material': _parse_alloc('alloc_material'),
                    'labor': _parse_alloc('alloc_labor'),
                    # Keep schema stable: store "Direct" and "Indirect" in existing columns.
                    'equipment': _parse_alloc('alloc_direct'),
                    'supply_and_install': Decimal('0'),
                    'ocm': _parse_alloc('alloc_indirect'),
                    'permit_and_licenses': Decimal('0'),
                    'contingency': _parse_alloc('alloc_contingency'),
                }

                allocation, _ = ProjectCostAllocation.objects.get_or_create(
                    project=project,
                    defaults={**allocation_data, 'set_by': request.user},
                )
                for field_name, value in allocation_data.items():
                    setattr(allocation, field_name, value)
                allocation.set_by = request.user
                allocation.save()

                messages.success(request, f'Allocation saved for {project.name}.')
            except (ValueError, InvalidOperation) as e:
                messages.error(request, str(e) or 'Invalid allocation values.')
            except Exception as e:
                logger.error(f"Error saving allocation: {str(e)}", exc_info=True)
                messages.error(request, 'Unable to save allocation. Please try again.')
            return redirect(next_url)

        # Filters
        prn_filter = (request.GET.get('prn') or '').strip()
        barangay_filter = request.GET.get('barangay')
        budget_status_filter = request.GET.get('budget_status')
        year_filter = request.GET.get('year')
        from django.db.models import Q
        projects = Project.objects.all()
        if prn_filter:
            projects = projects.filter(Q(prn__icontains=prn_filter))
        if barangay_filter:
            projects = projects.filter(barangay=barangay_filter)
        if year_filter:
            try:
                year_int = int(year_filter)
                # Use start year as the primary year filter (matches typical reporting UX)
                projects = projects.filter(start_date__year=year_int)
            except (TypeError, ValueError):
                year_filter = ''
        
        # Prepare financials
        project_financials = []
        over_budget_count = 0
        within_budget_count = 0
        under_budget_count = 0
        
        for project in projects:
            try:
                spent = ProjectCost.objects.filter(project=project).aggregate(total=Sum('amount'))['total'] or 0
                spent_float = float(spent)
                budget_float = float(project.project_cost) if project.project_cost else 0
                remaining = budget_float - spent_float
                
                if budget_float > 0:
                    utilization_percentage = (spent_float / budget_float) * 100
                    if spent_float > budget_float:
                        budget_status = 'over'
                        over_budget_count += 1
                    elif utilization_percentage >= 80:  # Within Budget: 80-100% utilization (at risk but not over)
                        budget_status = 'within'
                        within_budget_count += 1
                    else:
                        budget_status = 'under'
                        under_budget_count += 1
                else:
                    budget_status = 'under'
                    under_budget_count += 1
                
                # Calculate threshold (20% of budget) for color coding
                threshold = budget_float * 0.2

                # Badge used in refreshed UI
                percent_used = utilization_percentage if budget_float > 0 else 0.0
                if percent_used > 100:
                    status_label = 'Over Budget'
                elif percent_used >= 85:
                    status_label = 'Near Limit'
                else:
                    status_label = 'Within Budget'
                
                project_financials.append({
                    'id': project.id,
                    'prn': project.prn or '',
                    'name': project.name,
                    'barangay': project.barangay or '',
                    'budget': budget_float,
                    'spent': spent_float,
                    'remaining': remaining,
                    'budget_status': budget_status,
                    'threshold': threshold,
                    'percent_used': percent_used,
                    'status_label': status_label,
                })
            except Exception as e:
                logger.error(f"Error processing project {project.id}: {str(e)}", exc_info=True)
                continue
        
        # Store total count before filtering by budget status
        total_projects_before_status_filter = len(project_financials)
        
        # Apply budget status filter to the displayed list (but keep counts for all projects)
        if budget_status_filter:
            project_financials = [p for p in project_financials if p['budget_status'] == budget_status_filter]
        
        # Total projects in the filtered list (for display)
        total_projects = len(project_financials)

        # Screenshot summary cards
        total_approved_budget = sum([p.get('budget', 0) for p in project_financials]) if project_financials else 0
        total_spent_sum = sum([p.get('spent', 0) for p in project_financials]) if project_financials else 0
        total_remaining_sum = sum([p.get('remaining', 0) for p in project_financials]) if project_financials else 0
        near_limit_count = len([p for p in project_financials if 85 <= (p.get('percent_used') or 0) <= 100])
        over_count = len([p for p in project_financials if (p.get('percent_used') or 0) > 100])
        
        # Pagination - 25 items per page
        paginator = Paginator(project_financials, 25)
        page_number = request.GET.get('page', 1)
        try:
            page_obj = paginator.get_page(page_number)
        except:
            page_obj = paginator.get_page(1)

        # Drawer payload for currently visible projects
        page_projects = list(page_obj.object_list)
        page_project_ids = [p.get('id') for p in page_projects if p.get('id')]
        costs_map = defaultdict(list)
        allocation_map = {}
        if page_project_ids and allocation_table_exists:
            allocation_map = {
                a.project_id: a for a in ProjectCostAllocation.objects.filter(project_id__in=page_project_ids)
            }
        breakdown_map = defaultdict(lambda: {
            'material': 0.0,
            'labor': 0.0,
            'equipment': 0.0,
            'supply and install': 0.0,
            'ocm': 0.0,
            'permit&licenses': 0.0,
            'contingency': 0.0,
            'other': 0.0,
        })
        if page_project_ids:
            for c in ProjectCost.objects.filter(project_id__in=page_project_ids).order_by('-date', '-id'):
                amt = float(c.amount or 0)
                ctype = c.cost_type if c.cost_type in breakdown_map[c.project_id] else 'other'
                breakdown_map[c.project_id][ctype] += amt
                costs_map[c.project_id].append({
                    'cost_type': c.get_cost_type_display(),
                    'cost_subtype': c.get_cost_subtype_display() if hasattr(c, 'get_cost_subtype_display') else '',
                    'date': f"{c.date.strftime('%b')} {c.date.day}, {c.date.year}" if c.date else '',
                    'description': c.get_clean_description() if hasattr(c, 'get_clean_description') else (c.description or ''),
                    'amount': amt,
                })

        project_drawer_data = {}
        for p in page_projects:
            pid = p.get('id')
            if not pid:
                continue
            spent_breakdown = breakdown_map[pid]
            alloc = allocation_map.get(pid)
            material_alloc = float(getattr(alloc, 'material', 0) or 0)
            labor_alloc = float(getattr(alloc, 'labor', 0) or 0)
            direct_alloc = float(getattr(alloc, 'equipment', 0) or 0)
            indirect_alloc = float(getattr(alloc, 'ocm', 0) or 0)
            contingency_alloc = float(getattr(alloc, 'contingency', 0) or 0)

            # Remaining allocation per summary card after encoded entries
            # Material/Labor use their exact cost types, while other cost types
            # roll into Direct or Indirect based on finance workflow.
            material_remaining = material_alloc - spent_breakdown['material']
            labor_remaining = labor_alloc - spent_breakdown['labor']
            direct_spent = spent_breakdown['equipment'] + spent_breakdown['supply and install']
            indirect_spent = spent_breakdown['ocm'] + spent_breakdown['permit&licenses'] + spent_breakdown['other']
            contingency_remaining = contingency_alloc - spent_breakdown['contingency']
            total_direct_alloc = direct_alloc - direct_spent
            total_indirect_alloc = indirect_alloc - indirect_spent

            drawer_spent = (
                spent_breakdown['material'] + spent_breakdown['labor'] + spent_breakdown['equipment'] +
                spent_breakdown['supply and install'] + spent_breakdown['ocm'] + spent_breakdown['permit&licenses'] +
                spent_breakdown['contingency'] + spent_breakdown['other']
            )
            budget_value = float(p.get('budget') or 0)
            drawer_remaining = budget_value - drawer_spent
            drawer_percent_used = (drawer_spent / budget_value * 100.0) if budget_value > 0 else 0.0
            project_drawer_data[str(pid)] = {
                'id': pid,
                'prn': p.get('prn') or '',
                'name': p.get('name') or '',
                'barangay': p.get('barangay') or '',
                'budget': budget_value,
                'spent': drawer_spent,
                'remaining': drawer_remaining,
                'percent_used': drawer_percent_used,
                'breakdown': {
                    'material': material_remaining,
                    'labor': labor_remaining,
                    'direct': total_direct_alloc,
                    'indirect': total_indirect_alloc,
                    'contingency': contingency_remaining,
                    'total_project_cost': budget_value,
                },
                'allocation': {
                    'material': material_alloc,
                    'labor': labor_alloc,
                    'direct': direct_alloc,
                    'indirect': indirect_alloc,
                    'contingency': contingency_alloc,
                },
                'history': costs_map[pid],
            }
        
        # For filters - get unique barangays from all projects
        # Get all barangays, strip whitespace, convert to set for uniqueness, then sort
        barangay_list = Project.objects.exclude(barangay__isnull=True).exclude(barangay='').values_list('barangay', flat=True).distinct()
        # Normalize: strip whitespace and filter out empty strings
        all_barangays = sorted(set([b.strip() for b in barangay_list if b and b.strip()]))
        
        # Fallback to hardcoded list if no projects exist
        if not all_barangays:
            all_barangays = [
                'Apokon', 'Bincungan', 'Busaon', 'Canocotan', 'Cuambogan', 'La Filipina', 'Liboganon',
                'Madaum', 'Magdum', 'Magugpo East', 'Magugpo North', 'Magugpo Poblacion', 'Magugpo South',
                'Magugpo West', 'Mankilam', 'New Balamban', 'Nueva Fuerza', 'Pagsabangan', 'Pandapan',
                'San Agustin', 'San Isidro', 'San Miguel', 'Visayan Village'
            ]
        
        context = {
            'project_financials': list(page_obj.object_list),
            'page_obj': page_obj,
            'total_projects': total_projects,
            'over_budget_count': over_budget_count,
            'within_budget_count': within_budget_count,
            'under_budget_count': under_budget_count,
            'near_limit_count': near_limit_count,
            'over_count': over_count,
            'total_approved_budget': total_approved_budget,
            'total_spent_sum': total_spent_sum,
            'total_remaining_sum': total_remaining_sum,
            'all_barangays': all_barangays,
            'selected_prn': prn_filter or '',
            'selected_barangay': barangay_filter or '',
            'selected_budget_status': budget_status_filter or '',
            'selected_year': year_filter or '',
            'cost_type_options': ProjectCost.COST_TYPES,
            'project_drawer_data': project_drawer_data,
            'year_options': sorted(
                {d.year for d in Project.objects.exclude(start_date__isnull=True).values_list('start_date', flat=True) if d},
                reverse=True
            ),
            'receipt_qr_generate_url': _safe_reverse(
                'finance_generate_receipt_upload_qr',
                '/dashboard/finance/receipts/qr/',
            ),
            'receipt_status_url': _safe_reverse(
                'finance_receipt_upload_status_api',
                '/dashboard/finance/receipts/mobile-upload/status/',
            ),
        }
        return render(request, 'finance_manager/finance_cost_management.html', context)
    except Exception as e:
        logger.error(f"Error in finance_cost_management view: {str(e)}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        # Re-raise the exception so Django's error handling can show the actual error
        raise


@login_required
@finance_manager_required
@require_POST
def finance_generate_receipt_upload_qr(request):
    try:
        project_id = int(request.POST.get("project_id") or 0)
        project = get_object_or_404(Project, id=project_id)
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "error": "Invalid project selection."}, status=400)
    except Http404:
        return JsonResponse({"success": False, "error": "Project not found."}, status=404)

    try:
        token = _issue_mobile_receipt_token(project_id=project.id, user_id=request.user.id)
        upload_path = f"{reverse('finance_mobile_receipt_capture')}?token={token}"
        public_base_url = (getattr(settings, "MOBILE_RECEIPT_PUBLIC_BASE_URL", "") or "").strip()
        if public_base_url:
            upload_url = f"{public_base_url.rstrip('/')}{upload_path}"
        else:
            upload_url = request.build_absolute_uri(upload_path)
        qr_data_uri = _build_qr_data_uri(upload_url)
        return JsonResponse(
            {
                "success": True,
                "token": token,
                "upload_url": upload_url,
                "qr_image": qr_data_uri,
                "expires_in": MOBILE_RECEIPT_TOKEN_MAX_AGE_SECONDS,
            }
        )
    except Exception as exc:
        logger.error("Error generating receipt upload QR: %s", exc, exc_info=True)
        return JsonResponse({"success": False, "error": str(exc)}, status=500)


@ensure_csrf_cookie
def finance_mobile_receipt_capture(request):
    token = (request.GET.get("token") or "").strip()
    payload, token_error = _decode_mobile_receipt_token(token)
    if token_error:
        return render(
            request,
            "finance_manager/mobile_receipt_capture.html",
            {"is_valid": False, "error_message": token_error, "token": token},
            status=400,
        )

    session_data = cache.get(_mobile_receipt_cache_key(payload["nonce"]))
    if not session_data:
        return render(
            request,
            "finance_manager/mobile_receipt_capture.html",
            {"is_valid": False, "error_message": "Upload session expired.", "token": token},
            status=410,
        )

    project = Project.objects.filter(id=payload["project_id"]).first()
    if not project:
        return render(
            request,
            "finance_manager/mobile_receipt_capture.html",
            {"is_valid": False, "error_message": "Project not found for this token.", "token": token},
            status=404,
        )

    return render(
        request,
        "finance_manager/mobile_receipt_capture.html",
        {
            "is_valid": True,
            "token": token,
            "project": project,
            "upload_api_url": reverse("finance_mobile_receipt_upload_api"),
            "status_api_url": reverse("finance_receipt_upload_status_api"),
            "max_size_mb": MOBILE_RECEIPT_MAX_FILE_SIZE_BYTES // (1024 * 1024),
        },
    )


@csrf_exempt
@require_POST
def finance_mobile_receipt_upload_api(request):
    token = (request.POST.get("token") or "").strip()
    payload, token_error = _decode_mobile_receipt_token(token)
    if token_error:
        return JsonResponse({"success": False, "error": token_error}, status=400)

    cache_key = _mobile_receipt_cache_key(payload["nonce"])
    session_data = cache.get(cache_key)
    if not session_data:
        return JsonResponse({"success": False, "error": "Upload session expired."}, status=410)
    if session_data.get("consumed"):
        return JsonResponse({"success": False, "error": "Token already used."}, status=409)
    uploaded_files = request.FILES.getlist("image") or request.FILES.getlist("receipt")
    if not uploaded_files:
        single_file = request.FILES.get("image") or request.FILES.get("receipt")
        if single_file:
            uploaded_files = [single_file]

    if not uploaded_files:
        error_message = "Please capture or choose an image first."
        session_data.update({"last_event": "failure", "last_error": error_message, "last_message": error_message})
        cache.set(cache_key, session_data, timeout=MOBILE_RECEIPT_TOKEN_MAX_AGE_SECONDS)
        return JsonResponse({"success": False, "error": error_message}, status=400)

    try:
        for uploaded_file in uploaded_files:
            _validate_mobile_receipt_file(uploaded_file)
    except ValueError as exc:
        session_data.update({"last_event": "failure", "last_error": str(exc), "last_message": str(exc)})
        cache.set(cache_key, session_data, timeout=MOBILE_RECEIPT_TOKEN_MAX_AGE_SECONDS)
        return JsonResponse({"success": False, "error": str(exc)}, status=400)

    existing_uploads = list(session_data.get("temp_uploads") or [])
    saved_uploads = []
    try:
        for uploaded_file in uploaded_files:
            safe_name = _build_safe_receipt_name(uploaded_file.name, prefix="tmp")
            temp_path = f"receipts/tmp/{payload['nonce']}_{uuid4().hex[:8]}_{safe_name}"
            saved_path = default_storage.save(temp_path, uploaded_file)
            upload_meta = {
                "path": saved_path,
                "filename": safe_name,
                "uploaded_at": timezone.now().isoformat(),
            }
            existing_uploads.append(upload_meta)
            saved_uploads.append(upload_meta)
    except Exception:
        logger.error("Failed saving mobile receipt upload", exc_info=True)
        for upload_meta in saved_uploads:
            temp_path = upload_meta.get("path")
            if temp_path and default_storage.exists(temp_path):
                try:
                    default_storage.delete(temp_path)
                except Exception:
                    logger.warning("Could not roll back temp receipt path: %s", temp_path)
        error_message = "Unable to save receipt. Please try again."
        session_data.update({"last_event": "failure", "last_error": error_message, "last_message": error_message})
        cache.set(cache_key, session_data, timeout=MOBILE_RECEIPT_TOKEN_MAX_AGE_SECONDS)
        return JsonResponse({"success": False, "error": error_message}, status=500)

    latest_upload = existing_uploads[-1]
    session_data.update(
        {
            "uploaded": True,
            "temp_path": latest_upload.get("path", ""),
            "filename": latest_upload.get("filename", ""),
            "uploaded_at": latest_upload.get("uploaded_at", ""),
            "temp_uploads": existing_uploads,
            "uploaded_count": len(existing_uploads),
            "last_event": "success",
            "last_error": "",
            "last_message": f"Uploaded {len(uploaded_files)} image(s). Total queued: {len(existing_uploads)}.",
        }
    )
    cache.set(cache_key, session_data, timeout=MOBILE_RECEIPT_TOKEN_MAX_AGE_SECONDS)
    return JsonResponse(
        {
            "success": True,
            "filename": latest_upload.get("filename", ""),
            "uploaded_at": latest_upload.get("uploaded_at", ""),
            "uploaded_count": len(existing_uploads),
        }
    )


@csrf_exempt
@require_POST
def finance_mobile_receipt_event_api(request):
    token = (request.POST.get("token") or "").strip()
    event_type = (request.POST.get("event_type") or "").strip().lower()
    message = (request.POST.get("message") or "").strip()
    payload, token_error = _decode_mobile_receipt_token(token)
    if token_error:
        return JsonResponse({"success": False, "error": token_error}, status=400)

    cache_key = _mobile_receipt_cache_key(payload["nonce"])
    session_data = cache.get(cache_key)
    if not session_data:
        return JsonResponse({"success": False, "error": "Upload session expired."}, status=410)
    if event_type not in {"success", "failure"}:
        return JsonResponse({"success": False, "error": "Invalid event type."}, status=400)

    session_data["last_event"] = event_type
    session_data["last_message"] = message
    session_data["last_error"] = message if event_type == "failure" else ""
    cache.set(cache_key, session_data, timeout=MOBILE_RECEIPT_TOKEN_MAX_AGE_SECONDS)
    return JsonResponse({"success": True})


@login_required
@finance_manager_required
def finance_receipt_upload_status_api(request):
    token = (request.GET.get("token") or "").strip()
    payload, token_error = _decode_mobile_receipt_token(token)
    if token_error:
        return JsonResponse({"success": False, "error": token_error}, status=400)

    cache_key = _mobile_receipt_cache_key(payload["nonce"])
    session_data = cache.get(cache_key)
    if not session_data:
        return JsonResponse({"success": False, "error": "Upload session expired."}, status=410)

    if int(session_data.get("user_id") or 0) != int(request.user.id):
        return JsonResponse({"success": False, "error": "This token belongs to another user session."}, status=403)

    created_ts = float(session_data.get("created_ts") or 0)
    remaining = max(0, int(MOBILE_RECEIPT_TOKEN_MAX_AGE_SECONDS - (timezone.now().timestamp() - created_ts)))
    return JsonResponse(
        {
            "success": True,
            "uploaded": bool(session_data.get("uploaded")),
            "consumed": bool(session_data.get("consumed")),
            "filename": session_data.get("filename") or "",
            "uploaded_at": session_data.get("uploaded_at") or "",
            "uploaded_count": int(session_data.get("uploaded_count") or len(session_data.get("temp_uploads") or [])),
            "filenames": [item.get("filename") or "" for item in (session_data.get("temp_uploads") or []) if item.get("filename")],
            "last_event": session_data.get("last_event") or "",
            "last_error": session_data.get("last_error") or "",
            "last_message": session_data.get("last_message") or "",
            "expires_in": remaining,
        }
    )


@login_required
@finance_manager_required
def finance_notifications(request):
    """View for Finance Managers and Head Engineers to manage their notifications"""
    from projeng.models import Notification
    from projeng.utils import get_project_from_notification
    from django.contrib import messages
    from django.shortcuts import redirect
    from django.http import JsonResponse
    
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')

    if request.method == 'POST':
        action = request.POST.get('action')
        notification_id = request.POST.get('notification_id')

        if action == 'mark_read' and notification_id:
            try:
                notification = Notification.objects.get(id=notification_id, recipient=request.user)
                notification.is_read = True
                notification.save()
                return JsonResponse({'success': True})
            except Notification.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Notification not found'})

        elif action == 'mark_all_read':
            notifications.update(is_read=True)
            messages.success(request, "All notifications marked as read.")
            return redirect('finance_notifications')

        elif action == 'delete' and notification_id:
            try:
                notification = Notification.objects.get(id=notification_id, recipient=request.user)
                notification.delete()
                return JsonResponse({'success': True})
            except Notification.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Notification not found'})

        elif action == 'delete_all':
            try:
                deleted_count = notifications.delete()[0]
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': f'{deleted_count} notifications deleted'})
                messages.success(request, f"All {deleted_count} notifications deleted.")
                return redirect('finance_notifications')
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)})
                messages.error(request, f"Error deleting notifications: {str(e)}")
                return redirect('finance_notifications')

    unread_count = notifications.filter(is_read=False).count()
    
    # Extract project IDs for clickable notifications
    import logging
    logger = logging.getLogger(__name__)
    notifications_with_projects = []
    for notification in notifications:
        project_id = None
        try:
            if notification.message:
                # Log for debugging
                if 'Budget Review Request' in notification.message:
                    logger.info(f"Processing Budget Review Request notification {notification.id}: {notification.message[:100]}")
                project_id = get_project_from_notification(notification.message)
                if project_id:
                    logger.info(f"Extracted project_id={project_id} for notification {notification.id}")
                else:
                    if 'Budget Review Request' in notification.message:
                        logger.warning(f"Failed to extract project_id for Budget Review Request notification {notification.id}")
        except Exception as e:
            logger.error(f"Error getting project from notification {notification.id}: {str(e)}", exc_info=True)
        notifications_with_projects.append({
            'notification': notification,
            'project_id': project_id,
            'is_clickable': project_id is not None
        })

    context = {
        'notifications': notifications,
        'notifications_with_projects': notifications_with_projects,
        'unread_count': unread_count,
    }
    return render(request, 'finance_manager/finance_notifications.html', context)

@login_required
@finance_manager_required
def finance_project_detail(request, project_id):
    import logging
    logger = logging.getLogger(__name__)
    
    # Try to get project from projeng model first
    try:
        project = get_object_or_404(Project, id=project_id)
        logger.info(f"Finance project detail: Found project {project_id} in projeng model")
    except Http404:
        # Re-raise Http404 so Django can handle it properly
        logger.warning(f"Finance project detail: Project {project_id} not found")
        raise
    except Exception as e:
        logger.error(f"Finance project detail: Error getting project {project_id}: {str(e)}", exc_info=True)
        raise Http404("Project not found")
    
    try:
        costs = (
            ProjectCost.objects
            .filter(project=project)
            .prefetch_related('mobile_receipts')
            .order_by('-date')
        )
        total_spent = costs.aggregate(total=Sum('amount'))['total'] or 0
        project_budget = float(project.project_cost) if project.project_cost else 0
        total_spent_float = float(total_spent)
        remaining = project_budget - total_spent_float
        budget_utilization = (total_spent_float / project_budget * 100) if project_budget > 0 else 0
        
        # Calculate threshold (20% of budget) for color coding
        threshold = project_budget * 0.2
        
        cost_by_type = defaultdict(float)
        all_receipt_gallery = []
        for cost in costs:
            cost_by_type[cost.get_cost_type_display()] += float(cost.amount)
            receipt_gallery = []
            mobile_receipts = list(cost.mobile_receipts.all())
            for receipt in mobile_receipts:
                if not getattr(receipt, "image", None):
                    continue
                try:
                    receipt_url = receipt.image.url
                except Exception:
                    continue
                receipt_gallery.append(
                    {
                        "cost_id": cost.id,
                        "url": receipt_url,
                        "uploaded_at": receipt.uploaded_at,
                        "uploaded_label": timezone.localtime(receipt.uploaded_at).strftime("%b %d, %Y"),
                        "entry_date_label": cost.date.strftime("%b %d, %Y") if getattr(cost, "date", None) else "",
                        "type_label": cost.get_cost_type_display(),
                        "amount_label": f"{float(cost.amount):,.2f}",
                        "title": (cost.description or "").strip() or cost.get_cost_type_display(),
                        "caption": "Uploaded from mobile scanner",
                    }
                )

            if not receipt_gallery and cost.receipt:
                try:
                    legacy_url = cost.receipt.url
                except Exception:
                    legacy_url = ""
                if legacy_url:
                    receipt_gallery.append(
                        {
                            "cost_id": cost.id,
                            "url": legacy_url,
                            "uploaded_at": getattr(cost, "date", None),
                            "uploaded_label": cost.date.strftime("%b %d, %Y") if getattr(cost, "date", None) else "",
                            "entry_date_label": cost.date.strftime("%b %d, %Y") if getattr(cost, "date", None) else "",
                            "type_label": cost.get_cost_type_display(),
                            "amount_label": f"{float(cost.amount):,.2f}",
                            "title": (cost.description or "").strip() or cost.get_cost_type_display(),
                            "caption": "Attached to cost entry",
                        }
                    )

            cost.receipt_gallery = receipt_gallery
            cost.receipt_count = len(receipt_gallery)
            cost.has_receipts = bool(receipt_gallery)
            all_receipt_gallery.extend(receipt_gallery)
        
        # Budget Requests (model-based, with statuses + attachments + history)
        from projeng.models import BudgetRequest
        pending_budget_request = (
            BudgetRequest.objects
            .filter(project=project, status='pending')
            .select_related('requested_by')
            .prefetch_related('attachments')
            .order_by('-created_at')
            .first()
        )
        budget_requests = (
            BudgetRequest.objects
            .filter(project=project)
            .select_related('requested_by', 'reviewed_by')
            .prefetch_related('attachments', 'history')
            .order_by('-created_at')
        )
        
        context = {
            'project': project,
            'costs': costs,
            'total_spent': total_spent_float,
            'remaining': remaining,
            'budget_utilization': budget_utilization,
            'project_budget': project_budget,
            'threshold': threshold,
            'cost_by_type': dict(cost_by_type),
            'all_receipt_gallery': all_receipt_gallery,
            'all_receipt_count': len(all_receipt_gallery),
            'pending_budget_request': pending_budget_request,
            'budget_requests': budget_requests,
        }
        return render(request, 'finance_manager/finance_project_detail.html', context)
    except Exception as e:
        logger.error(f"Finance project detail: Error processing project {project_id}: {str(e)}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, f"Error loading project details: {str(e)}")
        # Redirect to finance cost management page instead of finance_projects
        return redirect('finance_cost_management') 


@login_required
@finance_manager_required
def finance_project_export_csv(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    costs = ProjectCost.objects.filter(project=project).order_by('-date', '-id')
    total_spent = float(costs.aggregate(total=Sum('amount'))['total'] or 0)
    budget = float(project.project_cost or 0)
    remaining = budget - total_spent
    utilization = (total_spent / budget * 100.0) if budget > 0 else 0.0

    response = HttpResponse(content_type='text/csv')
    filename = f'finance_project_report_{project.prn or project.id}_{datetime.now().strftime("%Y%m%d")}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['Finance Project Report'])
    writer.writerow(['Project Name', project.name or ''])
    writer.writerow(['PRN', project.prn or ''])
    writer.writerow(['Barangay', project.barangay or ''])
    writer.writerow(['Approved Budget', f'{budget:.2f}'])
    writer.writerow(['Total Spent', f'{total_spent:.2f}'])
    writer.writerow(['Remaining Budget', f'{remaining:.2f}'])
    writer.writerow(['Budget Utilization', f'{utilization:.2f}%'])
    writer.writerow([])
    writer.writerow(['Date', 'Cost Type', 'Description', 'Amount', 'Receipt'])
    for cost in costs:
        writer.writerow([
            cost.date.strftime('%Y-%m-%d') if cost.date else '',
            cost.get_cost_type_display(),
            cost.description or '',
            f'{float(cost.amount or 0):.2f}',
            cost.receipt.url if cost.receipt else '',
        ])
    return response


@login_required
@finance_manager_required
def finance_project_export_excel(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    costs = ProjectCost.objects.filter(project=project).order_by('-date', '-id')
    total_spent = float(costs.aggregate(total=Sum('amount'))['total'] or 0)
    budget = float(project.project_cost or 0)
    remaining = budget - total_spent
    utilization = (total_spent / budget * 100.0) if budget > 0 else 0.0

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = 'Project Report'

    summary_rows = [
        ['Finance Project Report', ''],
        ['Project Name', project.name or ''],
        ['PRN', project.prn or ''],
        ['Barangay', project.barangay or ''],
        ['Approved Budget', budget],
        ['Total Spent', total_spent],
        ['Remaining Budget', remaining],
        ['Budget Utilization (%)', utilization],
        ['', ''],
    ]
    for row in summary_rows:
        sheet.append(row)

    sheet.append(['Date', 'Cost Type', 'Description', 'Amount', 'Receipt'])
    for cost in costs:
        sheet.append([
            cost.date.strftime('%Y-%m-%d') if cost.date else '',
            cost.get_cost_type_display(),
            cost.description or '',
            float(cost.amount or 0),
            cost.receipt.url if cost.receipt else '',
        ])

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f'finance_project_report_{project.prn or project.id}_{datetime.now().strftime("%Y%m%d")}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
