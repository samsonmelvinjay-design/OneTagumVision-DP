"""
Budget notification views for Head Engineers to forward alerts to Finance
"""
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from projeng.models import Project as ProjEngProject
from projeng.utils import forward_budget_alert_to_finance
from gistagum.access_control import head_engineer_required


@login_required
@head_engineer_required
def forward_budget_alert_to_finance_view(request, project_id):
    """
    Allow Head Engineers to forward budget alerts to Finance Managers.
    """
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
        forward_budget_alert_to_finance(
            project=project,
            head_engineer=request.user,
            assessment_message=assessment_message if assessment_message else None,
            requested_budget_increase=requested_increase_float
        )
        
        messages.success(request, f"Budget alert forwarded to Finance Managers for project '{project.name}'.")
        return redirect('monitoring:project_detail', pk=project_id)
    
    messages.error(request, "Invalid request method.")
    return redirect('monitoring:project_detail', pk=project_id)

