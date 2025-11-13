from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from .finance_manager import finance_dashboard, finance_projects, finance_cost_management, finance_notifications
from .engineer_management import (
    engineer_list, engineer_create, engineer_detail,
    engineer_edit, engineer_deactivate, engineer_activate
)
from projeng.models import Project, ProjectProgress, ProjectCost
from django.contrib.auth.models import Group
from django.core.paginator import Paginator
from django.template.loader import get_template
from django.utils import timezone
import os
import json
import csv
import io
from datetime import datetime
import openpyxl
# Optional xhtml2pdf import
try:
    from xhtml2pdf import pisa
except Exception:
    pisa = None
from django.conf import settings
from collections import Counter, defaultdict
from monitoring.forms import ProjectForm

# Import centralized access control functions (MUST be before views that use them)
from gistagum.access_control import (
    is_head_engineer, 
    is_finance_manager, 
    is_project_engineer,
    is_project_or_head_engineer,
    is_finance_or_head_engineer,
    head_engineer_required,
    prevent_project_engineer_access,
    get_user_dashboard_url
)

def home(request):
    """
    Redirect to login page - no direct access to home
    """
    from django.shortcuts import redirect
    return redirect('login')

@login_required
@prevent_project_engineer_access
def dashboard(request):
    try:
        print(f"Dashboard view accessed by user: {request.user.username}, authenticated: {request.user.is_authenticated}")
        from projeng.models import Project
        from collections import Counter, defaultdict
        
        # Role-based queryset
        if is_head_engineer(request.user) or is_finance_manager(request.user):
            print(f"User {request.user.username} is head engineer or finance manager, showing all projects")
            projects = Project.objects.all()
        elif is_project_engineer(request.user):
            projects = Project.objects.filter(assigned_engineers=request.user)
        else:
            projects = Project.objects.none()
        # Recent projects (5 most recent)
        recent_projects = projects.order_by('-created_at')[:5]
        # Metrics
        project_count = projects.count()
        completed_count = projects.filter(status='completed').count()
        in_progress_count = projects.filter(status='in_progress').count() + projects.filter(status='ongoing').count()
        planned_count = projects.filter(status='planned').count() + projects.filter(status='pending').count()
        delayed_count = projects.filter(status='delayed').count()
        # Collaborative analytics
        collab_by_barangay = defaultdict(int)
        collab_by_status = defaultdict(int)
        for p in projects:
            if p.barangay and isinstance(p.barangay, str) and p.barangay.strip():
                collab_by_barangay[p.barangay.strip()] += 1
            if p.status and isinstance(p.status, str) and p.status.strip():
                # Use display-friendly status
                status = (
                    'Ongoing' if p.status in ['in_progress', 'ongoing'] else
                    'Planned' if p.status in ['planned', 'pending'] else
                    'Completed' if p.status == 'completed' else
                    'Delayed' if p.status == 'delayed' else p.status.title()
                )
                collab_by_status[status] += 1
        # Sort keys for consistent chart order
        collab_by_barangay = {k: collab_by_barangay[k] for k in sorted(collab_by_barangay.keys())}
        collab_by_status = {k: collab_by_status[k] for k in sorted(collab_by_status.keys())}
        
        # Calculate completion rate
        completion_rate = 0.0
        if project_count > 0:
            completion_rate = (completed_count / project_count) * 100
        
        context = {
            'recent_projects': recent_projects,
            'project_count': project_count,
            'completed_count': completed_count,
            'in_progress_count': in_progress_count,
            'planned_count': planned_count,
            'delayed_count': delayed_count,
            'completion_rate': round(completion_rate, 1),
            'collab_by_barangay': dict(collab_by_barangay),
            'collab_by_status': dict(collab_by_status),
        }
        return render(request, 'monitoring/dashboard.html', context)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error in dashboard view: {str(e)}', exc_info=True)
        from django.http import HttpResponseServerError
        return HttpResponseServerError(f'Server Error: {str(e)}')

@login_required
@prevent_project_engineer_access
def dashboard_budget_utilization_data(request):
    """API endpoint for Budget Utilization by Project chart"""
    from projeng.models import Project, ProjectCost
    from django.db.models import Sum
    from django.http import JsonResponse
    
    if is_head_engineer(request.user) or is_finance_manager(request.user):
        projects = Project.objects.filter(project_cost__isnull=False).exclude(project_cost=0)
    else:
        projects = Project.objects.none()
    
    # Calculate budget utilization for each project
    project_data = []
    for project in projects:
        total_cost = ProjectCost.objects.filter(project=project).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        if project.project_cost and float(project.project_cost) > 0:
            utilization = (float(total_cost) / float(project.project_cost)) * 100
            project_data.append({
                'name': project.name[:25] + '...' if len(project.name) > 25 else project.name,
                'utilization': round(utilization, 1),
                'total_cost': float(total_cost),
                'budget': float(project.project_cost)
            })
    
    # Sort by utilization (highest first) and take top 10
    project_data.sort(key=lambda x: x['utilization'], reverse=True)
    project_data = project_data[:10]
    
    labels = [p['name'] for p in project_data]
    data = [p['utilization'] for p in project_data]
    
    # Color coding: Red (>100%), Orange (80-100%), Green (<80%)
    background_colors = [
        'rgba(239, 68, 68, 0.7)' if d > 100 else
        'rgba(251, 146, 60, 0.7)' if d > 80 else
        'rgba(34, 197, 94, 0.7)'
        for d in data
    ]
    border_colors = [
        'rgba(239, 68, 68, 1)' if d > 100 else
        'rgba(251, 146, 60, 1)' if d > 80 else
        'rgba(34, 197, 94, 1)'
        for d in data
    ]
    
    return JsonResponse({
        'labels': labels,
        'datasets': [{
            'label': 'Budget Utilization (%)',
            'data': data,
            'backgroundColor': background_colors,
            'borderColor': border_colors,
            'borderWidth': 1
        }]
    })

@login_required
@prevent_project_engineer_access
def dashboard_cost_breakdown_data(request):
    """API endpoint for Cost Breakdown by Type chart"""
    from projeng.models import ProjectCost
    from django.db.models import Sum
    from django.http import JsonResponse
    
    if is_head_engineer(request.user) or is_finance_manager(request.user):
        # Get cost breakdown by type across all projects
        cost_by_type = ProjectCost.objects.all().values('cost_type').annotate(
            total=Sum('amount')
        ).order_by('-total')
    else:
        cost_by_type = []
    
    labels = [item['cost_type'].title() for item in cost_by_type]
    data = [float(item['total']) for item in cost_by_type]
    
    # Color scheme for cost types
    colors = {
        'Material': 'rgba(59, 130, 246, 0.7)',    # Blue
        'Labor': 'rgba(251, 191, 36, 0.7)',       # Yellow
        'Equipment': 'rgba(34, 197, 94, 0.7)',    # Green
        'Other': 'rgba(139, 92, 246, 0.7)'        # Purple
    }
    
    background_colors = [colors.get(label, 'rgba(156, 163, 175, 0.7)') for label in labels]
    border_colors = [bg.replace('0.7', '1') for bg in background_colors]
    
    return JsonResponse({
        'labels': labels,
        'datasets': [{
            'label': 'Total Cost (₱)',
            'data': data,
            'backgroundColor': background_colors,
            'borderColor': border_colors,
            'borderWidth': 2
        }]
    })

@login_required
@prevent_project_engineer_access
def dashboard_monthly_spending_data(request):
    """API endpoint for Monthly Spending Trend chart"""
    from projeng.models import ProjectCost
    from django.db.models import Sum
    from django.db.models.functions import TruncMonth
    from django.http import JsonResponse
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    if is_head_engineer(request.user) or is_finance_manager(request.user):
        # Get spending for the last 12 months
        twelve_months_ago = timezone.now() - timedelta(days=365)
        monthly_spending = (
            ProjectCost.objects
            .filter(date__gte=twelve_months_ago)
            .annotate(month=TruncMonth('date'))
            .values('month')
            .annotate(total=Sum('amount'))
            .order_by('month')
        )
    else:
        monthly_spending = []
    
    # Format data
    months = [item['month'].strftime('%b %Y') for item in monthly_spending]
    totals = [float(item['total']) for item in monthly_spending]
    
    # If no data, return empty chart
    if not months:
        months = ['No Data']
        totals = [0]
    
    return JsonResponse({
        'labels': months,
        'datasets': [{
            'label': 'Monthly Spending (₱)',
            'data': totals,
            'borderColor': 'rgba(59, 130, 246, 1)',
            'backgroundColor': 'rgba(59, 130, 246, 0.1)',
            'tension': 0.4,
            'fill': True,
            'borderWidth': 2
        }]
    })

