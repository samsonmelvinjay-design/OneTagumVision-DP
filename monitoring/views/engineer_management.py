"""
Engineer Management Views
Handles creation, viewing, editing, and management of Project Engineer accounts
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from projeng.models import Project
from monitoring.forms import EngineerCreateForm, EngineerEditForm
from gistagum.access_control import head_engineer_required


@head_engineer_required
def engineer_list(request):
    """List all Project Engineers with search and filter functionality"""
    # Get all Project Engineers (exclude Head Engineers and superusers)
    try:
        project_engineer_group = Group.objects.get(name='Project Engineer')
        head_engineer_group = Group.objects.get(name='Head Engineer')
        engineers = User.objects.filter(groups=project_engineer_group)
        engineers = engineers.exclude(groups=head_engineer_group).exclude(is_superuser=True)
    except Group.DoesNotExist:
        engineers = User.objects.none()

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        engineers = engineers.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        engineers = engineers.filter(is_active=True)
    elif status_filter == 'inactive':
        engineers = engineers.filter(is_active=False)

    # Sort engineers
    sort_by = request.GET.get('sort', 'username')
    if sort_by == 'name':
        engineers = engineers.order_by('first_name', 'last_name')
    elif sort_by == 'date_joined':
        engineers = engineers.order_by('-date_joined')
    elif sort_by == 'projects':
        engineers = engineers.annotate(project_count=Count('assigned_projects')).order_by('-project_count')
    else:
        engineers = engineers.order_by('username')

    # Get total count before pagination
    total_engineers = engineers.count()

    # Pagination (before getting project counts for performance)
    paginator = Paginator(engineers, 20)  # Show 20 engineers per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get project counts for each engineer on current page
    engineers_with_counts = []
    for engineer in page_obj:
        project_count = engineer.assigned_projects.count()
        engineers_with_counts.append({
            'engineer': engineer,
            'project_count': project_count,
        })

    context = {
        'engineers': engineers_with_counts,
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'total_engineers': total_engineers,
    }
    return render(request, 'monitoring/engineers/engineer_list.html', context)


@head_engineer_required
def engineer_create(request):
    """Create a new Project Engineer account"""
    if request.method == 'POST':
        form = EngineerCreateForm(request.POST)
        if form.is_valid():
            engineer = form.save()
            messages.success(request, f'Engineer account "{engineer.username}" has been created successfully!')
            return redirect('engineer_detail', engineer_id=engineer.id)
    else:
        form = EngineerCreateForm()

    context = {
        'form': form,
        'title': 'Create New Engineer Account',
    }
    return render(request, 'monitoring/engineers/engineer_create.html', context)


@head_engineer_required
def engineer_detail(request, engineer_id):
    """View detailed information about a specific engineer"""
    engineer = get_object_or_404(User, id=engineer_id)
    
    # Verify this is a Project Engineer (not Head Engineer or superuser)
    if engineer.is_superuser or engineer.groups.filter(name='Head Engineer').exists():
        messages.error(request, 'This user is not a Project Engineer.')
        return redirect('engineer_list')

    # Get assigned projects
    assigned_projects = engineer.assigned_projects.all()
    
    # Calculate statistics
    total_projects = assigned_projects.count()
    active_projects = assigned_projects.filter(status__in=['in_progress', 'ongoing']).count()
    completed_projects = assigned_projects.filter(status='completed').count()
    planned_projects = assigned_projects.filter(status__in=['planned', 'pending']).count()
    delayed_projects = assigned_projects.filter(status='delayed').count()

    # Calculate overall progress (average of all project progress)
    if total_projects > 0:
        total_progress = sum([p.progress or 0 for p in assigned_projects]) / total_projects
    else:
        total_progress = 0

    # Get project details for display
    projects_data = []
    for project in assigned_projects:
        projects_data.append({
            'id': project.id,
            'name': project.name,
            'status': project.status,
            'status_display': (
                'Ongoing' if project.status in ['in_progress', 'ongoing'] else
                'Planned' if project.status in ['planned', 'pending'] else
                'Completed' if project.status == 'completed' else
                'Delayed' if project.status == 'delayed' else project.status.title()
            ),
            'progress': project.progress or 0,
            'start_date': project.start_date,
            'end_date': project.end_date,
        })

    context = {
        'engineer': engineer,
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'planned_projects': planned_projects,
        'delayed_projects': delayed_projects,
        'total_progress': round(total_progress, 1),
        'projects': projects_data,
    }
    return render(request, 'monitoring/engineers/engineer_detail.html', context)


@head_engineer_required
def engineer_edit(request, engineer_id):
    """Edit an existing Project Engineer account"""
    engineer = get_object_or_404(User, id=engineer_id)
    
    # Verify this is a Project Engineer
    if engineer.is_superuser or engineer.groups.filter(name='Head Engineer').exists():
        messages.error(request, 'This user is not a Project Engineer.')
        return redirect('engineer_list')

    # Prevent Head Engineers from editing themselves (they should use admin)
    if engineer == request.user:
        messages.warning(request, 'You cannot edit your own account from this page.')
        return redirect('engineer_detail', engineer_id=engineer.id)

    if request.method == 'POST':
        form = EngineerEditForm(request.POST, instance=engineer)
        if form.is_valid():
            form.save()
            messages.success(request, f'Engineer account "{engineer.username}" has been updated successfully!')
            return redirect('engineer_detail', engineer_id=engineer.id)
    else:
        form = EngineerEditForm(instance=engineer)

    context = {
        'form': form,
        'engineer': engineer,
        'title': f'Edit Engineer: {engineer.get_full_name() or engineer.username}',
    }
    return render(request, 'monitoring/engineers/engineer_edit.html', context)


@head_engineer_required
def engineer_deactivate(request, engineer_id):
    """Deactivate a Project Engineer account"""
    engineer = get_object_or_404(User, id=engineer_id)
    
    # Verify this is a Project Engineer
    if engineer.is_superuser or engineer.groups.filter(name='Head Engineer').exists():
        messages.error(request, 'This user is not a Project Engineer.')
        return redirect('engineer_list')

    # Prevent Head Engineers from deactivating themselves
    if engineer == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('engineer_detail', engineer_id=engineer.id)

    if request.method == 'POST':
        engineer.is_active = False
        engineer.save()
        messages.success(request, f'Engineer account "{engineer.username}" has been deactivated.')
        return redirect('engineer_detail', engineer_id=engineer.id)
    
    # If GET request, show confirmation page or redirect
    return redirect('engineer_detail', engineer_id=engineer.id)


@head_engineer_required
def engineer_activate(request, engineer_id):
    """Activate a Project Engineer account"""
    engineer = get_object_or_404(User, id=engineer_id)
    
    # Verify this is a Project Engineer
    if engineer.is_superuser or engineer.groups.filter(name='Head Engineer').exists():
        messages.error(request, 'This user is not a Project Engineer.')
        return redirect('engineer_list')

    if request.method == 'POST':
        engineer.is_active = True
        engineer.save()
        messages.success(request, f'Engineer account "{engineer.username}" has been activated.')
        return redirect('engineer_detail', engineer_id=engineer.id)
    
    # If GET request, show confirmation page or redirect
    return redirect('engineer_detail', engineer_id=engineer.id)

