from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, Http404, HttpResponseBadRequest, HttpResponseServerError, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
import json
# from django.contrib.gis.geos import GEOSGeometry  # Temporarily disabled
from .models import (
    Layer, Project, ProjectProgress, ProjectCost, ProgressPhoto, ProjectDocument,
    Notification, BarangayMetadata, ZoningZone,
    BudgetRequest, BudgetRequestAttachment, BudgetRequestStatusHistory,
    ProjectProgressEditHistory
)
from django.contrib.auth.models import User, Group
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Max
from django.template.loader import render_to_string, get_template
import csv
from datetime import datetime, timedelta
import logging
from monitoring.models import Project as MonitoringProject
from django.db import models as _models
import openpyxl
import io
from django.template import Context
# Optional xhtml2pdf import (allow running without reportlab)
try:
    from xhtml2pdf import pisa  # type: ignore
except Exception:  # pragma: no cover - allow missing dep
    pisa = None
from django.core.paginator import Paginator
from django.db.models import Q
from django.forms.fields import DateField # Import DateField
from .utils import (
    flag_overdue_projects_as_delayed, 
    notify_head_engineers, 
    notify_admins,
    notify_head_engineer_about_budget_concern,
    forward_budget_alert_to_finance
)
from django.views.decorators.http import require_GET, require_http_methods
from django.db import transaction
import traceback
from django.db.models import ProtectedError
from django.contrib.auth.views import redirect_to_login
from django.conf import settings

# Import centralized access control functions
from gistagum.access_control import (
    is_project_engineer,
    is_head_engineer,
    is_project_or_head_engineer,
    is_finance_manager,
    is_finance_or_head_engineer,
    project_engineer_required,
    head_engineer_required,
    get_user_dashboard_url
)

def is_staff_or_superuser(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
def dashboard(request):
    try:
        from .models import Project, ProjectProgress, ProjectCost, ProjectDocument
        from django.db.models import Max, Case, When, Q, F
        from django.utils import timezone as django_timezone
        
        # Base queryset for all assigned projects
        if is_head_engineer(request.user):
            base_queryset = Project.objects.select_related('created_by').prefetch_related('assigned_engineers')
            all_assigned_projects = base_queryset
        else:
            base_queryset = Project.objects.filter(assigned_engineers=request.user).select_related('created_by').prefetch_related('assigned_engineers')
            all_assigned_projects = base_queryset
        
        # Get the 6 most recently active projects (FIFO: when a 7th project gets activity, the oldest is excluded)
        # Calculate the most recent activity by finding the max of:
        # - Latest progress update time
        # - Latest cost entry time  
        # - Latest document upload time
        # - Project's updated_at
        # Then order by this calculated value (most recent first) and limit to 6
        
        # Annotate with latest activity times from related models
        projects_with_activity = base_queryset.annotate(
            latest_progress_time=Max('progress_updates__created_at'),
            latest_cost_time=Max('costs__created_at'),
            latest_document_time=Max('documents__uploaded_at'),
        )
        
        # Convert to list and calculate most_recent_activity for sorting
        projects_list = []
        for project in projects_with_activity:
            # Find the most recent activity time from all sources
            activity_times = []
            if project.latest_progress_time:
                activity_times.append(project.latest_progress_time)
            if project.latest_cost_time:
                activity_times.append(project.latest_cost_time)
            if project.latest_document_time:
                activity_times.append(project.latest_document_time)
            if project.updated_at:
                activity_times.append(project.updated_at)
            
            # Set most_recent_activity to the latest time, or created_at if no activity
            project.most_recent_activity = max(activity_times) if activity_times else (project.created_at or django_timezone.now())
            projects_list.append(project)
        
        # Sort by most_recent_activity (descending - most recent first) and take top 6
        projects_list.sort(key=lambda p: p.most_recent_activity, reverse=True)
        assigned_projects = projects_list[:6]
        print("DEBUG: assigned_projects for user", request.user.username, ":", list(assigned_projects))
        today = timezone.now().date()
        status_counts = {'Planned': 0, 'In Progress': 0, 'Completed': 0, 'Delayed': 0}
        delayed_projects = []
        total_projects = all_assigned_projects.count()
        # Optimize: Get all progress updates in one query
        from django.db.models import Prefetch
        progress_prefetch = Prefetch(
            'progress_updates',
            queryset=ProjectProgress.objects.order_by('-date'),
            to_attr='latest_progress_list'
        )
        all_assigned_projects = all_assigned_projects.prefetch_related(progress_prefetch)
        for project in all_assigned_projects:
            latest_progress = project.latest_progress_list[0] if hasattr(project, 'latest_progress_list') and project.latest_progress_list else None
            progress = float(latest_progress.percentage_complete) if latest_progress else 0
            status = project.status
            # Completed when progress is 100 (or >= 99)
            if progress >= 99:
                status = 'completed'
            # Delayed when end date has passed and progress is still below 99
            elif project.end_date and project.end_date < today and progress < 99:
                status = 'delayed'
            elif status in ['in_progress', 'ongoing']:
                status = 'in_progress'
            elif status in ['planned', 'pending']:
                status = 'planned'
            if status == 'completed':
                status_counts['Completed'] += 1
            elif status == 'in_progress':
                status_counts['In Progress'] += 1
            elif status == 'delayed':
                status_counts['Delayed'] += 1
                delayed_projects.append(project)
            elif status == 'planned':
                status_counts['Planned'] += 1
        projects_data = []
        # Get project IDs from the list (for last update calculation)
        project_ids = [p.id for p in assigned_projects]
        
        # Get latest update times from all sources
        progress_times = {}
        cost_times = {}
        document_times = {}
        
        if project_ids:
            # Get latest progress times
            latest_progress = ProjectProgress.objects.filter(
                project_id__in=project_ids
            ).values('project_id').annotate(
                max_time=Max('created_at')
            ).values_list('project_id', 'max_time')
            
            # Get latest cost times
            latest_costs = ProjectCost.objects.filter(
                project_id__in=project_ids
            ).values('project_id').annotate(
                max_time=Max('created_at')
            ).values_list('project_id', 'max_time')
            
            # Get latest document times
            latest_documents = ProjectDocument.objects.filter(
                project_id__in=project_ids
            ).values('project_id').annotate(
                max_time=Max('uploaded_at')
            ).values_list('project_id', 'max_time')
            
            progress_times = dict(latest_progress)
            cost_times = dict(latest_costs)
            document_times = dict(latest_documents)
        
        # Prefetch progress updates for the assigned projects
        # Since assigned_projects is now a list, we need to fetch them as a queryset for prefetching
        if assigned_projects:
            project_ids = [p.id for p in assigned_projects]
            # Fetch projects with prefetch, maintaining order
            prefetched_queryset = Project.objects.filter(id__in=project_ids).prefetch_related(progress_prefetch)
            # Create a dict for quick lookup
            prefetched_dict = {p.id: p for p in prefetched_queryset}
            # Reconstruct list in original order with prefetched data
            assigned_projects_ordered = []
            for project in assigned_projects:
                if project.id in prefetched_dict:
                    prefetched_project = prefetched_dict[project.id]
                    # Copy prefetched attributes
                    if hasattr(prefetched_project, 'latest_progress_list'):
                        project.latest_progress_list = prefetched_project.latest_progress_list
                assigned_projects_ordered.append(project)
            assigned_projects = assigned_projects_ordered
        
        # Calculate last update for each project and prepare projects_data
        assigned_projects_with_updates = []
        for project in assigned_projects:
            # Calculate last update using the same logic as my_projects_view
            if project.status == 'planned':
                project.calculated_last_update = None
            else:
                last_updates = []
                
                # Add latest progress update time if it exists
                progress_time = progress_times.get(project.id)
                if progress_time:
                    last_updates.append(progress_time)
                
                # Add latest cost entry time if it exists
                cost_time = cost_times.get(project.id)
                if cost_time:
                    last_updates.append(cost_time)
                
                # Add latest document upload time if it exists
                doc_time = document_times.get(project.id)
                if doc_time:
                    last_updates.append(doc_time)
                
                # Get the most recent update (max of all timestamps)
                project.calculated_last_update = max(last_updates) if last_updates else None
            
            assigned_projects_with_updates.append(project)
            
            # Prepare projects_data for JavaScript
            latest_progress = project.latest_progress_list[0] if hasattr(project, 'latest_progress_list') and project.latest_progress_list else None
            progress = float(latest_progress.percentage_complete) if latest_progress else 0
            projects_data.append({
                'id': project.id,
                'name': project.name,
                'progress': progress,
                'barangay': project.barangay,
                'status': project.status,
                'description': project.description,
                'project_cost': str(project.project_cost) if project.project_cost is not None else "",
                'source_of_funds': project.source_of_funds,
                'prn': project.prn,
                'start_date': str(project.start_date) if project.start_date else "",
                'end_date': str(project.end_date) if project.end_date else "",
                'image': project.image.url if project.image else "",
            })
        context = {
            'assigned_projects': assigned_projects_with_updates,
            'total_projects': total_projects,
            'status_counts': status_counts,
            'delayed_count': status_counts['Delayed'],
            'delayed_projects': delayed_projects,
            'projects_data': projects_data,
        }
        print(f'Dashboard View Context: {context}') # Debugging line
        return render(request, 'projeng/dashboard.html', context)
    except Exception as e:
        print(f"Error in dashboard view: {str(e)}")
        raise

# Placeholder views for new sidebar links
@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
def my_projects_view(request):
    from django.db.models import Max
    from django.utils import timezone
    from decimal import Decimal, InvalidOperation
    from projeng.models import ProjectType
    
    # Build base queryset
    if is_head_engineer(request.user):
        projects_queryset = Project.objects.all()
        scope = (request.GET.get('scope') or 'all').strip().lower()
    else:
        # Panel #24: allow filtering "combined" vs "own" projects
        scope = (request.GET.get('scope') or 'assigned').strip().lower()
        if scope == 'own':
            projects_queryset = Project.objects.filter(created_by=request.user)
        elif scope == 'combined':
            projects_queryset = Project.objects.filter(
                Q(assigned_engineers=request.user) | Q(created_by=request.user)
            ).distinct()
        else:
            # default: assigned projects only
            scope = 'assigned'
            projects_queryset = Project.objects.filter(assigned_engineers=request.user)

    # Panel #4: additional filters (project cost + type)
    selected_project_type = (request.GET.get('project_type') or '').strip()
    cost_min_raw = (request.GET.get('cost_min') or '').strip()
    cost_max_raw = (request.GET.get('cost_max') or '').strip()

    if selected_project_type:
        try:
            projects_queryset = projects_queryset.filter(project_type_id=int(selected_project_type))
        except Exception:
            # Ignore invalid input rather than breaking the page
            selected_project_type = ''

    def _to_decimal(val: str):
        if not val:
            return None
        try:
            return Decimal(val)
        except (InvalidOperation, ValueError):
            return None

    cost_min = _to_decimal(cost_min_raw)
    cost_max = _to_decimal(cost_max_raw)
    if cost_min is not None:
        projects_queryset = projects_queryset.filter(project_cost__gte=cost_min)
    if cost_max is not None:
        projects_queryset = projects_queryset.filter(project_cost__lte=cost_max)
    
    # Get all project IDs first for efficient querying
    project_ids = list(projects_queryset.values_list('id', flat=True))
    
    # Initialize dictionaries for storing latest update times and progress
    progress_times = {}
    cost_times = {}
    document_times = {}
    latest_progress_percent = {}
    
    # Only query if we have projects
    if project_ids:
        # Get latest progress times using aggregation
        latest_progress = ProjectProgress.objects.filter(
            project_id__in=project_ids
        ).values('project_id').annotate(
            max_time=Max('created_at'),
            max_date=Max('date'),
            max_created=Max('created_at')
        )
        
        # Get latest progress percentage for delay calculation
        for item in latest_progress:
            latest = ProjectProgress.objects.filter(
                project_id=item['project_id'],
                date=item['max_date'],
                created_at=item['max_created']
            ).order_by('-created_at').first()
            if latest:
                progress_times[item['project_id']] = latest.created_at
                if latest.percentage_complete is not None:
                    latest_progress_percent[item['project_id']] = float(latest.percentage_complete)
        
        # Get latest cost times
        latest_costs = ProjectCost.objects.filter(
            project_id__in=project_ids
        ).values('project_id').annotate(
            max_time=Max('created_at')
        ).values_list('project_id', 'max_time')
        
        # Get latest document times
        latest_documents = ProjectDocument.objects.filter(
            project_id__in=project_ids
        ).values('project_id').annotate(
            max_time=Max('uploaded_at')
        ).values_list('project_id', 'max_time')
        
        # Build dictionaries for quick lookup
        cost_times = dict(latest_costs)
        document_times = dict(latest_documents)
    
    # Get projects with prefetch for efficient access
    projects = projects_queryset.select_related('created_by').prefetch_related('assigned_engineers')
    
    # Calculate status counts and delayed status dynamically
    today = timezone.now().date()
    delayed_count = 0
    planned_pending_count = 0
    
    # Calculate the most recent update time and status for each project
    projects_with_updates = []
    for project in projects:
        # Get latest progress percentage
        progress = latest_progress_percent.get(project.id, 0)
        stored_status = project.status or ''
        
        # Calculate actual status dynamically (same logic as head engineer module)
        calculated_status = stored_status
        # Completed when progress >= 99
        if progress >= 99:
            calculated_status = 'completed'
        # Delayed when end date has passed and progress is still below 99
        elif project.end_date and project.end_date < today and progress < 99:
            calculated_status = 'delayed'
            delayed_count += 1
        elif stored_status == 'delayed':
            calculated_status = 'delayed'
            delayed_count += 1
        elif stored_status in ['in_progress', 'ongoing']:
            calculated_status = 'in_progress'
        elif stored_status in ['planned', 'pending']:
            calculated_status = 'planned'
            planned_pending_count += 1
        
        # Store calculated status on project object for template filtering
        project.calculated_status = calculated_status
        
        # If project status is "planned", always show "None" for last update
        # Last update should only be shown when status is not "planned"
        if project.status == 'planned':
            project.calculated_last_update = None
            projects_with_updates.append(project)
            continue
        
        # For non-planned projects, calculate the most recent update
        # Collect all possible update timestamps
        last_updates = []
        
        # Add latest progress update time if it exists
        progress_time = progress_times.get(project.id)
        if progress_time:
            last_updates.append(progress_time)
        
        # Add latest cost entry time if it exists
        cost_time = cost_times.get(project.id)
        if cost_time:
            last_updates.append(cost_time)
        
        # Add latest document upload time if it exists
        doc_time = document_times.get(project.id)
        if doc_time:
            last_updates.append(doc_time)
        
        # Note: We don't include project.updated_at for field changes
        # Only count actual activity: progress updates, cost entries, or document uploads
        
        # Get the most recent update (max of all timestamps)
        last_update = max(last_updates) if last_updates else None
        
        # Add calculated_last_update to project for template access
        project.calculated_last_update = last_update
        projects_with_updates.append(project)
    
    project_type_options = ProjectType.objects.order_by('name')

    return render(request, 'projeng/my_projects.html', {
        'projects': projects_with_updates,
        'delayed_count': delayed_count,
        'planned_pending_count': planned_pending_count,
        'scope': request.GET.get('scope', 'assigned'),
        'project_type_options': project_type_options,
        'selected_project_type': selected_project_type,
        'cost_min': cost_min_raw,
        'cost_max': cost_max_raw,
    })

@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
def projeng_map_view(request):
    if is_head_engineer(request.user):
        layers = Layer.objects.all()
        all_projects = Project.objects.filter(latitude__isnull=False, longitude__isnull=False)
    else:
        layers = Layer.objects.filter(created_by=request.user)
        all_projects = Project.objects.filter(
            assigned_engineers=request.user,
            latitude__isnull=False,
            longitude__isnull=False
        )
    delayed_count = all_projects.filter(status='delayed').count()
    projects_with_coords = []
    for project in all_projects:
        if project.latitude != '' and project.longitude != '':
            projects_with_coords.append(project)
    projects_data = []
    for p in projects_with_coords:
        latest_progress = ProjectProgress.objects.filter(project=p).order_by('-date').first()
        progress = float(latest_progress.percentage_complete) if latest_progress else 0
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
            'progress': progress,
            'zone_type': p.zone_type or '',
        })
    context = {
        'layers': layers,
        'projects_data': projects_data,
        'delayed_count': delayed_count,
    }
    return render(request, 'projeng/projeng_map.html', context)