@login_required
@prevent_project_engineer_access
def project_list(request):
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            
            # Phase 4: Auto-detect zone before saving
            zone_type, confidence = project.detect_and_set_zone(save=False)
            
            project.save()
            form.save_m2m()  # Save assigned engineers
            
            # Log zone detection result (optional, for debugging)
            if zone_type:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Zone detected for project '{project.name}': {zone_type} (confidence: {confidence}%)")
            
            # Optionally add a success message or redirect
            return redirect('project_list')
        else:
            # Re-render with errors
            if is_head_engineer(request.user) or is_finance_manager(request.user):
                projects = Project.objects.all().order_by('-created_at')
            elif is_project_engineer(request.user):
                projects = Project.objects.filter(assigned_engineers=request.user).order_by('-created_at')
            else:
                projects = Project.objects.none()
            paginator = Paginator(projects, 10)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            return render(request, 'monitoring/project_list.html', {'page_obj': page_obj, 'form': form})
    # GET logic
    if is_head_engineer(request.user) or is_finance_manager(request.user):
        projects = Project.objects.all()
    elif is_project_engineer(request.user):
        projects = Project.objects.filter(assigned_engineers=request.user)
    else:
        projects = Project.objects.none()
    
    # Apply filters
    from django.db.models import Q
    barangay_filter = request.GET.get('barangay')
    duration_filter = request.GET.get('duration')
    status_filter = request.GET.get('status')
    search_query = request.GET.get('search', '').strip()
    
    # Barangay filter
    if barangay_filter:
        projects = projects.filter(barangay=barangay_filter)
    
    # Status filter
    if status_filter:
        # Handle "in_progress" to match both "in_progress" and "ongoing" statuses
        if status_filter == 'in_progress':
            projects = projects.filter(Q(status='in_progress') | Q(status='ongoing'))
        else:
            projects = projects.filter(status=status_filter)
    
    # Search filter (search in name, PRN, description)
    if search_query:
        projects = projects.filter(
            Q(name__icontains=search_query) |
            Q(prn__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Duration filter (based on project duration calculated from start_date and end_date)
    if duration_filter:
        # Filter projects that have both start and end dates, then filter by duration in Python
        # This is more reliable than raw SQL and works across all databases
        projects_with_dates = projects.filter(
            start_date__isnull=False,
            end_date__isnull=False
        )
        
        # Get project IDs that match the duration criteria
        matching_project_ids = []
        for project in projects_with_dates.only('id', 'start_date', 'end_date'):
            if project.start_date and project.end_date:
                duration_days = (project.end_date - project.start_date).days
                
                if duration_filter == 'lt6' and duration_days < 180:
                    matching_project_ids.append(project.id)
                elif duration_filter == '6to12' and 180 <= duration_days <= 365:
                    matching_project_ids.append(project.id)
                elif duration_filter == 'gt12' and duration_days > 365:
                    matching_project_ids.append(project.id)
        
        # Filter the queryset to only include matching projects
        if matching_project_ids:
            projects = projects.filter(id__in=matching_project_ids)
        else:
            # No projects match the duration criteria
            projects = projects.none()
    
    # Order by created_at descending
    projects = projects.order_by('-created_at')
    
    paginator = Paginator(projects, 15)  # Show 15 projects per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    form = ProjectForm()
    # Build projects_data for modal and JS (use filtered projects)
    projects_data = []
    for p in page_obj.object_list:
        projects_data.append({
            'id': p.id,
            'name': p.name,
            'prn': p.prn,
            'description': p.description,
            'barangay': p.barangay,
            'latitude': float(p.latitude) if p.latitude else '',
            'longitude': float(p.longitude) if p.longitude else '',
            'project_cost': str(p.project_cost) if p.project_cost is not None else '',
            'source_of_funds': p.source_of_funds,
            'start_date': str(p.start_date) if p.start_date else '',
            'end_date': str(p.end_date) if p.end_date else '',
            'status': p.status,
            'image': p.image.url if p.image else '',
            'progress': getattr(p, 'progress', 0),
            'assigned_engineers': [str(e) for e in p.assigned_engineers.all()] if hasattr(p, 'assigned_engineers') else [],
        })
    return render(request, 'monitoring/project_list.html', {
        'page_obj': page_obj,
        'form': form,
        'projects_data': projects_data,
    })

@login_required
@prevent_project_engineer_access
def map_view(request):
    if is_head_engineer(request.user) or is_finance_manager(request.user):
        projects = Project.objects.all()
    elif is_project_engineer(request.user):
        projects = Project.objects.filter(assigned_engineers=request.user)
    else:
        projects = Project.objects.none()
    # Only include projects with coordinates
    projects_with_coords = projects.filter(latitude__isnull=False, longitude__isnull=False).prefetch_related('assigned_engineers')
    
    # Get latest progress for all projects
    from django.db.models import Max
    project_ids = [p.id for p in projects_with_coords]
    latest_progress = {}
    if project_ids:
        from projeng.models import ProjectProgress
        latest_progress_qs = ProjectProgress.objects.filter(
            project_id__in=project_ids
        ).values('project_id').annotate(
            latest_date=Max('date'),
            latest_created=Max('created_at')
        )
        for item in latest_progress_qs:
            latest = ProjectProgress.objects.filter(
                project_id=item['project_id'],
                date=item['latest_date'],
                created_at=item['latest_created']
            ).order_by('-created_at').first()
            if latest and latest.percentage_complete is not None:
                latest_progress[item['project_id']] = int(latest.percentage_complete)
    
    projects_data = []
    for p in projects_with_coords:
        # Get assigned engineers as a list of usernames
        assigned_engineers = [eng.username for eng in p.assigned_engineers.all()]
        # Get progress - prefer latest progress update, fallback to project.progress field
        progress_value = latest_progress.get(p.id)
        if progress_value is None:
            progress_value = getattr(p, 'progress', 0)
            if progress_value is None:
                progress_value = 0
        
        projects_data.append({
            'id': p.id,
            'name': p.name,
            'latitude': float(p.latitude),
            'longitude': float(p.longitude),
            'barangay': p.barangay,
            'status': p.status,
            'description': p.description,
            'project_cost': str(p.project_cost) if p.project_cost is not None else "",
            'source_of_funds': p.source_of_funds,
            'prn': p.prn,
            'start_date': str(p.start_date) if p.start_date else "",
            'end_date': str(p.end_date) if p.end_date else "",
            'image': p.image.url if p.image else "",
            'progress': progress_value,
            'assigned_engineers': assigned_engineers,
        })
    return render(request, 'monitoring/map.html', {'projects_data': projects_data})

@login_required
@prevent_project_engineer_access
def reports(request):
    # This view is only accessible to Head Engineers and Finance Managers
    # Project Engineers are redirected by the decorator
    from projeng.models import ProjectCost
    from django.db.models import Q
    
    if is_head_engineer(request.user) or is_finance_manager(request.user):
        projects = Project.objects.all()
    else:
        projects = Project.objects.none()
    
    # Apply filters from request parameters
    barangay_filter = request.GET.get('barangay', '').strip()
    status_filter = request.GET.get('status', '').strip()
    start_date_filter = request.GET.get('start_date', '').strip()
    end_date_filter = request.GET.get('end_date', '').strip()
    
    # Filter by barangay
    if barangay_filter:
        projects = projects.filter(barangay=barangay_filter)
    
    # Filter by status
    if status_filter:
        # Handle "in_progress" to match both "in_progress" and "ongoing" statuses
        if status_filter == 'in_progress':
            projects = projects.filter(Q(status='in_progress') | Q(status='ongoing'))
        else:
            projects = projects.filter(status=status_filter)
    
    # Filter by start date
    if start_date_filter:
        try:
            from datetime import datetime
            start_date = datetime.strptime(start_date_filter, '%Y-%m-%d').date()
            projects = projects.filter(start_date__gte=start_date)
        except ValueError:
            pass
    
    # Filter by end date
    if end_date_filter:
        try:
            from datetime import datetime
            end_date = datetime.strptime(end_date_filter, '%Y-%m-%d').date()
            projects = projects.filter(end_date__lte=end_date)
        except ValueError:
            pass
    
    # Calculate budget metrics
    total_budget = 0
    total_spent = 0
    projects_with_budget = 0
    
    for p in projects:
        if p.project_cost:
            try:
                total_budget += float(p.project_cost)
                projects_with_budget += 1
            except (ValueError, TypeError):
                pass
    
    # Calculate total spent from ProjectCost
    project_ids = [p.id for p in projects]
    if project_ids:
        costs = ProjectCost.objects.filter(project_id__in=project_ids)
        for cost in costs:
            try:
                if cost.amount:
                    total_spent += float(cost.amount)
            except (ValueError, TypeError):
                pass
    
    remaining_budget = total_budget - total_spent
    budget_utilization = (total_spent / total_budget * 100) if total_budget > 0 else 0
    avg_project_cost = (total_budget / len(projects)) if len(projects) > 0 else 0
    
    # Prepare data for JS and summary cards
    projects_list = []
    status_map = defaultdict(int)
    barangay_map = defaultdict(int)
    for p in projects:
        projects_list.append({
            'id': p.id,
            'name': p.name,
            'prn': p.prn,
            'description': p.description,
            'barangay': p.barangay,
            'location': p.barangay,  # For compatibility
            'project_cost': str(p.project_cost) if p.project_cost is not None else '',
            'source_of_funds': p.source_of_funds,
            'start_date': str(p.start_date) if p.start_date else '',
            'end_date': str(p.end_date) if p.end_date else '',
            'status': p.status,
        })
        # For charts
        status = p.status
        if status in ['in_progress', 'ongoing']:
            status_map['Ongoing'] += 1
        elif status in ['planned', 'pending']:
            status_map['Planned'] += 1
        elif status == 'completed':
            status_map['Completed'] += 1
        elif status == 'delayed':
            status_map['Delayed'] += 1
        else:
            status_map[status.title()] += 1
        if p.barangay:
            barangay_map[p.barangay] += 1
    status_labels = list(status_map.keys())
    status_counts = list(status_map.values())
    barangay_labels = list(barangay_map.keys())
    barangay_counts = list(barangay_map.values())
    context = {
        'status_labels': json.dumps(status_labels),
        'status_counts': json.dumps(status_counts),
        'barangay_labels': json.dumps(barangay_labels),
        'barangay_counts': json.dumps(barangay_counts),
        'projects_json': projects_list,  # Pass list directly, let json_script handle encoding
        'total_budget': total_budget,
        'total_spent': total_spent,
        'remaining_budget': remaining_budget,
        'budget_utilization': budget_utilization,
        'avg_project_cost': avg_project_cost,
        'selected_barangay': barangay_filter,
        'selected_status': status_filter,
        'selected_start_date': start_date_filter,
        'selected_end_date': end_date_filter,
    }
    return render(request, 'monitoring/reports.html', context)

@login_required
@prevent_project_engineer_access
def budget_reports(request):
    
    from projeng.models import Project, ProjectCost
    from collections import defaultdict
    # Role-based queryset
    if is_head_engineer(request.user) or is_finance_manager(request.user):
        projects = Project.objects.all()
    elif is_project_engineer(request.user):
        projects = Project.objects.filter(assigned_engineers=request.user)
    else:
        projects = Project.objects.none()
    project_data = []
    project_names = []
    utilizations = []
    over_count = 0
    under_count = 0
    total_budget_sum = 0
    total_spent_sum = 0
    at_risk_count = 0
    for p in projects:
        # Calculate spent and utilization
        costs = ProjectCost.objects.filter(project=p)
        spent = sum([float(c.amount) for c in costs]) if costs else 0
        budget = float(p.project_cost) if p.project_cost else 0
        remaining = budget - spent
        utilization = (spent / budget * 100) if budget > 0 else 0
        over_under = 'Over' if spent > budget else 'Under'
        if over_under == 'Over':
            over_count += 1
        else:
            under_count += 1
        # Calculate summary totals
        total_budget_sum += budget
        total_spent_sum += spent
        if utilization > 90 and utilization <= 100:
            at_risk_count += 1
        # Cost breakdown by type
        cost_breakdown_map = defaultdict(float)
        for c in costs:
            cost_breakdown_map[c.get_cost_type_display()] += float(c.amount)
        cost_breakdown = [
            {'cost_type': k, 'total': v} for k, v in cost_breakdown_map.items()
        ]
        project_data.append({
            'id': p.id,
            'name': p.name,
            'prn': p.prn,
            'barangay': p.barangay,
            'project_cost': budget,
            'source_of_funds': p.source_of_funds,
            'status': p.status,
            'budget': budget,
            'spent': spent,
            'remaining': remaining,
            'utilization': utilization,
            'over_under': over_under,
            'cost_breakdown': cost_breakdown,
        })
        project_names.append(p.name)
        utilizations.append(utilization)
    context = {
        'project_data': project_data,
        'project_names': json.dumps(project_names),
        'utilizations': json.dumps(utilizations),
        'over_count': over_count,
        'under_count': under_count,
        'total_budget_sum': total_budget_sum,
        'total_spent_sum': total_spent_sum,
        'total_remaining_sum': total_budget_sum - total_spent_sum,
        'at_risk_count': at_risk_count,
    }
    return render(request, 'monitoring/budget_reports.html', context)

def project_update_api(request, pk):
    return HttpResponse("project_update_api placeholder")

@login_required
@head_engineer_required
def project_delete_api(request, pk):
    """Delete a project and notify all relevant users"""
    from django.db import transaction
    from django.http import JsonResponse, HttpResponseNotAllowed
    from projeng.models import Project as ProjEngProject
    from monitoring.models import Project as MonitoringProject
    from projeng.utils import notify_head_engineers, notify_admins, notify_finance_managers
    from django.contrib.auth.models import User
    
    if request.method != 'POST' and request.method != 'DELETE':
        return HttpResponseNotAllowed(['POST', 'DELETE'])
    
    try:
        with transaction.atomic():
            project_name = None
            project_prn = None
            assigned_engineers = []
            
            # Try to find the project in either model
            projeng_project = ProjEngProject.objects.filter(pk=pk).first()
            monitoring_project = MonitoringProject.objects.filter(pk=pk).first()
            
            if projeng_project:
                # Get project details before deletion
                project_name = projeng_project.name
                project_prn = projeng_project.prn
                assigned_engineers = list(projeng_project.assigned_engineers.all())
                
                # Delete the project (this will cascade to related objects)
                projeng_project.delete()
                
                # Also delete from monitoring if it exists
                if project_prn:
                    MonitoringProject.objects.filter(prn=project_prn).delete()
                else:
                    MonitoringProject.objects.filter(name=project_name).delete()
                    
            elif monitoring_project:
                # Get project details before deletion
                project_name = monitoring_project.name
                project_prn = monitoring_project.prn
                
                # Try to find corresponding projeng project to get assigned engineers
                if project_prn:
                    projeng_project = ProjEngProject.objects.filter(prn=project_prn).first()
                    if projeng_project:
                        assigned_engineers = list(projeng_project.assigned_engineers.all())
                        projeng_project.delete()
                
                # Delete from monitoring
                monitoring_project.delete()
            else:
                return JsonResponse({'success': False, 'error': 'Project not found'}, status=404)
            
            # Notify all relevant users about the deletion
            deleter_name = request.user.get_full_name() or request.user.username
            project_display = f"{project_name}" + (f" (PRN: {project_prn})" if project_prn else "")
            
            # Notify Head Engineers and Admins
            message = f"Project '{project_display}' has been deleted by {deleter_name}"
            notify_head_engineers(message)
            notify_admins(message)
            
            # Notify Finance Managers
            notify_finance_managers(message)
            
            # Notify assigned Project Engineers (with duplicate check)
            from projeng.models import Notification
            from django.utils import timezone
            from datetime import timedelta
            
            engineer_message = f"Project '{project_display}' that you were assigned to has been deleted by {deleter_name}"
            recent_time = timezone.now() - timedelta(seconds=10)
            
            from django.db.models import Q
            for engineer in assigned_engineers:
                # Check for duplicates before creating notification
                engineer_duplicate = Notification.objects.filter(
                    Q(recipient=engineer) &
                    Q(message__icontains=project_display) &
                    Q(message__icontains="that you were assigned to has been deleted") &
                    Q(created_at__gte=recent_time)
                ).exists()
                
                if not engineer_duplicate:
                    Notification.objects.create(
                        recipient=engineer,
                        message=engineer_message
                    )
            
            # Phase 3: Also broadcast via WebSocket (parallel to SSE)
            try:
                from projeng.channels_utils import broadcast_project_deleted
                broadcast_project_deleted(project_name, project_prn)
            except Exception as e:
                print(f"⚠️  WebSocket broadcast failed (SSE still works): {e}")
            
            return JsonResponse({
                'success': True,
                'message': f'Project "{project_name}" deleted successfully'
            })
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'An error occurred while deleting the project: {str(e)}'
        }, status=500)

