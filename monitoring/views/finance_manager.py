from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404
from django.contrib import messages
from projeng.models import Project, ProjectCost
from django.db.models import Sum
from collections import defaultdict
from django.db.models.functions import TruncMonth
from django.core.paginator import Paginator
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.urls import reverse

# Import centralized access control functions
from gistagum.access_control import (
    is_finance_manager,
    is_head_engineer,
    is_finance_or_head_engineer,
    finance_manager_required,
    get_user_dashboard_url
)

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
            'project_name': getattr(c.project, 'name', '') if getattr(c, 'project', None) else '',
            'barangay': getattr(c.project, 'barangay', '') if getattr(c, 'project', None) else '',
            'amount': float(getattr(c, 'amount', 0) or 0),
            'cost_type': c.get_cost_type_display() if hasattr(c, 'get_cost_type_display') else '',
            'date': getattr(c, 'date', None),
        })

    # Bar Chart: Top 10 projects by budget
    project_financials = []
    for project in projects:
        spent = ProjectCost.objects.filter(project=project).aggregate(total=Sum('amount'))['total'] or 0
        project_financials.append({
            'name': project.name,
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
        'project_names': project_names,
        'project_budgets': project_budgets,
        'project_spent': project_spent,
        'cost_by_type': dict(cost_by_type),
        'months': months,
        'cumulative': cumulative,
        'utilization_data': utilization_data,
        # New UI data (Finance Manager refreshed layout)
        'active_projects_count': active_projects_count,
        'over_budget_count': over_budget_count,
        'near_limit_count': near_limit_count,
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

                description = (request.POST.get('description') or '').strip() or 'No remarks provided.'
                receipt = request.FILES.get('receipt')

                ProjectCost.objects.create(
                    project=project,
                    date=entry_date,
                    cost_type=cost_type,
                    description=description,
                    amount=amount,
                    receipt=receipt,
                    created_by=request.user,
                )
                messages.success(request, f'Cost entry saved for {project.name}.')
            except (ValueError, InvalidOperation) as e:
                messages.error(request, str(e) or 'Invalid amount.')
            except Exception as e:
                logger.error(f"Error adding cost entry: {str(e)}", exc_info=True)
                messages.error(request, 'Unable to save cost entry. Please try again.')
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
        breakdown_map = defaultdict(lambda: {
            'material': 0.0,
            'labor': 0.0,
            'equipment': 0.0,
            'other': 0.0,
        })
        if page_project_ids:
            for c in ProjectCost.objects.filter(project_id__in=page_project_ids).order_by('-date', '-id'):
                amt = float(c.amount or 0)
                ctype = c.cost_type if c.cost_type in breakdown_map[c.project_id] else 'other'
                breakdown_map[c.project_id][ctype] += amt
                costs_map[c.project_id].append({
                    'cost_type': c.get_cost_type_display(),
                    'date': f"{c.date.strftime('%b')} {c.date.day}, {c.date.year}" if c.date else '',
                    'description': c.description or '',
                    'amount': amt,
                })

        project_drawer_data = {}
        for p in page_projects:
            pid = p.get('id')
            if not pid:
                continue
            b = breakdown_map[pid]
            total_direct = b['material'] + b['labor'] + b['equipment']
            total_indirect = b['other']
            project_drawer_data[str(pid)] = {
                'id': pid,
                'prn': p.get('prn') or '',
                'name': p.get('name') or '',
                'barangay': p.get('barangay') or '',
                'budget': float(p.get('budget') or 0),
                'spent': float(p.get('spent') or 0),
                'remaining': float(p.get('remaining') or 0),
                'percent_used': float(p.get('percent_used') or 0),
                'breakdown': {
                    'material': b['material'],
                    'labor': b['labor'],
                    'direct': total_direct,
                    'indirect': total_indirect,
                    'contingency': max(float(p.get('remaining') or 0), 0.0),
                    'total_project_cost': float(p.get('budget') or 0),
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
        costs = ProjectCost.objects.filter(project=project).order_by('-date')
        total_spent = costs.aggregate(total=Sum('amount'))['total'] or 0
        project_budget = float(project.project_cost) if project.project_cost else 0
        total_spent_float = float(total_spent)
        remaining = project_budget - total_spent_float
        budget_utilization = (total_spent_float / project_budget * 100) if project_budget > 0 else 0
        
        # Calculate threshold (20% of budget) for color coding
        threshold = project_budget * 0.2
        
        cost_by_type = defaultdict(float)
        for cost in costs:
            cost_by_type[cost.get_cost_type_display()] += float(cost.amount)
        
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
