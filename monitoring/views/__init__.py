from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from .finance_manager import finance_dashboard, finance_projects, finance_cost_management, finance_notifications
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

@login_required
@prevent_project_engineer_access
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

@login_required
@prevent_project_engineer_access
def reports(request):
    # This view is only accessible to Head Engineers and Finance Managers
    # Project Engineers are redirected by the decorator
    if is_head_engineer(request.user) or is_finance_manager(request.user):
        projects = Project.objects.all()
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
                    recipient=engineer,
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

def delayed_projects(request):
    return HttpResponse("delayed_projects placeholder")

def project_engineer_analytics(request, pk):
    return HttpResponse("project_engineer_analytics placeholder")

@login_required
@head_engineer_required
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

@login_required
@head_engineer_required
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
    try:
        project = Project.objects.get(pk=pk)
    except Project.DoesNotExist:
        return HttpResponse('Project not found.', status=404)
    
    # Get all progress updates
    progress_updates = ProjectProgress.objects.filter(project=project).order_by('date')
    costs = ProjectCost.objects.filter(project=project).order_by('date')
    
    # If xhtml2pdf is unavailable, return a friendly message
    if pisa is None:
        return HttpResponse('PDF export is temporarily unavailable (missing xhtml2pdf/reportlab).', content_type='text/plain')
    
    # Render the HTML template for the PDF
    template_path = 'monitoring/project_timeline_pdf.html'
    template = get_template(template_path)
    context = {
        'project': project,
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
    # Role-based queryset
    if is_head_engineer(request.user) or is_finance_manager(request.user):
        projects = Project.objects.all()
    elif is_project_engineer(request.user):
        projects = Project.objects.filter(assigned_engineers=request.user)
    else:
        projects = Project.objects.none()
    
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
    # Role-based queryset
    if is_head_engineer(request.user) or is_finance_manager(request.user):
        projects = Project.objects.all()
    elif is_project_engineer(request.user):
        projects = Project.objects.filter(assigned_engineers=request.user)
    else:
        projects = Project.objects.none()
    
    # If xhtml2pdf is unavailable, return a friendly message
    if pisa is None:
        return HttpResponse('PDF export is temporarily unavailable (missing xhtml2pdf/reportlab).', content_type='text/plain')
    
    # Render the HTML template for the PDF
    template_path = 'monitoring/reports_pdf.html'
    template = get_template(template_path)
    context = {'projects': projects}
    html = template.render(context)
    
    # Create a PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="projects_report_{timezone.now().strftime("%Y%m%d")}.pdf"'
    
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

    context = {
        'notifications': page_obj,  # Use paginated notifications
        'unread_count': unread_count,
        'page_obj': page_obj,  # For pagination controls
    }
    return render(request, 'monitoring/notifications.html', context)
