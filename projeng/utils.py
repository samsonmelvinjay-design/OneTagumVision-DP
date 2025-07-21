from django.utils import timezone
from django.contrib.auth.models import User
from .models import Notification

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

def notify_head_engineers(message):
    head_engineers = User.objects.filter(groups__name='Head Engineer')
    for user in head_engineers:
        Notification.objects.create(recipient=user, message=message)

def notify_admins(message):
    admins = User.objects.filter(is_superuser=True)
    for user in admins:
        Notification.objects.create(recipient=user, message=message) 