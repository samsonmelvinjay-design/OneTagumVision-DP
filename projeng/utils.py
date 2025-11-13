from django.utils import timezone
from django.contrib.auth.models import User
from .models import Notification
from datetime import timedelta

def flag_overdue_projects_as_delayed(projects, progress_model):
    """
    For each project in the queryset, if the project is ongoing (in_progress/ongoing),
    the end date has passed, and the latest progress is less than 100%,
    set the status to 'delayed' and save.
    :param projects: Queryset of Project-like objects
    :param progress_model: The ProjectProgress model to use for progress lookup
    """
    today = timezone.now().date()
    for project in projects:
        if project.status in ['in_progress', 'ongoing'] and project.end_date and project.end_date < today:
            progress_update = progress_model.objects.filter(project=project).order_by('-date').first()
            latest_progress = progress_update.percentage_complete if progress_update else 0
            if latest_progress < 98:
                project.status = 'delayed'
                project.save()

def _check_duplicate_notification(recipient, message, time_window_seconds=10):
    """
    Check if a notification with the same message was already created for the recipient
    within the specified time window to prevent duplicates.
    
    :param recipient: User object to check notifications for
    :param message: Message text to check for duplicates
    :param time_window_seconds: Time window in seconds to check for duplicates (default: 10)
    :return: True if duplicate exists, False otherwise
    """
    recent_time = timezone.now() - timedelta(seconds=time_window_seconds)
    return Notification.objects.filter(
        recipient=recipient,
        message=message,
        created_at__gte=recent_time
    ).exists()

