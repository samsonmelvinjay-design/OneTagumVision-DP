"""
Budget notification views for Head Engineers to forward alerts to Finance
"""
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseServerError
import logging
from projeng.models import Project as ProjEngProject
from projeng.utils import forward_budget_alert_to_finance
from gistagum.access_control import head_engineer_required

logger = logging.getLogger(__name__)


@login_required
@head_engineer_required
def forward_budget_alert_to_finance_view(request, project_id):
    """
    Allow Head Engineers to forward budget alerts to Finance Managers.
    """
    try:
        # Try to find project in projeng model
        project = get_object_or_404(ProjEngProject, pk=project_id)
        
        if request.method == 'POST':
            assessment_message = request.POST.get('assessment_message', '').strip()
            requested_increase = request.POST.get('requested_budget_increase', '').strip()
            
            try:
                requested_increase_float = float(requested_increase) if requested_increase else None
            except ValueError:
                requested_increase_float = None
            
            # Forward notification
            try:
                forward_budget_alert_to_finance(
                    project=project,
                    head_engineer=request.user,
                    assessment_message=assessment_message if assessment_message else None,
                    requested_budget_increase=requested_increase_float
                )
                messages.success(request, f"Budget alert forwarded to Finance Managers for project '{project.name}'.")
            except Exception as e:
                logger.error(f"Error forwarding budget alert: {str(e)}", exc_info=True)
                messages.error(request, f"Error forwarding budget alert: {str(e)}")
            
            return redirect('monitoring_project_detail', pk=project_id)
        
        # GET request - redirect back to project detail
        messages.info(request, "Please use the form to forward budget alerts.")
        return redirect('monitoring_project_detail', pk=project_id)
        
    except ProjEngProject.DoesNotExist:
        messages.error(request, "Project not found.")
        return redirect('dashboard')
    except Exception as e:
        logger.error(f"Unexpected error in forward_budget_alert_to_finance_view: {str(e)}", exc_info=True)
        messages.error(request, "An unexpected error occurred. Please try again.")
        return redirect('dashboard')

