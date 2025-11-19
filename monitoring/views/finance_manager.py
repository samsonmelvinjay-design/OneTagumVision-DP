from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404
from projeng.models import Project, ProjectCost
from django.db.models import Sum
from collections import defaultdict
from django.db.models.functions import TruncMonth
from django.core.paginator import Paginator

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
def finance_dashboard(request):
    projects = Project.objects.all()
    total_budget = projects.aggregate(total=Sum('project_cost'))['total'] or 0
    total_spent = ProjectCost.objects.aggregate(total=Sum('amount'))['total'] or 0
    remaining = total_budget - total_spent
    # Bar Chart: Top 10 projects by budget
    project_financials = []
    for project in projects:
        spent = ProjectCost.objects.filter(project=project).aggregate(total=Sum('amount'))['total'] or 0
        project_financials.append({
            'name': project.name,
            'budget': float(project.project_cost or 0),
            'spent': float(spent),
        })
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
    }
    return render(request, 'finance_manager/finance_dashboard.html', context)

@login_required
@finance_manager_required
def finance_projects(request):
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Filters
        barangay_filter = request.GET.get('barangay')
        status_filter = request.GET.get('status')
        projects = Project.objects.all()
        if barangay_filter:
            projects = projects.filter(barangay=barangay_filter)
        if status_filter:
            projects = projects.filter(status=status_filter)
        
        # List of projects with their financials
        project_financials = []
        for project in projects:
            try:
                spent = ProjectCost.objects.filter(project=project).aggregate(total=Sum('amount'))['total'] or 0
                spent_float = float(spent)
                budget_float = float(project.project_cost) if project.project_cost else 0
                remaining_proj = budget_float - spent_float
                
                # Calculate threshold (20% of budget) for color coding
                threshold = budget_float * 0.2
                
                project_financials.append({
                    'name': project.name,
                    'barangay': project.barangay or '',
                    'budget': budget_float,
                    'spent': spent_float,
                    'remaining': remaining_proj,
                    'status': project.status or 'planned',
                    'threshold': threshold,
                })
            except Exception as e:
                logger.error(f"Error processing project {project.id}: {str(e)}", exc_info=True)
                continue
        
        # Sort by budget and take top 10 for chart
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
        
        # Hardcoded list of 23 barangays
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
            'project_financials': project_financials,
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
        # Filters
        prn_filter = request.GET.get('prn')
        barangay_filter = request.GET.get('barangay')
        budget_status_filter = request.GET.get('budget_status')
        projects = Project.objects.all()
        if prn_filter:
            projects = projects.filter(prn__icontains=prn_filter)
        if barangay_filter:
            projects = projects.filter(barangay=barangay_filter)
        
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
                    if spent_float > budget_float:
                        budget_status = 'over'
                        over_budget_count += 1
                    elif abs(spent_float - budget_float) < 0.01:  # Use small epsilon for float comparison
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
        
        # Pagination - 25 items per page
        paginator = Paginator(project_financials, 25)
        page_number = request.GET.get('page', 1)
        try:
            page_obj = paginator.get_page(page_number)
        except:
            page_obj = paginator.get_page(1)
        
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
            'all_barangays': all_barangays,
            'selected_prn': prn_filter or '',
            'selected_barangay': barangay_filter or '',
            'selected_budget_status': budget_status_filter or '',
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
        
        # Get the most recent Budget Review Request notification for this project
        # to extract requested amount and assessment
        budget_request_info = None
        try:
            from projeng.models import Notification
            from django.contrib.auth.models import User
            
            # Get Finance Managers
            finance_managers = User.objects.filter(groups__name='Finance Manager').distinct()
            
            # Find the most recent Budget Review Request notification for this project
            # that was sent to any Finance Manager
            from django.db.models import Q
            # Build query to match project name or PRN
            project_query = Q(message__icontains=project.name)
            if project.prn:
                project_query |= Q(message__icontains=project.prn)
            
            notifications = Notification.objects.filter(
                recipient__in=finance_managers,
                message__icontains='Budget Review Request'
            ).filter(project_query).order_by('-created_at')
            
            if notifications.exists():
                latest_request_notification = notifications.first()
                request_date = latest_request_notification.created_at
                message = latest_request_notification.message
                
                # Check if there's a newer "Budget Increase Approved" or "Budget Increase Rejected" notification
                # If there is, the request has already been processed, so don't show the buttons
                # Note: Approval/Rejection notifications are sent to Head Engineers, but we check all notifications
                # to see if a response has been made for this project
                response_notifications = Notification.objects.filter(
                    created_at__gt=request_date
                ).filter(
                    Q(message__icontains='Budget Increase Approved') | 
                    Q(message__icontains='Budget Increase Rejected') |
                    Q(message__icontains='✅ Budget Increase Approved') |
                    Q(message__icontains='❌ Budget Increase Rejected')
                ).filter(project_query).order_by('-created_at')
                
                # Only show budget request info if there's no response yet
                if not response_notifications.exists():
                    # Parse the notification message to extract requested amount and assessment
                    import re
                    
                    # Extract requested budget increase amount
                    requested_amount = None
                    amount_match = re.search(r'Requested budget increase:\s*₱([\d,]+\.?\d*)', message)
                    if amount_match:
                        try:
                            amount_str = amount_match.group(1).replace(',', '')
                            requested_amount = float(amount_str)
                        except (ValueError, AttributeError):
                            pass
                    
                    # Extract assessment message
                    assessment = None
                    assessment_match = re.search(r'Assessment from [^:]+:\s*(.+?)(?:\.\s*$|$)', message)
                    if assessment_match:
                        assessment = assessment_match.group(1).strip()
                        # Clean up common endings
                        if assessment.endswith('.'):
                            assessment = assessment[:-1]
                    
                    # Extract Head Engineer name
                    head_engineer_name = None
                    engineer_match = re.search(r'Assessment from ([^:]+):', message)
                    if engineer_match:
                        head_engineer_name = engineer_match.group(1).strip()
                    
                    if requested_amount or assessment:
                        budget_request_info = {
                            'requested_amount': requested_amount,
                            'assessment': assessment,
                            'head_engineer_name': head_engineer_name,
                            'notification_date': latest_request_notification.created_at,
                        }
        except Exception as e:
            logger.error(f"Error extracting budget request info: {str(e)}", exc_info=True)
        
        context = {
            'project': project,
            'costs': costs,
            'total_spent': total_spent_float,
            'remaining': remaining,
            'budget_utilization': budget_utilization,
            'project_budget': project_budget,
            'threshold': threshold,
            'cost_by_type': dict(cost_by_type),
            'budget_request_info': budget_request_info,
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