@login_required
@prevent_project_engineer_access
def delayed_projects(request):
    """View for displaying delayed projects with filters"""
    from projeng.models import Project
    from django.core.paginator import Paginator
    from django.db.models import Q
    
    # Get delayed projects
    if is_head_engineer(request.user) or is_finance_manager(request.user):
        projects = Project.objects.filter(status='delayed')
    elif is_project_engineer(request.user):
        projects = Project.objects.filter(status='delayed', assigned_engineers=request.user)
    else:
        projects = Project.objects.none()
    
    # Apply filters
    barangay_filter = request.GET.get('barangay')
    search_query = request.GET.get('search', '').strip()
    sort_by = request.GET.get('sort', 'created_at')
    
    # Barangay filter
    if barangay_filter:
        projects = projects.filter(barangay=barangay_filter)
    
    # Search filter
    if search_query:
        projects = projects.filter(
            Q(name__icontains=search_query) |
            Q(prn__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(barangay__icontains=search_query)
        )
    
    # Sort
    if sort_by == 'name':
        projects = projects.order_by('name')
    elif sort_by == 'barangay':
        projects = projects.order_by('barangay')
    else:  # default to created_at
        projects = projects.order_by('-created_at')
    
    total_delayed = projects.count()
    
    # Pagination
    paginator = Paginator(projects, 20)  # Show 20 projects per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'monitoring/delayed_projects.html', {
        'page_obj': page_obj,
        'total_delayed': total_delayed,
    })