@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
def upload_docs_view(request):
    if is_head_engineer(request.user):
        assigned_projects = Project.objects.all()
    else:
        assigned_projects = Project.objects.filter(assigned_engineers=request.user)
    delayed_count = assigned_projects.filter(status='delayed').count()
    projects_data = []
    for project in assigned_projects:
        latest_progress = ProjectProgress.objects.filter(project=project).order_by('-date').first()
        progress = float(latest_progress.percentage_complete) if latest_progress else 0
        projects_data.append({
            'id': project.id,
            'name': project.name,
            'progress': progress,
            'barangay': project.barangay,
            'status': project.status,
            'description': project.description,
            'project_cost': str(project.project_cost) if project.project_cost is not None else "",
            'source_of_funds': project.source_of_funds,
            'prn': project.prn,
            'start_date': str(project.start_date) if project.start_date else "",
            'end_date': str(project.end_date) if project.end_date else "",
            'image': project.image.url if project.image else "",
        })
    context = {
        'assigned_projects': assigned_projects,
        'delayed_count': delayed_count,
        'projects_data': projects_data,
    }
    
    return render(request, 'projeng/upload_docs.html', context)

@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
def my_reports_view(request):
    from .models import ProjectType
    # Build base queryset
    if is_head_engineer(request.user):
        assigned_projects = Project.objects.all()
    else:
        assigned_projects = Project.objects.filter(assigned_engineers=request.user)
    
    # Get filter options from base queryset (before applying filters)
    base_queryset = assigned_projects
    source_of_funds_options = list(
        base_queryset.filter(source_of_funds__isnull=False)
        .exclude(source_of_funds='')
        .values_list('source_of_funds', flat=True)
        .distinct()
        .order_by('source_of_funds')
    )
    project_type_options = ProjectType.objects.order_by('name')
    
    # Apply filters
    barangay_filter = request.GET.get('barangay')
    status_filter = request.GET.get('status')
    start_date_filter = request.GET.get('start_date')
    end_date_filter = request.GET.get('end_date')
    source_of_funds_filter = request.GET.get('source_of_funds')
    project_type_filter = request.GET.get('project_type')
    
    if barangay_filter:
        assigned_projects = assigned_projects.filter(barangay=barangay_filter)
    if status_filter:
        # Handle "in_progress" to match both "in_progress" and "ongoing" statuses
        if status_filter == 'in_progress':
            assigned_projects = assigned_projects.filter(Q(status='in_progress') | Q(status='ongoing'))
        else:
            assigned_projects = assigned_projects.filter(status=status_filter)
    if start_date_filter:
        try:
            start_date = datetime.strptime(start_date_filter, '%Y-%m-%d').date()
            assigned_projects = assigned_projects.filter(start_date__gte=start_date)
        except ValueError:
            pass
    if end_date_filter:
        try:
            end_date = datetime.strptime(end_date_filter, '%Y-%m-%d').date()
            assigned_projects = assigned_projects.filter(end_date__lte=end_date)
        except ValueError:
            pass
    if source_of_funds_filter:
        assigned_projects = assigned_projects.filter(source_of_funds=source_of_funds_filter)
    if project_type_filter:
        try:
            assigned_projects = assigned_projects.filter(project_type_id=int(project_type_filter))
        except (ValueError, TypeError):
            pass
    
    # Optimize status counts - use aggregation instead of multiple queries (single query)
    from django.db.models import Count, Q
    status_counts = {}
    status_aggregation = assigned_projects.values('status').annotate(count=Count('id'))
    status_dict = {item['status']: item['count'] for item in status_aggregation}
    for status_key, status_display in Project.STATUS_CHOICES:
        status_counts[status_display] = status_dict.get(status_key, 0)
    
    # Get delayed count from status_counts (already calculated, no extra query needed)
    delayed_count = status_counts.get('Delayed', 0)
    total_projects = assigned_projects.count()
    barangays = [
        "Apokon", "Bincungan", "Busaon", "Canocotan", "Cuambogan", "La Filipina", "Liboganon", "Madaum", "Magdum", "Magugpo East", "Magugpo North", "Magugpo Poblacion", "Magugpo South", "Magugpo West", "Mankilam", "New Balamban", "Nueva Fuerza", "Pagsabangan", "Pandapan", "San Agustin", "San Isidro", "San Miguel", "Visayan Village"
    ]
    # Filter statuses to only show: Planned, In Progress, Completed
    statuses = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    # Optimize query - use select_related and prefetch_related to avoid N+1 queries
    assigned_projects = assigned_projects.select_related('created_by', 'project_type').prefetch_related('assigned_engineers')
    
    paginator = Paginator(assigned_projects, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Optimize progress queries - get all progress updates for projects in this page efficiently
    # Instead of N+1 queries, fetch all progress records for these projects in 1-2 queries
    project_ids = [project.id for project in page_obj.object_list]
    latest_progress_per_project = {}
    if project_ids:
        # Get all progress records for these projects (one query instead of N queries)
        all_progresses = ProjectProgress.objects.filter(
            project_id__in=project_ids
        ).order_by('project_id', '-date', '-created_at').select_related('project')
        
        # Process in Python to get the latest for each project
        # Since we ordered by project_id, -date, -created_at, we can iterate once
        current_project_id = None
        for progress in all_progresses:
            if progress.project_id != current_project_id:
                latest_progress_per_project[progress.project_id] = progress.percentage_complete
                current_project_id = progress.project_id
    
    projects_list_for_modal = []
    for project in page_obj.object_list:
        progress = latest_progress_per_project.get(project.id, 0)
        projects_list_for_modal.append({
            'id': project.id,
            'prn': project.prn or '',
            'name': project.name or '',
            'description': project.description or '',
            'barangay': project.barangay or '',
            'project_cost': str(project.project_cost) if project.project_cost is not None else '',
            'source_of_funds': project.source_of_funds or '',
            'project_type_id': project.project_type_id,
            'project_type_name': project.project_type.name if project.project_type else '',
            'start_date': str(project.start_date) if project.start_date else '',
            'end_date': str(project.end_date) if project.end_date else '',
            'status': project.status or '',
            'status_display': project.get_status_display() or '',
            'progress': progress,
        })
    context = {
        'page_obj': page_obj,
        'projects_data': projects_list_for_modal,
        'total_projects': total_projects,
        'status_counts': status_counts,
        'barangays': barangays,
        'statuses': statuses,
        'source_of_funds_options': source_of_funds_options,
        'project_type_options': project_type_options,
        'selected_barangay': barangay_filter,
        'selected_status': status_filter,
        'selected_start_date': start_date_filter,
        'selected_end_date': end_date_filter,
        'selected_source_of_funds': source_of_funds_filter,
        'selected_project_type': project_type_filter,
        'delayed_count': delayed_count,
    }
    return render(request, 'projeng/my_reports.html', context)

# Placeholder view for project detail
@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
def project_detail_view(request, pk):
    try:
        from django.db.models import Max
        
        # Optimize query with select_related and prefetch_related
        project = Project.objects.select_related('created_by').prefetch_related('assigned_engineers').get(pk=pk)
        
        # Check permissions - head engineers can see all, project engineers only their assigned
        if not is_head_engineer(request.user):
            if request.user not in project.assigned_engineers.all():
                raise PermissionDenied("You are not assigned to this project.")
        
        # Calculate last update using the same logic as my_projects_view
        # If project status is "planned", always show "None" for last update
        if project.status == 'planned':
            project.calculated_last_update = None
        else:
            # For non-planned projects, calculate the most recent update
            last_updates = []
            
            # Get latest progress update time
            latest_progress = ProjectProgress.objects.filter(project=project).aggregate(Max('created_at'))
            if latest_progress['created_at__max']:
                last_updates.append(latest_progress['created_at__max'])
            
            # Get latest cost entry time
            latest_cost = ProjectCost.objects.filter(project=project).aggregate(Max('created_at'))
            if latest_cost['created_at__max']:
                last_updates.append(latest_cost['created_at__max'])
            
            # Get latest document upload time
            latest_document = ProjectDocument.objects.filter(project=project).aggregate(Max('uploaded_at'))
            if latest_document['uploaded_at__max']:
                last_updates.append(latest_document['uploaded_at__max'])
            
            # Get the most recent update (max of all timestamps)
            # Only count actual activity: progress updates, cost entries, or document uploads
            project.calculated_last_update = max(last_updates) if last_updates else None
        
        # Build activity history log
        activity_log = []
        
        # Add project creation
        activity_log.append({
            'type': 'project_created',
            'timestamp': project.created_at,
            'user': project.created_by,
            'message': f'Project "{project.name}" was created',
            'icon': 'plus-circle',
            'color': 'blue'
        })
        
        # Add progress updates
        progress_updates = ProjectProgress.objects.filter(project=project).select_related('created_by', 'milestone').order_by('-created_at')
        for progress in progress_updates:
            milestone_info = ''
            if progress.milestone:
                milestone_info = f' (Milestone: {progress.milestone.name})'
            
            activity_log.append({
                'type': 'progress_update',
                'progress_id': progress.id,
                'timestamp': progress.created_at,
                'user': progress.created_by,
                'message': f'Progress updated to {progress.percentage_complete}%{milestone_info}',
                'description': progress.description,
                'justification': progress.justification,
                'date': progress.date,
                'percentage': progress.percentage_complete,
                'milestone': progress.milestone.name if progress.milestone else None,
                'icon': 'chart-bar',
                'color': 'green'
            })
        
        # Add cost entries
        cost_entries = ProjectCost.objects.filter(project=project).select_related('created_by').order_by('-created_at')
        for cost in cost_entries:
            activity_log.append({
                'type': 'cost_entry',
                'timestamp': cost.created_at,
                'user': cost.created_by,
                'message': f'Cost entry added: {cost.get_cost_type_display()} - ₱{cost.amount:,.2f}',
                'description': cost.description,
                'date': cost.date,
                'amount': cost.amount,
                'cost_type': cost.get_cost_type_display(),
                'icon': 'currency-dollar',
                'color': 'yellow'
            })

        # Add budget requests (additional budget) to activity history
        budget_requests = (
            BudgetRequest.objects
            .filter(project=project)
            .select_related('requested_by', 'reviewed_by')
            .prefetch_related('attachments', 'history')
            .order_by('-created_at')
        )
        for br in budget_requests:
            activity_log.append({
                'type': 'budget_request',
                'timestamp': br.created_at,
                'user': br.requested_by,
                'message': f'Budget request submitted: ₱{float(br.requested_amount):,.2f} ({br.get_status_display()})',
                'description': br.reason,
                'requested_amount': br.requested_amount,
                'status': br.status,
                'icon': 'clipboard',
                'color': 'indigo'
            })
            if br.reviewed_at and br.reviewed_by and br.status in ['approved', 'rejected', 'cancelled']:
                activity_log.append({
                    'type': 'budget_request_decision',
                    'timestamp': br.reviewed_at,
                    'user': br.reviewed_by,
                    'message': (
                        f'Budget request {br.get_status_display().lower()}'
                        + (f': ₱{float(br.approved_amount):,.2f} approved' if br.status == 'approved' and br.approved_amount else '')
                    ),
                    'description': br.decision_notes,
                    'status': br.status,
                    'approved_amount': br.approved_amount,
                    'decision_notes': br.decision_notes,
                    'icon': 'check-circle' if br.status == 'approved' else 'x-circle',
                    'color': 'green' if br.status == 'approved' else 'red'
                })
        
        # Add document uploads
        documents = ProjectDocument.objects.filter(project=project).select_related('uploaded_by').order_by('-uploaded_at')
        for doc in documents:
            activity_log.append({
                'type': 'document_upload',
                'timestamp': doc.uploaded_at,
                'user': doc.uploaded_by,
                'message': f'Document uploaded: {doc.name}',
                'document_name': doc.name,
                'icon': 'document',
                'color': 'purple'
            })
        
        # Pass documents separately for the dedicated documents section
        
        # Sort by timestamp (most recent first)
        activity_log.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Limit to 10 most recent activities
        activity_log = activity_log[:10]
        
        # Progress Trends Data for Analytics
        progress_updates_for_chart = ProjectProgress.objects.filter(project=project).order_by('date', 'created_at')
        progress_timeline_data = []
        progress_percentages = []
        progress_dates = []
        
        for progress in progress_updates_for_chart:
            progress_timeline_data.append({
                'date': progress.date.isoformat(),
                'percentage': progress.percentage_complete,
                'description': progress.description[:50] + '...' if len(progress.description) > 50 else progress.description
            })
            progress_dates.append(progress.date.strftime('%Y-%m-%d'))
            progress_percentages.append(progress.percentage_complete)
        
        # Timeline Comparison: Expected vs Actual Progress (working days only: exclude weekends + PH holidays)
        timeline_comparison = None
        if project.start_date and project.end_date:
            from datetime import date, timedelta
            import json
            from projeng.working_days import working_days_between
            today = date.today()
            total_days = working_days_between(project.start_date, project.end_date)
            elapsed_days = working_days_between(project.start_date, min(today, project.end_date)) if today >= project.start_date else 0
            remaining_days = working_days_between(today, project.end_date) if today <= project.end_date else 0

            if total_days > 0 and elapsed_days >= 0:
                # Calculate expected progress based on linear timeline (working days)
                expected_progress = min(100, (elapsed_days / total_days) * 100)
                actual_progress = progress_percentages[-1] if progress_percentages else 0
                progress_variance = actual_progress - expected_progress

                # Generate expected progress data points for chart (working days per date)
                all_dates_set = set(progress_dates)
                current_date = project.start_date
                while current_date <= project.end_date and current_date <= today:
                    all_dates_set.add(current_date.strftime('%Y-%m-%d'))
                    current_date += timedelta(days=7)
                all_dates_sorted = sorted(list(all_dates_set))

                expected_progress_data = []
                actual_progress_aligned = []
                for date_str in all_dates_sorted:
                    year, month, day = map(int, date_str.split('-'))
                    date_obj = date(year, month, day)
                    working_elapsed = working_days_between(project.start_date, date_obj) if date_obj >= project.start_date else 0
                    expected_pct = min(100, (working_elapsed / total_days) * 100) if total_days > 0 else 0
                    expected_progress_data.append(expected_pct)
                    actual_pct = 0
                    for i, prog_date in enumerate(progress_dates):
                        if prog_date <= date_str:
                            actual_pct = progress_percentages[i]
                        else:
                            break
                    actual_progress_aligned.append(actual_pct)

                timeline_comparison = {
                    'expected_progress': round(expected_progress, 2),
                    'actual_progress': actual_progress,
                    'progress_variance': round(progress_variance, 2),
                    'elapsed_days': elapsed_days,
                    'total_days': total_days,
                    'remaining_days': remaining_days,
                    'is_ahead': progress_variance > 0,
                    'is_behind': progress_variance < -5,
                    'expected_progress_data': expected_progress_data,
                    'expected_dates': all_dates_sorted,
                    'actual_progress_aligned': actual_progress_aligned,
                }
        
        # Calculate budget information
        from django.db.models import Sum
        total_cost = ProjectCost.objects.filter(project=project).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Calculate remaining budget
        project_cost = float(project.project_cost) if project.project_cost else 0
        total_cost_float = float(total_cost)
        remaining_budget = project_cost - total_cost_float if project_cost > 0 else None
        budget_utilization = (total_cost_float / project_cost * 100) if project_cost > 0 else 0
        over_budget_amount = abs(remaining_budget) if remaining_budget is not None and remaining_budget < 0 else 0

        # Ratios for comprehensive analytics (panel: #11/#19/#29)
        expected_progress_pct = None
        actual_progress_pct = None
        performance_ratio = None
        efficiency_ratio = None
        if timeline_comparison:
            expected_progress_pct = timeline_comparison.get('expected_progress')
            actual_progress_pct = timeline_comparison.get('actual_progress')
        if actual_progress_pct is None:
            actual_progress_pct = project.progress or 0
        if expected_progress_pct and expected_progress_pct > 0:
            performance_ratio = float(actual_progress_pct) / float(expected_progress_pct)
        if budget_utilization and budget_utilization > 0:
            efficiency_ratio = float(actual_progress_pct) / float(budget_utilization)
        
        # Determine budget status for color coding
        budget_status = 'normal'
        if project_cost > 0:
            if budget_utilization >= 100:
                budget_status = 'over'
            elif budget_utilization >= 80:
                budget_status = 'warning'
            elif budget_utilization >= 50:
                budget_status = 'normal'
            else:
                budget_status = 'good'
        
        # Convert lists to JSON for JavaScript
        import json
        from collections import defaultdict
        progress_dates_json = json.dumps(progress_dates)
        progress_percentages_json = json.dumps(progress_percentages)
        timeline_comparison_json = json.dumps(timeline_comparison) if timeline_comparison else None
        expected_dates_json = json.dumps(timeline_comparison['expected_dates']) if timeline_comparison else '[]'
        expected_progress_data_json = json.dumps(timeline_comparison['expected_progress_data']) if timeline_comparison else '[]'
        actual_progress_aligned_json = json.dumps(timeline_comparison['actual_progress_aligned']) if timeline_comparison else '[]'

        # Report data for PDFMake (Print Report)
        progress_updates_for_report = ProjectProgress.objects.filter(project=project).order_by('date', 'created_at').select_related('created_by')
        costs_for_report = ProjectCost.objects.filter(project=project).order_by('date').select_related('created_by')
        cost_breakdown = defaultdict(float)
        for c in costs_for_report:
            cost_breakdown[c.get_cost_type_display()] += float(c.amount or 0)
        latest_progress_obj = ProjectProgress.objects.filter(project=project).order_by('-date', '-created_at').first()
        budget_status_label = 'UNDER BUDGET'
        if budget_utilization >= 100:
            budget_status_label = 'OVER BUDGET'
        elif budget_utilization >= 90:
            budget_status_label = 'AT RISK'
        if timeline_comparison:
            days_elapsed = timeline_comparison.get('elapsed_days', 0)
            total_days = timeline_comparison.get('total_days', 0)
            days_remaining = timeline_comparison.get('remaining_days', 0)
            expected_progress = timeline_comparison.get('expected_progress')
            progress_variance = timeline_comparison.get('progress_variance')
        else:
            days_elapsed = total_days = days_remaining = 0
            expected_progress = progress_variance = None
        report_data = {
            'project': {
                'name': project.name or '',
                'prn': project.prn or '',
                'barangay': project.barangay or '',
                'status': project.get_status_display() if hasattr(project, 'get_status_display') else (project.status or ''),
                'start_date': project.start_date.strftime('%B %d, %Y') if project.start_date else '',
                'end_date': project.end_date.strftime('%B %d, %Y') if project.end_date else '',
                'project_cost': project_cost,
                'source_of_funds': getattr(project, 'source_of_funds', '') or '',
                'description': (project.description or '')[:200],
            },
            'assigned_engineers': [u.get_full_name() or u.username for u in project.assigned_engineers.all()],
            'latest_progress_pct': latest_progress_obj.percentage_complete if latest_progress_obj else 0,
            'total_cost': total_cost_float,
            'budget': project_cost,
            'remaining_budget': remaining_budget,
            'budget_utilization': float(budget_utilization),
            'budget_status_label': budget_status_label,
            'days_elapsed': days_elapsed,
            'total_days': total_days,
            'days_remaining': days_remaining,
            'expected_progress': expected_progress,
            'progress_variance': progress_variance,
            'cost_breakdown': dict(cost_breakdown),
            'generated_by': request.user.get_full_name() or request.user.username,
            'generated_at': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
            'progress_updates': [
                {
                    'date': u.date.strftime('%Y-%m-%d') if getattr(u, 'date', None) else '',
                    'percentage_complete': getattr(u, 'percentage_complete', 0),
                    'description': (getattr(u, 'description', None) or '')[:80],
                    'engineer': u.created_by.get_full_name() or getattr(u.created_by, 'username', '') if getattr(u, 'created_by', None) else '',
                }
                for u in progress_updates_for_report
            ],
            'uploaded_images': [],  # Project engineer report without embedded images
        }

        return render(request, 'projeng/project_detail.html', {
            'project': project,
            'status_choices': Project.STATUS_CHOICES,
            'activity_log': activity_log,
            'documents': documents,  # Pass documents for dedicated section
            'budget_requests': budget_requests,
            'can_edit_any_progress': is_head_engineer(request.user),
            'progress_timeline_data': progress_timeline_data,
            'progress_dates': progress_dates_json,
            'progress_percentages': progress_percentages_json,
            'timeline_comparison': timeline_comparison,
            'performance_ratio': performance_ratio,
            'efficiency_ratio': efficiency_ratio,
            'expected_dates_json': expected_dates_json,
            'expected_progress_data_json': expected_progress_data_json,
            'actual_progress_aligned_json': actual_progress_aligned_json,
            'total_cost': total_cost_float,
            'remaining_budget': remaining_budget,
            'budget_utilization': budget_utilization,
            'budget_status': budget_status,
            'over_budget_amount': over_budget_amount,
            'report_data': report_data,
        })
    except Project.DoesNotExist:
        raise Http404("Project does not exist.")
    except PermissionDenied:
        return HttpResponseForbidden("You are not assigned to view this project.")
    except Exception as e:
        logging.error(f"Error in project_detail_view: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return HttpResponseServerError(f"An error occurred: {str(e)}")

@user_passes_test(is_project_engineer, login_url='/accounts/login/')
@csrf_exempt # Use csrf_exempt for simplicity in development, consider csrf_protect in production
def update_project_status(request, pk):
    if request.method == 'POST':
        try:
            project = Project.objects.get(pk=pk)

            # Ensure the logged-in user is assigned to this project before allowing update
            if request.user not in project.assigned_engineers.all():
                 return JsonResponse({'success': False, 'error': 'You are not assigned to this project.'}, status=403)

            data = json.loads(request.body)
            new_status = data.get('status')

            # Validate the new status against the model choices
            valid_statuses = [choice[0] for choice in Project.STATUS_CHOICES]
            if new_status not in valid_statuses:
                 return JsonResponse({'success': False, 'error': 'Invalid status provided.'}, status=400)

            project.status = new_status
            # Store who made the update for notification purposes
            project._updated_by_username = request.user.get_full_name() or request.user.username
            project.save()

            # You could also update the last_update field here if needed
            # project.last_update = timezone.now().date()
            # project.save()

            return JsonResponse({'success': True, 'message': 'Project status updated successfully!', 'new_status_display': project.get_status_display()})

        except Project.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Project not found.'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)

@login_required
@csrf_exempt
def save_layer(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Extract data from the request
            name = data.get('name')
            description = data.get('description')
            layer_type = data.get('type')
            geometry = data.get('geometry')
            
            # Debug print the received geometry
            print("Received geometry data:", json.dumps(geometry, indent=2))
            # Add debug prints for type and content of geometry
            print(f"Type of received geometry: {type(geometry)}")
            print(f"Content of received geometry: {geometry}")
            
            # Validate required fields
            if not all([name, layer_type, geometry]):
                return JsonResponse({
                    'success': False,
                    'error': 'Missing required fields'
                })
            
            # Convert GeoJSON to GEOS geometry - Temporarily disabled
            # geos_geometry = GEOSGeometry(json.dumps(geometry))
            
            # Create new layer
            layer = Layer.objects.create(
                name=name,
                description=description,
                type=layer_type,
                # geometry=geos_geometry,  # Temporarily disabled
                created_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Layer saved successfully',
                'layer_id': layer.id
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })

@user_passes_test(is_staff_or_superuser, login_url='/accounts/login/')
def get_project_engineers(request):
    # Allow staff, superuser, and head engineers
    if not (request.user.is_authenticated and (
        request.user.is_staff or
        request.user.is_superuser or
        request.user.groups.filter(name='Head Engineer').exists()
    )):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Not authorized'}, status=403)
        return redirect_to_login(request.get_full_path())
    try:
        project_engineer_group = Group.objects.get(name='Project Engineer')
        head_engineer_group = Group.objects.get(name='Head Engineer')
        engineers = User.objects.filter(groups=project_engineer_group)
        engineers = engineers.exclude(groups=head_engineer_group).exclude(is_superuser=True).order_by('username')
        engineers_data = [{'id': engineer.id, 'username': engineer.username, 'full_name': engineer.get_full_name() or engineer.username} for engineer in engineers]
        return JsonResponse(engineers_data, safe=False)
    except Group.DoesNotExist:
        return JsonResponse([], safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@user_passes_test(is_project_engineer, login_url='/accounts/login/')
def project_analytics(request, pk):
    try:
        project = Project.objects.get(pk=pk)
        if request.user not in project.assigned_engineers.all():
            raise PermissionDenied("You are not assigned to this project.")
        progress_updates = ProjectProgress.objects.filter(project=project).order_by('-date')
        print(f"DEBUG: All progress updates for project {project.id} ({project.name}):")
        for pu in progress_updates:
            print(f"  id={pu.id}, date={pu.date}, percentage_complete={pu.percentage_complete}, description={pu.description}")
        latest_progress = progress_updates.first()
        total_progress = latest_progress.percentage_complete if latest_progress else 0
        costs = ProjectCost.objects.filter(project=project)
        total_cost = costs.aggregate(total=Sum('amount'))['total'] or 0
        cost_by_type = costs.values('cost_type').annotate(total=Sum('amount'))
        budget_utilization = (total_cost / project.project_cost * 100) if project.project_cost else 0
        # Calculate budget remaining
        budget_remaining = (project.project_cost - total_cost) if project.project_cost else None
        # Determine budget status for color coding
        budget_status = 'good'  # default
        if budget_remaining is not None:
            # Convert to float for comparison
            budget_remaining_float = float(budget_remaining)
            project_cost_float = float(project.project_cost) if project.project_cost else 0
            if budget_remaining_float < 0:
                budget_status = 'over'  # Over budget (red)
            elif project_cost_float > 0 and budget_remaining_float < (project_cost_float * 0.1):
                budget_status = 'warning'  # Less than 10% remaining (orange)
            else:
                budget_status = 'good'  # Within budget (blue)
        timeline_data = {
            'start_date': project.start_date,
            'end_date': project.end_date,
            'days_elapsed': (timezone.now().date() - project.start_date).days if project.start_date else None,
            'total_days': (project.end_date - project.start_date).days if project.start_date and project.end_date else None,
        }
        
        # Calculate remaining_budget (used by template) - convert to float
        remaining_budget = float(budget_remaining) if budget_remaining is not None else None
        total_cost_float = float(total_cost)
        over_budget_amount = abs(remaining_budget) if remaining_budget is not None and remaining_budget < 0 else 0
        
        # Build activity history log (simplified for analytics view)
        activity_log = []
        # Add project creation
        if project.created_at:
            activity_log.append({
                'type': 'project_created',
                'timestamp': project.created_at,
                'message': f'Project "{project.name}" was created',
                'user': project.created_by,
            })
        # Add progress updates
        for progress in progress_updates[:10]:  # Limit to recent 10
            activity_log.append({
                'type': 'progress_update',
                'timestamp': progress.created_at,
                'message': f'Progress updated to {progress.percentage_complete}%',
                'description': progress.description,
                'user': progress.created_by,
                'percentage': progress.percentage_complete,
                'date': progress.date,
            })
        # Add cost entries
        for cost in costs[:10]:  # Limit to recent 10
            activity_log.append({
                'type': 'cost_entry',
                'timestamp': cost.created_at,
                'message': f'Cost entry added: {project.name} - {cost.get_cost_type_display()} ₱{cost.amount:.2f}',
                'user': cost.created_by,
                'cost_type': cost.get_cost_type_display(),
                'date': cost.date,
            })
        activity_log.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Progress timeline data for charts
        progress_timeline_data = []
        progress_percentages = []
        progress_dates = []
        for progress in progress_updates.order_by('date', 'created_at'):
            progress_timeline_data.append({
                'date': progress.date.isoformat(),
                'percentage': progress.percentage_complete,
            })
            progress_percentages.append(progress.percentage_complete)
            progress_dates.append(progress.date.isoformat())
        
        # Timeline comparison (working days only: exclude weekends + PH holidays)
        timeline_comparison = None
        if project.start_date and project.end_date:
            from projeng.working_days import working_days_between
            today = timezone.now().date()
            total_days = working_days_between(project.start_date, project.end_date)
            elapsed_days = working_days_between(project.start_date, min(today, project.end_date)) if today >= project.start_date else 0
            remaining_days = working_days_between(today, project.end_date) if today <= project.end_date else 0
            expected_progress = min(100, (elapsed_days / total_days * 100)) if total_days > 0 else 0
            progress_variance = total_progress - expected_progress

            timeline_comparison = {
                'expected_progress': round(expected_progress, 2),
                'actual_progress': total_progress,
                'progress_variance': round(progress_variance, 2),
                'elapsed_days': elapsed_days,
                'total_days': total_days,
                'remaining_days': remaining_days,
                'is_ahead': progress_variance > 0,
                'is_behind': progress_variance < -5,
                'expected_progress_data': [expected_progress],
                'expected_dates': [project.start_date.isoformat()],
                'actual_progress_aligned': [total_progress],
            }

        # Ratios for comprehensive analytics (panel: #11/#19/#29)
        performance_ratio = (float(total_progress) / float(timeline_comparison['expected_progress'])) if (timeline_comparison and timeline_comparison.get('expected_progress')) else None
        efficiency_ratio = (float(total_progress) / float(budget_utilization)) if budget_utilization > 0 else None
        
        # Convert to JSON for JavaScript
        import json
        progress_dates_json = json.dumps(progress_dates)
        progress_percentages_json = json.dumps(progress_percentages)
        expected_dates_json = json.dumps(timeline_comparison['expected_dates']) if timeline_comparison else '[]'
        expected_progress_data_json = json.dumps(timeline_comparison['expected_progress_data']) if timeline_comparison else '[]'
        actual_progress_aligned_json = json.dumps(timeline_comparison['actual_progress_aligned']) if timeline_comparison else '[]'
        
        context = {
            'project': project,
            'status_choices': Project.STATUS_CHOICES,
            'latest_progress': latest_progress,
            'total_progress': total_progress,
            'total_cost': total_cost_float,
            'cost_by_type': cost_by_type,
            'budget_utilization': budget_utilization,
            'budget_remaining': budget_remaining,  # Keep for backward compatibility
            'remaining_budget': remaining_budget,  # New variable name used by template
            'budget_status': budget_status,
            'over_budget_amount': over_budget_amount,
            'timeline_data': timeline_data,
            'today': timezone.now().date(),
            'activity_log': activity_log,
            'progress_timeline_data': progress_timeline_data,
            'progress_dates': progress_dates_json,
            'progress_percentages': progress_percentages_json,
            'timeline_comparison': timeline_comparison,
            'performance_ratio': performance_ratio,
            'efficiency_ratio': efficiency_ratio,
            'expected_dates_json': expected_dates_json,
            'expected_progress_data_json': expected_progress_data_json,
            'actual_progress_aligned_json': actual_progress_aligned_json,
        }
        
        return render(request, 'projeng/project_detail.html', context)
    except Project.DoesNotExist:
        raise Http404("Project does not exist or you are not assigned to it.")
    except PermissionDenied:
        return HttpResponseForbidden("You are not assigned to view this project.")
    except Exception as e:
        logging.error(f"Error in project_analytics view: {e}")
        return HttpResponseServerError("An error occurred while loading project analytics.")

@user_passes_test(is_project_engineer, login_url='/accounts/login/')
def export_project_report(request, pk):
    try:
        project = Project.objects.get(pk=pk)
        
        # Get all relevant data
        progress_updates = ProjectProgress.objects.filter(project=project).order_by('date')
        costs = ProjectCost.objects.filter(project=project)
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{project.name}_report_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        
        # Write project details
        writer.writerow(['Project Report'])
        writer.writerow(['Project Name', project.name])
        writer.writerow(['PRN', project.prn])
        writer.writerow(['Status', project.get_status_display()])
        writer.writerow(['Start Date', project.start_date])
        writer.writerow(['End Date', project.end_date])
        writer.writerow(['Budget', project.project_cost])
        writer.writerow([])
        
        # Write progress updates
        writer.writerow(['Progress Updates'])
        writer.writerow(['Date', 'Percentage Complete', 'Description'])
        for update in progress_updates:
            writer.writerow([update.date, update.percentage_complete, update.description])
        writer.writerow([])
        
        # Write cost breakdown
        writer.writerow(['Cost Breakdown'])
        writer.writerow(['Date', 'Type', 'Description', 'Amount'])
        for cost in costs:
            writer.writerow([cost.date, cost.get_cost_type_display(), cost.description, cost.amount])
        
        return response
    except Project.DoesNotExist:
        return JsonResponse({'error': 'Project not found'}, status=404)

@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
@csrf_exempt
def add_progress_update(request, pk):
    try:
        project = Project.objects.get(pk=pk)
        
        # Check permissions - head engineers can add updates to any project
        if not is_head_engineer(request.user):
            if request.user not in project.assigned_engineers.all():
                return JsonResponse({'error': 'You are not assigned to this project.'}, status=403)
    except Project.DoesNotExist:
        return JsonResponse({'error': 'Project not found.'}, status=404)
    
    if request.method == 'GET':
        # Render combined form page for adding progress update or cost entry
        from datetime import date
        today = date.today()
        from projeng.models import ProjectCost, ProjectProgress, ProjectMilestone
        
        # Get current progress percentage
        latest_progress = ProjectProgress.objects.filter(project=project).order_by('-date', '-created_at').first()
        current_progress = latest_progress.percentage_complete if latest_progress else (project.progress or 0)
        
        # Get milestones for this project
        milestones = ProjectMilestone.objects.filter(project=project, is_completed=False).order_by('target_date')
        
        return render(request, 'projeng/add_update.html', {
            'project': project,
            'today': today,
            'cost_types': ProjectCost.COST_TYPES,
            'current_progress': current_progress,
            'milestones': milestones
        })
    
    if request.method == 'POST':
        try:
            # Use request.POST and request.FILES for multipart/form-data
            date_str = request.POST.get('date')
            raw_percentage = request.POST.get('percentage_complete')
            print(f"DEBUG: Raw percentage_complete value: {raw_percentage!r}")
            try:
                percentage_complete = round(float(raw_percentage), 2)  # store exact input, max 2 decimals
                if not (0 <= percentage_complete <= 100):
                    raise ValueError("Percentage out of range")
            except (TypeError, ValueError) as e:
                logging.exception("Invalid percentage value")
                return JsonResponse({'error': 'Invalid percentage value. Please enter a number between 0 and 100 (decimals allowed, e.g. 20.25).'}, status=400)
            description = request.POST.get('description')

            print('Current user:', request.user, '| Authenticated:', request.user.is_authenticated)

            # Always use today's date for progress update
            from datetime import date
            progress_date = date.today()

            # Get current progress to validate against
            from projeng.models import ProjectProgress
            latest_progress = ProjectProgress.objects.filter(project=project).order_by('-date', '-created_at').first()
            current_progress = latest_progress.percentage_complete if latest_progress else (project.progress or 0)
            progress_increase = percentage_complete - current_progress
            
            # Validation: Prevent going backwards (unless explicitly allowed for corrections)
            if percentage_complete < current_progress:
                return JsonResponse({
                    'error': f'Progress cannot decrease. Current progress is {current_progress}%. If you need to correct this, please contact an administrator.'
                }, status=400)
            
            # Validation: Prevent unrealistic jumps (more than 30% increase in one update)
            if percentage_complete > current_progress + 30:
                return JsonResponse({
                    'error': f'Progress increase is too large. Current progress is {current_progress}%. Maximum allowed increase is 30% per update (up to {current_progress + 30}%).'
                }, status=400)
            
            # Validation: Require justification for increases >10%
            justification = request.POST.get('justification', '').strip()
            if progress_increase > 10 and not justification:
                return JsonResponse({
                    'error': f'Justification is required for progress increases greater than 10%. Please explain why the progress increased by {progress_increase}%.'
                }, status=400)
            
            # Validation: Require photos for increases >10%
            uploaded_photos = request.FILES.getlist('photos')
            if progress_increase > 10 and len(uploaded_photos) == 0:
                return JsonResponse({
                    'error': f'Photos are required for progress increases greater than 10%. Please upload at least one photo showing the work completed.'
                }, status=400)
            
            # Timeline validation disabled: engineers can enter any progress from current up to 100%.

            # Audit log for progress update
            import logging
            audit_logger = logging.getLogger('project_audit')
            if not audit_logger.handlers:
                handler = logging.FileHandler('project_audit.log')
                formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
                handler.setFormatter(formatter)
                audit_logger.addHandler(handler)
                audit_logger.setLevel(logging.INFO)
            audit_logger.info(f"User {request.user.username} updated progress for project {project.id} ({project.name}) to {percentage_complete}% on {progress_date}")

            # Get milestone if provided
            milestone_id = request.POST.get('milestone')
            milestone = None
            if milestone_id:
                try:
                    from projeng.models import ProjectMilestone
                    milestone = ProjectMilestone.objects.get(pk=milestone_id, project=project)
                except (ProjectMilestone.DoesNotExist, ValueError):
                    milestone = None
            
            progress = ProjectProgress(
                project=project,
                date=progress_date,
                percentage_complete=percentage_complete,
                description=description,
                milestone=milestone,
                justification=justification if progress_increase > 10 else None,
                created_by=request.user
            )
            progress.save()
            
            # If milestone is linked and progress reaches estimated contribution, mark milestone as completed
            if milestone and not milestone.is_completed:
                if percentage_complete >= milestone.estimated_progress_contribution:
                    milestone.mark_completed()
            print(f"DEBUG: Saved ProjectProgress with id={progress.id}, percentage_complete={progress.percentage_complete}, project_id={project.id}")

            # Update the parent project's progress field
            project.progress = percentage_complete
            # Store who made the update for notification purposes
            project._updated_by_username = request.user.get_full_name() or request.user.username
            project.save(update_fields=["progress"])
            print(f"DEBUG: Updated Project id={project.id} progress to {project.progress}")

            # Handle multiple photo uploads (already retrieved above for validation)
            for photo in uploaded_photos:
                ProgressPhoto.objects.create(
                    progress_update=progress,
                    image=photo
                )

            # Check if progress is 99% or more and update project status if needed
            if percentage_complete >= 99 and project.status != 'completed':
                project.status = 'completed'
                project.save(update_fields=["status"])
                print(f"DEBUG: ProjEngProject {project.prn} status updated to completed.")
                # Also update the corresponding monitoring project if it exists
                try:
                    from monitoring.models import Project as MonitoringProject
                    monitoring_project = MonitoringProject.objects.get(
                        name=project.name,
                        barangay=project.barangay
                    )
                    monitoring_project.status = 'completed'
                    monitoring_project.progress = percentage_complete
                    monitoring_project.save(update_fields=["status", "progress"])
                    print(f"DEBUG: MonitoringProject {monitoring_project.prn} status synced to completed.")
                except MonitoringProject.DoesNotExist:
                    print(f"DEBUG: No corresponding MonitoringProject found for {project.prn} ({project.name} in {project.barangay}).")
                    pass  # No corresponding monitoring project found
                except Exception as e:
                    print(f"ERROR: Failed to sync MonitoringProject status for {project.prn}: {e}")
            else:
                # Also update the corresponding monitoring project progress if it exists
                try:
                    from monitoring.models import Project as MonitoringProject
                    monitoring_project = MonitoringProject.objects.get(
                        name=project.name,
                        barangay=project.barangay
                    )
                    monitoring_project.progress = percentage_complete
                    monitoring_project.save(update_fields=["progress"])
                    print(f"DEBUG: MonitoringProject {monitoring_project.prn} progress synced to {percentage_complete}%.")
                except MonitoringProject.DoesNotExist:
                    print(f"DEBUG: No corresponding MonitoringProject found for {project.prn} ({project.name} in {project.barangay}).")
                    pass  # No corresponding monitoring project found
                except Exception as e:
                    print(f"ERROR: Failed to sync MonitoringProject progress for {project.prn}: {e}")

            # Notifications are now handled by the signal in projeng/signals.py
            # This prevents duplicate notifications

            return JsonResponse({
                'success': True,
                'message': 'Progress update added successfully',
                'progress': {
                    'id': progress.id,
                    'date': progress.date.strftime('%Y-%m-%d') if progress.date else '',
                    'percentage_complete': progress.percentage_complete,
                    'description': progress.description,
                    'photo_count': len(uploaded_photos),
                }
            })
        except Project.DoesNotExist:
            return JsonResponse({'error': 'Project not found'}, status=404)
        except Exception as e:
            logging.exception("Error adding progress update")
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
@transaction.atomic
def edit_progress_update(request, pk, update_id):
    project = get_object_or_404(Project, pk=pk)
    progress = get_object_or_404(
        ProjectProgress.objects.select_related('created_by', 'milestone').prefetch_related('photos'),
        pk=update_id,
        project=project,
    )

    # Permissions: head engineers can edit any; project engineers must be assigned
    if not is_head_engineer(request.user):
        if request.user not in project.assigned_engineers.all():
            raise PermissionDenied("You are not assigned to this project.")

    from projeng.models import ProjectMilestone
    milestones = ProjectMilestone.objects.filter(project=project).order_by('target_date', 'created_at')

    if request.method == 'GET':
        return render(request, 'projeng/edit_progress_update.html', {
            'project': project,
            'progress_update': progress,
            'milestones': milestones,
        })

    if request.method != 'POST':
        return HttpResponseNotAllowed(['GET', 'POST'])

    raw_percentage = request.POST.get('percentage_complete')
    try:
        new_percentage = round(float(raw_percentage), 2)
        if not (0 <= new_percentage <= 100):
            raise ValueError("Percentage out of range")
    except (TypeError, ValueError):
        return HttpResponseBadRequest("Invalid percentage value. Please enter a number between 0 and 100 (decimals allowed).")

    new_description = (request.POST.get('description') or '').strip()
    new_justification = (request.POST.get('justification') or '').strip()
    edit_reason = (request.POST.get('edit_reason') or '').strip()

    if not new_description:
        return HttpResponseBadRequest("Description is required.")
    if not edit_reason:
        return HttpResponseBadRequest("Edit reason is required.")

    milestone_id = (request.POST.get('milestone') or '').strip()
    milestone = None
    if milestone_id:
        try:
            milestone = ProjectMilestone.objects.get(pk=int(milestone_id), project=project)
        except Exception:
            milestone = None

    uploaded_photos = request.FILES.getlist('photos')

    old_percentage = progress.percentage_complete
    delta = new_percentage - old_percentage

    # Validation: prevent unrealistic jumps (more than 30% change in one edit)
    if delta > 30:
        return HttpResponseBadRequest(
            f"Progress increase is too large. Maximum allowed increase is 30% per edit (up to {old_percentage + 30}%)."
        )
    if delta < -30:
        return HttpResponseBadRequest(
            f"Progress decrease is too large. Maximum allowed decrease is 30% per edit (down to {old_percentage - 30}%)."
        )

    # Validation: require justification/photos for significant increases
    if delta > 10:
        if not new_justification:
            return HttpResponseBadRequest(
                f"Justification is required for progress increases greater than 10% (increase: {delta}%)."
            )
        existing_photo_count = progress.photos.count()
        if existing_photo_count + len(uploaded_photos) == 0:
            return HttpResponseBadRequest(
                "At least one photo is required for progress increases greater than 10%."
            )

    # Validation: require justification for any decrease (correction)
    if delta < 0 and not new_justification:
        return HttpResponseBadRequest("Justification is required when decreasing progress (correction).")

    # Timeline validation disabled (match add_progress).

    # Create audit history record
    ProjectProgressEditHistory.objects.create(
        progress_update=progress,
        edited_by=request.user,
        from_percentage=old_percentage,
        to_percentage=new_percentage,
        from_description=progress.description,
        to_description=new_description,
        from_justification=progress.justification,
        to_justification=new_justification or None,
        edit_reason=edit_reason,
        added_photos_count=len(uploaded_photos),
    )

    # Apply edits
    progress.percentage_complete = new_percentage
    progress.description = new_description
    progress.justification = new_justification or None
    progress.milestone = milestone
    progress.updated_by = request.user
    progress.is_edited = True
    progress.last_edit_reason = edit_reason
    progress.save()

    for photo in uploaded_photos:
        ProgressPhoto.objects.create(progress_update=progress, image=photo)

    # Recalculate the project's current progress from latest update
    latest_progress = (
        ProjectProgress.objects
        .filter(project=project)
        .order_by('-date', '-created_at')
        .first()
    )
    project.progress = latest_progress.percentage_complete if latest_progress else (project.progress or 0)
    project._updated_by_username = request.user.get_full_name() or request.user.username
    project.save(update_fields=["progress"])

    # Sync monitoring project if it exists
    try:
        monitoring_project = MonitoringProject.objects.get(name=project.name, barangay=project.barangay)
        monitoring_project.progress = project.progress
        if project.progress >= 99 and monitoring_project.status != 'completed':
            monitoring_project.status = 'completed'
            monitoring_project.save(update_fields=["status", "progress"])
        else:
            monitoring_project.save(update_fields=["progress"])
    except MonitoringProject.DoesNotExist:
        pass

    messages.success(request, "Progress update edited successfully.")
    return redirect('projeng:projeng_project_detail', pk=project.pk)

@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
@csrf_exempt
def add_cost_entry(request, pk):
    try:
        project = Project.objects.get(pk=pk)
        
        # Check permissions - head engineers can add cost entries to any project
        if not is_head_engineer(request.user):
            if request.user not in project.assigned_engineers.all():
                return JsonResponse({'error': 'You are not assigned to this project.'}, status=403)
    except Project.DoesNotExist:
        return JsonResponse({'error': 'Project not found.'}, status=404)
    
    if request.method == 'GET':
        # Render combined form page for adding progress update or cost entry
        from datetime import date
        today = date.today()
        from projeng.models import ProjectCost, ProjectProgress, ProjectMilestone
        
        # Get current progress percentage (for consistency, even though cost form doesn't use it)
        latest_progress = ProjectProgress.objects.filter(project=project).order_by('-date', '-created_at').first()
        current_progress = latest_progress.percentage_complete if latest_progress else (project.progress or 0)
        
        # Get milestones for this project
        milestones = ProjectMilestone.objects.filter(project=project, is_completed=False).order_by('target_date')
        
        return render(request, 'projeng/add_update.html', {
            'project': project,
            'today': today,
            'cost_types': ProjectCost.COST_TYPES,
            'current_progress': current_progress,
            'milestones': milestones
        })
    
    if request.method == 'POST':
        try:
            from decimal import Decimal, InvalidOperation
            from projeng.models import ProjectCost
            
            # Use request.POST and request.FILES for multipart/form-data
            date = request.POST.get('date')
            cost_type = request.POST.get('cost_type')
            description = request.POST.get('description')
            amount_str = request.POST.get('amount')
            receipt = request.FILES.get('receipt')

            # Validate and convert amount to Decimal
            if not amount_str:
                return JsonResponse({'error': 'Amount is required'}, status=400)
            
            try:
                amount = Decimal(str(amount_str))
            except (ValueError, InvalidOperation):
                return JsonResponse({'error': 'Invalid amount format'}, status=400)

            # Validate and parse date
            if not date:
                return JsonResponse({'error': 'Date is required'}, status=400)
            
            # Parse date string to date object
            # Handle different date formats: YYYY-MM-DD, MM/DD/YYYY, etc.
            from datetime import datetime
            try:
                # Try common date formats
                date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']
                parsed_date = None
                for fmt in date_formats:
                    try:
                        parsed_date = datetime.strptime(date, fmt).date()
                        break
                    except ValueError:
                        continue
                
                if not parsed_date:
                    # If no format matches, try Django's date parser
                    from django.utils.dateparse import parse_date
                    parsed_date = parse_date(date)
                    
                if not parsed_date:
                    return JsonResponse({'error': 'Invalid date format. Please use YYYY-MM-DD or MM/DD/YYYY'}, status=400)
            except (ValueError, TypeError) as e:
                return JsonResponse({'error': f'Invalid date format: {str(e)}'}, status=400)

            cost = ProjectCost(
                project=project,
                date=parsed_date,
                cost_type=cost_type,
                description=description,
                amount=amount,
                created_by=request.user
            )
            if receipt:
                cost.receipt = receipt
            cost.save()

            return JsonResponse({
                'success': True,
                'message': 'Cost entry added successfully',
                'cost': {
                    'date': str(cost.date),
                    'cost_type': cost.get_cost_type_display(),
                    'description': cost.description,
                    'amount': str(cost.amount),
                }
            })
        except Project.DoesNotExist:
            return JsonResponse({'error': 'Project not found'}, status=404)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
def dashboard_progress_over_time_data(request):
    """API endpoint for Project Progress Over Time chart (week/month/year)."""
    from .models import Project, ProjectProgress
    from datetime import datetime, timedelta
    from collections import defaultdict
    from django.utils import timezone
    
    if is_head_engineer(request.user):
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(assigned_engineers=request.user)
    
    # Determine period: week / month / year (default month)
    period = (request.GET.get('period') or 'month').strip().lower()
    today = timezone.now().date()
    if period == 'year':
        start_date = today - timedelta(days=365 * 5)
        bucket_fmt = '%Y'  # year
        label_fmt = '%Y'
    elif period == 'week':
        # Last 12 weeks
        start_date = today - timedelta(days=7 * 12)
        bucket_fmt = '%G-%V'  # ISO year-week
        label_fmt = 'Wk %V %b %d'
    else:
        # Default: last 12 months
        start_date = today - timedelta(days=365)
        bucket_fmt = '%Y-%m'
        label_fmt = '%b %Y'

    # Get progress updates since start_date
    progress_updates = ProjectProgress.objects.filter(
        project__in=projects,
        date__gte=start_date
    ).order_by('date')
    
    # Group by bucket depending on period
    bucket_progress = defaultdict(list)
    for update in progress_updates:
        # Guard against missing dates / percentages
        if not update.date or update.percentage_complete is None:
            continue
        if period == 'week':
            iso_year, iso_week, _ = update.date.isocalendar()
            bucket_key = f"{iso_year}-{iso_week:02d}"
        else:
            bucket_key = update.date.strftime(bucket_fmt)
        bucket_progress[bucket_key].append(update.percentage_complete)
    
    # Calculate average progress per bucket
    buckets = sorted(bucket_progress.keys())
    avg_progress = [sum(bucket_progress[b]) / len(bucket_progress[b]) for b in buckets] if buckets else []
    
    # Format labels
    labels = []
    for key in buckets:
        try:
            if period == 'year':
                dt = datetime.strptime(key, '%Y')
            elif period == 'week':
                year, week = map(int, key.split('-'))
                # ISO week to date (Monday of that week)
                dt = datetime.fromisocalendar(year, week, 1)
            else:
                dt = datetime.strptime(key, '%Y-%m')
            labels.append(dt.strftime(label_fmt))
        except ValueError:
            labels.append(key)
    
    # If no data, return empty chart
    if not labels:
        labels = ['No Data']
        avg_progress = [0]
    
    return JsonResponse({
    'labels': labels,
        'datasets': [{
            'label': 'Average Progress (%)',
            'data': avg_progress,
            'borderColor': 'rgba(54, 162, 235, 1)',
            'backgroundColor': 'rgba(54, 162, 235, 0.1)',
            'tension': 0.4,
            'fill': True
        }]
    })

@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
def dashboard_budget_utilization_data(request):
    """API endpoint for Budget Utilization chart (week/month/year)."""
    from .models import Project, ProjectCost
    from django.db.models import Sum
    from datetime import timedelta
    from django.utils import timezone
    
    if is_head_engineer(request.user):
        projects = Project.objects.filter(project_cost__isnull=False)
    else:
        projects = Project.objects.filter(
            assigned_engineers=request.user,
            project_cost__isnull=False
        )

    # Period window based on ProjectCost.date
    period = (request.GET.get('period') or 'month').strip().lower()
    today = timezone.now().date()
    if period == 'year':
        start_date = today - timedelta(days=365 * 5)
    elif period == 'week':
        start_date = today - timedelta(days=7 * 12)
    else:
        start_date = today - timedelta(days=365)

    # Calculate budget utilization for each project
    project_data = []
    for project in projects:
        total_cost = ProjectCost.objects.filter(
            project=project,
            date__gte=start_date
        ).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        if project.project_cost and float(project.project_cost) > 0:
            utilization = (float(total_cost) / float(project.project_cost)) * 100
            project_data.append({
                'name': project.name[:20] + '...' if len(project.name) > 20 else project.name,
                'utilization': round(utilization, 1)
            })
    
    # Sort by utilization and take top 10
    project_data.sort(key=lambda x: x['utilization'], reverse=True)
    project_data = project_data[:10]
    
    labels = [p['name'] for p in project_data]
    data = [p['utilization'] for p in project_data]
    
    return JsonResponse({
        'labels': labels,
        'datasets': [{
            'label': 'Budget Utilization (%)',
            'data': data,
            'backgroundColor': [
                'rgba(255, 99, 132, 0.6)' if d > 100 else
                'rgba(255, 206, 86, 0.6)' if d > 80 else
                'rgba(75, 192, 192, 0.6)'
                for d in data
            ],
            'borderColor': [
                'rgba(255, 99, 132, 1)' if d > 100 else
                'rgba(255, 206, 86, 1)' if d > 80 else
                'rgba(75, 192, 192, 1)'
                for d in data
            ],
            'borderWidth': 1
        }]
    })

@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
def dashboard_cost_breakdown_data(request):
    """API endpoint for Cost Breakdown by Type chart (week/month/year)."""
    from .models import Project, ProjectCost
    from django.db.models import Sum
    from datetime import timedelta
    from django.utils import timezone
    
    if is_head_engineer(request.user):
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(assigned_engineers=request.user)

    # Period window for costs
    period = (request.GET.get('period') or 'month').strip().lower()
    today = timezone.now().date()
    if period == 'year':
        start_date = today - timedelta(days=365 * 5)
    elif period == 'week':
        start_date = today - timedelta(days=7 * 12)
    else:
        start_date = today - timedelta(days=365)

    # Get cost breakdown by type
    cost_by_type = ProjectCost.objects.filter(
        project__in=projects,
        date__gte=start_date
    ).values('cost_type').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    labels = [item['cost_type'].title() for item in cost_by_type]
    data = [float(item['total']) for item in cost_by_type]
    
    colors = {
        'Material': 'rgba(54, 162, 235, 0.6)',
        'Labor': 'rgba(255, 206, 86, 0.6)',
        'Equipment': 'rgba(75, 192, 192, 0.6)',
        'Other': 'rgba(153, 102, 255, 0.6)'
    }
    
    background_colors = [colors.get(label, 'rgba(201, 203, 207, 0.6)') for label in labels]
    border_colors = [bg.replace('0.6', '1') for bg in background_colors]
    
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

@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
def dashboard_projects_by_barangay_data(request):
    """API endpoint for Projects by Barangay chart (week/month/year)."""
    from .models import Project
    from django.db.models import Count
    from datetime import timedelta
    from django.utils import timezone
    
    if is_head_engineer(request.user):
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(assigned_engineers=request.user)

    # Time window based on project start_date
    period = (request.GET.get('period') or 'month').strip().lower()
    today = timezone.now().date()
    if period == 'year':
        start_date = today - timedelta(days=365 * 5)
    elif period == 'week':
        start_date = today - timedelta(days=7 * 12)
    else:
        start_date = today - timedelta(days=365)

    projects = projects.filter(start_date__isnull=False, start_date__gte=start_date)

    # Count projects by barangay
    barangay_counts = projects.values('barangay').annotate(
        count=Count('id')
    ).order_by('-count')[:10]  # Top 10 barangays
    
    labels = [item['barangay'] for item in barangay_counts]
    data = [item['count'] for item in barangay_counts]
    
    return JsonResponse({
        'labels': labels,
        'datasets': [{
            'label': 'Number of Projects',
            'data': data,
            'backgroundColor': 'rgba(54, 162, 235, 0.6)',
            'borderColor': 'rgba(54, 162, 235, 1)',
            'borderWidth': 1
        }]
    })

@csrf_exempt
@login_required
def engineer_projects_api(request, engineer_id):
    try:
        projects = Project.objects.filter(assigned_engineers__id=engineer_id)
        projects_data = [
            {"name": p.name, "status": p.status} for p in projects
        ]
        # Count by status
        status_counts = {}
        for p in projects:
            status = p.status or "Unknown"
            status_counts[status] = status_counts.get(status, 0) + 1
        return JsonResponse({
            "projects": projects_data,
            "status_counts": status_counts,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@user_passes_test(is_project_engineer, login_url='/accounts/login/')
@csrf_exempt
def upload_project_photo(request, pk):
    # This endpoint is disabled because ProgressPhoto requires a progress_update.
    return JsonResponse({'success': False, 'error': 'Direct photo upload is not supported. Please upload photos as part of a progress update.'}, status=400)

@user_passes_test(is_project_engineer, login_url='/accounts/login/')
@csrf_exempt
def upload_project_document(request, pk):
    if request.method == 'POST':
        project = get_object_or_404(Project, pk=pk)
        if request.user not in project.assigned_engineers.all():
            return JsonResponse({'success': False, 'error': 'You are not assigned to this project.'}, status=403)
        
        # Handle multiple files
        files = request.FILES.getlist('files')
        names = request.POST.getlist('names')  # Array of names corresponding to files
        
        if not files:
            return JsonResponse({'success': False, 'error': 'No files provided'}, status=400)
        
        uploaded_documents = []
        errors = []
        
        for i, file in enumerate(files):
            # Get corresponding name or use filename
            name = names[i] if i < len(names) and names[i].strip() else file.name
            
            try:
                document = ProjectDocument.objects.create(
                    project=project,
                    file=file,
                    name=name,
                    uploaded_by=request.user
                )
                uploaded_documents.append({
                    'name': document.name,
                    'file_url': document.file.url,
                    'uploaded_by': document.uploaded_by.get_full_name() or document.uploaded_by.username,
                    'uploaded_at': document.uploaded_at.strftime('%B %d, %Y')
                })
            except Exception as e:
                errors.append(f"Failed to upload {file.name}: {str(e)}")
        
        if uploaded_documents:
            return JsonResponse({
                'success': True,
                'message': f'{len(uploaded_documents)} document(s) uploaded successfully',
                'documents': uploaded_documents,
                'errors': errors if errors else None
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to upload documents. ' + '; '.join(errors) if errors else 'Unknown error'
            }, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
@csrf_exempt
def get_project_documents(request, pk):
    """API endpoint to get all documents for a project"""
    try:
        project = Project.objects.get(pk=pk)
        
        # Check permissions
        if not is_head_engineer(request.user):
            if request.user not in project.assigned_engineers.all():
                return JsonResponse({'error': 'You are not assigned to this project.'}, status=403)
        
        documents = ProjectDocument.objects.filter(project=project).select_related('uploaded_by').order_by('-uploaded_at')
        
        documents_data = []
        for doc in documents:
            documents_data.append({
                'id': doc.id,
                'name': doc.name,
                'file_url': doc.file.url,
                'uploaded_by': doc.uploaded_by.get_full_name() if doc.uploaded_by else 'Unknown',
                'uploaded_at': doc.uploaded_at.strftime('%B %d, %Y %I:%M %p')
            })
        
        return JsonResponse({'documents': documents_data}, status=200)
    except Project.DoesNotExist:
        return JsonResponse({'error': 'Project not found.'}, status=404)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching documents for project {pk}: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

# Report Export Views
@login_required
def export_reports_csv(request):
    # Get projects assigned to the current project engineer
    from gistagum.access_control import is_head_engineer
    if is_head_engineer(request.user):
        assigned_projects = Project.objects.all()
    else:
        assigned_projects = Project.objects.filter(assigned_engineers=request.user)

    # Apply all filters (same as my_reports_view)
    barangay_filter = request.GET.get('barangay')
    status_filter = request.GET.get('status')
    start_date_filter = request.GET.get('start_date')
    end_date_filter = request.GET.get('end_date')
    source_of_funds_filter = request.GET.get('source_of_funds')
    project_type_filter = request.GET.get('project_type')
    
    if barangay_filter:
        assigned_projects = assigned_projects.filter(barangay=barangay_filter)
    if status_filter:
        # Handle "in_progress" to match both "in_progress" and "ongoing" statuses
        if status_filter == 'in_progress':
            assigned_projects = assigned_projects.filter(Q(status='in_progress') | Q(status='ongoing'))
        else:
            assigned_projects = assigned_projects.filter(status=status_filter)
    if start_date_filter:
        try:
            from datetime import datetime
            start_date = datetime.strptime(start_date_filter, '%Y-%m-%d').date()
            assigned_projects = assigned_projects.filter(start_date__gte=start_date)
        except ValueError:
            pass
    if end_date_filter:
        try:
            from datetime import datetime
            end_date = datetime.strptime(end_date_filter, '%Y-%m-%d').date()
            assigned_projects = assigned_projects.filter(end_date__lte=end_date)
        except ValueError:
            pass
    if source_of_funds_filter:
        assigned_projects = assigned_projects.filter(source_of_funds=source_of_funds_filter)
    if project_type_filter:
        try:
            assigned_projects = assigned_projects.filter(project_type_id=int(project_type_filter))
        except (ValueError, TypeError):
            pass

    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="assigned_projects_report.csv"'

    writer = csv.writer(response)
    # Write the header row
    writer.writerow(['#', 'PRN#', 'Name of Project', 'Project Description', 'Barangay', 'Project Cost', 'Source of Funds', 'Project Type', 'Date Started', 'Date Ended', 'Status'])

    # Write data rows (use select_related for project_type)
    for i, project in enumerate(assigned_projects.select_related('project_type')):
        writer.writerow([
            i + 1,
            project.prn or '',
            project.name or '',
            project.description or '',
            project.barangay or '',
            project.project_cost if project.project_cost is not None else '',
            project.source_of_funds or '',
            project.project_type.name if project.project_type else '',
            project.start_date.strftime('%Y-%m-%d') if project.start_date else '',
            project.end_date.strftime('%Y-%m-%d') if project.end_date else '',
            project.get_status_display() or '',
        ])

    return response 

@login_required
def export_reports_excel(request):
    # Get projects assigned to the current project engineer
    from gistagum.access_control import is_head_engineer
    if is_head_engineer(request.user):
        assigned_projects = Project.objects.all()
    else:
        assigned_projects = Project.objects.filter(assigned_engineers=request.user)

    # Apply all filters (same as my_reports_view)
    barangay_filter = request.GET.get('barangay')
    status_filter = request.GET.get('status')
    start_date_filter = request.GET.get('start_date')
    end_date_filter = request.GET.get('end_date')
    source_of_funds_filter = request.GET.get('source_of_funds')
    project_type_filter = request.GET.get('project_type')
    
    if barangay_filter:
        assigned_projects = assigned_projects.filter(barangay=barangay_filter)
    if status_filter:
        # Handle "in_progress" to match both "in_progress" and "ongoing" statuses
        if status_filter == 'in_progress':
            assigned_projects = assigned_projects.filter(Q(status='in_progress') | Q(status='ongoing'))
        else:
            assigned_projects = assigned_projects.filter(status=status_filter)
    if start_date_filter:
        try:
            from datetime import datetime
            start_date = datetime.strptime(start_date_filter, '%Y-%m-%d').date()
            assigned_projects = assigned_projects.filter(start_date__gte=start_date)
        except ValueError:
            pass
    if end_date_filter:
        try:
            from datetime import datetime
            end_date = datetime.strptime(end_date_filter, '%Y-%m-%d').date()
            assigned_projects = assigned_projects.filter(end_date__lte=end_date)
        except ValueError:
            pass
    if source_of_funds_filter:
        assigned_projects = assigned_projects.filter(source_of_funds=source_of_funds_filter)
    if project_type_filter:
        try:
            assigned_projects = assigned_projects.filter(project_type_id=int(project_type_filter))
        except (ValueError, TypeError):
            pass

    # Create a new workbook and select the active sheet
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Assigned Projects"

    # Write the header row
    headers = ['#', 'PRN#', 'Name of Project', 'Project Description', 'Barangay', 'Project Cost', 'Source of Funds', 'Project Type', 'Date Started', 'Date Ended', 'Status']
    sheet.append(headers)

    # Write data rows
    for i, project in enumerate(assigned_projects.select_related('project_type')):
        sheet.append([
            i + 1,
            project.prn or '',
            project.name or '',
            project.description or '',
            project.barangay or '',
            project.project_cost if project.project_cost is not None else '',
            project.source_of_funds or '',
            project.project_type.name if project.project_type else '',
            project.start_date.strftime('%Y-%m-%d') if project.start_date else '',
            project.end_date.strftime('%Y-%m-%d') if project.end_date else '',
            project.get_status_display() or '',
        ])

    # Create an in-memory BytesIO stream
    excel_file = io.BytesIO()
    workbook.save(excel_file)
    excel_file.seek(0)

    # Create the HttpResponse object with the appropriate Excel header.
    response = HttpResponse(excel_file.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="assigned_projects_report.xlsx"'

    return response


@login_required
def export_reports_json(request):
    """Return filtered projects as JSON for client-side PDF generation (pdfmake)."""
    from gistagum.access_control import is_head_engineer
    if is_head_engineer(request.user):
        assigned_projects = Project.objects.all()
    else:
        assigned_projects = Project.objects.filter(assigned_engineers=request.user)

    barangay_filter = request.GET.get('barangay')
    status_filter = request.GET.get('status')
    start_date_filter = request.GET.get('start_date')
    end_date_filter = request.GET.get('end_date')
    source_of_funds_filter = request.GET.get('source_of_funds')
    project_type_filter = request.GET.get('project_type')

    if barangay_filter:
        assigned_projects = assigned_projects.filter(barangay=barangay_filter)
    if status_filter:
        if status_filter == 'in_progress':
            assigned_projects = assigned_projects.filter(Q(status='in_progress') | Q(status='ongoing'))
        else:
            assigned_projects = assigned_projects.filter(status=status_filter)
    if start_date_filter:
        try:
            start_date = datetime.strptime(start_date_filter, '%Y-%m-%d').date()
            assigned_projects = assigned_projects.filter(start_date__gte=start_date)
        except ValueError:
            pass
    if end_date_filter:
        try:
            end_date = datetime.strptime(end_date_filter, '%Y-%m-%d').date()
            assigned_projects = assigned_projects.filter(end_date__lte=end_date)
        except ValueError:
            pass
    if source_of_funds_filter:
        assigned_projects = assigned_projects.filter(source_of_funds=source_of_funds_filter)
    if project_type_filter:
        try:
            assigned_projects = assigned_projects.filter(project_type_id=int(project_type_filter))
        except (ValueError, TypeError):
            pass

    projects_list = []
    for project in assigned_projects.select_related('project_type').order_by('name'):
        status_display = (
            'Completed' if project.status == 'completed' else
            'Delayed' if project.status == 'delayed' else
            'Ongoing' if project.status in ['in_progress', 'ongoing'] else
            'Planned' if project.status in ['planned', 'pending'] else
            (project.status or '').title()
        )
        projects_list.append({
            'id': project.id,
            'prn': project.prn or '',
            'name': project.name or '',
            'description': (project.description or '')[:200],
            'barangay': project.barangay or '',
            'project_cost': str(project.project_cost) if project.project_cost is not None else '',
            'source_of_funds': project.source_of_funds or '',
            'project_type_name': project.project_type.name if project.project_type else '',
            'start_date': str(project.start_date) if project.start_date else '',
            'end_date': str(project.end_date) if project.end_date else '',
            'status': project.status or '',
            'status_display': status_display,
            'progress': project.progress or 0,
        })
    return JsonResponse({'projects': projects_list})


@login_required
def export_reports_pdf(request):
    """Legacy server-side PDF endpoint. PDF export is now client-side via pdfmake.
    Redirects to My Reports page."""
    messages.info(request, 'Use the Export button on this page, then Export PDF.')
    return redirect('projeng:projeng_my_reports') 

@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
@require_GET
def map_projects_api(request):
    from django.db.models import Max
    from django.utils import timezone
    
    # Role-based queryset
    if is_head_engineer(request.user):
        all_projects = Project.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        )
    else:
        all_projects = Project.objects.filter(
            assigned_engineers=request.user,
            latitude__isnull=False,
            longitude__isnull=False
        )
    projects_with_coords = [p for p in all_projects if p.latitude != '' and p.longitude != '']
    
    # Get project IDs for batch progress queries
    project_ids = [p.id for p in projects_with_coords]
    latest_progress_percent = {}
    
    if project_ids:
        # Get latest progress for delay calculation
        latest_progress_qs = ProjectProgress.objects.filter(
            project_id__in=project_ids
        ).values('project_id').annotate(
            max_date=Max('date'),
            max_created=Max('created_at')
        )
        for item in latest_progress_qs:
            latest = ProjectProgress.objects.filter(
                project_id=item['project_id'],
                date=item['max_date'],
                created_at=item['max_created']
            ).order_by('-created_at').first()
            if latest and latest.percentage_complete is not None:
                latest_progress_percent[item['project_id']] = float(latest.percentage_complete)
    
    # Calculate status dynamically (including delayed)
    today = timezone.now().date()
    projects_data = []
    for p in projects_with_coords:
        progress = latest_progress_percent.get(p.id, 0)
        stored_status = p.status or ''
        
        # Calculate actual status dynamically (same logic as my_projects_view)
        calculated_status = stored_status
        # Completed when progress >= 99
        if progress >= 99:
            calculated_status = 'completed'
        # Delayed when end date has passed and progress is still below 99
        elif p.end_date and p.end_date < today and progress < 99:
            calculated_status = 'delayed'
        elif stored_status == 'delayed':
            calculated_status = 'delayed'
        elif stored_status in ['in_progress', 'ongoing']:
            calculated_status = 'in_progress'
        elif stored_status in ['planned', 'pending']:
            calculated_status = 'planned'
        
        projects_data.append({
            'id': p.id,
            'name': p.name,
            'latitude': float(p.latitude),
            'longitude': float(p.longitude),
            'barangay': p.barangay,
            'status': p.status,  # Keep original status
            'calculated_status': calculated_status,  # Add calculated status for filtering
            'description': p.description,
            'project_cost': str(p.project_cost) if p.project_cost is not None else "",
            'source_of_funds': p.source_of_funds,
            'prn': p.prn,
            'start_date': str(p.start_date) if p.start_date else "",
            'end_date': str(p.end_date) if p.end_date else "",
            'image': p.image.url if p.image else "",
            'progress': progress,
            'zone_type': p.zone_type or '',
        })
    return JsonResponse({'projects': projects_data}) 

@user_passes_test(is_project_engineer, login_url='/accounts/login/')
@require_GET
def dashboard_card_data_api(request):
    from .models import Project, ProjectProgress
    all_assigned_projects = Project.objects.filter(assigned_engineers=request.user)
    today = timezone.now().date()
    status_counts = {'planned': 0, 'in_progress': 0, 'completed': 0, 'delayed': 0}
    for project in all_assigned_projects:
        latest_progress = ProjectProgress.objects.filter(project=project).order_by('-date').first()
        progress = float(latest_progress.percentage_complete) if latest_progress else 0
        status = project.status
        # Completed when progress >= 99
        if progress >= 99:
            status = 'completed'
        # Delayed when end date has passed and progress is still below 99
        elif project.end_date and project.end_date < today and progress < 99:
            status = 'delayed'
        elif status in ['in_progress', 'ongoing']:
            status = 'in_progress'
        elif status in ['planned', 'pending']:
            status = 'planned'
        if status == 'completed':
            status_counts['completed'] += 1
        elif status == 'in_progress':
            status_counts['in_progress'] += 1
        elif status == 'delayed':
            status_counts['delayed'] += 1
        elif status == 'planned':
            status_counts['planned'] += 1
    total_projects = all_assigned_projects.count()
    delayed_count = status_counts['delayed']
    return JsonResponse({
        'total_projects': total_projects,
        'status_counts': status_counts,
        'delayed_count': delayed_count,
    }) 

@user_passes_test(is_head_engineer, login_url='/accounts/login/')
@csrf_exempt
@transaction.atomic
def project_delete_api(request, pk):
    print(f"DEBUG: Received delete request for project id: {pk}, method: {request.method}")
    if request.method == 'POST' or request.method == 'DELETE':
        try:
            deleted = False
            # Try MonitoringProject first
            monitoring_project = MonitoringProject.objects.filter(pk=pk).first()
            if monitoring_project:
                prn = getattr(monitoring_project, 'prn', None)
                name = getattr(monitoring_project, 'name', None)
                barangay = getattr(monitoring_project, 'barangay', None)
                monitoring_project.delete()
                deleted = True
                # Try to delete corresponding ProjEngProject
                if prn:
                    Project.objects.filter(prn=prn).delete()
                elif name and barangay:
                    Project.objects.filter(name=name, barangay=barangay).delete()
            else:
                # Try ProjEngProject
                projeng_project = Project.objects.filter(pk=pk).first()
                if projeng_project:
                    prn = getattr(projeng_project, 'prn', None)
                    name = getattr(projeng_project, 'name', None)
                    barangay = getattr(projeng_project, 'barangay', None)
                    projeng_project.delete()
                    deleted = True
                    # Try to delete corresponding MonitoringProject
                    if prn:
                        MonitoringProject.objects.filter(prn=prn).delete()
                    elif name and barangay:
                        MonitoringProject.objects.filter(name=name, barangay=barangay).delete()
            if deleted:
                print(f"DEBUG: Deleted project(s) with id {pk} and corresponding entries.")
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Project not found'}, status=404)
        except Exception as e:
            print(f"DEBUG: Exception occurred: {e}")
            import traceback; traceback.print_exc()
            transaction.set_rollback(True)
            return JsonResponse({'success': False, 'error': f'An unexpected error occurred: {str(e)}'}, status=500)
    print("DEBUG: Method not allowed")
    return HttpResponseNotAllowed(['POST', 'DELETE']) 

@login_required
def notifications_view(request):
    """View for all Project Engineers, Head Engineers, and Admins to manage their notifications"""
    # Allow all users in Project Engineer, Head Engineer, or is_superuser
    if not (
        request.user.groups.filter(name='Project Engineer').exists() or
        request.user.groups.filter(name='Head Engineer').exists() or
        request.user.is_superuser
    ):
        messages.error(request, "You don't have permission to view notifications.")
        return redirect('projeng:projeng_dashboard')

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
            try:
                updated_count = notifications.filter(is_read=False).update(is_read=True)
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': f'{updated_count} notifications marked as read'})
                messages.success(request, f"All {updated_count} notifications marked as read.")
                return redirect('projeng:projeng_notifications')
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)})
                messages.error(request, f"Error marking notifications as read: {str(e)}")
                return redirect('projeng:projeng_notifications')

        elif action == 'delete' and notification_id:
            try:
                notification = Notification.objects.get(id=notification_id, recipient=request.user)
                notification.delete()
                return JsonResponse({'success': True})
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
                return redirect('projeng:projeng_notifications')
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)})
                messages.error(request, f"Error deleting notifications: {str(e)}")
                return redirect('projeng:projeng_notifications')

    unread_count = notifications.filter(is_read=False).count()

    context = {
        'notifications': notifications,
        'unread_count': unread_count,
    }
    return render(request, 'projeng/notifications.html', context)

