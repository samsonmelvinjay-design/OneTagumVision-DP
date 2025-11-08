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