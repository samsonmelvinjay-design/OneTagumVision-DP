from django.shortcuts import render, redirect, get_object_or_404
from django.core.serializers import serialize
from .models import Project as MonitoringProject
from projeng.models import Project as ProjEngProject, ProjectProgress, ProjectCost, ProgressPhoto
from .forms import ProjectForm
from django.http import JsonResponse, HttpResponseNotAllowed, HttpResponseBadRequest, Http404, HttpResponseForbidden, HttpResponseServerError
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict
import json
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from collections import Counter
from django.contrib.auth.decorators import user_passes_test, login_required
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.conf import settings
from django.db import transaction, models
from django.db.models import OuterRef, Max, Subquery, IntegerField, Q, Sum, Exists
from itertools import chain
from django.utils import timezone
import logging
from projeng.utils import flag_overdue_projects_as_delayed
from decimal import Decimal
from django.views.decorators.http import require_GET
import traceback
from django.db.models import ProtectedError

def is_head_engineer(user):
    return user.is_authenticated and user.groups.filter(name='Head Engineer').exists()

def is_project_or_head_engineer(user):
    return user.is_authenticated and (user.groups.filter(name='Head Engineer').exists() or user.groups.filter(name='Project Engineer').exists())

@login_required(login_url='/accounts/login/')
def home(request):
    print(f"Inside home view. User is authenticated: {request.user.is_authenticated}")
    print(f"User: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
    if request.user.is_authenticated:
        print(f"User groups inside home view: {list(request.user.groups.values_list('name', flat=True))}")
    return render(request, 'monitoring/home.html')

@user_passes_test(is_head_engineer, login_url='/accounts/login/')
def dashboard(request):
    from projeng.models import Project as ProjEngProject, ProjectProgress
    all_projects = MonitoringProject.objects.all()
    today = timezone.now().date()
    completed_count = 0
    in_progress_count = 0
    delayed_count = 0
    planned_count = 0
    for p in all_projects:
        # Try to find the corresponding ProjEngProject by PRN
        projeng_project = ProjEngProject.objects.filter(prn=getattr(p, "prn", None)).first()
        if projeng_project:
            latest_progress = ProjectProgress.objects.filter(project=projeng_project).order_by('-date').first()
            progress = int(latest_progress.percentage_complete) if latest_progress else 0
        else:
            progress = 0
        # Dynamic status logic
        status = p.status
        if progress >= 99:
            status = 'completed'
        elif progress < 99 and p.end_date and p.end_date < today:
            status = 'delayed'
        elif status in ['in_progress', 'ongoing']:
            status = 'in_progress'
        elif status in ['planned', 'pending']:
            status = 'planned'
        if status == 'completed':
            completed_count += 1
        elif status == 'in_progress':
            in_progress_count += 1
        elif status == 'delayed':
            delayed_count += 1
        elif status == 'planned':
            planned_count += 1
    project_count = all_projects.count()
    recent_projects = all_projects.order_by('-created_at')[:5]
    return render(request, 'monitoring/dashboard.html', {
        'project_count': project_count,
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'delayed_count': delayed_count,
        'planned_count': planned_count,
        'recent_projects': recent_projects,
    })

def project_to_dict(project):
    data = model_to_dict(project)
    data['image'] = project.image.url if project.image else None
    # Serialize assigned_engineers ManyToMany field
    if 'assigned_engineers' in data and data['assigned_engineers'] is not None:
        # Convert the QuerySet of Users to a list of user IDs
        data['assigned_engineers'] = list(project.assigned_engineers.values_list('id', flat=True))
    # Add a source field to identify the database the project came from
    data['source'] = 'projeng' if isinstance(project, ProjEngProject) else 'monitoring'
    return data

@transaction.atomic
def project_list(request):
    try:
        form = ProjectForm()  # Always define form
        if request.method == 'POST':
            form = ProjectForm(request.POST, request.FILES)
            if form.is_valid():
                # Save to project engineer database (primary)
                projeng_project = form.save(commit=False)
                projeng_project.created_by = request.user
                try:
                    projeng_project.save()
                    form.save_m2m()  # Save many-to-many relationships for projeng_project

                    # Check if a corresponding project already exists in the monitoring database
                    # Use PRN as the unique identifier for matching
                    monitoring_project, created = MonitoringProject.objects.get_or_create(
                        prn=projeng_project.prn,
                        defaults={
                            'name': projeng_project.name,
                            'description': projeng_project.description,
                            'barangay': projeng_project.barangay,
                            'project_cost': projeng_project.project_cost,
                            'source_of_funds': projeng_project.source_of_funds,
                            'status': projeng_project.status,
                            'latitude': projeng_project.latitude,
                            'longitude': projeng_project.longitude,
                            'start_date': projeng_project.start_date,
                            'end_date': projeng_project.end_date,
                             # Copy image on creation - handled by model save
                            'image': projeng_project.image 
                        }
                    )

                    if not created:
                        # If project existed, update its fields from the projeng project
                        monitoring_project.name = projeng_project.name
                        monitoring_project.description = projeng_project.description
                        monitoring_project.barangay = projeng_project.barangay
                        monitoring_project.project_cost = projeng_project.project_cost
                        monitoring_project.source_of_funds = projeng_project.source_of_funds
                        monitoring_project.status = projeng_project.status
                        monitoring_project.latitude = projeng_project.latitude
                        monitoring_project.longitude = projeng_project.longitude
                        monitoring_project.start_date = projeng_project.start_date
                        monitoring_project.end_date = projeng_project.end_date
                        if projeng_project.image:
                            monitoring_project.image = projeng_project.image # Update image if present
                        monitoring_project.save()

                    # --- Copy assigned engineers from projeng_project to monitoring_project ---
                    if hasattr(monitoring_project, 'assigned_engineers'):
                        monitoring_project.assigned_engineers.clear()
                        monitoring_project.assigned_engineers.set(projeng_project.assigned_engineers.all())
                    else:
                        print("Warning: MonitoringProject model does not have assigned_engineers field. Cannot copy assignments.")
                    # --- End copy assigned engineers ---

                    print("Project saved/synced in both databases.")
                    print("Project Engineer Project:", projeng_project)
                    print("Head Engineer Project:", monitoring_project)

                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'success': True, 'project': project_to_dict(projeng_project)}) # Return projeng project data
                    else:
                        # For non-AJAX requests, redirect to the project list page
                        return redirect('project_list')
                except Exception as save_error:
                    logging.exception("Error saving project after form validation")
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'error': f'Error saving project: {save_error}'}, status=500)
                    else:
                        # For non-AJAX, show error on the page
                        form.add_error(None, f'Error saving project: {save_error}')

            else:
                # For invalid POST, if it was AJAX, return errors.
                logging.warning(f"Project form validation failed: {form.errors}")
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'errors': form.errors}, status=400)
                else:
                    pass # Fall through to GET handling with form errors

        # --- GET request handling (and non-AJAX POST with errors) ---

        # Fetch all projects from both databases, ordered by most recent first
        # Now that MonitoringProject has assigned_engineers, we can filter here
        if request.user.groups.filter(name='Project Engineer').exists():
             # Project Engineers only see projects assigned to them from the Monitoring DB
             combined_projects = MonitoringProject.objects.filter(assigned_engineers=request.user).order_by('-created_at')
        elif request.user.groups.filter(name='Head Engineer').exists() or request.user.is_superuser or request.user.is_staff:
            # Head Engineers and staff see all projects from Monitoring DB
            # For simplicity here, they see Monitoring Projects. Adjust if they should see ProjEng Projects.
             combined_projects = MonitoringProject.objects.all().order_by('-created_at')
        else:
             # Other users see no projects
             combined_projects = MonitoringProject.objects.none()

        # Apply barangay filter if selected
        barangay = request.GET.get('barangay')
        if barangay:
            combined_projects = [p for p in combined_projects if p.barangay == barangay] # Filtering list in Python after fetching - could optimize with DB filter

        # Note: Sorting already done by order_by in DB query

        # Debug output: print all project names and PRNs in the combined list
        # print('Combined Projects:')
        # for p in combined_projects:
        #     print(f'PRN: {getattr(p, "prn", "")}, Name: {p.name}, Barangay: {p.barangay}, Assigned: {list(p.assigned_engineers.values_list('username', flat=True)) if hasattr(p, 'assigned_engineers') else 'N/A'}')

        # Paginate the combined projects
        paginator = Paginator(list(combined_projects), 10)  # Use list() for pagination after potential Python filtering
        page_number = request.GET.get('page')

        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            page_obj = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 999), deliver last page of results.
            page_obj = paginator.page(paginator.num_pages)

        # Create a JSON-serializable list of all projects for JavaScript
        # Ensure correct project objects (MonitoringProject) are used here
        projects_data = []
        for p in page_obj.object_list: # Iterate over projects on the current page
            # Try to find the corresponding ProjEngProject by PRN
            projeng_project = ProjEngProject.objects.filter(prn=getattr(p, "prn", None)).first()
            if projeng_project:
                latest_progress = ProjectProgress.objects.filter(project=projeng_project).order_by('-date').first()
                progress = int(latest_progress.percentage_complete) if latest_progress else 0
            else:
                progress = 0  # Or use p.progress if you want to fallback to MonitoringProject's own field

            start_date_str = p.start_date.isoformat() if p.start_date else '';
            end_date_str = p.end_date.isoformat() if p.end_date else '';
            created_at_str = p.created_at.isoformat() if p.created_at else '';

            projects_data.append({
                "id": p.id,
                "prn": getattr(p, "prn", ""),
                "name": p.name,
                "description": p.description,
                "barangay": p.barangay,
                "project_cost": str(getattr(p, "project_cost", "")) if getattr(p, "project_cost", None) else "",
                "source_of_funds": getattr(p, "source_of_funds", ""),
                "status": p.status,
                "latitude": str(getattr(p, "latitude", "")) if getattr(p, "latitude", None) else "",
                "longitude": str(getattr(p, "longitude", "")) if getattr(p, "longitude", None) else "",
                "start_date": start_date_str,
                "end_date": end_date_str,
                "image": p.image.url if getattr(p, "image", None) else "",
                "progress": progress,
                "assigned_engineers": list(p.assigned_engineers.values_list('username', flat=True)) if hasattr(p, 'assigned_engineers') else [],
            })

        context = {
            'page_obj': page_obj, # Pass the Page object for pagination in template
            'form': form, # Always defined
            'projects_data': projects_data, # Pass the list directly for json_script
        }
        return render(request, 'monitoring/project_list.html', context)

    except Exception as e:
        print(f"Error in project_list view: {str(e)}")
        # Return a server error response for AJAX requests
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        # For non-AJAX requests, re-raise the exception for Django to handle
        raise