@login_required
@require_GET
def notifications_api(request):
    """API endpoint for real-time notifications"""
    if not (
        request.user.groups.filter(name='Project Engineer').exists() or
        request.user.groups.filter(name='Head Engineer').exists() or
        request.user.is_superuser
    ):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:10]
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    
    return JsonResponse({
        'unread_count': unread_count,
        'notifications': [
            {
                'id': n.id,
                'message': n.message,
                'created_at': timezone.localtime(n.created_at).isoformat(),  # Convert to local timezone
                'is_read': n.is_read
            }
            for n in notifications
        ]
    })

@login_required
@require_GET
def get_project_from_notification_api(request):
    """API endpoint to get project ID from notification message"""
    from .utils import get_project_from_notification
    import logging
    
    logger = logging.getLogger(__name__)
    
    message = request.GET.get('message', '')
    if not message:
        return JsonResponse({'error': 'Message parameter required'}, status=400)
    
    # Decode URL encoding
    import urllib.parse
    message = urllib.parse.unquote(message)
    
    # Also handle unicode escapes in URL-encoded message
    message = message.replace('\\u0027', "'").replace('\\u0022', '"')
    
    logger.info(f"API request to get project from notification (decoded): {message[:200]}...")
    
    # Get project ID
    project_id = get_project_from_notification(message)
    logger.info(f"API response: project_id={project_id}")
    
    if project_id is None:
        logger.warning(f"Could not find project for message: {message[:200]}")
        # Try to list some projects for debugging
        from .models import Project
        sample_projects = Project.objects.all()[:10]
        logger.info(f"Sample projects in database (first 10):")
        for p in sample_projects:
            logger.info(f"  - ID: {p.id}, Name: '{p.name}', PRN: '{p.prn}'")
        
        # Also try to find projects with similar PRNs
        import re
        prn_match = re.search(r"PRN[:\s]*([A-Z0-9\s]+)", message, re.IGNORECASE)
        if prn_match:
            extracted_prn = prn_match.group(1).strip()
            logger.info(f"Searching for projects with PRN containing '{extracted_prn}'...")
            similar_projects = Project.objects.filter(prn__icontains=extracted_prn)[:5]
            for p in similar_projects:
                logger.info(f"  - Found similar: ID: {p.id}, Name: '{p.name}', PRN: '{p.prn}'")
    
    return JsonResponse({'project_id': project_id})

