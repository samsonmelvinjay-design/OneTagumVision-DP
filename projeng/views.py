from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, Http404, HttpResponseBadRequest, HttpResponseServerError, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
import json
from django.contrib.gis.geos import GEOSGeometry
from .models import Layer, Project, ProjectProgress, ProjectCost, ProgressPhoto, ProjectDocument
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
from xhtml2pdf import pisa
from django.core.paginator import Paginator
from django.db.models import Q
from django.forms.fields import DateField # Import DateField
from .utils import flag_overdue_projects_as_delayed
from django.views.decorators.http import require_GET
from django.db import transaction
import traceback
from django.db.models import ProtectedError
from django.contrib.auth.views import redirect_to_login

def is_project_engineer(user):
    return user.is_authenticated and user.groups.filter(name='Project Engineer').exists()

def is_staff_or_superuser(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

def is_project_or_head_engineer(user):
    return user.is_authenticated and (user.groups.filter(name='Project Engineer').exists() or user.groups.filter(name='Head Engineer').exists())

def is_head_engineer(user):
    return user.is_authenticated and user.groups.filter(name='Head Engineer').exists()

@user_passes_test(is_project_engineer, login_url='/accounts/login/')
def dashboard(request):
    try:
        from .models import Project, ProjectProgress
        # Get the 5 most recently assigned projects for the current user
        assigned_projects = Project.objects.filter(assigned_engineers=request.user).order_by('-pk')[:5]

        # Calculate status counts (based on all assigned projects, not just the top 5)
        all_assigned_projects = Project.objects.filter(assigned_engineers=request.user)
        today = timezone.now().date()
        status_counts = {'Planned': 0, 'In Progress': 0, 'Completed': 0, 'Delayed': 0}
        delayed_projects = []
        total_projects = all_assigned_projects.count()
        for project in all_assigned_projects:
            latest_progress = ProjectProgress.objects.filter(project=project).order_by('-date').first()
            progress = int(latest_progress.percentage_complete) if latest_progress else 0
            # Dynamic status logic
            status = project.status
            if progress >= 99:
                status = 'completed'
            elif progress < 99 and project.end_date and project.end_date < today:
                status = 'delayed'
            elif status in ['in_progress', 'ongoing']:
                status = 'in_progress'
            elif status in ['planned', 'pending']:
                status = 'planned'
            # Count for cards (use display names)
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
            'assigned_projects': assigned_projects, # Pass only the top 5 for display
            'total_projects': total_projects, # Pass total count for all
            'status_counts': status_counts, # Pass status counts for all
            'delayed_count': status_counts['Delayed'], # Pass delayed count
            'delayed_projects': delayed_projects, # Pass delayed projects list
            'projects_data': projects_data,
        }
        print(f'Dashboard View Context: {context}') # Debugging line
        return render(request, 'projeng/dashboard.html', context)
    except Exception as e:
        print(f"Error in dashboard view: {str(e)}")
        raise

# Placeholder views for new sidebar links
@user_passes_test(is_project_engineer, login_url='/accounts/login/')
def my_projects_view(request):
    # Get projects where the current user is in the assigned_engineers field
    projects = Project.objects.filter(assigned_engineers=request.user)
    delayed_count = projects.filter(status='delayed').count() # Calculate delayed count
    return render(request, 'projeng/my_projects.html', {'projects': projects, 'delayed_count': delayed_count})

@user_passes_test(is_project_engineer, login_url='/accounts/login/')
def projeng_map_view(request):
    # Get all layers for the current user
    layers = Layer.objects.filter(created_by=request.user)
    
    # Get assigned projects from ProjEngProject that have coordinates
    all_projects = Project.objects.filter(
        assigned_engineers=request.user,
        latitude__isnull=False,
        longitude__isnull=False
    )

    delayed_count = Project.objects.filter(assigned_engineers=request.user, status='delayed').count() # Calculate delayed count

    # Filter out projects with empty strings in latitude or longitude in Python
    projects_with_coords = []
    for project in all_projects:
        if project.latitude != '' and project.longitude != '':
            projects_with_coords.append(project)

    # Prepare projects_data for the map, ensuring latitude and longitude are floats
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
        'delayed_count': delayed_count, # Pass delayed count
    }
    return render(request, 'projeng/projeng_map.html', context)

