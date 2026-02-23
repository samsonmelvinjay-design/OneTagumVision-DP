"""
Engineer Management Views
Handles creation, viewing, editing, and management of Project Engineer accounts
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from projeng.models import Project, ProjectType, ProjectProgress
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
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if request.method == 'POST':
        form = EngineerCreateForm(request.POST)
        if form.is_valid():
            engineer = form.save()
            if is_ajax:
                from django.http import JsonResponse
                return JsonResponse({
                    'success': True,
                    'message': f'Engineer account "{engineer.username}" has been created successfully!',
                    'redirect_url': f'/dashboard/engineers/{engineer.id}/'
                })
            messages.success(request, f'Engineer account "{engineer.username}" has been created successfully!')
            return redirect('engineer_detail', engineer_id=engineer.id)
    else:
        form = EngineerCreateForm()

    context = {
        'form': form,
        'title': 'Create New Engineer Account',
    }
    
    # If AJAX request, return just the form content (modal version)
    if is_ajax:
        from django.template.loader import render_to_string
        form_html = render_to_string('monitoring/engineers/engineer_create_modal.html', context, request=request)
        from django.http import HttpResponse
        return HttpResponse(form_html)
    
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
    
    today = timezone.now().date()
    project_ids = list(assigned_projects.values_list('id', flat=True))
    latest_progress = {}
    if project_ids:
        progresses = ProjectProgress.objects.filter(
            project_id__in=project_ids,
            percentage_complete__isnull=False
        ).values('project_id', 'percentage_complete', 'date', 'created_at').order_by('project_id', '-date', '-created_at')
        seen = set()
        for rec in progresses:
            if rec['project_id'] not in seen:
                seen.add(rec['project_id'])
                latest_progress[rec['project_id']] = float(rec['percentage_complete'])
    
    # Calculate statistics (including dynamic delayed status)
    total_projects = assigned_projects.count()
    active_projects = 0
    completed_projects = 0
    planned_projects = 0
    delayed_projects = 0
    for p in assigned_projects:
        progress = latest_progress.get(p.id, 0) or (p.progress or 0)
        stored_status = p.status or ''
        if progress >= 99:
            completed_projects += 1
        elif stored_status == 'delayed':
            delayed_projects += 1
        elif progress < 99 and p.end_date and p.end_date < today and stored_status in ['in_progress', 'ongoing']:
            delayed_projects += 1
        elif stored_status in ['in_progress', 'ongoing']:
            active_projects += 1
        elif stored_status in ['planned', 'pending']:
            planned_projects += 1
        elif stored_status == 'completed':
            completed_projects += 1

    # Calculate overall progress (average of all project progress)
    if total_projects > 0:
        total_progress = sum([p.progress or 0 for p in assigned_projects]) / total_projects
    else:
        total_progress = 0

    # Filters for the assigned projects list (include planned + extra filters)
    search_query = (request.GET.get('search') or '').strip()
    status_filter = (request.GET.get('status') or '').strip()
    project_type_filter = (request.GET.get('project_type') or '').strip()
    scope_filter = (request.GET.get('scope') or '').strip().lower()
    cost_min_raw = (request.GET.get('cost_min') or '').strip()
    cost_max_raw = (request.GET.get('cost_max') or '').strip()

    # Scope: all (default), combined (shared with other engineers), own (engineer is sole assignee)
    # Compute scope from Project table so counts are correct (annotating on reverse M2M can give wrong results)
    filtered_projects = assigned_projects
    if scope_filter == 'own':
        own_ids = Project.objects.annotate(num_assignees=Count('assigned_engineers', distinct=True)).filter(num_assignees=1).values_list('id', flat=True)
        filtered_projects = filtered_projects.filter(id__in=own_ids)
    elif scope_filter == 'combined':
        combined_ids = Project.objects.annotate(num_assignees=Count('assigned_engineers', distinct=True)).filter(num_assignees__gt=1).values_list('id', flat=True)
        filtered_projects = filtered_projects.filter(id__in=combined_ids)

    if search_query:
        filtered_projects = filtered_projects.filter(
            Q(name__icontains=search_query) |
            Q(prn__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    if status_filter and status_filter != 'delayed':
        if status_filter == 'in_progress':
            filtered_projects = filtered_projects.filter(status__in=['in_progress', 'ongoing'])
        elif status_filter == 'planned':
            filtered_projects = filtered_projects.filter(status__in=['planned', 'pending'])
        elif status_filter == 'completed':
            filtered_projects = filtered_projects.filter(status='completed')
        else:
            filtered_projects = filtered_projects.filter(status=status_filter)

    if project_type_filter:
        try:
            filtered_projects = filtered_projects.filter(project_type_id=int(project_type_filter))
        except (TypeError, ValueError):
            project_type_filter = ''

    # Cost range filters
    from decimal import Decimal, InvalidOperation
    if cost_min_raw:
        try:
            filtered_projects = filtered_projects.filter(project_cost__gte=Decimal(cost_min_raw))
        except (InvalidOperation, ValueError):
            cost_min_raw = ''
    if cost_max_raw:
        try:
            filtered_projects = filtered_projects.filter(project_cost__lte=Decimal(cost_max_raw))
        except (InvalidOperation, ValueError):
            cost_max_raw = ''

    filtered_projects = filtered_projects.select_related('project_type').order_by('-created_at')

    project_type_options = ProjectType.objects.all().order_by('name')

    # Get project details for display (filtered), with calculated status for delayed detection
    projects_data = []
    for project in filtered_projects:
        progress = latest_progress.get(project.id, 0) or (project.progress or 0)
        stored_status = project.status or ''
        if progress >= 99:
            calculated_status = 'completed'
        elif stored_status == 'delayed':
            calculated_status = 'delayed'
        elif progress < 99 and project.end_date and project.end_date < today and stored_status in ['in_progress', 'ongoing']:
            calculated_status = 'delayed'
        elif stored_status in ['in_progress', 'ongoing']:
            calculated_status = 'in_progress'
        elif stored_status in ['planned', 'pending']:
            calculated_status = 'planned'
        else:
            calculated_status = stored_status or ''
        
        status_display = (
            'Completed' if calculated_status == 'completed' else
            'Delayed' if calculated_status == 'delayed' else
            'Ongoing' if calculated_status in ['in_progress', 'ongoing'] else
            'Planned' if calculated_status in ['planned', 'pending'] else
            (calculated_status or stored_status or '').title()
        )
        
        projects_data.append({
            'id': project.id,
            'name': project.name,
            'status': calculated_status,
            'status_display': status_display,
            'progress': progress,
            'start_date': project.start_date,
            'end_date': project.end_date,
            'project_type': project.project_type.name if getattr(project, 'project_type', None) else '',
            'project_cost': project.project_cost,
        })
    
    if status_filter == 'delayed':
        projects_data = [p for p in projects_data if p['status'] == 'delayed']

    context = {
        'engineer': engineer,
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'planned_projects': planned_projects,
        'delayed_projects': delayed_projects,
        'total_progress': round(total_progress, 1),
        'projects': projects_data,
        'project_type_options': project_type_options,
        'search_query': search_query,
        'status_filter': status_filter,
        'project_type_filter': project_type_filter,
        'scope_filter': scope_filter,
        'cost_min': cost_min_raw,
        'cost_max': cost_max_raw,
    }
    return render(request, 'monitoring/engineers/engineer_detail.html', context)


@head_engineer_required
def engineer_edit(request, engineer_id):
    """Edit an existing Project Engineer account"""
    engineer = get_object_or_404(User, id=engineer_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Verify this is a Project Engineer
    if engineer.is_superuser or engineer.groups.filter(name='Head Engineer').exists():
        if is_ajax:
            from django.http import JsonResponse
            return JsonResponse({'success': False, 'error': 'This user is not a Project Engineer.'}, status=400)
        messages.error(request, 'This user is not a Project Engineer.')
        return redirect('engineer_list')

    # Prevent Head Engineers from editing themselves (they should use admin)
    if engineer == request.user:
        if is_ajax:
            from django.http import JsonResponse
            return JsonResponse({'success': False, 'error': 'You cannot edit your own account from this page.'}, status=400)
        messages.warning(request, 'You cannot edit your own account from this page.')
        return redirect('engineer_detail', engineer_id=engineer.id)

    if request.method == 'POST':
        form = EngineerEditForm(request.POST, instance=engineer)
        if form.is_valid():
            form.save()
            password_updated = getattr(form, 'password_updated', False)
            success_message = f'Engineer account "{engineer.username}" has been updated successfully!'
            if password_updated:
                success_message += ' Password was changed.'
            if is_ajax:
                from django.http import JsonResponse
                return JsonResponse({
                    'success': True,
                    'message': success_message,
                    'password_updated': password_updated,
                    'redirect_url': request.META.get('HTTP_REFERER', f'/dashboard/engineers/{engineer.id}/')
                })
            messages.success(request, success_message)
            return redirect('engineer_detail', engineer_id=engineer.id)
    else:
        form = EngineerEditForm(instance=engineer)

    context = {
        'form': form,
        'engineer': engineer,
        'title': f'Edit Engineer: {engineer.get_full_name() or engineer.username}',
    }
    
    # If AJAX request, return just the form content (modal version)
    if is_ajax:
        from django.template.loader import render_to_string
        form_html = render_to_string('monitoring/engineers/engineer_edit_modal.html', context, request=request)
        from django.http import HttpResponse
        return HttpResponse(form_html)
    
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


@head_engineer_required
def engineer_delete(request, engineer_id):
    """Delete a Project Engineer account"""
    engineer = get_object_or_404(User, id=engineer_id)

    # Ensure we're only deleting project engineers
    if engineer.is_superuser or engineer.groups.filter(name='Head Engineer').exists():
        messages.error(request, 'This user is not a Project Engineer.')
        return redirect('engineer_list')

    # Prevent accidental self-deletion
    if engineer == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('engineer_detail', engineer_id=engineer.id)

    if request.method == 'POST':
        username = engineer.username
        engineer.delete()
        messages.success(request, f'Engineer account "{username}" has been deleted.')
        return redirect('engineer_list')

    return redirect('engineer_detail', engineer_id=engineer.id)