@login_required
@require_GET
def projects_updates_api(request):
    """API endpoint for real-time project updates"""
    from django.utils import timezone
    from datetime import timedelta
    
    # Get projects updated in the last 5 minutes
    recent_time = timezone.now() - timedelta(minutes=5)
    
    if request.user.groups.filter(name='Head Engineer').exists() or request.user.is_superuser:
        # Head engineers see all projects
        recent_projects = Project.objects.filter(
            updated_at__gte=recent_time
        ).order_by('-updated_at')[:10]
    elif request.user.groups.filter(name='Project Engineer').exists():
        # Project engineers see their assigned projects
        recent_projects = Project.objects.filter(
            assigned_engineers=request.user,
            updated_at__gte=recent_time
        ).order_by('-updated_at')[:10]
    else:
        recent_projects = Project.objects.none()
    
    return JsonResponse({
        'updates': [
            {
                'id': p.id,
                'name': p.name,
                'status': p.status,
                'updated_at': timezone.localtime(p.updated_at).isoformat(),  # Convert to local timezone
                'barangay': p.barangay or '',
            }
            for p in recent_projects
        ],
        'count': recent_projects.count()
    }) 

# ============================================================================
# Phase 2: Barangay Metadata and Zoning API Endpoints
# ============================================================================

@require_http_methods(["GET"])
@login_required
def barangay_metadata_api(request):
    """
    Return all barangay metadata.
    Accessible to all authenticated users (for map display).
    """
    barangays = BarangayMetadata.objects.all().order_by('name')
    count = barangays.count()
    
    # Log warning if no data exists (for debugging)
    if count == 0:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning('BarangayMetadata table is empty! Run: python manage.py populate_barangay_metadata')
    
    data = []
    for barangay in barangays:
        data.append({
            'name': barangay.name,
            'population': barangay.population,
            'land_area': float(barangay.land_area) if barangay.land_area else None,
            'density': float(barangay.density) if barangay.density else None,
            'growth_rate': float(barangay.growth_rate) if barangay.growth_rate else None,
            'barangay_class': barangay.barangay_class,
            'economic_class': barangay.economic_class,
            'elevation_type': barangay.elevation_type,
            'industrial_zones': barangay.industrial_zones,
            'primary_industries': barangay.primary_industries,
            'special_features': barangay.special_features,
            'zoning_summary': barangay.get_zoning_summary(),
        })
    
    return JsonResponse({
        'barangays': data,
        'count': count,  # Include count for debugging
        'message': 'No barangay metadata found. Run: python manage.py populate_barangay_metadata' if count == 0 else None
    })