@user_passes_test(is_project_engineer, login_url='/accounts/login/')
def upload_docs_view(request):
    # Get projects assigned to the current user
    assigned_projects = Project.objects.filter(assigned_engineers=request.user)
    
    delayed_count = assigned_projects.filter(status='delayed').count() # Calculate delayed count

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
        'delayed_count': delayed_count, # Pass delayed count
        'projects_data': projects_data,
    }
    
    return render(request, 'projeng/upload_docs.html', context)

@user_passes_test(is_project_engineer, login_url='/accounts/login/')
def my_reports_view(request):
    # Get projects where the current user is in the assigned_engineers field
    assigned_projects = Project.objects.filter(assigned_engineers=request.user)

    # Calculate delayed count for ALL assigned projects (before filtering)
    # This is usually what's desired for a persistent counter
    all_assigned_projects_count = Project.objects.filter(assigned_engineers=request.user).count()
    delayed_count = Project.objects.filter(assigned_engineers=request.user, status='delayed').count()

    # --- Filtering Logic ---
    barangay_filter = request.GET.get('barangay')
    status_filter = request.GET.get('status')
    start_date_filter = request.GET.get('start_date')
    end_date_filter = request.GET.get('end_date')

    if barangay_filter:
        assigned_projects = assigned_projects.filter(barangay=barangay_filter)
    if status_filter:
        assigned_projects = assigned_projects.filter(status=status_filter)
    if start_date_filter:
        try:
            # Attempt to parse the date. Use a lenient format for user input.
            start_date = datetime.strptime(start_date_filter, '%Y-%m-%d').date()
            assigned_projects = assigned_projects.filter(start_date__gte=start_date)
        except ValueError:
            # Handle invalid date format if necessary, maybe add an error message to context
            pass # Or log the error
    if end_date_filter:
        try:
            # Attempt to parse the date
            end_date = datetime.strptime(end_date_filter, '%Y-%m-%d').date()
            assigned_projects = assigned_projects.filter(end_date__lte=end_date)
        except ValueError:
            # Handle invalid date format
            pass # Or log the error
    # --- End Filtering Logic ---

    # Calculate status counts on the filtered projects
    status_counts = {}
    for status_key, status_display in Project.STATUS_CHOICES:
        # Filter counts based on the current applied filters
        count_query = assigned_projects.filter(status=status_key)

        count = count_query.count()
        status_counts[status_display] = count


    total_projects = assigned_projects.count() # Total projects AFTER filtering

    # Get distinct barangays for filtering from the original assigned projects
    # This ensures all possible barangays are listed, even if no projects are currently shown for a barangay due to other filters.
    all_assigned_projects = Project.objects.filter(assigned_engineers=request.user)
    barangays = all_assigned_projects.values_list('barangay', flat=True).distinct().exclude(barangay__isnull=True).exclude(barangay__exact='').order_by('barangay')
    statuses = Project.STATUS_CHOICES # Use defined status choices

    # --- Pagination Logic ---
    paginator = Paginator(assigned_projects, 10) # Show 10 projects per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    # --- End Pagination Logic ---

    # Convert the projects for the CURRENT page to a list of dictionaries for JSON serialization (for the modal)
    projects_list_for_modal = []
    for project in page_obj.object_list:
        latest_progress = ProjectProgress.objects.filter(project=project).order_by('-date').first()
        progress = int(latest_progress.percentage_complete) if latest_progress else 0
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
        'page_obj': page_obj, # Pass the Page object for pagination
        'projects_data': projects_list_for_modal, # Pass the list of dictionaries for the modal
        'total_projects': total_projects, # Total projects AFTER filtering
        'status_counts': status_counts, # Status counts AFTER filtering
        'barangays': barangays, # All distinct barangays for filter dropdown
        'statuses': statuses, # All status choices for filter dropdown
        'selected_barangay': barangay_filter, # Pass selected filter values to template
        'selected_status': status_filter,
        'selected_start_date': start_date_filter,
        'selected_end_date': end_date_filter,
        'delayed_count': delayed_count, # Pass delayed count
    }
    return render(request, 'projeng/my_reports.html', context)

