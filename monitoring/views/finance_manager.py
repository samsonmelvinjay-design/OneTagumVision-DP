from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from projeng.models import Project, ProjectCost
from django.db.models import Sum
from collections import defaultdict
from django.db.models.functions import TruncMonth

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
                
                project_financials.append({
                    'name': project.name,
                    'barangay': project.barangay or '',
                    'budget': budget_float,
                    'spent': spent_float,
                    'remaining': remaining_proj,
                    'status': project.status or 'planned',
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
        all_statuses = [s[0] for s in Project.STATUS_CHOICES if s[0] != 'cancelled']
        
        context = {
            'project_financials': project_financials,
            'project_names': project_names,
            'project_budgets': project_budgets,
            'project_spent': project_spent,
            'cost_by_type': dict(cost_by_type),
            'all_barangays': all_barangays,
            'all_statuses': all_statuses,
            'selected_barangay': barangay_filter or '',
            'selected_status': status_filter or '',
        }
        return render(request, 'finance_manager/finance_projects.html', context)
    except Exception as e:
        logger.error(f"Error in finance_projects view: {str(e)}", exc_info=True)
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, f"Error loading projects: {str(e)}")
        return redirect('finance_dashboard')

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
                
                project_financials.append({
                    'id': project.id,
                    'prn': project.prn or '',
                    'name': project.name,
                    'barangay': project.barangay or '',
                    'budget': budget_float,
                    'spent': spent_float,
                    'remaining': remaining,
                    'budget_status': budget_status,
                })
            except Exception as e:
                logger.error(f"Error processing project {project.id}: {str(e)}", exc_info=True)
                continue
        
        # Apply budget status filter AFTER counting
        if budget_status_filter:
            project_financials = [p for p in project_financials if p['budget_status'] == budget_status_filter]
            # Recalculate counts based on filtered results
            over_budget_count = len([p for p in project_financials if p['budget_status'] == 'over'])
            within_budget_count = len([p for p in project_financials if p['budget_status'] == 'within'])
            under_budget_count = len([p for p in project_financials if p['budget_status'] == 'under'])
        
        total_projects = len(project_financials)
        
        # For filters
        all_barangays = [
            'Apokon', 'Bincungan', 'Busaon', 'Canocotan', 'Cuambogan', 'La Filipina', 'Liboganon',
            'Madaum', 'Magdum', 'Magugpo East', 'Magugpo North', 'Magugpo Poblacion', 'Magugpo South',
            'Magugpo West', 'Mankilam', 'New Balamban', 'Nueva Fuerza', 'Pagsabangan', 'Pandapan',
            'San Agustin', 'San Isidro', 'San Miguel', 'Visayan Village'
        ]
        
        context = {
            'project_financials': project_financials,
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
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, f"Error loading finance management: {str(e)}")
        return redirect('finance_dashboard')

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
    
    try:
        # Try to get project from projeng model first
        project = get_object_or_404(Project, id=project_id)
        logger.info(f"Finance project detail: Found project {project_id} in projeng model")
    except Exception as e:
        logger.error(f"Finance project detail: Error getting project {project_id}: {str(e)}", exc_info=True)
        from django.http import Http404
        raise Http404("Project not found")
    
    try:
        costs = ProjectCost.objects.filter(project=project).order_by('-date')
        total_spent = costs.aggregate(total=Sum('amount'))['total'] or 0
        project_budget = float(project.project_cost) if project.project_cost else 0
        total_spent_float = float(total_spent)
        remaining = project_budget - total_spent_float
        budget_utilization = (total_spent_float / project_budget * 100) if project_budget > 0 else 0
        
        cost_by_type = defaultdict(float)
        for cost in costs:
            cost_by_type[cost.get_cost_type_display()] += float(cost.amount)
        
        context = {
            'project': project,
            'costs': costs,
            'total_spent': total_spent_float,
            'remaining': remaining,
            'budget_utilization': budget_utilization,
            'project_budget': project_budget,
            'cost_by_type': dict(cost_by_type),
        }
        return render(request, 'finance_manager/finance_project_detail.html', context)
    except Exception as e:
        logger.error(f"Finance project detail: Error processing project {project_id}: {str(e)}", exc_info=True)
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, f"Error loading project details: {str(e)}")
        return redirect('finance_projects') 