@require_http_methods(["GET"])
@head_engineer_required
def barangay_zoning_stats_api(request):
    """
    Return zoning statistics with project counts.
    Accessible to Head Engineers only (for analytics dashboard).
    """
    # Get project counts per barangay
    project_counts = Project.objects.values('barangay').annotate(
        total_projects=Count('id'),
        total_cost=Sum('project_cost'),
        completed=Count('id', filter=Q(status='completed')),
        ongoing=Count('id', filter=Q(status__in=['in_progress', 'ongoing'])),
        planned=Count('id', filter=Q(status='planned')),
        delayed=Count('id', filter=Q(status='delayed')),
    )
    
    # Convert to dictionary for easier lookup
    project_counts_dict = {
        item['barangay']: item 
        for item in project_counts 
        if item['barangay']
    }
    
    # Combine with metadata
    stats = {}
    for barangay in BarangayMetadata.objects.all().order_by('name'):
        project_data = project_counts_dict.get(barangay.name, {})
        stats[barangay.name] = {
            'metadata': {
                'barangay_class': barangay.barangay_class,
                'economic_class': barangay.economic_class,
                'elevation_type': barangay.elevation_type,
                'population': barangay.population,
                'density': float(barangay.density) if barangay.density else None,
                'growth_rate': float(barangay.growth_rate) if barangay.growth_rate else None,
            },
            'projects': {
                'total': project_data.get('total_projects', 0),
                'completed': project_data.get('completed', 0),
                'ongoing': project_data.get('ongoing', 0),
                'planned': project_data.get('planned', 0),
                'delayed': project_data.get('delayed', 0),
                'total_cost': float(project_data.get('total_cost', 0)) if project_data.get('total_cost') else 0,
            }
        }
    
    return JsonResponse({'stats': stats})