# Placeholder view for project detail
@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
def project_detail_view(request, pk):
    project = get_object_or_404(Project, pk=pk)

    return render(request, 'projeng/project_detail.html', {'project': project})

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
            
            # Convert GeoJSON to GEOS geometry
            geos_geometry = GEOSGeometry(json.dumps(geometry))
            
            # Create new layer
            layer = Layer.objects.create(
                name=name,
                description=description,
                type=layer_type,
                geometry=geos_geometry,
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
    if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Not authorized'}, status=403)
        return redirect_to_login(request.get_full_path())
    try:
        project_engineer_group = Group.objects.get(name='Project Engineer')
        engineers = User.objects.filter(groups=project_engineer_group).order_by('username')
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
            'timeline_data': timeline_data,
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

@user_passes_test(is_project_engineer, login_url='/accounts/login/')
@csrf_exempt
def add_progress_update(request, pk):
    if request.method == 'POST':
        try:
            project = Project.objects.get(pk=pk)
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

            progress = ProjectProgress(
                project=project,
                date=datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None,
                percentage_complete=percentage_complete,
                description=description,
                created_by=request.user
            )
            progress.save()
            print(f"DEBUG: Saved ProjectProgress with id={progress.id}, percentage_complete={progress.percentage_complete}, project_id={project.id}")

            # Update the parent project's progress field
            project.progress = percentage_complete
            project.save(update_fields=["progress"])
            print(f"DEBUG: Updated Project id={project.id} progress to {project.progress}")

            # Handle multiple photo uploads
            uploaded_photos = request.FILES.getlist('photos')
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

@user_passes_test(is_project_engineer, login_url='/accounts/login/')
@csrf_exempt
def add_cost_entry(request, pk):
    if request.method == 'POST':
        try:
            project = Project.objects.get(pk=pk)
            # Use request.POST and request.FILES for multipart/form-data
            date = request.POST.get('date')
            cost_type = request.POST.get('cost_type')
            description = request.POST.get('description')
            amount = request.POST.get('amount')
            receipt = request.FILES.get('receipt')

            cost = ProjectCost(
                project=project,
                date=date,
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
                    'date': cost.date,
                    'cost_type': cost.get_cost_type_display(),
                    'description': cost.description,
                    'amount': str(cost.amount),
                }
            })
        except Project.DoesNotExist:
            return JsonResponse({'error': 'Project not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@user_passes_test(is_project_engineer, login_url='/accounts/login/')
def analytics_overview(request):
    # Placeholder for general analytics overview
    return render(request, 'projeng/analytics_overview.html')

@user_passes_test(is_project_engineer, login_url='/accounts/login/')
def analytics_overview_data(request):
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
    # Prepare data for Chart.js
    status_labels = ['Planned', 'In Progress', 'Completed', 'Delayed']
    status_data = [status_counts['planned'], status_counts['in_progress'], status_counts['completed'], status_counts['delayed']]
    background_colors = [
        'rgba(54, 162, 235, 0.6)',      # Blue
        'rgba(255, 206, 86, 0.6)',      # Yellow
        'rgba(75, 192, 192, 0.6)',      # Green
        'rgba(135, 206, 250, 0.6)',     # Light Blue
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