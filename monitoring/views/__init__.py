from django.shortcuts import render, redirect
from django.http import HttpResponse
from .finance_manager import finance_dashboard, finance_projects, finance_cost_management, finance_notifications
from projeng.models import Project
from django.contrib.auth.models import Group
from django.core.paginator import Paginator
import os
import json
from django.http import JsonResponse
from django.conf import settings
from collections import Counter, defaultdict
from monitoring.forms import ProjectForm

def home(request):
    return render(request, 'monitoring/home.html')

def dashboard(request):
    from projeng.models import Project
    from collections import Counter, defaultdict
    # Role-based queryset
    if is_head_engineer(request.user) or is_finance_manager(request.user):
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
    context = {
        'recent_projects': recent_projects,
        'project_count': project_count,
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'planned_count': planned_count,
        'delayed_count': delayed_count,
        'collab_by_barangay': dict(collab_by_barangay),
        'collab_by_status': dict(collab_by_status),
    }
    return render(request, 'monitoring/dashboard.html', context)

def project_list(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            form.save_m2m()  # Save assigned engineers
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
        projects = Project.objects.all().order_by('-created_at')
    elif is_project_engineer(request.user):
        projects = Project.objects.filter(assigned_engineers=request.user).order_by('-created_at')
    else:
        projects = Project.objects.none()
    paginator = Paginator(projects, 10)  # Show 10 projects per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    form = ProjectForm()
    # Build projects_data for modal and JS
    projects_data = []
    for p in projects:
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

def map_view(request):
    if is_head_engineer(request.user) or is_finance_manager(request.user):
        projects = Project.objects.all()
    elif is_project_engineer(request.user):
        projects = Project.objects.filter(assigned_engineers=request.user)
    else:
        projects = Project.objects.none()
    # Only include projects with coordinates
    projects_with_coords = projects.filter(latitude__isnull=False, longitude__isnull=False)
    projects_data = []
    for p in projects_with_coords:
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
            'progress': getattr(p, 'progress', 0),
        })
    return render(request, 'monitoring/map.html', {'projects_data': projects_data})

def reports(request):
    # Role-based queryset
    if is_head_engineer(request.user) or is_finance_manager(request.user):
        projects = Project.objects.all()
    elif is_project_engineer(request.user):
        projects = Project.objects.filter(assigned_engineers=request.user)
    else:
        projects = Project.objects.none()
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
        'projects_json': json.dumps(projects_list),
    }
    return render(request, 'monitoring/reports.html', context)

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
    }
    return render(request, 'monitoring/budget_reports.html', context)

def project_update_api(request, pk):
    return HttpResponse("project_update_api placeholder")

def project_delete_api(request, pk):
    return HttpResponse("project_delete_api placeholder")

def delayed_projects(request):
    return HttpResponse("delayed_projects placeholder")

def project_engineer_analytics(request, pk):
    return HttpResponse("project_engineer_analytics placeholder")

def head_engineer_analytics(request):
    from projeng.models import Project, ProjectProgress
    from django.contrib.auth.models import User
    import json
    # Get all projects
    projects = Project.objects.all()
    # Prepare project list for the table and JS
    projects_list = []
    total_projects = projects.count()
    completed_projects = 0
    ongoing_projects = 0
    planned_projects = 0
    delayed_projects = 0
    for p in projects:
        # Get latest progress
        latest_progress = ProjectProgress.objects.filter(project=p).order_by('-date').first()
        progress = int(latest_progress.percentage_complete) if latest_progress else 0
        # Status display
        status_display = (
            'Ongoing' if p.status in ['in_progress', 'ongoing'] else
            'Planned' if p.status in ['planned', 'pending'] else
            'Completed' if p.status == 'completed' else
            'Delayed' if p.status == 'delayed' else p.status.title()
        )
        # Count for cards
        if status_display == 'Completed':
            completed_projects += 1
        elif status_display == 'Ongoing':
            ongoing_projects += 1
        elif status_display == 'Planned':
            planned_projects += 1
        elif status_display == 'Delayed':
            delayed_projects += 1
        # Assigned engineers
        assigned_to = list(p.assigned_engineers.values_list('username', flat=True))
        projects_list.append({
            'id': p.id,
            'name': p.name,
            'prn': p.prn,
            'barangay': p.barangay,
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
        'total_projects': total_projects,
        'completed_projects': completed_projects,
        'ongoing_projects': ongoing_projects,
        'planned_projects': planned_projects,
        'delayed_projects': delayed_projects,
        'user_role': 'head_engineer',
    }
    return render(request, 'monitoring/analytics.html', context)

def project_detail(request, pk):
    return HttpResponse("project_detail placeholder")

def head_engineer_project_detail(request, pk):
    from projeng.models import Project, ProjectProgress, ProjectCost
    from django.contrib.auth.models import User
    import json
    try:
        project = Project.objects.get(pk=pk)
    except Project.DoesNotExist:
        return HttpResponse('Project not found.', status=404)
    # Get all progress updates
    progress_updates = ProjectProgress.objects.filter(project=project).order_by('date')
    assigned_to = list(project.assigned_engineers.values_list('username', flat=True))
    # Get all cost entries
    costs = ProjectCost.objects.filter(project=project).order_by('date')
    # Analytics & summary
    latest_progress = progress_updates.last() if progress_updates else None
    total_cost = sum([float(c.amount) for c in costs]) if costs else 0
    budget_utilization = (total_cost / float(project.project_cost) * 100) if project.project_cost else 0
    timeline_data = {
        'start_date': project.start_date,
        'end_date': project.end_date,
        'days_elapsed': (project.end_date - project.start_date).days if project.start_date and project.end_date else None,
        'total_days': (project.end_date - project.start_date).days if project.start_date and project.end_date else None,
    }
    context = {
        'project': project,
        'progress_updates': progress_updates,
        'assigned_to': assigned_to,
        'costs': costs,
        'latest_progress': latest_progress,
        'total_cost': total_cost,
        'budget_utilization': budget_utilization,
        'timeline_data': timeline_data,
    }
    return render(request, 'monitoring/head_engineer_project_detail.html', context)

def head_dashboard_card_data_api(request):
    return HttpResponse("head_dashboard_card_data_api placeholder")

def barangay_geojson_view(request):
    geojson_path = os.path.join(settings.BASE_DIR, 'static', 'data', 'tagum_barangays.geojson')
    with open(geojson_path, 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)
    return JsonResponse(geojson_data, safe=False)

def export_project_timeline_pdf(request, pk):
    return HttpResponse("export_project_timeline_pdf placeholder")

def is_head_engineer(user):
    return user.is_authenticated and user.groups.filter(name='Head Engineer').exists()

def is_finance_manager(user):
    return user.is_authenticated and user.groups.filter(name='Finance Manager').exists()

def is_project_engineer(user):
    return user.is_authenticated and user.groups.filter(name='Project Engineer').exists()