@require_http_methods(["GET"])
@login_required
def barangay_zone_data_api(request):
    """
    Return zone data aggregated by barangay for map visualization.
    Shows which zone types have projects in each barangay.
    """
    from collections import defaultdict
    
    # Get all projects with zone_type
    projects_with_zones = Project.objects.filter(
        zone_type__isnull=False
    ).exclude(zone_type='')
    
    # Aggregate by barangay and zone_type
    barangay_zone_data = defaultdict(lambda: defaultdict(int))
    zone_types_in_barangay = defaultdict(set)
    
    for project in projects_with_zones:
        if project.barangay and project.zone_type:
            barangay_zone_data[project.barangay][project.zone_type] += 1
            zone_types_in_barangay[project.barangay].add(project.zone_type)
    
    # Get all active zones from ZoningZone model
    all_zones = ZoningZone.objects.filter(is_active=True)
    zones_by_barangay = defaultdict(list)
    
    for zone in all_zones:
        zones_by_barangay[zone.barangay].append({
            'zone_type': zone.zone_type,
            'location_description': zone.location_description,
            'keywords': zone.get_keywords_list()
        })
    
    # Build response data
    response_data = {}
    
    # Process barangays with projects
    for barangay, zone_counts in barangay_zone_data.items():
        # Find dominant zone (most projects)
        dominant_zone = max(zone_counts.items(), key=lambda x: x[1])[0] if zone_counts else None
        
        response_data[barangay] = {
            'dominant_zone': dominant_zone,
            'zone_counts': dict(zone_counts),
            'total_projects': sum(zone_counts.values()),
            'zone_types': list(zone_types_in_barangay[barangay]),
            'available_zones': zones_by_barangay.get(barangay, [])
        }
    
    # Also include barangays that have zones defined but no projects yet
    for barangay, zones in zones_by_barangay.items():
        if barangay not in response_data:
            # Get most common zone type for this barangay
            zone_type_counts = defaultdict(int)
            for zone in zones:
                zone_type_counts[zone['zone_type']] += 1
            
            dominant_zone = max(zone_type_counts.items(), key=lambda x: x[1])[0] if zone_type_counts else None
            
            response_data[barangay] = {
                'dominant_zone': dominant_zone,
                'zone_counts': {},
                'total_projects': 0,
                'zone_types': list(zone_type_counts.keys()),
                'available_zones': zones
            }
    
    return JsonResponse({
        'barangay_zones': response_data,
        'count': len(response_data)
    })