def project_engineer_analytics(request, pk):
    return HttpResponse("project_engineer_analytics placeholder")

@login_required
@head_engineer_required
def head_engineer_analytics(request):
    from projeng.models import Project, ProjectProgress
    from django.contrib.auth.models import User
    from django.core.paginator import Paginator
    import json
    # Get all projects
    projects = Project.objects.all()
    
    # Apply search filter
    search_query = request.GET.get('search', '').strip()
    if search_query:
        projects = projects.filter(name__icontains=search_query)
    
    # Apply barangay filter
    barangay_filter = request.GET.get('barangay', '')
    if barangay_filter:
        projects = projects.filter(barangay=barangay_filter)
    
    # Apply status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        # Handle "in_progress" to match both "in_progress" and "ongoing" statuses
        if status_filter == 'in_progress':
            projects = projects.filter(Q(status='in_progress') | Q(status='ongoing'))
        else:
            projects = projects.filter(status=status_filter)
    
    # Count totals (before filtering for pagination)
    total_projects_all = Project.objects.all().count()
    completed_projects = Project.objects.filter(status='completed').count()
    ongoing_projects = Project.objects.filter(status__in=['in_progress', 'ongoing']).count()
    planned_projects = Project.objects.filter(status__in=['planned', 'pending']).count()
    delayed_projects = Project.objects.filter(status='delayed').count()
    
    # Order by created_at descending
    projects = projects.order_by('-created_at')
    
    # Pagination - 15 items per page
    paginator = Paginator(projects, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get all project IDs for batch queries
    project_ids = [p.id for p in page_obj.object_list]
    
    # Batch fetch latest progress for all projects on this page
    from django.db.models import Max
    latest_progress_dict = {}
    if project_ids:
        # Get the latest progress update for each project
        for project_id in project_ids:
            latest = ProjectProgress.objects.filter(
                project_id=project_id
            ).order_by('-date', '-created_at').first()
            if latest:
                latest_progress_dict[project_id] = latest
    
    # Batch fetch assigned engineers for all projects
    from django.db.models import Prefetch
    projects_with_engineers = Project.objects.filter(
        id__in=project_ids
    ).prefetch_related('assigned_engineers')
    engineers_dict = {}
    for proj in projects_with_engineers:
        engineers_dict[proj.id] = [eng.username for eng in proj.assigned_engineers.all()]
    
    # Prepare project list for the table and JS (only for current page)
    projects_list = []
    for p in page_obj.object_list:
        # Get latest progress from batch query
        latest_progress = latest_progress_dict.get(p.id)
        
        # Calculate progress - priority: 1) completed status = 100%, 2) latest progress update, 3) project.progress field, 4) 0
        if p.status == 'completed':
            progress = 100
        elif latest_progress and latest_progress.percentage_complete is not None:
            # Ensure progress is between 0 and 100
            try:
                progress = max(0, min(100, int(latest_progress.percentage_complete)))
            except (ValueError, TypeError):
                progress = 0
        elif hasattr(p, 'progress') and p.progress is not None:
            # Fallback to project's direct progress field
            try:
                progress = max(0, min(100, int(p.progress)))
            except (ValueError, TypeError):
                progress = 0
        else:
            progress = 0
        
        # Status display
        status_display = (
            'Ongoing' if p.status in ['in_progress', 'ongoing'] else
            'Planned' if p.status in ['planned', 'pending'] else
            'Completed' if p.status == 'completed' else
            'Delayed' if p.status == 'delayed' else p.status.title()
        )
        
        # Assigned engineers from batch query
        assigned_to = engineers_dict.get(p.id, [])
        
        projects_list.append({
            'id': p.id,
            'name': p.name,
            'prn': p.prn or '',
            'barangay': p.barangay or '',
            'total_progress': progress,
            'status': p.status,
            'status_display': status_display,
            'start_date': str(p.start_date) if p.start_date else '',
            'end_date': str(p.end_date) if p.end_date else '',
            'assigned_to': assigned_to,
        })
    context = {
        'projects': projects_list,  # for Django template rendering
        'projects_json': json.dumps(projects_list),  # for JS
        'page_obj': page_obj,  # for pagination
        'total_projects': total_projects_all,
        'completed_projects': completed_projects,
        'ongoing_projects': ongoing_projects,
        'planned_projects': planned_projects,
        'delayed_projects': delayed_projects,
        'user_role': 'head_engineer',
        'search_query': search_query,
        'barangay_filter': barangay_filter,
        'status_filter': status_filter,
    }
    return render(request, 'monitoring/analytics.html', context)

def project_detail(request, pk):
    return HttpResponse("project_detail placeholder")

@login_required
@head_engineer_required
def head_engineer_project_detail(request, pk):
    import logging
    import json
    from projeng.models import Project, ProjectProgress, ProjectCost, Notification
    from django.contrib.auth.models import User
    from projeng.utils import get_project_from_notification
    from django.http import HttpResponse
    
    logger = logging.getLogger(__name__)
    
    try:
        project = Project.objects.get(pk=pk)
    except Project.DoesNotExist:
        return HttpResponse('Project not found.', status=404)
    except Exception as e:
        logger.error(f"Error fetching project {pk}: {e}")
        return HttpResponse(f'Error loading project: {str(e)}', status=500)
    
    try:
        # Auto-mark notifications as read for this project
        # Get all unread notifications for the user
        unread_notifications = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        )
        
        # Mark notifications related to this project as read
        for notification in unread_notifications:
            try:
                if notification.message:
                    project_id = get_project_from_notification(notification.message)
                    if project_id == project.id:
                        notification.is_read = True
                        notification.save()
            except Exception as e:
                # Log error but continue processing
                logger.warning(f"Error processing notification {notification.id}: {e}")
                continue
        
        # Get all progress updates - order by date and id to avoid duplicates and ensure consistent ordering
        progress_updates = ProjectProgress.objects.filter(project=project).order_by('date', 'id').distinct()
        assigned_to = list(project.assigned_engineers.values_list('username', flat=True))
        # Get all cost entries with created_by prefetched
        costs = ProjectCost.objects.filter(project=project).select_related('created_by').order_by('date')
        # Analytics & summary
        latest_progress = progress_updates.last() if progress_updates else None
        
        # Calculate total cost safely
        total_cost = 0
        try:
            if costs:
                for c in costs:
                    try:
                        total_cost += float(c.amount) if c.amount else 0
                    except (ValueError, TypeError):
                        continue
        except Exception as e:
            logger.warning(f"Error calculating total cost: {e}")
            total_cost = 0
        
        # Calculate budget utilization safely
        try:
            if project.project_cost:
                project_cost_float = float(project.project_cost)
                if project_cost_float > 0:
                    budget_utilization = (total_cost / project_cost_float) * 100
                else:
                    budget_utilization = 0
            else:
                budget_utilization = 0
        except (ValueError, TypeError) as e:
            logger.warning(f"Error calculating budget utilization: {e}")
            budget_utilization = 0
        
        timeline_data = {
            'start_date': project.start_date,
            'end_date': project.end_date,
            'days_elapsed': (project.end_date - project.start_date).days if project.start_date and project.end_date else None,
            'total_days': (project.end_date - project.start_date).days if project.start_date and project.end_date else None,
        }
        
        context = {
            'project': project,
            'projeng_project': project,  # Pass project as projeng_project for template compatibility
            'progress_updates': progress_updates,
            'assigned_to': assigned_to,
            'costs': costs,
            'latest_progress': latest_progress,
            'total_cost': total_cost,
            'budget_utilization': budget_utilization,
            'timeline_data': timeline_data,
        }
        
        return render(request, 'monitoring/head_engineer_project_detail.html', context)
    
    except Exception as e:
        logger.error(f"Error in head_engineer_project_detail for project {pk}: {e}", exc_info=True)
        return HttpResponse(f'Server error: {str(e)}', status=500)

