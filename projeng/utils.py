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
    head_engineers = User.objects.filter(groups__name='Head Engineer')
    for user in head_engineers:
        if check_duplicates and _check_duplicate_notification(user, message):
            continue  # Skip if duplicate exists
        Notification.objects.create(recipient=user, message=message)

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
        try:
            project = Project.objects.get(name=project_name)
            return project.id
        except Project.DoesNotExist:
            pass
    
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
    
    return None 