def _get_zone_display_name(zone_type):
    """Helper function to get display name for zone type"""
    zone_names = {
        'R-1': 'Low Density Residential',
        'R-2': 'Medium Density Residential',
        'R-3': 'High Density Residential',
        'SHZ': 'Socialized Housing',
        'C-1': 'Major Commercial',
        'C-2': 'Minor Commercial',
        'I-1': 'Heavy Industrial',
        'I-2': 'Light/Medium Industrial',
        'AGRO': 'Agro-Industrial',
        'INS-1': 'Institutional',
        'PARKS': 'Parks & Open Spaces',
        'AGRICULTURAL': 'Agricultural',
        'ECO-TOURISM': 'Eco-tourism',
        'SPECIAL': 'Special Use',
    }
    return zone_names.get(zone_type, zone_type)


@require_http_methods(["GET"])
@login_required
@user_passes_test(is_head_engineer, login_url='/accounts/login/')
def zone_analytics_api(request):
    """
    API endpoint for zone analytics charts.
    Returns aggregated project data by zone type.
    Optional ?period=week|month|year filters by project created_at.
    Accessible to Head Engineers only.
    """
    from django.db.models import Q

    # Optional period filter (week/month/year)
    period = (request.GET.get('period') or 'month').strip().lower()
    now = timezone.now().date()
    if period == 'week':
        start_date = now - timedelta(days=7)
    elif period == 'year':
        start_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=30)

    # Get all projects with zone_type (optionally filtered by period)
    projects_with_zones = Project.objects.filter(
        zone_type__isnull=False
    ).exclude(zone_type='').filter(created_at__date__gte=start_date)

    # Aggregate by zone_type
    zone_stats = projects_with_zones.values('zone_type').annotate(
        total_projects=Count('id'),
        completed=Count('id', filter=Q(status='completed')),
        in_progress=Count('id', filter=Q(status__in=['in_progress', 'ongoing'])),
        planned=Count('id', filter=Q(status__in=['planned', 'pending'])),
        delayed=Count('id', filter=Q(status='delayed')),
        total_cost=Sum('project_cost')
    ).order_by('zone_type')
    
    # Format response
    zones = []
    for stat in zone_stats:
        zones.append({
            'zone_type': stat['zone_type'],
            'display_name': _get_zone_display_name(stat['zone_type']),
            'total_projects': stat['total_projects'],
            'completed': stat['completed'],
            'in_progress': stat['in_progress'],
            'planned': stat['planned'],
            'delayed': stat.get('delayed', 0),
            'total_cost': float(stat['total_cost'] or 0)
        })
    
    return JsonResponse({
        'zones': zones
    })


@login_required
@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
def create_budget_request(request, project_id):
    """
    Create a BudgetRequest (additional budget) with optional proof attachments.
    This is the persistent (model-based) request flow used for OJT/deployment readiness.
    """
    project = get_object_or_404(Project, pk=project_id)

    # Permissions: head engineers can access all; project engineers only if assigned
    if not is_head_engineer(request.user) and request.user not in project.assigned_engineers.all():
        return HttpResponseForbidden("You are not assigned to this project.")

    if request.method != 'POST':
        return redirect('projeng:projeng_project_detail', pk=project_id)

    requested_amount_raw = (request.POST.get('requested_amount') or '').strip()
    reason = (request.POST.get('reason') or '').strip()
    proofs = request.FILES.getlist('proofs')

    if not requested_amount_raw:
        messages.error(request, "Requested amount is required.")
        return redirect('projeng:projeng_project_detail', pk=project_id)
    if not reason:
        messages.error(request, "Reason/justification is required.")
        return redirect('projeng:projeng_project_detail', pk=project_id)

    from decimal import Decimal, InvalidOperation
    try:
        requested_amount = Decimal(requested_amount_raw)
    except (InvalidOperation, ValueError):
        messages.error(request, "Invalid amount format.")
        return redirect('projeng:projeng_project_detail', pk=project_id)

    if requested_amount <= 0:
        messages.error(request, "Requested amount must be greater than 0.")
        return redirect('projeng:projeng_project_detail', pk=project_id)

    br = BudgetRequest.objects.create(
        project=project,
        requested_by=request.user,
        requested_amount=requested_amount,
        reason=reason,
        status='pending',
    )

    BudgetRequestStatusHistory.objects.create(
        budget_request=br,
        from_status=None,
        to_status='pending',
        action_by=request.user,
        notes='Budget request submitted'
    )

    for f in proofs:
        BudgetRequestAttachment.objects.create(
            budget_request=br,
            file=f,
            uploaded_by=request.user
        )

    # Notify Finance Managers + Head Engineers
    from .utils import format_project_display, notify_finance_managers, notify_head_engineers
    project_display = format_project_display(project)
    requester_name = request.user.get_full_name() or request.user.username
    msg = (
        f"📌 Budget Request Submitted: {project_display} "
        f"Requested increase: ₱{float(requested_amount):,.2f}. "
        f"Submitted by {requester_name}."
    )
    notify_finance_managers(msg, check_duplicates=False)
    notify_head_engineers(msg, check_duplicates=False)

    messages.success(request, "Budget request submitted successfully.")
    return redirect('projeng:projeng_project_detail', pk=project_id)