@login_required
@head_engineer_required
def head_dashboard_card_data_api(request):
    return HttpResponse("head_dashboard_card_data_api placeholder")

def barangay_geojson_view(request):
    geojson_path = os.path.join(settings.BASE_DIR, 'static', 'data', 'tagum_barangays.geojson')
    with open(geojson_path, 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)
    return JsonResponse(geojson_data, safe=False)

def export_project_timeline_pdf(request, pk):
    """Export project timeline as PDF"""
    from projeng.models import Project as ProjEngProject, ProjectProgress as ProjEngProjectProgress
    try:
        # Try to get project from projeng first (since head_engineer_project_detail uses projeng Project)
        try:
            project = ProjEngProject.objects.get(pk=pk)
            projeng_project = project
        except ProjEngProject.DoesNotExist:
            # Fallback to monitoring project
            project = Project.objects.get(pk=pk)
            projeng_project = None
            if project.prn:
                try:
                    projeng_project = ProjEngProject.objects.get(prn=project.prn)
                except ProjEngProject.DoesNotExist:
                    pass
    except Project.DoesNotExist:
        return HttpResponse('Project not found.', status=404)
    
    # Get all progress updates - order by date and id to avoid duplicates
    if projeng_project:
        progress_updates = ProjEngProjectProgress.objects.filter(project=projeng_project).order_by('date', 'id').distinct()
    else:
        progress_updates = []
    
    # Get costs - try from projeng project first, then monitoring project
    if projeng_project:
        costs = ProjectCost.objects.filter(project=projeng_project).order_by('date')
    else:
        costs = ProjectCost.objects.filter(project=project).order_by('date') if hasattr(project, 'projectcost_set') else []
    
    # If xhtml2pdf is unavailable, return a friendly message
    if pisa is None:
        return HttpResponse('PDF export is temporarily unavailable (missing xhtml2pdf/reportlab).', content_type='text/plain')
    
    # Render the HTML template for the PDF
    template_path = 'monitoring/project_timeline_pdf.html'
    template = get_template(template_path)
    context = {
        'project': project,
        'projeng_project': projeng_project,
        'progress_updates': progress_updates,
        'costs': costs,
        'total_cost': sum([float(c.amount) for c in costs]) if costs else 0,
    }
    html = template.render(context)
    
    # Create a PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="project_{project.id}_timeline_{timezone.now().strftime("%Y%m%d")}.pdf"'
    
    # Create a file-like object to write the PDF data to
    buffer = io.BytesIO()
    
    # Create the PDF object, and write the HTML to it
    pisa_status = pisa.CreatePDF(html, dest=buffer)
    
    # If there were no errors, return the PDF file
    if not pisa_status.err:
        return HttpResponse(buffer.getvalue(), content_type='application/pdf')
    
    # If there were errors, return an error message
    return HttpResponse('We had some errors generating the PDF.', content_type='text/plain')

@login_required
def export_reports_csv(request):
    """Export monitoring reports as CSV"""
    from django.db.models import Q
    
    # Role-based queryset
    if is_head_engineer(request.user) or is_finance_manager(request.user):
        projects = Project.objects.all()
    elif is_project_engineer(request.user):
        projects = Project.objects.filter(assigned_engineers=request.user)
    else:
        projects = Project.objects.none()
    
    # Apply filters from request parameters
    barangay_filter = request.GET.get('barangay', '').strip()
    status_filter = request.GET.get('status', '').strip()
    start_date_filter = request.GET.get('start_date', '').strip()
    end_date_filter = request.GET.get('end_date', '').strip()
    
    # Filter by barangay
    if barangay_filter:
        projects = projects.filter(barangay=barangay_filter)
    
    # Filter by status
    if status_filter:
        # Handle "in_progress" to match both "in_progress" and "ongoing" statuses
        if status_filter == 'in_progress':
            projects = projects.filter(Q(status='in_progress') | Q(status='ongoing'))
        else:
            projects = projects.filter(status=status_filter)
    
    # Filter by start date
    if start_date_filter:
        try:
            from datetime import datetime
            start_date = datetime.strptime(start_date_filter, '%Y-%m-%d').date()
            projects = projects.filter(start_date__gte=start_date)
        except (ValueError, TypeError):
            pass  # Invalid date format, ignore filter
    
    # Filter by end date
    if end_date_filter:
        try:
            from datetime import datetime
            end_date = datetime.strptime(end_date_filter, '%Y-%m-%d').date()
            projects = projects.filter(end_date__lte=end_date)
        except (ValueError, TypeError):
            pass  # Invalid date format, ignore filter
    
    # Create the HttpResponse object with the appropriate CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="projects_report_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    # Write the header row
    writer.writerow(['#', 'PRN#', 'Name of Project', 'Project Description', 'Barangay', 'Project Cost', 'Source of Funds', 'Date Started', 'Date Ended', 'Status'])
    
    # Write data rows
    for i, project in enumerate(projects):
        writer.writerow([
            i + 1,
            project.prn or '',
            project.name or '',
            project.description or '',
            project.barangay or '',
            project.project_cost if project.project_cost is not None else '',
            project.source_of_funds or '',
            project.start_date.strftime('%Y-%m-%d') if project.start_date else '',
            project.end_date.strftime('%Y-%m-%d') if project.end_date else '',
            project.get_status_display() or '',
        ])
    
    return response