@user_passes_test(is_head_engineer, login_url='/accounts/login/')
def map_view(request):
    # Fetch all Monitoring Projects that have valid latitude and longitude (not null)
    all_projects = MonitoringProject.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False,
    )

    # Filter out projects with empty strings in latitude or longitude in Python
    projects_with_coords = []
    for project in all_projects:
        if project.latitude != '' and project.longitude != '':
            projects_with_coords.append(project)

    # Prepare projects_data for the map, ensuring latitude and longitude are floats
    projects_data = []
    for p in projects_with_coords:
        latest_progress = None
        # Find the corresponding project in the ProjEng DB using PRN
        try:
            projeng_project = ProjEngProject.objects.filter(prn=p.prn).first()
            if projeng_project:
                # Get latest progress from ProjEng DB
                progress_update = ProjectProgress.objects.filter(project=projeng_project).order_by('-date').first()
                if progress_update:
                    latest_progress = progress_update.percentage_complete
        except Exception as e:
            print(f"Error fetching progress for project {p.prn}: {e}")
            latest_progress = 0 # Default to 0 on error

        projects_data.append({
            "id": p.id,
            "name": p.name,
            "prn": getattr(p, "prn", ""),
            "barangay": p.barangay,
            "status": p.status,
            "latitude": float(p.latitude) if p.latitude else None,
            "longitude": float(p.longitude) if p.longitude else None,
            "image": p.image.url if getattr(p, "image", None) else "",
            "progress": latest_progress if latest_progress is not None else 0, # Include progress
            "assigned_engineers": [e.get_full_name() or e.username for e in p.assigned_engineers.all()] if hasattr(p, 'assigned_engineers') else [], # Include assigned engineers
            "description": p.description,
            "project_cost": str(getattr(p, "project_cost", "")) if getattr(p, "project_cost", None) else "",
            "source_of_funds": getattr(p, "source_of_funds", ""),
            "start_date": p.start_date.isoformat() if p.start_date else '',
            "end_date": p.end_date.isoformat() if p.end_date else '',
        })

    context = {
        'projects_data': projects_data, # projects_data is now a list of dicts
    }
    return render(request, 'monitoring/map.html', context)