@login_required
@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
def send_budget_alert(request, project_id):
    """
    Allow Project Engineers to manually send budget alerts to Head Engineers.
    """
    # Add immediate logging to verify function is called
    import sys
    print(f"send_budget_alert: Function called - method={request.method}, project_id={project_id}, user={request.user.username}", file=sys.stderr)
    logging.info(f"send_budget_alert: Function called - method={request.method}, project_id={project_id}, user={request.user.username}")
    
    try:
        project = get_object_or_404(Project, pk=project_id)
        print(f"send_budget_alert: Project found - {project.name} (ID: {project.id})", file=sys.stderr)
        logging.info(f"send_budget_alert: Project found - {project.name} (ID: {project.id})")
        
        # Check if user has access to this project
        # Note: For Project Engineers, check if user is in assigned_engineers
        # For Head Engineers, they can access all projects
        if is_project_engineer(request.user):
            if request.user not in project.assigned_engineers.all():
                print(f"send_budget_alert: Access denied - user {request.user.username} not in assigned_engineers for project {project.id}", file=sys.stderr)
                print(f"send_budget_alert: Assigned engineers: {[e.username for e in project.assigned_engineers.all()]}", file=sys.stderr)
                messages.error(request, "You don't have access to this project.")
                return redirect('projeng:projeng_dashboard')
            else:
                print(f"send_budget_alert: Access granted - user {request.user.username} is assigned to project {project.id}", file=sys.stderr)
        
        if request.method == 'POST':
            print(f"send_budget_alert: POST request received for project {project_id} by user {request.user.username}", file=sys.stderr)
            logging.info(f"send_budget_alert: POST request received for project {project_id} by user {request.user.username}")
            custom_message = request.POST.get('message', '').strip()
            print(f"send_budget_alert: Custom message: '{custom_message}'", file=sys.stderr)
            logging.info(f"send_budget_alert: Custom message: '{custom_message}'")
            
            # Send notification
            try:
                print(f"send_budget_alert: Calling notify_head_engineer_about_budget_concern", file=sys.stderr)
                logging.info(f"send_budget_alert: Calling notify_head_engineer_about_budget_concern")
                notification_count = notify_head_engineer_about_budget_concern(
                    project=project,
                    sender_user=request.user,
                    message=custom_message if custom_message else None
                )
                print(f"send_budget_alert: Function returned notification_count: {notification_count}", file=sys.stderr)
                logging.info(f"send_budget_alert: Function returned notification_count: {notification_count}")
                
                # Check if Head Engineers exist
                from django.contrib.auth.models import User
                head_engineers = User.objects.filter(groups__name='Head Engineer').distinct()
                head_engineer_count = head_engineers.count()
                logging.info(f"send_budget_alert: Found {head_engineer_count} Head Engineer(s) in system")
                
                if notification_count > 0:
                    messages.success(request, f"Budget alert sent to {notification_count} Head Engineer(s) for project '{project.name}'.")
                    logging.info(f"send_budget_alert: Success message set")
                elif head_engineer_count == 0:
                    messages.warning(request, f"No Head Engineers found in the system. Please ensure at least one user is in the 'Head Engineer' group.")
                    logging.warning(f"send_budget_alert: No Head Engineers found")
                else:
                    messages.warning(request, f"Budget alert submitted, but no notifications were created. Please check system logs.")
                    logging.warning(f"send_budget_alert: No notifications created despite {head_engineer_count} Head Engineers existing")
                
            except Exception as e:
                logging.error(f"send_budget_alert: Exception occurred: {str(e)}", exc_info=True)
                messages.error(request, f"Error sending budget alert: {str(e)}")
            
            return redirect('projeng:projeng_project_detail', pk=project_id)
        
        # GET request - show form (or handle via AJAX)
        print(f"send_budget_alert: GET request received, redirecting", file=sys.stderr)
        messages.error(request, "Invalid request method.")
        return redirect('projeng:projeng_project_detail', pk=project_id)
    except Project.DoesNotExist:
        print(f"send_budget_alert: Project.DoesNotExist exception", file=sys.stderr)
        messages.error(request, "Project not found.")
        return redirect('projeng:projeng_dashboard')
    except Exception as e:
        import sys
        print(f"send_budget_alert: EXCEPTION occurred: {str(e)}", file=sys.stderr)
        import traceback
        print(f"send_budget_alert: Traceback: {traceback.format_exc()}", file=sys.stderr)
        logging.error(f"Error in send_budget_alert: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while sending the budget alert: {str(e)}")
        return redirect('projeng:projeng_project_detail', pk=project_id)


# ============================================================================
# ZONE COMPATIBILITY RECOMMENDATION API ENDPOINTS
# ============================================================================

@login_required
@require_GET
def zone_recommendation_api(request):
    """
    API endpoint to get zone recommendations for a project type.
    
    Query parameters:
    - project_type_code: Code of the project type (required)
    - selected_zone: Optional selected zone to validate
    - barangay: Optional barangay name for location-specific scoring
    - limit: Maximum number of recommendations (default: 5)
    
    Returns JSON with zone validation and recommendations.
    """
    from .zone_recommendation import ZoneCompatibilityEngine
    
    project_type_code = request.GET.get('project_type_code')
    if not project_type_code:
        return JsonResponse({
            'error': 'project_type_code parameter is required'
        }, status=400)
    
    selected_zone = request.GET.get('selected_zone')
    barangay = request.GET.get('barangay')
    limit = int(request.GET.get('limit', 5))
    
    try:
        engine = ZoneCompatibilityEngine()
        result = engine.recommend_zones(
            project_type_code=project_type_code,
            selected_zone=selected_zone,
            barangay=barangay,
            limit=limit
        )
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Zone recommendations API called: project_type={project_type_code}, selected_zone={selected_zone}, barangay={barangay}")
        logger.info(f"Result: allowed_zones={len(result.get('allowed_zones', []))}, recommendations={len(result.get('recommendations', []))}")
        
        return JsonResponse(result)
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting zone recommendations: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JsonResponse({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


@login_required
@require_GET
def zone_validation_api(request):
    """
    API endpoint to validate if a project type is allowed in a zone.
    
    Query parameters:
    - project_type_code: Code of the project type (required)
    - zone_type: Zone type code (required)
    
    Returns JSON with validation results.
    """
    from .zone_recommendation import ZoneCompatibilityEngine
    
    project_type_code = request.GET.get('project_type_code')
    zone_type = request.GET.get('zone_type')
    
    if not project_type_code or not zone_type:
        return JsonResponse({
            'error': 'Both project_type_code and zone_type parameters are required'
        }, status=400)
    
    try:
        engine = ZoneCompatibilityEngine()
        result = engine.validate_project_zone(project_type_code, zone_type)
        return JsonResponse(result)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error validating zone: {e}")
        return JsonResponse({
            'error': str(e)
        }, status=500)


@login_required
@require_GET
def project_types_api(request):
    """
    API endpoint to get all available project types.
    
    Returns JSON with list of project types.
    """
    from .models import ProjectType
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Debug: Log user and request info
        logger.info(f"project_types_api called by user: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
        
        # Get all project types
        project_types = ProjectType.objects.all().order_by('name')
        count = project_types.count()
        logger.info(f"Found {count} project types in database")
        
        # Debug: Log first few project types
        if count > 0:
            first_few = list(project_types[:5])
            logger.info(f"First few project types: {[pt.name for pt in first_few]}")
        else:
            logger.warning("No project types found in database!")
            # Try to see if there are any at all
            all_types = ProjectType.objects.all()
            logger.warning(f"Direct query count: {all_types.count()}")
        
        data = [
            {
                'code': pt.code,
                'name': pt.name,
                'description': pt.description or '',
                'density_level': pt.density_level or '',
                'height_category': pt.height_category or '',
            }
            for pt in project_types
        ]
        
        logger.info(f"Serialized {len(data)} project types for API response")
        response_data = {'project_types': data}
        
        # Debug: Log response data structure
        logger.info(f"Response data keys: {list(response_data.keys())}")
        logger.info(f"Response project_types length: {len(response_data['project_types'])}")
        
        return JsonResponse(response_data)
    except Exception as e:
        logger.error(f"Error getting project types: {e}", exc_info=True)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JsonResponse({
            'error': str(e)
        }, status=500)


@login_required
@user_passes_test(is_head_engineer, login_url='/accounts/login/')
@require_GET
def project_zone_recommendations_api(request, project_id):
    """
    API endpoint to get zone recommendations for a specific project.
    
    Returns JSON with recommendations for the project.
    """
    from .zone_recommendation import ZoneCompatibilityEngine
    from .models import Project, ProjectType
    
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({
            'error': 'Project not found'
        }, status=404)
    
    # Get project type from project model if available, otherwise from request parameter
    if project.project_type:
        project_type_code = project.project_type.code
    else:
        project_type_code = request.GET.get('project_type_code')
        if not project_type_code:
            return JsonResponse({
                'error': 'project_type_code parameter is required. Either set project.project_type or provide project_type_code in request.'
            }, status=400)
    
    try:
        engine = ZoneCompatibilityEngine()
        result = engine.recommend_zones(
            project_type_code=project_type_code,
            selected_zone=project.zone_type,
            barangay=project.barangay,
            limit=10
        )
        
        # Also get saved recommendations if any
        saved_recommendations = project.zone_recommendations.all().order_by('rank')
        result['saved_recommendations'] = [
            {
                'zone_type': rec.recommended_zone,
                'overall_score': rec.overall_score,
                'rank': rec.rank,
                'is_selected': rec.is_selected,
                'reasoning': rec.reasoning,
                'advantages': rec.advantages,
                'constraints': rec.constraints,
            }
            for rec in saved_recommendations
        ]
        
        return JsonResponse(result)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting project zone recommendations: {e}")
        return JsonResponse({
            'error': str(e)
        }, status=500)


@login_required
def clustering_comparison_view(request):
    """Display clustering algorithm comparison results"""
    from projeng.models import ClusteringAlgorithmComparison
    from projeng.clustering_comparison import run_clustering_comparison
    
    # Get latest comparison
    latest_comparison = ClusteringAlgorithmComparison.objects.first()
    
    # Run new comparison if requested
    if request.GET.get('run_comparison') == 'true':
        try:
            comparison_data = run_clustering_comparison()
            
            # Save to database
            results = comparison_data['results']
            comparison = ClusteringAlgorithmComparison.objects.create(
                total_projects=comparison_data['total_projects'],
                valid_projects=comparison_data['valid_projects'],
                best_algorithm=comparison_data['best_algorithm'],
                # Administrative
                admin_silhouette=results['administrative']['metrics']['silhouette_score'],
                admin_zas=results['administrative']['metrics']['zoning_alignment_score'],
                admin_calinski=results['administrative']['metrics']['calinski_harabasz_score'],
                admin_davies=results['administrative']['metrics']['davies_bouldin_score'],
                admin_execution_time=results['administrative']['metrics']['execution_time'],
                admin_cluster_count=results['administrative']['metrics']['cluster_count'],
                # K-Means
                kmeans_silhouette=results['kmeans']['metrics']['silhouette_score'],
                kmeans_zas=results['kmeans']['metrics']['zoning_alignment_score'],
                kmeans_calinski=results['kmeans']['metrics']['calinski_harabasz_score'],
                kmeans_davies=results['kmeans']['metrics']['davies_bouldin_score'],
                kmeans_execution_time=results['kmeans']['metrics']['execution_time'],
                kmeans_cluster_count=results['kmeans']['metrics']['cluster_count'],
                # DBSCAN
                dbscan_silhouette=results['dbscan']['metrics']['silhouette_score'],
                dbscan_zas=results['dbscan']['metrics']['zoning_alignment_score'],
                dbscan_calinski=results['dbscan']['metrics']['calinski_harabasz_score'],
                dbscan_davies=results['dbscan']['metrics']['davies_bouldin_score'],
                dbscan_execution_time=results['dbscan']['metrics']['execution_time'],
                dbscan_cluster_count=results['dbscan']['metrics']['cluster_count'],
                dbscan_noise_count=results['dbscan']['metrics'].get('noise_count', 0),
                # Hierarchical
                hierarchical_silhouette=results['hierarchical']['metrics']['silhouette_score'],
                hierarchical_zas=results['hierarchical']['metrics']['zoning_alignment_score'],
                hierarchical_calinski=results['hierarchical']['metrics']['calinski_harabasz_score'],
                hierarchical_davies=results['hierarchical']['metrics']['davies_bouldin_score'],
                hierarchical_execution_time=results['hierarchical']['metrics']['execution_time'],
                hierarchical_cluster_count=results['hierarchical']['metrics']['cluster_count'],
            )
            latest_comparison = comparison
        except Exception as e:
            error_message = str(e)
            return render(request, 'projeng/clustering_comparison.html', {
                'error': error_message,
                'latest_comparison': latest_comparison
            })
    
    # Format data for template
    comparison_table = []
    if latest_comparison:
        comparison_table = [
            {
                'algorithm': 'Administrative Spatial Analysis',
                'silhouette_score': latest_comparison.admin_silhouette,
                'zoning_alignment_score': latest_comparison.admin_zas,
                'calinski_harabasz_score': latest_comparison.admin_calinski,
                'davies_bouldin_score': latest_comparison.admin_davies,
                'execution_time': latest_comparison.admin_execution_time,
                'cluster_count': latest_comparison.admin_cluster_count,
                'noise_count': 0,
                'strengths': [
                    "Perfect alignment with administrative boundaries",
                    "Fast execution time",
                    "Governance-oriented clustering",
                    "No parameter tuning required"
                ],
                'weaknesses': [
                    "May not capture spatial density patterns",
                    "Ignores geographic proximity"
                ],
                'remarks': "Most effective for governance-oriented clustering; ideal for ONETAGUMVISION"
            },
            {
                'algorithm': 'K-Means Clustering',
                'silhouette_score': latest_comparison.kmeans_silhouette,
                'zoning_alignment_score': latest_comparison.kmeans_zas,
                'calinski_harabasz_score': latest_comparison.kmeans_calinski,
                'davies_bouldin_score': latest_comparison.kmeans_davies,
                'execution_time': latest_comparison.kmeans_execution_time,
                'cluster_count': latest_comparison.kmeans_cluster_count,
                'noise_count': 0,
                'strengths': [
                    "Handles irregular spatial patterns",
                    "Fast and scalable",
                    "Good for spherical clusters"
                ],
                'weaknesses': [
                    "Requires predefined number of clusters",
                    "May not align with administrative boundaries"
                ],
                'remarks': "Good for spatial pattern identification; useful for exploratory analysis"
            },
            {
                'algorithm': 'DBSCAN Clustering',
                'silhouette_score': latest_comparison.dbscan_silhouette,
                'zoning_alignment_score': latest_comparison.dbscan_zas,
                'calinski_harabasz_score': latest_comparison.dbscan_calinski,
                'davies_bouldin_score': latest_comparison.dbscan_davies,
                'execution_time': latest_comparison.dbscan_execution_time,
                'cluster_count': latest_comparison.dbscan_cluster_count,
                'noise_count': latest_comparison.dbscan_noise_count or 0,
                'strengths': [
                    "Identifies irregular spatial patterns",
                    "No need to specify cluster count",
                    "Handles noise/outliers well"
                ],
                'weaknesses': [
                    "Does not conform to administrative boundaries",
                    "Sensitive to parameter tuning"
                ],
                'remarks': "Effective for identifying dense regions; less suitable for governance"
            },
            {
                'algorithm': 'Hierarchical Clustering',
                'silhouette_score': latest_comparison.hierarchical_silhouette,
                'zoning_alignment_score': latest_comparison.hierarchical_zas,
                'calinski_harabasz_score': latest_comparison.hierarchical_calinski,
                'davies_bouldin_score': latest_comparison.hierarchical_davies,
                'execution_time': latest_comparison.hierarchical_execution_time,
                'cluster_count': latest_comparison.hierarchical_cluster_count,
                'noise_count': 0,
                'strengths': [
                    "Multi-level visualization of relationships",
                    "No need to specify cluster count upfront",
                    "Provides dendrogram for analysis"
                ],
                'weaknesses': [
                    "Computationally intensive",
                    "May not align with administrative boundaries"
                ],
                'remarks': "Provides detailed cluster relationships; best for analytical visualization"
            }
        ]
        # Sort by zoning alignment score
        comparison_table.sort(key=lambda x: x['zoning_alignment_score'], reverse=True)
    
    context = {
        'latest_comparison': latest_comparison,
        'comparison_table': comparison_table,
        'best_algorithm': latest_comparison.best_algorithm if latest_comparison else None,
        'total_projects': latest_comparison.total_projects if latest_comparison else 0,
        'valid_projects': latest_comparison.valid_projects if latest_comparison else 0,
    }
    
    return render(request, 'projeng/clustering_comparison.html', context) 