@login_required
def export_reports_excel(request):
    """Export monitoring reports as Excel"""
    from django.db.models import Q
    
    # Role-based queryset
    if is_head_engineer(request.user) or is_finance_manager(request.user):
        projects = Project.objects.all()
    elif is_project_engineer(request.user):
        projects = Project.objects.filter(assigned_engineers=request.user)
    else:
        projects = Project.objects.none()
    
    # Apply filters from request parameters
    barangay_filter = request.GET.get('barangay', '').strip()
    status_filter = request.GET.get('status', '').strip()
    start_date_filter = request.GET.get('start_date', '').strip()
    end_date_filter = request.GET.get('end_date', '').strip()
    
    # Filter by barangay
    if barangay_filter:
        projects = projects.filter(barangay=barangay_filter)
    
    # Filter by status
    if status_filter:
        # Handle "in_progress" to match both "in_progress" and "ongoing" statuses
        if status_filter == 'in_progress':
            projects = projects.filter(Q(status='in_progress') | Q(status='ongoing'))
        else:
            projects = projects.filter(status=status_filter)
    
    # Filter by start date
    if start_date_filter:
        try:
            from datetime import datetime
            start_date = datetime.strptime(start_date_filter, '%Y-%m-%d').date()
            projects = projects.filter(start_date__gte=start_date)
        except (ValueError, TypeError):
            pass  # Invalid date format, ignore filter
    
    # Filter by end date
    if end_date_filter:
        try:
            from datetime import datetime
            end_date = datetime.strptime(end_date_filter, '%Y-%m-%d').date()
            projects = projects.filter(end_date__lte=end_date)
        except (ValueError, TypeError):
            pass  # Invalid date format, ignore filter
    
    # Create a new workbook and select the active sheet
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Projects Report"
    
    # Write the header row
    headers = ['#', 'PRN#', 'Name of Project', 'Project Description', 'Barangay', 'Project Cost', 'Source of Funds', 'Date Started', 'Date Ended', 'Status']
    sheet.append(headers)
    
    # Write data rows
    for i, project in enumerate(projects):
        sheet.append([
            i + 1,
            project.prn or '',
            project.name or '',
            project.description or '',
            project.barangay or '',
            project.project_cost if project.project_cost is not None else '',
            project.source_of_funds or '',
            project.start_date.strftime('%Y-%m-%d') if project.start_date else '',
            project.end_date.strftime('%Y-%m-%d') if project.end_date else '',
            project.get_status_display() or '',
        ])
    
    # Create an in-memory BytesIO stream
    excel_file = io.BytesIO()
    workbook.save(excel_file)
    excel_file.seek(0)
    
    # Create the HttpResponse object with the appropriate Excel header
    response = HttpResponse(excel_file.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="projects_report_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    
    return response

@login_required
def export_reports_pdf(request):
    """Export monitoring reports as PDF"""
    from collections import defaultdict
    from django.db.models import Q
    
    # Role-based queryset
    if is_head_engineer(request.user) or is_finance_manager(request.user):
        projects = Project.objects.all()
    elif is_project_engineer(request.user):
        projects = Project.objects.filter(assigned_engineers=request.user)
    else:
        projects = Project.objects.none()
    
    # Apply filters from request parameters
    barangay_filter = request.GET.get('barangay', '').strip()
    status_filter = request.GET.get('status', '').strip()
    start_date_filter = request.GET.get('start_date', '').strip()
    end_date_filter = request.GET.get('end_date', '').strip()
    
    # Filter by barangay
    if barangay_filter:
        projects = projects.filter(barangay=barangay_filter)
    
    # Filter by status
    if status_filter:
        # Handle "in_progress" to match both "in_progress" and "ongoing" statuses
        if status_filter == 'in_progress':
            projects = projects.filter(Q(status='in_progress') | Q(status='ongoing'))
        else:
            projects = projects.filter(status=status_filter)
    
    # Filter by start date
    if start_date_filter:
        try:
            from datetime import datetime
            start_date = datetime.strptime(start_date_filter, '%Y-%m-%d').date()
            projects = projects.filter(start_date__gte=start_date)
        except (ValueError, TypeError):
            pass  # Invalid date format, ignore filter
    
    # Filter by end date
    if end_date_filter:
        try:
            from datetime import datetime
            end_date = datetime.strptime(end_date_filter, '%Y-%m-%d').date()
            projects = projects.filter(end_date__lte=end_date)
        except (ValueError, TypeError):
            pass  # Invalid date format, ignore filter
    
    # Calculate summary statistics
    total_projects = projects.count()
    status_map = defaultdict(int)
    barangay_map = defaultdict(int)
    total_budget = 0
    
    for p in projects:
        # Status counts
        status = p.status
        if status in ['in_progress', 'ongoing']:
            status_map['Ongoing'] += 1
        elif status in ['planned', 'pending']:
            status_map['Planned'] += 1
        elif status == 'completed':
            status_map['Completed'] += 1
        elif status == 'delayed':
            status_map['Delayed'] += 1
        else:
            status_map[status.title()] += 1
        
        # Barangay counts
        if p.barangay:
            barangay_map[p.barangay] += 1
        
        # Budget totals
        if p.project_cost:
            total_budget += float(p.project_cost)
    
    completed_count = status_map.get('Completed', 0)
    ongoing_count = status_map.get('Ongoing', 0)
    planned_count = status_map.get('Planned', 0)
    delayed_count = status_map.get('Delayed', 0)
    
    # Get top barangay
    top_barangay = None
    top_barangay_count = 0
    if barangay_map:
        top_barangay = max(barangay_map.items(), key=lambda x: x[1])
        top_barangay_name = top_barangay[0]
        top_barangay_count = top_barangay[1]
    else:
        top_barangay_name = "N/A"
    
    # If xhtml2pdf is unavailable, return a friendly message
    if pisa is None:
        return HttpResponse('PDF export is temporarily unavailable (missing xhtml2pdf/reportlab).', content_type='text/plain')
    
    # Render the HTML template for the PDF
    template_path = 'monitoring/reports_pdf.html'
    template = get_template(template_path)
    context = {
        'projects': projects,
        'total_projects': total_projects,
        'completed_count': completed_count,
        'ongoing_count': ongoing_count,
        'planned_count': planned_count,
        'delayed_count': delayed_count,
        'total_budget': total_budget,
        'status_map': dict(status_map),
        'barangay_map': dict(barangay_map),
        'top_barangay_name': top_barangay_name,
        'top_barangay_count': top_barangay_count,
        'generated_by': request.user.get_full_name() or request.user.username,
        'generated_at': timezone.now(),
    }
    html = template.render(context)
    
    # Create a PDF
    response = HttpResponse(content_type='application/pdf')
    # Use 'inline' to display in browser, 'attachment' to force download
    response['Content-Disposition'] = f'inline; filename="projects_report_{timezone.now().strftime("%Y%m%d")}.pdf"'
    
    # Create a file-like object to write the PDF data to
    buffer = io.BytesIO()
    
    # Create the PDF object, and write the HTML to it
    pisa_status = pisa.CreatePDF(html, dest=buffer)
    
    # If there were no errors, return the PDF file
    if not pisa_status.err:
        return HttpResponse(buffer.getvalue(), content_type='application/pdf')
    
    # If there were errors, return an error message
    return HttpResponse('We had some errors generating the PDF.', content_type='text/plain')

@login_required
def export_budget_reports_csv(request):
    """Export budget reports as CSV"""
    from projeng.models import ProjectCost
    from collections import defaultdict
    
    # Role-based queryset
    if is_head_engineer(request.user) or is_finance_manager(request.user):
        projects = Project.objects.all()
    elif is_project_engineer(request.user):
        projects = Project.objects.filter(assigned_engineers=request.user)
    else:
        projects = Project.objects.none()
    
    # Create the HttpResponse object with the appropriate CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="budget_report_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    # Write the header row
    writer.writerow(['#', 'PRN#', 'Project Name', 'Barangay', 'Budget', 'Spent', 'Remaining', 'Utilization %', 'Status', 'Over/Under Budget'])
    
    # Write data rows
    for i, project in enumerate(projects):
        costs = ProjectCost.objects.filter(project=project)
        spent = sum([float(c.amount) for c in costs]) if costs else 0
        budget = float(project.project_cost) if project.project_cost else 0
        remaining = budget - spent
        utilization = (spent / budget * 100) if budget > 0 else 0
        over_under = 'Over' if spent > budget else 'Under'
        
        writer.writerow([
            i + 1,
            project.prn or '',
            project.name or '',
            project.barangay or '',
            budget,
            spent,
            remaining,
            f'{utilization:.2f}%',
            project.get_status_display() or '',
            over_under,
        ])
    
    return response

@login_required
def export_budget_reports_excel(request):
    """Export budget reports as Excel"""
    from projeng.models import ProjectCost
    
    # Role-based queryset
    if is_head_engineer(request.user) or is_finance_manager(request.user):
        projects = Project.objects.all()
    elif is_project_engineer(request.user):
        projects = Project.objects.filter(assigned_engineers=request.user)
    else:
        projects = Project.objects.none()
    
    # Create a new workbook and select the active sheet
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Budget Report"
    
    # Write the header row
    headers = ['#', 'PRN#', 'Project Name', 'Barangay', 'Budget', 'Spent', 'Remaining', 'Utilization %', 'Status', 'Over/Under Budget']
    sheet.append(headers)
    
    # Write data rows
    for i, project in enumerate(projects):
        costs = ProjectCost.objects.filter(project=project)
        spent = sum([float(c.amount) for c in costs]) if costs else 0
        budget = float(project.project_cost) if project.project_cost else 0
        remaining = budget - spent
        utilization = (spent / budget * 100) if budget > 0 else 0
        over_under = 'Over' if spent > budget else 'Under'
        
        sheet.append([
            i + 1,
            project.prn or '',
            project.name or '',
            project.barangay or '',
            budget,
            spent,
            remaining,
            f'{utilization:.2f}%',
            project.get_status_display() or '',
            over_under,
        ])
    
    # Create an in-memory BytesIO stream
    excel_file = io.BytesIO()
    workbook.save(excel_file)
    excel_file.seek(0)
    
    # Create the HttpResponse object with the appropriate Excel header
    response = HttpResponse(excel_file.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="budget_report_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    
    return response

@login_required
def export_budget_reports_pdf(request):
    """Export budget reports as PDF"""
    from projeng.models import ProjectCost
    from collections import defaultdict
    
    # Role-based queryset
    if is_head_engineer(request.user) or is_finance_manager(request.user):
        projects = Project.objects.all()
    elif is_project_engineer(request.user):
        projects = Project.objects.filter(assigned_engineers=request.user)
    else:
        projects = Project.objects.none()
    
    # Prepare project data
    project_data = []
    for project in projects:
        costs = ProjectCost.objects.filter(project=project)
        spent = sum([float(c.amount) for c in costs]) if costs else 0
        budget = float(project.project_cost) if project.project_cost else 0
        remaining = budget - spent
        utilization = (spent / budget * 100) if budget > 0 else 0
        over_under = 'Over' if spent > budget else 'Under'
        
        project_data.append({
            'project': project,
            'budget': budget,
            'spent': spent,
            'remaining': remaining,
            'utilization': utilization,
            'over_under': over_under,
        })
    
    # If xhtml2pdf is unavailable, return a friendly message
    if pisa is None:
        return HttpResponse('PDF export is temporarily unavailable (missing xhtml2pdf/reportlab).', content_type='text/plain')
    
    # Render the HTML template for the PDF
    template_path = 'monitoring/budget_reports_pdf.html'
    template = get_template(template_path)
    context = {'project_data': project_data}
    html = template.render(context)
    
    # Create a PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="budget_report_{timezone.now().strftime("%Y%m%d")}.pdf"'
    
    # Create a file-like object to write the PDF data to
    buffer = io.BytesIO()
    
    # Create the PDF object, and write the HTML to it
    pisa_status = pisa.CreatePDF(html, dest=buffer)
    
    # If there were no errors, return the PDF file
    if not pisa_status.err:
        return HttpResponse(buffer.getvalue(), content_type='application/pdf')
    
    # If there were errors, return an error message
    return HttpResponse('We had some errors generating the PDF.', content_type='text/plain')

@login_required
@head_engineer_required
def head_engineer_notifications(request):
    """View for Head Engineers to manage their notifications"""
    from projeng.models import Notification
    from django.contrib import messages
    from django.shortcuts import redirect
    from django.http import JsonResponse
    from django.core.paginator import Paginator
    from django.db.models import Q
    
    # Get all notifications for the user
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')

    if request.method == 'POST':
        action = request.POST.get('action')
        notification_id = request.POST.get('notification_id')

        if action == 'mark_read' and notification_id:
            try:
                notification = Notification.objects.get(id=notification_id, recipient=request.user)
                notification.is_read = True
                notification.save()
                return JsonResponse({'success': True, 'message': 'Notification marked as read'})
            except Notification.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Notification not found'})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})

        elif action == 'mark_all_read':
            try:
                updated_count = notifications.filter(is_read=False).update(is_read=True)
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': f'{updated_count} notifications marked as read'})
                messages.success(request, f"All {updated_count} notifications marked as read.")
                return redirect('head_engineer_notifications')
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)})
                messages.error(request, f"Error marking notifications as read: {str(e)}")
                return redirect('head_engineer_notifications')

        elif action == 'delete' and notification_id:
            try:
                notification = Notification.objects.get(id=notification_id, recipient=request.user)
                notification.delete()
                return JsonResponse({'success': True, 'message': 'Notification deleted'})
            except Notification.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Notification not found'})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})

        elif action == 'delete_all':
            try:
                deleted_count = notifications.delete()[0]
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': f'{deleted_count} notifications deleted'})
                messages.success(request, f"All {deleted_count} notifications deleted.")
                return redirect('head_engineer_notifications')
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)})
                messages.error(request, f"Error deleting notifications: {str(e)}")
                return redirect('head_engineer_notifications')

    # Pagination for large number of notifications
    paginator = Paginator(notifications, 50)  # Show 50 notifications per page
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.get_page(page_number)
    except:
        page_obj = paginator.get_page(1)

    unread_count = notifications.filter(is_read=False).count()
    
    # Add project IDs to notifications for clickable links
    from projeng.utils import get_project_from_notification
    notifications_with_projects = []
    for notification in page_obj:
        project_id = None
        try:
            if notification.message:
                project_id = get_project_from_notification(notification.message)
        except Exception as e:
            # Log error but don't break the page
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting project from notification {notification.id}: {str(e)}")
        notifications_with_projects.append({
            'notification': notification,
            'project_id': project_id
        })

    context = {
        'notifications': page_obj,  # Use paginated notifications
        'notifications_with_projects': notifications_with_projects,  # Notifications with project IDs
        'unread_count': unread_count,
        'page_obj': page_obj,  # For pagination controls
    }
    return render(request, 'monitoring/notifications.html', context)

