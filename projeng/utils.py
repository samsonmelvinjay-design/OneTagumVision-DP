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
    """
    from .models import Project
    import re
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Pattern 0: "You have been assigned to project 'ProjectName (PRN: PRN123)' by ..."
    match = re.search(r"You have been assigned to project '([^']+)'", notification_message)
    if match:
        project_text = match.group(1).strip()
        logger.info(f"Extracted project text: '{project_text}'")
        
        # Try to extract PRN first (more reliable)
        # Handle both "PRN: PRN123" and "PRN:PRN123" formats
        prn_match = re.search(r"\(PRN:\s*([^)]+)\)", project_text)
        if prn_match:
            prn = prn_match.group(1).strip()
            logger.info(f"Extracted PRN: '{prn}'")
            
            # Try exact match first
            try:
                project = Project.objects.get(prn=prn)
                logger.info(f"Found project by exact PRN match: {project.id} - {project.name}")
                return project.id
            except Project.DoesNotExist:
                pass
            
            # Try with case-insensitive match
            try:
                project = Project.objects.get(prn__iexact=prn)
                logger.info(f"Found project by case-insensitive PRN match: {project.id} - {project.name}")
                return project.id
            except Project.DoesNotExist:
                pass
            
            # Try removing "PRN" prefix if present (e.g., "PRN9091" -> "9091")
            prn_clean = re.sub(r'^PRN\s*', '', prn, flags=re.IGNORECASE).strip()
            if prn_clean != prn:
                try:
                    project = Project.objects.get(prn__iexact=prn_clean)
                    logger.info(f"Found project by cleaned PRN: {project.id} - {project.name}")
                    return project.id
                except Project.DoesNotExist:
                    pass
                # Also try with "PRN" prefix
                try:
                    project = Project.objects.get(prn__iexact=f"PRN{prn_clean}")
                    logger.info(f"Found project by PRN with prefix: {project.id} - {project.name}")
                    return project.id
                except Project.DoesNotExist:
                    pass
        
        # Fallback to project name (remove PRN part if present)
        project_name = re.sub(r'\s*\(PRN:[^)]+\)', '', project_text).strip()
        logger.info(f"Trying project name: '{project_name}'")
        try:
            project = Project.objects.get(name=project_name)
            logger.info(f"Found project by name: {project.id} - {project.name}")
            return project.id
        except Project.DoesNotExist:
            pass
        except Project.MultipleObjectsReturned:
            # If multiple projects with same name, try to get the most recent one
            project = Project.objects.filter(name=project_name).order_by('-created_at').first()
            if project:
                logger.info(f"Found project by name (multiple found, using most recent): {project.id} - {project.name}")
                return project.id
        
        logger.warning(f"Could not find project for text: '{project_text}'")
    
    # Pattern 1: "Progress for project 'ProjectName' updated..."
    match = re.search(r"Progress for project '([^']+)'", notification_message)
    if match:
        project_name = match.group(1)
        try:
            project = Project.objects.get(name=project_name)
            return project.id
        except Project.DoesNotExist:
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