def reports(request):
    from projeng.models import Project as ProjEngProject, ProjectProgress
    projects = MonitoringProject.objects.all()
    project_list = []
    today = timezone.now().date()
    for p in projects:
        # Try to find the corresponding ProjEngProject by PRN
        projeng_project = ProjEngProject.objects.filter(prn=getattr(p, "prn", None)).first()
        if projeng_project:
            latest_progress = ProjectProgress.objects.filter(project=projeng_project).order_by('-date').first()
            progress = int(latest_progress.percentage_complete) if latest_progress else 0
        else:
            progress = 0
        # Dynamic status logic
        status = p.status
        if progress >= 99:
            status = 'completed'
        elif progress < 99 and p.end_date and p.end_date < today:
            status = 'delayed'
        elif status in ['in_progress', 'ongoing']:
            status = 'in_progress'
        elif status in ['planned', 'pending']:
            status = 'planned'
        project_list.append({
            "prn": p.prn,
            "name": p.name,
            "description": p.description,
            "barangay": p.barangay,
            "location": p.barangay,  # If you have a separate location field, use p.location
            "project_cost": p.project_cost,
            "source_of_funds": p.source_of_funds,
            "start_date": p.start_date.strftime('%Y-%m-%d') if p.start_date else '',
            "end_date": p.end_date.strftime('%Y-%m-%d') if p.end_date else '',
            "status": status,
        })
    context = {}
    context['projects_json'] = json.dumps(project_list)

    # Chart data
    status_labels = ['Completed', 'Ongoing', 'Planned', 'Delayed']
    status_map = {
        'completed': 'Completed',
        'in_progress': 'Ongoing',
        'ongoing': 'Ongoing',
        'planned': 'Planned',
        'pending': 'Planned',
        'delayed': 'Delayed',
    }
    status_counts = Counter(status_map.get(p['status'].lower(), p['status'].capitalize()) for p in project_list)
    context['status_labels'] = json.dumps(status_labels)
    context['status_counts'] = json.dumps([status_counts.get(label, 0) for label in status_labels])

    barangay_labels = sorted(set(p['barangay'] for p in project_list if p['barangay']))
    barangay_counts = Counter(p['barangay'] for p in project_list if p['barangay'])
    context['barangay_labels'] = json.dumps(barangay_labels)
    context['barangay_counts'] = json.dumps([barangay_counts.get(label, 0) for label in barangay_labels])

    # For table rendering (optional, not used by JS filtering)
    context['projects'] = projects
    return render(request, 'monitoring/reports.html', context)