@login_required
@head_engineer_required
def export_project_comprehensive_pdf(request, pk):
    """Export comprehensive project report (Progress + Budget) as PDF"""
    from projeng.models import Project, ProjectProgress, ProjectCost
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        project = Project.objects.get(pk=pk)
    except Project.DoesNotExist:
        return HttpResponse('Project not found.', status=404)
    
    # Get all progress updates
    progress_updates = ProjectProgress.objects.filter(project=project).order_by('date', 'id').distinct()
    
    # Get all cost entries
    costs = ProjectCost.objects.filter(project=project).order_by('date')
    
    # Calculate analytics
    latest_progress = progress_updates.last() if progress_updates else None
    total_progress = latest_progress.percentage_complete if latest_progress else 0
    total_cost = sum([float(c.amount) for c in costs]) if costs else 0
    budget = float(project.project_cost) if project.project_cost else 0
    remaining_budget = budget - total_cost
    budget_utilization = (total_cost / budget * 100) if budget > 0 else 0
    
    # Calculate timeline
    today = timezone.now().date()
    days_elapsed = (today - project.start_date).days if project.start_date else 0
    total_days = (project.end_date - project.start_date).days if project.start_date and project.end_date else 0
    days_remaining = total_days - days_elapsed if total_days > 0 else 0
    
    # Cost breakdown by category
    from collections import defaultdict
    cost_breakdown = defaultdict(float)
    for cost in costs:
        cost_breakdown[cost.get_cost_type_display()] += float(cost.amount)
    
    # Assigned engineers
    assigned_engineers = project.assigned_engineers.all()
    
    # If xhtml2pdf is unavailable, return a friendly message
    if pisa is None:
        return HttpResponse('PDF export is temporarily unavailable (missing xhtml2pdf/reportlab).', content_type='text/plain')
    
    # Render the HTML template for the PDF
    template_path = 'monitoring/project_comprehensive_report_pdf.html'
    template = get_template(template_path)
    context = {
        'project': project,
        'progress_updates': progress_updates,
        'costs': costs,
        'latest_progress': latest_progress,
        'total_progress': total_progress,
        'total_cost': total_cost,
        'budget': budget,
        'remaining_budget': remaining_budget,
        'budget_utilization': budget_utilization,
        'days_elapsed': days_elapsed,
        'total_days': total_days,
        'days_remaining': days_remaining,
        'cost_breakdown': dict(cost_breakdown),
        'assigned_engineers': assigned_engineers,
        'generated_by': request.user.get_full_name() or request.user.username,
        'generated_at': timezone.now(),
    }
    html = template.render(context)
    
    # Create PDF
    result = io.BytesIO()
    pdf = pisa.CreatePDF(io.BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        filename = f"project_report_{project.prn or project.id}_{timezone.now().strftime('%Y%m%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    return HttpResponse('Error generating PDF', content_type='text/plain')

@login_required
@head_engineer_required
def export_project_comprehensive_excel(request, pk):
    """Export comprehensive project report (Progress + Budget) as Excel"""
    from projeng.models import Project, ProjectProgress, ProjectCost
    from django.utils import timezone
    from collections import defaultdict
    
    try:
        project = Project.objects.get(pk=pk)
    except Project.DoesNotExist:
        return HttpResponse('Project not found.', status=404)
    
    # Get all progress updates
    progress_updates = ProjectProgress.objects.filter(project=project).order_by('date', 'id').distinct()
    
    # Get all cost entries
    costs = ProjectCost.objects.filter(project=project).order_by('date')
    
    # Calculate analytics
    latest_progress = progress_updates.last() if progress_updates else None
    total_progress = latest_progress.percentage_complete if latest_progress else 0
    total_cost = sum([float(c.amount) for c in costs]) if costs else 0
    budget = float(project.project_cost) if project.project_cost else 0
    remaining_budget = budget - total_cost
    budget_utilization = (total_cost / budget * 100) if budget > 0 else 0
    
    # Create Excel workbook
    wb = openpyxl.Workbook()
    
    # Sheet 1: Project Overview
    ws1 = wb.active
    ws1.title = "Project Overview"
    ws1.append(['PROJECT COMPREHENSIVE REPORT'])
    ws1.append(['Project Name', project.name])
    ws1.append(['PRN Number', project.prn or 'N/A'])
    ws1.append(['Location', project.barangay or 'N/A'])
    ws1.append(['Status', project.get_status_display()])
    ws1.append(['Start Date', str(project.start_date) if project.start_date else 'N/A'])
    ws1.append(['End Date', str(project.end_date) if project.end_date else 'N/A'])
    ws1.append(['Assigned Engineers', ', '.join([e.get_full_name() or e.username for e in project.assigned_engineers.all()])])
    ws1.append([])
    ws1.append(['PROGRESS SUMMARY'])
    ws1.append(['Overall Progress', f'{total_progress}%'])
    ws1.append(['BUDGET SUMMARY'])
    ws1.append(['Total Budget', f'₱{budget:,.2f}'])
    ws1.append(['Total Spent', f'₱{total_cost:,.2f}'])
    ws1.append(['Remaining', f'₱{remaining_budget:,.2f}'])
    ws1.append(['Utilization', f'{budget_utilization:.2f}%'])
    
    # Sheet 2: Progress Details
    ws2 = wb.create_sheet("Progress Details")
    ws2.append(['Date', 'Progress %', 'Description', 'Engineer'])
    for update in progress_updates:
        engineer_name = update.created_by.get_full_name() or update.created_by.username if update.created_by else 'N/A'
        ws2.append([
            str(update.date),
            update.percentage_complete,
            update.description or '',
            engineer_name
        ])
    
    # Sheet 3: Budget Details
    ws3 = wb.create_sheet("Budget Details")
    ws3.append(['Date', 'Category', 'Description', 'Amount'])
    for cost in costs:
        ws3.append([
            str(cost.date),
            cost.get_cost_type_display(),
            cost.description or '',
            float(cost.amount)
        ])
    ws3.append([])
    ws3.append(['TOTAL', '', '', f'₱{total_cost:,.2f}'])
    
    # Sheet 4: Cost Breakdown
    ws4 = wb.create_sheet("Cost Breakdown")
    cost_breakdown = defaultdict(float)
    for cost in costs:
        cost_breakdown[cost.get_cost_type_display()] += float(cost.amount)
    ws4.append(['Category', 'Amount'])
    for category, amount in cost_breakdown.items():
        ws4.append([category, f'₱{amount:,.2f}'])
    ws4.append(['TOTAL', f'₱{total_cost:,.2f}'])
    
    # Sheet 5: Progress vs Budget
    ws5 = wb.create_sheet("Progress vs Budget")
    ws5.append(['Date', 'Progress %', 'Budget Used %', 'Efficiency Ratio'])
    for update in progress_updates:
        # Calculate budget used up to this date
        costs_up_to_date = ProjectCost.objects.filter(project=project, date__lte=update.date)
        budget_used = sum([float(c.amount) for c in costs_up_to_date]) if costs_up_to_date else 0
        budget_used_pct = (budget_used / budget * 100) if budget > 0 else 0
        efficiency = (update.percentage_complete / budget_used_pct) if budget_used_pct > 0 else 0
        ws5.append([
            str(update.date),
            update.percentage_complete,
            f'{budget_used_pct:.2f}%',
            f'{efficiency:.2f}'
        ])
    
    # Save to response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"project_report_{project.prn or project.id}_{timezone.now().strftime('%Y%m%d')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response

@login_required
@head_engineer_required
def export_project_comprehensive_csv(request, pk):
    """Export comprehensive project report (Progress + Budget) as CSV"""
    from projeng.models import Project, ProjectProgress, ProjectCost
    from django.utils import timezone
    
    try:
        project = Project.objects.get(pk=pk)
    except Project.DoesNotExist:
        return HttpResponse('Project not found.', status=404)
    
    # Get all progress updates
    progress_updates = ProjectProgress.objects.filter(project=project).order_by('date', 'id').distinct()
    
    # Get all cost entries
    costs = ProjectCost.objects.filter(project=project).order_by('date')
    
    # Calculate analytics
    latest_progress = progress_updates.last() if progress_updates else None
    total_progress = latest_progress.percentage_complete if latest_progress else 0
    total_cost = sum([float(c.amount) for c in costs]) if costs else 0
    budget = float(project.project_cost) if project.project_cost else 0
    remaining_budget = budget - total_cost
    budget_utilization = (total_cost / budget * 100) if budget > 0 else 0
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    filename = f"project_report_{project.prn or project.id}_{timezone.now().strftime('%Y%m%d')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    
    # Project Information
    writer.writerow(['PROJECT COMPREHENSIVE REPORT'])
    writer.writerow(['Project Name', project.name])
    writer.writerow(['PRN Number', project.prn or 'N/A'])
    writer.writerow(['Location', project.barangay or 'N/A'])
    writer.writerow(['Status', project.get_status_display()])
    writer.writerow(['Start Date', str(project.start_date) if project.start_date else 'N/A'])
    writer.writerow(['End Date', str(project.end_date) if project.end_date else 'N/A'])
    writer.writerow([])
    
    # Progress Summary
    writer.writerow(['PROGRESS SUMMARY'])
    writer.writerow(['Overall Progress', f'{total_progress}%'])
    writer.writerow([])
    
    # Budget Summary
    writer.writerow(['BUDGET SUMMARY'])
    writer.writerow(['Total Budget', f'₱{budget:,.2f}'])
    writer.writerow(['Total Spent', f'₱{total_cost:,.2f}'])
    writer.writerow(['Remaining', f'₱{remaining_budget:,.2f}'])
    writer.writerow(['Utilization', f'{budget_utilization:.2f}%'])
    writer.writerow([])
    
    # Progress Details
    writer.writerow(['PROGRESS DETAILS'])
    writer.writerow(['Date', 'Progress %', 'Description', 'Engineer'])
    for update in progress_updates:
        engineer_name = update.created_by.get_full_name() or update.created_by.username if update.created_by else 'N/A'
        writer.writerow([
            str(update.date),
            update.percentage_complete,
            update.description or '',
            engineer_name
        ])
    writer.writerow([])
    
    # Budget Details
    writer.writerow(['BUDGET DETAILS'])
    writer.writerow(['Date', 'Category', 'Description', 'Amount'])
    for cost in costs:
        writer.writerow([
            str(cost.date),
            cost.get_cost_type_display(),
            cost.description or '',
            float(cost.amount)
        ])
    writer.writerow([])
    writer.writerow(['TOTAL', '', '', f'₱{total_cost:,.2f}'])
    
    return response

    writer.writerow(['Remaining', f'₱{remaining_budget:,.2f}'])
    writer.writerow(['Utilization', f'{budget_utilization:.2f}%'])
    writer.writerow([])
    
    # Progress Details
    writer.writerow(['PROGRESS DETAILS'])
    writer.writerow(['Date', 'Progress %', 'Description', 'Engineer'])
    for update in progress_updates:
        engineer_name = update.created_by.get_full_name() or update.created_by.username if update.created_by else 'N/A'
        writer.writerow([
            str(update.date),
            update.percentage_complete,
            update.description or '',
            engineer_name
        ])
    writer.writerow([])
    
    # Budget Details
    writer.writerow(['BUDGET DETAILS'])
    writer.writerow(['Date', 'Category', 'Description', 'Amount'])
    for cost in costs:
        writer.writerow([
            str(cost.date),
            cost.get_cost_type_display(),
            cost.description or '',
            float(cost.amount)
        ])
    writer.writerow([])
    writer.writerow(['TOTAL', '', '', f'₱{total_cost:,.2f}'])
    
    return response
