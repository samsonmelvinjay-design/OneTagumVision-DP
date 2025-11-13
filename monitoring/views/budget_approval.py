"""
Budget approval views for Finance Managers to approve/reject budget increase requests
"""
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
import logging
from projeng.models import Project as ProjEngProject
from projeng.utils import notify_head_engineers, format_project_display

logger = logging.getLogger(__name__)

from gistagum.access_control import finance_manager_required


@login_required
@finance_manager_required
def approve_budget_request(request, project_id):
    """
    Allow Finance Managers to approve budget increase requests.
    """
    try:
        project = get_object_or_404(ProjEngProject, pk=project_id)
        
        if request.method == 'POST':
            approved_amount = request.POST.get('approved_amount', '').strip()
            notes = request.POST.get('notes', '').strip()
            
            try:
                approved_amount_float = float(approved_amount) if approved_amount else None
            except ValueError:
                messages.error(request, "Invalid amount format. Please enter a valid number.")
                return redirect('finance_project_detail', project_id=project_id)
            
            if approved_amount_float is None or approved_amount_float <= 0:
                messages.error(request, "Approved amount must be greater than 0.")
                return redirect('finance_project_detail', project_id=project_id)
            
            # Get current budget
            current_budget = float(project.project_cost) if project.project_cost else 0
            new_budget = current_budget + approved_amount_float
            
            # Update project budget
            project.project_cost = new_budget
            project.save()
            
            # Format amounts for notification
            project_display = format_project_display(project)
            finance_manager_name = request.user.get_full_name() or request.user.username
            formatted_approved = f"₱{approved_amount_float:,.2f}"
            formatted_old = f"₱{current_budget:,.2f}"
            formatted_new = f"₱{new_budget:,.2f}"
            
            # Build notification message
            if notes:
                message = (
                    f"✅ Budget Increase Approved: {project_display} "
                    f"Budget increased by {formatted_approved} "
                    f"(from {formatted_old} to {formatted_new}). "
                    f"Approved by {finance_manager_name}. "
                    f"Notes: {notes}"
                )
            else:
                message = (
                    f"✅ Budget Increase Approved: {project_display} "
                    f"Budget increased by {formatted_approved} "
                    f"(from {formatted_old} to {formatted_new}). "
                    f"Approved by {finance_manager_name}."
                )
            
            # Notify Head Engineers
            notify_head_engineers(message, check_duplicates=False)
            
            messages.success(request, f"Budget increase approved. Project budget updated from {formatted_old} to {formatted_new}.")
            logger.info(f"Budget increase approved for project {project.id} by {request.user.username}: {formatted_approved}")
            
            return redirect('finance_project_detail', project_id=project_id)
        
        # GET request - redirect back to project detail
        messages.info(request, "Please use the form to approve budget requests.")
        return redirect('finance_project_detail', project_id=project_id)
        
    except ProjEngProject.DoesNotExist:
        messages.error(request, "Project not found.")
        return redirect('finance_projects')
    except Exception as e:
        logger.error(f"Unexpected error in approve_budget_request: {str(e)}", exc_info=True)
        messages.error(request, "An unexpected error occurred. Please try again.")
        return redirect('finance_project_detail', project_id=project_id)


@login_required
@finance_manager_required
def reject_budget_request(request, project_id):
    """
    Allow Finance Managers to reject budget increase requests.
    """
    try:
        project = get_object_or_404(ProjEngProject, pk=project_id)
        
        if request.method == 'POST':
            rejection_reason = request.POST.get('rejection_reason', '').strip()
            
            # Format for notification
            project_display = format_project_display(project)
            finance_manager_name = request.user.get_full_name() or request.user.username
            current_budget = float(project.project_cost) if project.project_cost else 0
            formatted_budget = f"₱{current_budget:,.2f}"
            
            # Build notification message
            if rejection_reason:
                message = (
                    f"❌ Budget Increase Rejected: {project_display} "
                    f"Budget increase request has been rejected. "
                    f"Current budget remains at {formatted_budget}. "
                    f"Rejected by {finance_manager_name}. "
                    f"Reason: {rejection_reason}"
                )
            else:
                message = (
                    f"❌ Budget Increase Rejected: {project_display} "
                    f"Budget increase request has been rejected. "
                    f"Current budget remains at {formatted_budget}. "
                    f"Rejected by {finance_manager_name}."
                )
            
            # Notify Head Engineers
            notify_head_engineers(message, check_duplicates=False)
            
            messages.success(request, f"Budget increase request rejected. Head Engineers have been notified.")
            logger.info(f"Budget increase rejected for project {project.id} by {request.user.username}")
            
            return redirect('finance_project_detail', project_id=project_id)
        
        # GET request - redirect back to project detail
        messages.info(request, "Please use the form to reject budget requests.")
        return redirect('finance_project_detail', project_id=project_id)
        
    except ProjEngProject.DoesNotExist:
        messages.error(request, "Project not found.")
        return redirect('finance_projects')
    except Exception as e:
        logger.error(f"Unexpected error in reject_budget_request: {str(e)}", exc_info=True)
        messages.error(request, "An unexpected error occurred. Please try again.")
        return redirect('finance_project_detail', project_id=project_id)