@csrf_exempt
def project_update_api(request, pk):
    if request.method == 'POST':
        try:
            # Update in project engineer database (primary)
            projeng_project = ProjEngProject.objects.get(pk=pk)
            data = json.loads(request.body)
            
            # Get the latest progress update
            latest_progress = ProjectProgress.objects.filter(project=projeng_project).order_by('-date').first()
            if latest_progress:
                projeng_project.progress = int(latest_progress.percentage_complete)
                projeng_project.save(update_fields=["progress"])
            # Check if progress is 99% or more and update status to completed
            if latest_progress and int(latest_progress.percentage_complete) >= 99:
                projeng_project.status = 'completed'
            else:
                # Update status from request data if not completed by progress
                projeng_project.status = data.get('status', projeng_project.status)
            
            projeng_project.save()

            # Update corresponding project in head engineer database
            try:
                # Find by name and barangay, assuming uniqueness
                monitoring_project = MonitoringProject.objects.get(
                    name=projeng_project.name,
                    barangay=projeng_project.barangay
                )
                monitoring_project.status = projeng_project.status
                monitoring_project.progress = projeng_project.progress
                monitoring_project.save(update_fields=["status", "progress"])
                print(f"DEBUG: MonitoringProject {monitoring_project.prn} status and progress synced to {monitoring_project.status}, {monitoring_project.progress}%.")
            except MonitoringProject.DoesNotExist:
                # If corresponding project doesn't exist, create it
                monitoring_project = MonitoringProject(
                    prn=projeng_project.prn,
                    name=projeng_project.name,
                    description=projeng_project.description,
                    barangay=projeng_project.barangay,
                    project_cost=projeng_project.project_cost,
                    source_of_funds=projeng_project.source_of_funds,
                    status=projeng_project.status,
                    latitude=projeng_project.latitude,
                    longitude=projeng_project.longitude,
                    start_date=projeng_project.start_date,
                    end_date=projeng_project.end_date,
                    image=projeng_project.image
                )
                monitoring_project.save()
                print(f"DEBUG: Created new MonitoringProject {monitoring_project.prn} with status {monitoring_project.status}")
            except MonitoringProject.MultipleObjectsReturned:
                print(f"Warning: Multiple monitoring projects found for {projeng_project.name} - {projeng_project.barangay}")

            return JsonResponse({'success': True, 'status': projeng_project.status})
        except ProjEngProject.DoesNotExist:
            return JsonResponse({'error': 'Project not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            print(f"Error updating project API: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return HttpResponseNotAllowed(['POST'])

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
                    ProjEngProject.objects.filter(prn=prn).delete()
                elif name and barangay:
                    ProjEngProject.objects.filter(name=name, barangay=barangay).delete()
            else:
                # Try ProjEngProject
                projeng_project = ProjEngProject.objects.filter(pk=pk).first()
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

@user_passes_test(is_head_engineer, login_url='/accounts/login/')
def delayed_projects(request):
    today = timezone.now().date()
    # Get all delayed projects from MonitoringProject
    monitoring_delayed = MonitoringProject.objects.filter(status='delayed')
    # Get all delayed projects from ProjEngProject
    projeng_delayed = ProjEngProject.objects.filter(status='delayed')
    seen = set()
    all_delayed = []
    # Add Monitoring projects first (preferred source)
    for p in monitoring_delayed:
        key = (getattr(p, 'prn', None), getattr(p, 'barangay', None))
        seen.add(key)
        all_delayed.append({
            'prn': getattr(p, 'prn', ''),
            'name': getattr(p, 'name', ''),
            'barangay': getattr(p, 'barangay', ''),
            'progress': getattr(p, 'progress', 0),
            'start_date': p.start_date.strftime('%Y-%m-%d') if p.start_date else '',
            'end_date': p.end_date.strftime('%Y-%m-%d') if p.end_date else '',
            'assigned_engineers': [e.get_full_name() or e.username for e in p.assigned_engineers.all()] if hasattr(p, 'assigned_engineers') else [],
            'source': 'Monitoring',
        })
    # Add ProjEng projects only if not already present
    for p in projeng_delayed:
        key = (getattr(p, 'prn', None), getattr(p, 'barangay', None))
        if key not in seen:
            all_delayed.append({
                'prn': getattr(p, 'prn', ''),
                'name': getattr(p, 'name', ''),
                'barangay': getattr(p, 'barangay', ''),
                'progress': getattr(p, 'progress', 0),
                'start_date': p.start_date.strftime('%Y-%m-%d') if p.start_date else '',
                'end_date': p.end_date.strftime('%Y-%m-%d') if p.end_date else '',
                'assigned_engineers': [e.get_full_name() or e.username for e in p.assigned_engineers.all()] if hasattr(p, 'assigned_engineers') else [],
                'source': 'ProjEng',
            })
    context = {
        'delayed_projects': all_delayed,
        'total_delayed': len(all_delayed),
    }
    return render(request, 'monitoring/delayed_projects.html', context)

@login_required
def project_engineer_analytics(request, pk):
    # Get the specific project being analyzed
    project = ProjEngProject.objects.get(pk=pk)
    
    # Get latest progress for the specific project
    latest_progress = ProjectProgress.objects.filter(project=project).order_by('-date').first()
    current_progress_percentage = int(latest_progress.percentage_complete) if latest_progress else 0
    last_update_date = latest_progress.date if latest_progress else None
    last_update_description = latest_progress.description if latest_progress else "No updates yet."

    # Determine status for display based on latest progress and end date for the specific project
    current_status = project.status # Default to current status from DB
    today = timezone.now().date()
    if current_progress_percentage >= 99:
        current_status = 'completed'
    elif current_progress_percentage < 99 and project.end_date and project.end_date < today:
        current_status = 'delayed'

    # Get all projects assigned to the current project engineer for the table/list below
    # This part remains to populate the table if needed on the same page
    assigned_projeng_projects = ProjEngProject.objects.filter(assigned_engineers=request.user)
    
    # Prepare data for the list of projects (similar to previous logic, but ensure latest progress is used)
    projects_data_list = []
    for proj in assigned_projeng_projects:
         # Get latest progress for EACH project in the list
        latest_proj_progress = ProjectProgress.objects.filter(project=proj).order_by('-date').first()
        current_proj_progress_percentage = int(latest_proj_progress.percentage_complete) if latest_proj_progress else 0
        
        # Determine status for display for EACH project in the list
        current_proj_status = proj.status # Default to current status from DB
        if current_proj_progress_percentage >= 99:
            current_proj_status = 'completed'
        elif current_proj_progress_percentage < 99 and proj.end_date and proj.end_date < today:
            current_proj_status = 'delayed'

        projects_data_list.append({
            'id': proj.id,
            'name': proj.name,
            'prn': proj.prn,
            'barangay': proj.barangay,
            'progress': current_proj_progress_percentage,
            'status': current_proj_status,
            'start_date': proj.start_date.isoformat() if proj.start_date else '',
            'end_date': proj.end_date.isoformat() if proj.end_date else '',
            'projeng_id': proj.id,
        })

    # Recalculate counts based on the projects_data_list
    total_projects_count = len(projects_data_list)
    completed_projects_count = len([p for p in projects_data_list if p['status'] == 'completed'])
    ongoing_projects_count = len([p for p in projects_data_list if p['status'] in ['ongoing', 'in_progress']])
    planned_projects_count = len([p for p in projects_data_list if p['status'] in ['planned', 'pending']])
    delayed_projects_count = len([p for p in projects_data_list if p['status'] == 'delayed'])

    context = {
        'project': project, # Pass the specific project object
        'current_progress_percentage': current_progress_percentage,
        'last_update_date': last_update_date,
        'last_update_description': last_update_description,
        'current_status': current_status,
        'projects': projects_data_list, # Pass the list of all assigned projects
        'user_role': 'project_engineer',
        'total_projects': len(projects_data_list),
        'completed_projects': len([p for p in projects_data_list if p['status'] == 'completed']),
        'ongoing_projects': len([p for p in projects_data_list if p['status'] in ['ongoing', 'in_progress']]),
        'planned_projects': len([p for p in projects_data_list if p['status'] in ['planned', 'pending']]),
        'delayed_projects': len([p for p in projects_data_list if p['status'] == 'delayed'])
    }

    return render(request, 'projeng/project_analytics.html', context)

@user_passes_test(is_head_engineer, login_url='/accounts/login/')
def head_engineer_analytics(request):
    all_projects = MonitoringProject.objects.all()
    from projeng.models import ProjectProgress
    projects_data = []
    today = timezone.now().date()

    for project in all_projects:
        # Get corresponding ProjEng project to check progress
        projeng_project = ProjEngProject.objects.filter(prn=project.prn).first()
        
        # Determine status for display based on progress and end date
        current_status = project.status # Default to current status from DB
        if projeng_project:
            # Get latest progress
            latest_progress = ProjectProgress.objects.filter(project=projeng_project).order_by('-date').first()
            current_progress = int(latest_progress.percentage_complete) if latest_progress else 0
            
            if current_progress >= 99:
                current_status = 'completed'
            elif current_progress < 99 and project.end_date and project.end_date < today:
                current_status = 'delayed'
        
        # Removed save logic from here to prevent recursion
        # Status updates should be handled by add_progress_update and project_update_api

        # Rest of the existing code for project data collection
        status_raw = current_status
        status_display = status_raw.replace('_', ' ').title()
        
        try:
            # Modified this section to use projeng_project if found, otherwise use monitoring project data where possible
            if projeng_project:
                updates = []
                total_progress = 0 # Calculate total progress for display in analytics, not cumulative
                latest_progress_percentage = 0
                latest_progress_description = ''
                latest_progress_date = None

                progress_updates_list = ProjectProgress.objects.filter(project=projeng_project).order_by('-date')
                
                if progress_updates_list.exists():
                    latest_update = progress_updates_list.first()
                    latest_progress_percentage = int(latest_update.percentage_complete)
                    latest_progress_description = latest_update.description
                    latest_progress_date = latest_update.date

                    for update in progress_updates_list:
                         if hasattr(update, 'created_by') and update.created_by:
                             engineer_name = update.created_by.get_full_name() or update.created_by.username or 'Unknown'
                         else:
                             engineer_name = 'Unknown'
                         # Try both 'photos' and 'progressphoto_set' for related photos
                         try:
                             photos_qs = getattr(update, 'photos', None)
                             if photos_qs is None:
                                 photos_qs = getattr(update, 'progressphoto_set', None)
                             if photos_qs is not None:
                                 photos = [photo.image.url for photo in photos_qs.all()]
                             else:
                                 photos = []
                         except Exception:
                             photos = []
                         updates.append({
                             'date': update.date.strftime('%Y-%m-%d'),
                             'percentage_complete': update.percentage_complete,
                             'description': update.description,
                             'engineer': engineer_name,
                             'photos': photos,
                         })

                # Use projeng_project data for cost and timeline if available
                cost_entries_list = ProjectCost.objects.filter(project=projeng_project).order_by('date')
                cost_entries_data = [{
                    'date': cost.date.strftime('%Y-%m-%d'),
                    'cost_type': cost.get_cost_type_display(),
                    'description': cost.description,
                    'amount': str(cost.amount),
                    'receipt_url': cost.receipt.url if cost.receipt else None,
                } for cost in cost_entries_list]
                total_cost = cost_entries_list.aggregate(total=Sum('amount'))['total'] or 0
                cost_by_type = cost_entries_list.values('cost_type').annotate(total=Sum('amount'))

                # Recalculate budget utilization using ProjEng project cost
                budget_utilization = (total_cost / projeng_project.project_cost * 100) if projeng_project.project_cost and projeng_project.project_cost > 0 else 0

                # Use projeng_project dates for timeline
                def safe_iso(val):
                    import datetime
                    if isinstance(val, str):
                        return val
                    if isinstance(val, (datetime.date, datetime.datetime)):
                        return val.isoformat()
                    return ''
                timeline_data = {
                     'start_date': safe_iso(projeng_project.start_date) if projeng_project.start_date else '',
                     'end_date': safe_iso(projeng_project.end_date) if projeng_project.end_date else '',
                     'days_elapsed': (timezone.now().date() - projeng_project.start_date).days if projeng_project.start_date else 0,
                     'total_days': (projeng_project.end_date - projeng_project.start_date).days if projeng_project.start_date and projeng_project.end_date else 0,
                 }
                assigned_engineers_list = [e.get_full_name() or e.username for e in projeng_project.assigned_engineers.all()]

                projects_data.append({
                    'id': project.id, # Monitoring Project ID
                    'name': project.name or '',
                    'prn': project.prn or '',
                    'barangay': project.barangay or '',
                    'status': status_raw or '',
                    'status_display': status_display or '',
                    'assigned_to': assigned_engineers_list or [],
                    'progress_updates': updates or [],
                    'total_progress': latest_progress_percentage if 'latest_progress_percentage' in locals() and latest_progress_percentage is not None else 0,
                    'latest_progress_description': latest_progress_description if 'latest_progress_description' in locals() else '',
                    'latest_progress_date': latest_progress_date.strftime('%Y-%m-%d') if 'latest_progress_date' in locals() and latest_progress_date else '',
                    'project_cost': projeng_project.project_cost if projeng_project and projeng_project.project_cost is not None else (project.project_cost if project.project_cost is not None else ''),
                    'source_of_funds': projeng_project.source_of_funds if projeng_project and projeng_project.source_of_funds else (project.source_of_funds or ''),
                    'start_date': timeline_data['start_date'],
                    'end_date': timeline_data['end_date'],
                    'cost_entries': cost_entries_data or [],
                    'total_cost': total_cost if total_cost is not None else 0,
                    'cost_by_type': list(cost_by_type) if cost_by_type else [],
                    'budget_utilization': budget_utilization if budget_utilization is not None else 0,
                    'days_elapsed': timeline_data['days_elapsed'],
                    'total_days': timeline_data['total_days'],
                    'projeng_id': projeng_project.id if projeng_project else '',
                })
            else:
                # Handle case where no matching ProjEng project is found
                # Use data from the Monitoring project, providing default values where ProjEng data would be
                assigned_engineers_list = [e.get_full_name() or e.username for e in project.assigned_engineers.all()]
                projects_data.append({
                    'id': project.id,
                    'name': project.name or '',
                    'prn': project.prn or '',
                    'barangay': project.barangay or '',
                    'status': status_raw or '',
                    'status_display': status_display or '',
                    'assigned_to': assigned_engineers_list or [],
                    'progress_updates': [],
                    'total_progress': 0,
                    'latest_progress_description': '',
                    'latest_progress_date': '',
                    'project_cost': project.project_cost if project.project_cost is not None else '',
                    'source_of_funds': project.source_of_funds or '',
                    'start_date': project.start_date.isoformat() if project.start_date else '',
                    'end_date': project.end_date.isoformat() if project.end_date else '',
                    'cost_entries': [],
                    'total_cost': 0,
                    'cost_by_type': [],
                    'budget_utilization': 0,
                    'days_elapsed': (timezone.now().date() - project.start_date).days if project.start_date else 0,
                    'total_days': (project.end_date - project.start_date).days if project.start_date and project.end_date else 0,
                    'projeng_id': '',
                })
        except Exception as e:
            print(f"Error processing project {project.name} (Monitoring ID: {project.id}): {e}")
            # Append minimal data to projects_data on error to avoid breaking the page
            projects_data.append({
                 'id': project.id,
                 'name': project.name or '',
                 'prn': project.prn or '',
                 'barangay': project.barangay or '',
                 'status': 'error',
                 'status_display': 'Error Loading',
                 'assigned_to': [],
                 'progress_updates': [],
                 'total_progress': 0,
                 'latest_progress_description': '',
                 'latest_progress_date': '',
                 'project_cost': '',
                 'source_of_funds': '',
                 'start_date': project.start_date.isoformat() if project.start_date else '',
                 'end_date': project.end_date.isoformat() if project.end_date else '',
                 'cost_entries': [],
                 'total_cost': 0,
                 'cost_by_type': [],
                 'budget_utilization': 0,
                 'days_elapsed': (timezone.now().date() - project.start_date).days if project.start_date else 0,
                 'total_days': (project.end_date - project.start_date).days if project.start_date and project.end_date else 0,
                 'projeng_id': '',
             })

    # After building projects_data, recursively convert all Decimals
    projects_data = safe_number(projects_data)
    context = {
        'projects': projects_data,
        'user_role': 'head_engineer',
        'total_projects': len(projects_data),
        'completed_projects': len([p for p in projects_data if p.get('status') == 'completed']),
        'ongoing_projects': len([p for p in projects_data if p.get('status') in ['in_progress', 'ongoing']]),
        'planned_projects': len([p for p in projects_data if p.get('status') in ['planned', 'pending']]),
        'delayed_projects': len([p for p in projects_data if p.get('status') == 'delayed'])
    }

    print('Projects in analytics:')
    for p in projects_data:
        # Safely access dictionary keys
        name = p.get('name', 'N/A')
        status = p.get('status', 'N/A')
        progress = p.get('total_progress', 'N/A') # Use total_progress for display in analytics
        print(f"Name: {name}, Status: {status}, Progress: {progress}%")
    
    print("Projects data being sent to template:", projects_data)
    return render(request, 'monitoring/analytics.html', context)

def project_detail(request, pk):
    project = get_object_or_404(MonitoringProject, pk=pk)
    return render(request, 'monitoring/project_detail.html', {'project': project})

@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
def head_engineer_project_detail(request, pk):
    try:
        # Fetch the project from the Monitoring DB (Head Engineer's view)
        project = get_object_or_404(MonitoringProject, pk=pk)

        # Although Head Engineers can see all projects, it's good practice to ensure
        # they have the 'Head Engineer' permission to access this specific view.
        # The user_passes_test decorator already handles this.

        # --- Fetch related data from the ProjEng DB ---
        # Find the corresponding project in the ProjEng DB using PRN or other identifier
        # Assuming PRN is unique across both DBs for corresponding projects
        try:
            projeng_project = ProjEngProject.objects.filter(prn=project.prn).first()
        except ProjEngProject.DoesNotExist:
            projeng_project = None # Handle case where no corresponding ProjEng project exists

        latest_progress = None
        progress_updates = None
        costs = None
        total_cost = 0
        cost_by_type = None
        budget_utilization = 0
        timeline_data = None
        project_photos = None

        if projeng_project:
            # Get progress data from ProjEng DB
            progress_updates = ProjectProgress.objects.filter(project=projeng_project).order_by('-date')
            latest_progress = progress_updates.first()
            # Get project photos related to progress updates from ProjEng DB
            project_photos = ProgressPhoto.objects.filter(progress_update__project=projeng_project).order_by('-progress_update__date') if projeng_project else ProgressPhoto.objects.none()

            # Get cost data from ProjEng DB
            costs = ProjectCost.objects.filter(project=projeng_project) if projeng_project else ProjectCost.objects.none()
            total_cost = costs.aggregate(total=Sum('amount'))['total'] or 0
            cost_by_type = costs.values('cost_type').annotate(total=Sum('amount')) if costs else []

            # Calculate budget utilization (using ProjEng project cost if available)
            budget_utilization = (total_cost / projeng_project.project_cost * 100) if projeng_project and projeng_project.project_cost and projeng_project.project_cost > 0 else 0
            
            # Get timeline data from ProjEng DB dates
            timeline_data = {
                'start_date': projeng_project.start_date if projeng_project else None,
                'end_date': projeng_project.end_date if projeng_project else None,
                'days_elapsed': (timezone.now().date() - projeng_project.start_date).days if projeng_project and projeng_project.start_date else None,
                'total_days': (projeng_project.end_date - projeng_project.start_date).days if projeng_project and projeng_project.start_date and projeng_project.end_date else None,
            }
        
        # If no corresponding ProjEng project, use Monitoring project dates for timeline if available
        if not timeline_data or (not timeline_data['start_date'] and project.start_date):
             timeline_data = {
                 'start_date': project.start_date,
                 'end_date': project.end_date,
                 'days_elapsed': (timezone.now().date() - project.start_date).days if project.start_date else None,
                 'total_days': (project.end_date - project.start_date).days if project.start_date and project.end_date else None,
             }


        context = {
            'project': project, # Pass the MonitoringProject object
            'projeng_project': projeng_project, # Pass the related ProjEngProject object (can be None)
            'latest_progress': latest_progress,
            'progress_updates': progress_updates, # Pass all progress updates
            'total_cost': total_cost,
            'cost_by_type': cost_by_type,
            'costs': costs, # Pass all cost entries
            'budget_utilization': budget_utilization,
            'timeline_data': timeline_data,
            'project_photos': project_photos, # Pass project photos
            'user_role': 'head_engineer', # Indicate the role for template logic
        }

        return render(request, 'monitoring/head_engineer_project_detail.html', context)

    except Http404:
        raise # Re-raise Http404
    except Exception as e:
        logging.error(f"Error in head_engineer_project_detail view for project {pk}: {e}")
        return HttpResponseServerError("An error occurred while loading project details.") 

def safe_number(val):
    if isinstance(val, Decimal):
        return float(val)
    elif isinstance(val, list):
        return [safe_number(v) for v in val]
    elif isinstance(val, dict):
        return {k: safe_number(v) for k, v in val.items()}
    return val 

@user_passes_test(is_head_engineer, login_url='/accounts/login/')
@require_GET
def head_dashboard_card_data_api(request):
    all_projects = MonitoringProject.objects.all()
    status_counts = {}
    for status_key, status_display in MonitoringProject.STATUS_CHOICES:
        count = all_projects.filter(status=status_key).count()
        status_counts[status_key] = count
    total_projects = all_projects.count()
    delayed_count = all_projects.filter(status='delayed').count()
    return JsonResponse({
        'total_projects': total_projects,
        'status_counts': status_counts,
        'delayed_count': delayed_count,
    }) 