def notify_head_engineers(message, check_duplicates=True):
    """Notify Head Engineers about important updates"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Get Head Engineers - try both exact match and case-insensitive
    head_engineers = User.objects.filter(groups__name='Head Engineer').distinct()
    head_engineer_count = head_engineers.count()
    logger.info(f"notify_head_engineers: Found {head_engineer_count} Head Engineer(s)")
    
    if head_engineer_count == 0:
        logger.warning("notify_head_engineers: No Head Engineers found with group name 'Head Engineer'")
        # Try to find any users with similar group names for debugging
        from django.contrib.auth.models import Group
        all_groups = Group.objects.all()
        logger.warning(f"Available groups: {[g.name for g in all_groups]}")
        return 0
    
    notification_count = 0
    for user in head_engineers:
        logger.info(f"notify_head_engineers: Processing Head Engineer: {user.username} (ID: {user.id})")
        if check_duplicates and _check_duplicate_notification(user, message):
            logger.debug(f"notify_head_engineers: Skipping duplicate for {user.username}")
            continue  # Skip if duplicate exists
        try:
            notification = Notification.objects.create(recipient=user, message=message)
            notification_count += 1
            logger.info(f"notify_head_engineers: Created notification ID {notification.id} for {user.username}")
        except Exception as e:
            logger.error(f"notify_head_engineers: Failed to create notification for {user.username}: {str(e)}", exc_info=True)
    
    logger.info(f"notify_head_engineers: Created {notification_count} notification(s) total")
    return notification_count

def notify_admins(message, check_duplicates=True):
    """Notify Admins about important updates"""
    admins = User.objects.filter(is_superuser=True)
    for user in admins:
        if check_duplicates and _check_duplicate_notification(user, message):
            continue  # Skip if duplicate exists
        Notification.objects.create(recipient=user, message=message)

def notify_finance_managers(message, check_duplicates=True):
    """Notify Finance Managers about financial updates"""
    finance_managers = User.objects.filter(groups__name='Finance Manager')
    for user in finance_managers:
        if check_duplicates and _check_duplicate_notification(user, message):
            continue  # Skip if duplicate exists
        Notification.objects.create(recipient=user, message=message)

def notify_head_engineers_and_finance(message, check_duplicates=True):
    """Notify both Head Engineers and Finance Managers"""
    notify_head_engineers(message, check_duplicates=check_duplicates)
    notify_finance_managers(message, check_duplicates=check_duplicates)

def format_project_display(project):
    """Helper function to format project display name consistently"""
    project_name = project.name.strip() if project.name else "Unnamed Project"
    if project.prn:
        return f"{project_name} (PRN: {project.prn})"
    return project_name

def notify_head_engineer_about_budget_concern(project, sender_user, message=None, utilization_percentage=None):
    """
    Allow Project Engineers to manually notify Head Engineers about budget concerns.
    
    Args:
        project: Project instance
        sender_user: User sending the notification (Project Engineer)
        message: Optional custom message
        utilization_percentage: Current budget utilization percentage
    
    Returns:
        int: Number of notifications created (0 if failed)
    """
    import logging
    logger = logging.getLogger(__name__)
    from django.db.models import Sum
    from .models import ProjectCost
    
    # Calculate current budget status if not provided
    if utilization_percentage is None:
        if not project.project_cost:
            logger = logging.getLogger(__name__)
            logger.warning(f"Cannot send budget alert for project {project.name} (ID: {project.id}) - no budget set")
            return 0  # Return 0 instead of None
        
        total_costs = ProjectCost.objects.filter(project=project).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        try:
            total_costs_float = float(total_costs)
            project_budget_float = float(project.project_cost)
            utilization_percentage = (total_costs_float / project_budget_float) * 100 if project_budget_float > 0 else 0
        except (ValueError, TypeError) as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error calculating utilization for project {project.name}: {str(e)}")
            utilization_percentage = 0
    
    project_display = format_project_display(project)
    sender_name = sender_user.get_full_name() or sender_user.username
    
    # Build notification message
    if message:
        notification_message = (
            f"📋 Budget Concern: {project_display} - {message} "
            f"(Current utilization: {utilization_percentage:.1f}%) "
            f"- Reported by {sender_name}"
        )
    else:
        notification_message = (
            f"📋 Budget Concern: {project_display} is at {utilization_percentage:.1f}% of budget. "
            f"Reported by {sender_name}. Please review."
        )
    
    # Notify all Head Engineers
    # Use check_duplicates=False for manual alerts to ensure they always go through
    logger.info(f"notify_head_engineer_about_budget_concern: Starting notification process")
    logger.info(f"notify_head_engineer_about_budget_concern: Project: {project.name} (ID: {project.id})")
    logger.info(f"notify_head_engineer_about_budget_concern: Sender: {sender_name}")
    logger.info(f"notify_head_engineer_about_budget_concern: Message: {notification_message}")
    notification_count = notify_head_engineers(notification_message, check_duplicates=False)
    logger.info(f"notify_head_engineer_about_budget_concern: Completed - sent to {notification_count} Head Engineer(s)")
    return notification_count

def can_update_budget(user, project):
    """
    Check if user can update project budget.
    
    Rules:
    - Finance Managers: Can update any project budget
    - Head Engineers: Can update any project budget
    - Project Engineers: Cannot update budgets
    """
    from gistagum.access_control import is_finance_manager, is_head_engineer
    
    return is_finance_manager(user) or is_head_engineer(user)

def forward_budget_alert_to_finance(project, head_engineer, assessment_message=None, requested_budget_increase=None):
    """
    Allow Head Engineers to forward budget alerts to Finance Managers with their assessment.
    
    Args:
        project: Project instance
        head_engineer: Head Engineer forwarding the alert
        assessment_message: Optional assessment/recommendation from Head Engineer
        requested_budget_increase: Optional requested budget increase amount
    """
    from django.db.models import Sum
    from .models import ProjectCost
    
    # Calculate current budget status
    total_costs = ProjectCost.objects.filter(project=project).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    try:
        total_costs_float = float(total_costs)
        project_budget_float = float(project.project_cost) or 0
        utilization_percentage = (total_costs_float / project_budget_float) * 100 if project_budget_float > 0 else 0
        remaining = project_budget_float - total_costs_float
    except (ValueError, TypeError):
        return
    
    project_display = format_project_display(project)
    head_engineer_name = head_engineer.get_full_name() or head_engineer.username
    
    formatted_total = f"₱{total_costs_float:,.2f}"
    formatted_budget = f"₱{project_budget_float:,.2f}"
    formatted_remaining = f"₱{max(0, remaining):,.2f}"
    
    # Build notification message
    if requested_budget_increase:
        formatted_increase = f"₱{float(requested_budget_increase):,.2f}"
        message = (
            f"💰 Budget Review Request: {project_display} "
            f"(Utilization: {utilization_percentage:.1f}% | Spent: {formatted_total} | Budget: {formatted_budget}). "
            f"Requested budget increase: {formatted_increase}. "
            f"Assessment from {head_engineer_name}: {assessment_message or 'Please review and approve.'}"
        )
    else:
        message = (
            f"💰 Budget Review Request: {project_display} "
            f"(Utilization: {utilization_percentage:.1f}% | Spent: {formatted_total} | Budget: {formatted_budget} | Remaining: {formatted_remaining}). "
            f"Assessment from {head_engineer_name}: {assessment_message or 'Please review.'}"
        )
    
    # Notify Finance Managers
    notify_finance_managers(message, check_duplicates=True)

def get_project_from_notification(notification_message):
    """
    Extract project information from notification message to find the related project.
    Returns project ID if found, None otherwise.
    Checks both projeng.models.Project and monitoring.models.Project.
    """
    from .models import Project as ProjengProject
    import re
    import logging
    import codecs
    
    logger = logging.getLogger(__name__)
    
    # Decode unicode escapes (e.g., \u0027 -> ')
    # Handle both string and bytes
    try:
        if isinstance(notification_message, bytes):
            notification_message = notification_message.decode('utf-8')
        # Replace unicode escape sequences
        notification_message = notification_message.encode('utf-8').decode('unicode_escape')
    except Exception as e:
        logger.warning(f"Error decoding unicode escapes: {e}")
        # Try manual replacement as fallback
        notification_message = notification_message.replace('\\u0027', "'").replace('\\u0022', '"')
    
    logger.info(f"Processing notification message: {notification_message[:200]}")
    
    # Helper function to search in a Project model
    def search_in_project_model(ProjectModel, model_name):
        """Search for project in a specific Project model"""
        # Pattern 0: "You have been assigned to project 'ProjectName (PRN: PRN123)' by ..."
        match = re.search(r"You have been assigned to project ['\u0027]([^'\u0027]+)['\u0027]", notification_message)
        if not match:
            return None
            
        project_text = match.group(1).strip()
        logger.info(f"[{model_name}] Extracted project text: '{project_text}'")
        
        # Try to extract PRN first (more reliable)
        prn_match = re.search(r"\(PRN:\s*([^)]+)\)", project_text)
        if prn_match:
            prn = prn_match.group(1).strip()
            prn_normalized = re.sub(r'\s+', ' ', prn).strip()
            logger.info(f"[{model_name}] Extracted PRN: '{prn_normalized}'")
            
            # Try exact match
            try:
                project = ProjectModel.objects.get(prn=prn_normalized)
                logger.info(f"[{model_name}] Found project by exact PRN: {project.id} - {project.name}")
                return project.id
            except ProjectModel.DoesNotExist:
                pass
            
            # Try case-insensitive
            try:
                project = ProjectModel.objects.get(prn__iexact=prn_normalized)
                logger.info(f"[{model_name}] Found project by case-insensitive PRN: {project.id} - {project.name}")
                return project.id
            except ProjectModel.DoesNotExist:
                pass
            
            # Try normalized (remove spaces/dashes)
            prn_no_spaces = re.sub(r'[\s\-_]+', '', prn_normalized)
            projects = ProjectModel.objects.filter(prn__isnull=False).exclude(prn='')
            for project in projects:
                if not project.prn:
                    continue
                project_prn_no_spaces = re.sub(r'[\s\-_]+', '', project.prn)
                if prn_no_spaces.lower() == project_prn_no_spaces.lower():
                    logger.info(f"[{model_name}] Found project by normalized PRN: {project.id} - {project.name} (PRN: {project.prn})")
                    return project.id
        
        # Fallback to project name
        project_name = re.sub(r'\s*\(PRN:[^)]+\)', '', project_text).strip()
        logger.info(f"[{model_name}] Trying project name: '{project_name}'")
        
        try:
            project = ProjectModel.objects.get(name__iexact=project_name)
            logger.info(f"[{model_name}] Found project by name: {project.id} - {project.name}")
            return project.id
        except ProjectModel.DoesNotExist:
            pass
        except ProjectModel.MultipleObjectsReturned:
            project = ProjectModel.objects.filter(name__iexact=project_name).order_by('-created_at').first()
            if project:
                logger.info(f"[{model_name}] Found project by name (multiple): {project.id} - {project.name}")
                return project.id
        
        return None
    
    # First, try to find in projeng.models.Project (project engineer's projects)
    project_id = search_in_project_model(ProjengProject, "projeng")
    if project_id:
        return project_id
    
    # If not found, try monitoring.models.Project (head engineer's projects)
    try:
        from monitoring.models import Project as MonitoringProject
        project_id = search_in_project_model(MonitoringProject, "monitoring")
        if project_id:
            logger.info(f"Found project in monitoring app: {project_id}")
            return project_id
    except ImportError:
        logger.warning("Could not import monitoring.models.Project")
    except Exception as e:
        logger.warning(f"Error searching in monitoring Project model: {e}")
    
    # If the main pattern didn't match, continue to other patterns below
    # (Pattern 1, 2, 3, etc. for other notification types)
    
    # Pattern 1: "Progress for project 'ProjectName' updated..." (for other notification types)
    # Note: This is handled by the helper function above, but keeping for other patterns
    match = re.search(r"Progress for project '([^']+)'", notification_message)
    if match:
        project_name = match.group(1)
        # Try both models
        for ProjectModel, model_name in [(ProjengProject, "projeng"), (None, "monitoring")]:
            if ProjectModel is None:
                try:
                    from monitoring.models import Project as MonitoringProject
                    ProjectModel = MonitoringProject
                except:
                    continue
            try:
                project = ProjectModel.objects.get(name__iexact=project_name)
                logger.info(f"[{model_name}] Found project by name (Pattern 1): {project.id} - {project.name}")
                return project.id
            except ProjectModel.DoesNotExist:
                pass
    
    # Pattern 2: "Cost entry added: ProjectName - ..."
    match = re.search(r"Cost entry added: ([^-]+) -", notification_message)
    if match:
        project_name = match.group(1).strip()
        # Try both models (same as Pattern 1)
        for ProjectModel, model_name in [(ProjengProject, "projeng"), (None, "monitoring")]:
            if ProjectModel is None:
                try:
                    from monitoring.models import Project as MonitoringProject
                    ProjectModel = MonitoringProject
                except:
                    continue
            try:
                project = ProjectModel.objects.get(name__iexact=project_name)
                logger.info(f"[{model_name}] Found project by name (Pattern 2 - Cost entry): {project.id} - {project.name}")
                return project.id
            except ProjectModel.DoesNotExist:
                pass
            except ProjectModel.MultipleObjectsReturned:
                project = ProjectModel.objects.filter(name__iexact=project_name).order_by('-created_at').first()
                if project:
                    logger.info(f"[{model_name}] Found project by name (Pattern 2 - Cost entry, multiple): {project.id} - {project.name}")
                    return project.id
    
    # Pattern 3: "New project created: ProjectName (PRN: PRN123) ..."
    match = re.search(r"New project created: ([^(]+)", notification_message)
    if match:
        project_name = match.group(1).strip()
        # Try to extract PRN if available
        prn_match = re.search(r"\(PRN: ([^)]+)\)", notification_message)
        if prn_match:
            prn = prn_match.group(1).strip()
            try:
                project = Project.objects.get(prn=prn)
                return project.id
            except Project.DoesNotExist:
                pass
        # Fallback to name
        try:
            project = Project.objects.get(name=project_name)
            return project.id
        except Project.DoesNotExist:
            pass
    
    # Pattern 4: "Project status updated: ProjectName (PRN: PRN123) ..."
    match = re.search(r"Project (?:status|budget|description|dates|information) updated: ([^(]+)", notification_message)
    if match:
        project_name = match.group(1).strip()
        prn_match = re.search(r"\(PRN: ([^)]+)\)", notification_message)
        if prn_match:
            prn = prn_match.group(1).strip()
            try:
                project = Project.objects.get(prn=prn)
                return project.id
            except Project.DoesNotExist:
                pass
        try:
            project = Project.objects.get(name=project_name)
            return project.id
        except Project.DoesNotExist:
            pass
    
    # Pattern 5: "Cost entry deleted: ProjectName - ..."
    match = re.search(r"Cost entry deleted: ([^-]+) -", notification_message)
    if match:
        project_name = match.group(1).strip()
        try:
            project = Project.objects.get(name=project_name)
            return project.id
        except Project.DoesNotExist:
            pass
    
    # Pattern 6: "Progress update deleted: ProjectName - ..."
    match = re.search(r"Progress update deleted: ([^-]+) -", notification_message)
    if match:
        project_name = match.group(1).strip()
        try:
            project = Project.objects.get(name=project_name)
            return project.id
        except Project.DoesNotExist:
            pass
    
    # Pattern 7: "⚠️ Budget Over-Utilized: ProjectName (PRN: PRN123) has exceeded..."
    match = re.search(r"Budget Over-Utilized: ([^(]+)", notification_message)
    if match:
        project_text = match.group(1).strip()
        # Try to extract PRN first (more reliable)
        prn_match = re.search(r"\(PRN:\s*([^)]+)\)", notification_message)
        if prn_match:
            prn = prn_match.group(1).strip()
            prn_normalized = re.sub(r'\s+', ' ', prn).strip()
            try:
                project = Project.objects.get(prn=prn_normalized)
                return project.id
            except Project.DoesNotExist:
                pass
            except Project.MultipleObjectsReturned:
                project = Project.objects.filter(prn=prn_normalized).order_by('-created_at').first()
                if project:
                    return project.id
        
        # Fallback to project name (remove PRN if present)
        project_name = re.sub(r'\s*\(PRN:[^)]+\)', '', project_text).strip()
        try:
            project = Project.objects.get(name__iexact=project_name)
            return project.id
        except Project.DoesNotExist:
            pass
        except Project.MultipleObjectsReturned:
            project = Project.objects.filter(name__iexact=project_name).order_by('-created_at').first()
            if project:
                return project.id
    
    # Pattern 8: Budget notifications - "WARNING:", "CRITICAL:", "URGENT:" with project name and PRN
    # Examples:
    # "⚠️ WARNING: ProjectName (PRN: PRN123) is at 80.0% of budget..."
    # "⚠️ CRITICAL: ProjectName (PRN: PRN123) is at 95.0% of budget..."
    # "🚨 URGENT: ProjectName (PRN: PRN123) is OVER BUDGET..."
    budget_patterns = [
        r"⚠️\s*(?:WARNING|CRITICAL):\s*([^(]+)\s*\(PRN:\s*([^)]+)\)",  # WARNING/CRITICAL with ⚠️
        r"🚨\s*URGENT:\s*([^(]+)\s*\(PRN:\s*([^)]+)\)",  # URGENT with 🚨
        r"(?:WARNING|CRITICAL|URGENT):\s*([^(]+)\s*\(PRN:\s*([^)]+)\)",  # Fallback without emoji
    ]
    
    for pattern in budget_patterns:
        match = re.search(pattern, notification_message, re.IGNORECASE)
        if match:
            project_text = match.group(1).strip()
            prn = match.group(2).strip() if len(match.groups()) >= 2 else None
            
            # Try both models
            for ProjectModel, model_name in [(ProjengProject, "projeng"), (None, "monitoring")]:
                if ProjectModel is None:
                    try:
                        from monitoring.models import Project as MonitoringProject
                        ProjectModel = MonitoringProject
                    except:
                        continue
                
                # Try PRN first (more reliable)
                if prn:
                    prn_normalized = re.sub(r'\s+', ' ', prn).strip()
                    try:
                        project = ProjectModel.objects.get(prn__iexact=prn_normalized)
                        logger.info(f"[{model_name}] Found project by PRN (Budget notification): {project.id} - {project.name}")
                        return project.id
                    except ProjectModel.DoesNotExist:
                        pass
                    except ProjectModel.MultipleObjectsReturned:
                        project = ProjectModel.objects.filter(prn__iexact=prn_normalized).order_by('-created_at').first()
                        if project:
                            logger.info(f"[{model_name}] Found project by PRN (Budget notification, multiple): {project.id} - {project.name}")
                            return project.id
                
                # Fallback to project name
                project_name = re.sub(r'\s*\(PRN:[^)]+\)', '', project_text).strip()
                try:
                    project = ProjectModel.objects.get(name__iexact=project_name)
                    logger.info(f"[{model_name}] Found project by name (Budget notification): {project.id} - {project.name}")
                    return project.id
                except ProjectModel.DoesNotExist:
                    pass
                except ProjectModel.MultipleObjectsReturned:
                    project = ProjectModel.objects.filter(name__iexact=project_name).order_by('-created_at').first()
                    if project:
                        logger.info(f"[{model_name}] Found project by name (Budget notification, multiple): {project.id} - {project.name}")
                        return project.id
    
    # Pattern 9: Budget Concern notifications - "📋 Budget Concern: ProjectName (PRN: ...)"
    match = re.search(r"📋\s*Budget Concern:\s*([^(]+)\s*\(PRN:\s*([^)]+)\)", notification_message)
    if match:
        project_text = match.group(1).strip()
        prn = match.group(2).strip()
        prn_normalized = re.sub(r'\s+', ' ', prn).strip()
        
        # Try both models
        for ProjectModel, model_name in [(ProjengProject, "projeng"), (None, "monitoring")]:
            if ProjectModel is None:
                try:
                    from monitoring.models import Project as MonitoringProject
                    ProjectModel = MonitoringProject
                except:
                    continue
            
            try:
                project = ProjectModel.objects.get(prn__iexact=prn_normalized)
                logger.info(f"[{model_name}] Found project by PRN (Budget Concern): {project.id} - {project.name}")
                return project.id
            except ProjectModel.DoesNotExist:
                pass
            except ProjectModel.MultipleObjectsReturned:
                project = ProjectModel.objects.filter(prn__iexact=prn_normalized).order_by('-created_at').first()
                if project:
                    logger.info(f"[{model_name}] Found project by PRN (Budget Concern, multiple): {project.id} - {project.name}")
                    return project.id
            
            # Fallback to project name
            project_name = re.sub(r'\s*\(PRN:[^)]+\)', '', project_text).strip()
            try:
                project = ProjectModel.objects.get(name__iexact=project_name)
                logger.info(f"[{model_name}] Found project by name (Budget Concern): {project.id} - {project.name}")
                return project.id
            except ProjectModel.DoesNotExist:
                pass
            except ProjectModel.MultipleObjectsReturned:
                project = ProjectModel.objects.filter(name__iexact=project_name).order_by('-created_at').first()
                if project:
                    logger.info(f"[{model_name}] Found project by name (Budget Concern, multiple): {project.id} - {project.name}")
                    return project.id
    
    # Pattern 10: Budget Review Request - "💰 Budget Review Request: ProjectName (PRN: ...)"
    match = re.search(r"💰\s*Budget Review Request:\s*([^(]+)\s*\(PRN:\s*([^)]+)\)", notification_message)
    if match:
        project_text = match.group(1).strip()
        prn = match.group(2).strip()
        prn_normalized = re.sub(r'\s+', ' ', prn).strip()
        
        # Try both models
        for ProjectModel, model_name in [(ProjengProject, "projeng"), (None, "monitoring")]:
            if ProjectModel is None:
                try:
                    from monitoring.models import Project as MonitoringProject
                    ProjectModel = MonitoringProject
                except:
                    continue
            
            try:
                project = ProjectModel.objects.get(prn__iexact=prn_normalized)
                logger.info(f"[{model_name}] Found project by PRN (Budget Review Request): {project.id} - {project.name}")
                return project.id
            except ProjectModel.DoesNotExist:
                pass
            except ProjectModel.MultipleObjectsReturned:
                project = ProjectModel.objects.filter(prn__iexact=prn_normalized).order_by('-created_at').first()
                if project:
                    logger.info(f"[{model_name}] Found project by PRN (Budget Review Request, multiple): {project.id} - {project.name}")
                    return project.id
            
            # Fallback to project name
            project_name = re.sub(r'\s*\(PRN:[^)]+\)', '', project_text).strip()
            try:
                project = ProjectModel.objects.get(name__iexact=project_name)
                logger.info(f"[{model_name}] Found project by name (Budget Review Request): {project.id} - {project.name}")
                return project.id
            except ProjectModel.DoesNotExist:
                pass
            except ProjectModel.MultipleObjectsReturned:
                project = ProjectModel.objects.filter(name__iexact=project_name).order_by('-created_at').first()
                if project:
                    logger.info(f"[{model_name}] Found project by name (Budget Review Request, multiple): {project.id} - {project.name}")
                    return project.id
    
    # Pattern 11: Generic budget notification - "ProjectName (PRN: ...) is at X% of budget"
    match = re.search(r"([^(]+)\s*\(PRN:\s*([^)]+)\)\s+is\s+(?:at|OVER)\s+.*budget", notification_message, re.IGNORECASE)
    if match:
        project_text = match.group(1).strip()
        prn = match.group(2).strip()
        prn_normalized = re.sub(r'\s+', ' ', prn).strip()
        
        # Try both models
        for ProjectModel, model_name in [(ProjengProject, "projeng"), (None, "monitoring")]:
            if ProjectModel is None:
                try:
                    from monitoring.models import Project as MonitoringProject
                    ProjectModel = MonitoringProject
                except:
                    continue
            
            try:
                project = ProjectModel.objects.get(prn__iexact=prn_normalized)
                logger.info(f"[{model_name}] Found project by PRN (Generic budget): {project.id} - {project.name}")
                return project.id
            except ProjectModel.DoesNotExist:
                pass
            except ProjectModel.MultipleObjectsReturned:
                project = ProjectModel.objects.filter(prn__iexact=prn_normalized).order_by('-created_at').first()
                if project:
                    logger.info(f"[{model_name}] Found project by PRN (Generic budget, multiple): {project.id} - {project.name}")
                    return project.id
            
            # Fallback to project name
            project_name = re.sub(r'\s*\(PRN:[^)]+\)', '', project_text).strip()
            try:
                project = ProjectModel.objects.get(name__iexact=project_name)
                logger.info(f"[{model_name}] Found project by name (Generic budget): {project.id} - {project.name}")
                return project.id
            except ProjectModel.DoesNotExist:
                pass
            except ProjectModel.MultipleObjectsReturned:
                project = ProjectModel.objects.filter(name__iexact=project_name).order_by('-created_at').first()
                if project:
                    logger.info(f"[{model_name}] Found project by name (Generic budget, multiple): {project.id} - {project.name}")
                    return project.id
    
    return None 