from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, Http404, HttpResponseBadRequest, HttpResponseServerError, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
import json
# from django.contrib.gis.geos import GEOSGeometry  # Temporarily disabled
from .models import Layer, Project, ProjectProgress, ProjectCost, ProgressPhoto, ProjectDocument, Notification, BarangayMetadata, ZoningZone
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
from .utils import flag_overdue_projects_as_delayed, notify_head_engineers, notify_admins
from django.views.decorators.http import require_GET, require_http_methods
from django.db import transaction
import traceback
from django.db.models import ProtectedError
from django.contrib.auth.views import redirect_to_login

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
            progress = int(latest_progress.percentage_complete) if latest_progress else 0
            status = project.status
            if progress >= 99:
                status = 'completed'
            elif progress < 99 and project.end_date and project.end_date < today:
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
            progress = int(latest_progress.percentage_complete) if latest_progress else 0
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
    
    # Build base queryset
    if is_head_engineer(request.user):
        projects_queryset = Project.objects.all()
    else:
        projects_queryset = Project.objects.filter(assigned_engineers=request.user)
    
    delayed_count = projects_queryset.filter(status='delayed').count()
    
    # Get all project IDs first for efficient querying
    project_ids = list(projects_queryset.values_list('id', flat=True))
    
    # Initialize dictionaries for storing latest update times
    progress_times = {}
    cost_times = {}
    document_times = {}
    
    # Only query if we have projects
    if project_ids:
        # Get latest progress times using aggregation
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
        
        # Build dictionaries for quick lookup
        progress_times = dict(latest_progress)
        cost_times = dict(latest_costs)
        document_times = dict(latest_documents)
    
    # Get projects with prefetch for efficient access
    projects = projects_queryset.select_related('created_by').prefetch_related('assigned_engineers')
    
    # Calculate the most recent update time for each project
    projects_with_updates = []
    for project in projects:
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
    
    return render(request, 'projeng/my_projects.html', {
        'projects': projects_with_updates,
        'delayed_count': delayed_count
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
        progress = int(latest_progress.percentage_complete) if latest_progress else 0
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
        progress = int(latest_progress.percentage_complete) if latest_progress else 0
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
    # Build base queryset
    if is_head_engineer(request.user):
        assigned_projects = Project.objects.all()
    else:
        assigned_projects = Project.objects.filter(assigned_engineers=request.user)
    
    # Apply filters
    barangay_filter = request.GET.get('barangay')
    status_filter = request.GET.get('status')
    start_date_filter = request.GET.get('start_date')
    end_date_filter = request.GET.get('end_date')
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
    assigned_projects = assigned_projects.select_related('created_by').prefetch_related('assigned_engineers')
    
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
        'selected_barangay': barangay_filter,
        'selected_status': status_filter,
        'selected_start_date': start_date_filter,
        'selected_end_date': end_date_filter,
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
        
        # Sort by timestamp (most recent first)
        activity_log.sort(key=lambda x: x['timestamp'], reverse=True)
        
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
        
        # Timeline Comparison: Expected vs Actual Progress
        timeline_comparison = None
        if project.start_date and project.end_date:
            from datetime import date, timedelta
            import json
            today = date.today()
            total_days = (project.end_date - project.start_date).days
            elapsed_days = (today - project.start_date).days if today >= project.start_date else 0
            
            if total_days > 0 and elapsed_days >= 0:
                # Calculate expected progress based on linear timeline
                expected_progress = min(100, (elapsed_days / total_days) * 100)
                actual_progress = progress_percentages[-1] if progress_percentages else 0
                progress_variance = actual_progress - expected_progress
                
                # Generate expected progress data points for chart
                # Combine actual progress dates with expected timeline dates for better alignment
                all_dates_set = set(progress_dates)  # Actual progress update dates
                # Add weekly expected dates from start to today
                current_date = project.start_date
                while current_date <= project.end_date and current_date <= today:
                    all_dates_set.add(current_date.strftime('%Y-%m-%d'))
                    current_date += timedelta(days=7)  # Weekly intervals
                
                # Sort all dates
                all_dates_sorted = sorted(list(all_dates_set))
                
                # Calculate expected progress for each date
                expected_progress_data = []
                actual_progress_aligned = []
                
                for date_str in all_dates_sorted:
                    # Parse date string (format: YYYY-MM-DD)
                    year, month, day = map(int, date_str.split('-'))
                    date_obj = date(year, month, day)
                    days_elapsed = (date_obj - project.start_date).days
                    if days_elapsed >= 0:
                        expected_pct = min(100, (days_elapsed / total_days) * 100) if total_days > 0 else 0
                        expected_progress_data.append(expected_pct)
                    else:
                        expected_progress_data.append(0)
                    
                    # Find actual progress for this date (use latest progress up to this date)
                    actual_pct = 0
                    for i, prog_date in enumerate(progress_dates):
                        if prog_date <= date_str:
                            actual_pct = progress_percentages[i]
                        else:
                            break
                    actual_progress_aligned.append(actual_pct)
                
                expected_dates = all_dates_sorted
                
                timeline_comparison = {
                    'expected_progress': round(expected_progress, 2),
                    'actual_progress': actual_progress,
                    'progress_variance': round(progress_variance, 2),
                    'elapsed_days': elapsed_days,
                    'total_days': total_days,
                    'remaining_days': max(0, (project.end_date - today).days),
                    'is_ahead': progress_variance > 0,
                    'is_behind': progress_variance < -5,  # Consider behind if more than 5% behind
                    'expected_progress_data': expected_progress_data,
                    'expected_dates': expected_dates,
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
        progress_dates_json = json.dumps(progress_dates)
        progress_percentages_json = json.dumps(progress_percentages)
        timeline_comparison_json = json.dumps(timeline_comparison) if timeline_comparison else None
        expected_dates_json = json.dumps(timeline_comparison['expected_dates']) if timeline_comparison else '[]'
        expected_progress_data_json = json.dumps(timeline_comparison['expected_progress_data']) if timeline_comparison else '[]'
        actual_progress_aligned_json = json.dumps(timeline_comparison['actual_progress_aligned']) if timeline_comparison else '[]'
        
        return render(request, 'projeng/project_detail.html', {
            'project': project,
            'status_choices': Project.STATUS_CHOICES,
            'activity_log': activity_log,
            'progress_timeline_data': progress_timeline_data,
            'progress_dates': progress_dates_json,
            'progress_percentages': progress_percentages_json,
            'timeline_comparison': timeline_comparison,
            'expected_dates_json': expected_dates_json,
            'expected_progress_data_json': expected_progress_data_json,
            'actual_progress_aligned_json': actual_progress_aligned_json,
            'total_cost': total_cost_float,
            'remaining_budget': remaining_budget,
            'budget_utilization': budget_utilization,
            'budget_status': budget_status,
            'over_budget_amount': over_budget_amount,
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
        context = {
            'project': project,
            'latest_progress': latest_progress,
            'total_progress': total_progress,
            'total_cost': total_cost,
            'cost_by_type': cost_by_type,
            'budget_utilization': budget_utilization,
            'budget_remaining': budget_remaining,
            'budget_status': budget_status,
            'timeline_data': timeline_data,
            'today': timezone.now().date(),
        }
        return render(request, 'projeng/project_management.html', context)
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
                percentage_complete = int(raw_percentage)
                if not (0 <= percentage_complete <= 100):
                    raise ValueError("Percentage out of range")
            except Exception as e:
                logging.exception("Invalid percentage value")
                return JsonResponse({'error': 'Invalid percentage value. Please enter a number between 0 and 100.'}, status=400)
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
            
            # Timeline validation: ensure progress is within the timeline (with 10% buffer)
            if project.start_date and project.end_date:
                total_days = (project.end_date - project.start_date).days
                elapsed_days = (progress_date - project.start_date).days
                if total_days > 0 and elapsed_days >= 0:
                    elapsed_percent = (elapsed_days / total_days) * 100
                    allowed_progress = elapsed_percent + 10  # 10% buffer
                    if percentage_complete > allowed_progress:
                        return JsonResponse({'error': f'Progress ({percentage_complete}%) exceeds what is reasonable for the current timeline (allowed up to {allowed_progress:.1f}%).'}, status=400)

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

@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
def analytics_overview(request):
    return render(request, 'projeng/analytics_overview.html')

@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
def analytics_overview_data(request):
    from .models import Project, ProjectProgress
    if is_head_engineer(request.user):
        all_projects = Project.objects.all()
    else:
        all_projects = Project.objects.filter(assigned_engineers=request.user)
    today = timezone.now().date()
    status_counts = {'planned': 0, 'in_progress': 0, 'completed': 0, 'delayed': 0}
    for project in all_projects:
        latest_progress = ProjectProgress.objects.filter(project=project).order_by('-date').first()
        progress = int(latest_progress.percentage_complete) if latest_progress else 0
        status = project.status
        if progress >= 99:
            status = 'completed'
        elif progress < 99 and project.end_date and project.end_date < today:
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
    status_labels = ['Planned', 'In Progress', 'Completed', 'Delayed']
    status_data = [status_counts['planned'], status_counts['in_progress'], status_counts['completed'], status_counts['delayed']]
    background_colors = [
        'rgba(54, 162, 235, 0.6)',
        'rgba(255, 206, 86, 0.6)',
        'rgba(75, 192, 192, 0.6)',
        'rgba(135, 206, 250, 0.6)',
    ]
    border_colors = [
        'rgba(54, 162, 235, 1)',
        'rgba(255, 206, 86, 1)',
        'rgba(75, 192, 192, 1)',
        'rgba(135, 206, 250, 1)',
    ]
    chart_data = {
        'labels': status_labels,
        'datasets': [{
            'label': 'Number of Projects',
            'data': status_data,
            'backgroundColor': background_colors,
            'borderColor': border_colors,
            'borderWidth': 1
        }]
    }
    return JsonResponse(chart_data)

@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
def dashboard_progress_over_time_data(request):
    """API endpoint for Project Progress Over Time chart"""
    from .models import Project, ProjectProgress
    from django.db.models import Avg
    from datetime import datetime, timedelta
    from collections import defaultdict
    
    if is_head_engineer(request.user):
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(assigned_engineers=request.user)
    
    # Get progress updates for the last 6 months
    six_months_ago = timezone.now().date() - timedelta(days=180)
    progress_updates = ProjectProgress.objects.filter(
        project__in=projects,
        date__gte=six_months_ago
    ).order_by('date')
    
    # Group by month
    monthly_progress = defaultdict(list)
    for update in progress_updates:
        month_key = update.date.strftime('%Y-%m')
        monthly_progress[month_key].append(update.percentage_complete)
    
    # Calculate average progress per month
    months = sorted(monthly_progress.keys())
    avg_progress = [sum(monthly_progress[m]) / len(monthly_progress[m]) for m in months] if months else []
    
    # Format month labels
    month_labels = []
    for m in months:
        try:
            dt = datetime.strptime(m, '%Y-%m')
            month_labels.append(dt.strftime('%b %Y'))
        except ValueError:
            month_labels.append(m)
    
    # If no data, return empty chart
    if not month_labels:
        month_labels = ['No Data']
        avg_progress = [0]
    
    return JsonResponse({
        'labels': month_labels,
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
    """API endpoint for Budget Utilization chart"""
    from .models import Project, ProjectCost
    from django.db.models import Sum
    
    if is_head_engineer(request.user):
        projects = Project.objects.filter(project_cost__isnull=False)
    else:
        projects = Project.objects.filter(
            assigned_engineers=request.user,
            project_cost__isnull=False
        )
    
    # Calculate budget utilization for each project
    project_data = []
    for project in projects:
        total_cost = ProjectCost.objects.filter(project=project).aggregate(
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
    """API endpoint for Cost Breakdown by Type chart"""
    from .models import Project, ProjectCost
    from django.db.models import Sum
    
    if is_head_engineer(request.user):
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(assigned_engineers=request.user)
    
    # Get cost breakdown by type
    cost_by_type = ProjectCost.objects.filter(
        project__in=projects
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
    """API endpoint for Projects by Barangay chart"""
    from .models import Project
    from django.db.models import Count
    
    if is_head_engineer(request.user):
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(assigned_engineers=request.user)
    
    # Count projects by barangay
    barangay_counts = projects.filter(
        barangay__isnull=False
    ).values('barangay').annotate(
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
        file = request.FILES.get('file')
        name = request.POST.get('name')
        if file and name:
            document = ProjectDocument.objects.create(
                project=project,
                file=file,
                name=name,
                uploaded_by=request.user
            )
            return JsonResponse({
                'success': True,
                'message': 'Document uploaded successfully',
                'document': {
                    'name': document.name,
                    'file_url': document.file.url,
                    'uploaded_by': document.uploaded_by.get_full_name() or document.uploaded_by.username,
                    'uploaded_at': document.uploaded_at.strftime('%B %d, %Y')
                }
            })
        else:
            return JsonResponse({'success': False, 'error': 'Missing file or name'}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

# Report Export Views
@login_required
def export_reports_csv(request):
    # Get projects assigned to the current project engineer
    assigned_projects = Project.objects.filter(assigned_engineers=request.user)

    # --- Filtering by Barangay ---
    barangay_filter = request.GET.get('barangay')
    if barangay_filter:
        assigned_projects = assigned_projects.filter(barangay=barangay_filter)
    # --- End Filtering ---

    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="assigned_projects_report.csv"'

    writer = csv.writer(response)
    # Write the header row
    writer.writerow(['#', 'PRN#', 'Name of Project', 'Project Description', 'Barangay', 'Project Cost', 'Source of Funds', 'Date Started', 'Date Ended', 'Status'])

    # Write data rows
    for i, project in enumerate(assigned_projects):
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
    # Get projects assigned to the current project engineer
    assigned_projects = Project.objects.filter(assigned_engineers=request.user)

    # --- Filtering by Barangay ---
    barangay_filter = request.GET.get('barangay')
    if barangay_filter:
        assigned_projects = assigned_projects.filter(barangay=barangay_filter)
    # --- End Filtering ---

    # Create a new workbook and select the active sheet
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Assigned Projects"

    # Write the header row
    headers = ['#', 'PRN#', 'Name of Project', 'Project Description', 'Barangay', 'Project Cost', 'Source of Funds', 'Date Started', 'Date Ended', 'Status']
    sheet.append(headers)

    # Write data rows
    for i, project in enumerate(assigned_projects):
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

    # Create the HttpResponse object with the appropriate Excel header.
    response = HttpResponse(excel_file.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="assigned_projects_report.xlsx"'

    return response

@login_required
def export_reports_pdf(request):
    # Get projects assigned to the current project engineer
    assigned_projects = Project.objects.filter(assigned_engineers=request.user)

    # --- Filtering by Barangay ---
    barangay_filter = request.GET.get('barangay')
    if barangay_filter:
        assigned_projects = assigned_projects.filter(barangay=barangay_filter)
    # --- End Filtering ---

    # If xhtml2pdf is unavailable, return a friendly message
    if pisa is None:
        return HttpResponse('PDF export is temporarily unavailable (missing xhtml2pdf/reportlab).', content_type='text/plain')

    # Render the HTML template for the PDF
    template_path = 'projeng/reports/assigned_projects_pdf.html'
    template = get_template(template_path)
    context = {'projects': assigned_projects}
    html = template.render(context)

    # Create a PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="assigned_projects_report.pdf"'

    # Create a file-like object to write the PDF data to
    buffer = io.BytesIO()

    # Create the PDF object, and write the HTML to it.
    pisa_status = pisa.CreatePDF(
        html,                   # HTML to convert
        dest=buffer             # File handle to receive the PDF
    )

    # If there were no errors, return the PDF file
    if not pisa_status.err:
        return HttpResponse(buffer.getvalue(), content_type='application/pdf')

    # If there were errors, return an error message
    return HttpResponse('We had some errors <pre>' + html + '</pre>', content_type='text/plain') 

@user_passes_test(is_project_engineer, login_url='/accounts/login/')
@require_GET
def map_projects_api(request):
    all_projects = Project.objects.filter(
        assigned_engineers=request.user,
        latitude__isnull=False,
        longitude__isnull=False
    )
    projects_with_coords = [p for p in all_projects if p.latitude != '' and p.longitude != '']
    projects_data = []
    for p in projects_with_coords:
        latest_progress = ProjectProgress.objects.filter(project=p).order_by('-date').first()
        progress = int(latest_progress.percentage_complete) if latest_progress else 0
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
        progress = int(latest_progress.percentage_complete) if latest_progress else 0
        status = project.status
        if progress >= 99:
            status = 'completed'
        elif progress < 99 and project.end_date and project.end_date < today:
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
def zone_analytics_api(request):
    """
    Return zone analytics data for charts.
    Shows project distribution, costs, and statistics by zone type.
    """
    # Check if user is head engineer (return JSON error for API, not redirect)
    if not is_head_engineer(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    from collections import defaultdict
    
    try:
        # Get all projects with zone_type
        projects_with_zones = Project.objects.filter(
            zone_type__isnull=False
        ).exclude(zone_type='')
        
        # Aggregate statistics by zone type
        zone_stats = defaultdict(lambda: {
            'total_projects': 0,
            'total_cost': 0,
            'completed': 0,
            'in_progress': 0,
            'planned': 0,
            'delayed': 0,
            'validated': 0,
            'unvalidated': 0
        })
        
        for project in projects_with_zones:
            zone_type = project.zone_type
            if not zone_type:
                continue
                
            zone_stats[zone_type]['total_projects'] += 1
            
            # Add project cost
            if project.project_cost:
                try:
                    zone_stats[zone_type]['total_cost'] += float(project.project_cost)
                except (ValueError, TypeError):
                    pass
            
            # Count by status
            status = project.status.lower() if project.status else ''
            if status == 'completed':
                zone_stats[zone_type]['completed'] += 1
            elif status in ['in_progress', 'ongoing']:
                zone_stats[zone_type]['in_progress'] += 1
            elif status == 'planned':
                zone_stats[zone_type]['planned'] += 1
            elif status == 'delayed':
                zone_stats[zone_type]['delayed'] += 1
            
            # Count validated vs unvalidated
            if project.zone_validated:
                zone_stats[zone_type]['validated'] += 1
            else:
                zone_stats[zone_type]['unvalidated'] += 1
        
        # Convert to list format for charts
        zone_list = []
        for zone_type, stats in sorted(zone_stats.items()):
            zone_list.append({
                'zone_type': zone_type,
                'display_name': _get_zone_display_name(zone_type),
                **stats
            })
        
        # Calculate totals
        total_projects = sum(s['total_projects'] for s in zone_stats.values())
        total_cost = sum(s['total_cost'] for s in zone_stats.values())
        
        return JsonResponse({
            'zones': zone_list,
            'summary': {
                'total_projects': total_projects,
                'total_cost': total_cost,
                'zone_count': len(zone_stats)
            }
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error in zone_analytics_api: {str(e)}', exc_info=True)
        return JsonResponse({'error': 'Internal server error'}, status=500) 