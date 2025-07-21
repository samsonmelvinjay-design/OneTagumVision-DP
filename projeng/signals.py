from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Project, ProjectProgress, ProjectCost, ProjectDocument, Notification
from monitoring.models import Project as MonitoringProject
from .utils import notify_head_engineers, notify_admins

@receiver(post_save, sender=Project)
def sync_projeng_to_monitoring(sender, instance, **kwargs):
    print(f"SIGNAL: sync_projeng_to_monitoring called for Project id={instance.id}, prn={instance.prn}")
    try:
        if instance.prn:
            monitoring_project, created = MonitoringProject.objects.get_or_create(
                prn=instance.prn,
                defaults={
                    'name': instance.name,
                    'description': instance.description,
                    'barangay': instance.barangay,
                    'project_cost': str(instance.project_cost) if instance.project_cost is not None else '',
                    'source_of_funds': instance.source_of_funds,
                    'status': instance.status,
                    'latitude': instance.latitude or 0,
                    'longitude': instance.longitude or 0,
                    'start_date': instance.start_date,
                    'end_date': instance.end_date,
                    'image': instance.image,
                }
            )
            if not created:
                monitoring_project.name = instance.name
                monitoring_project.description = instance.description
                monitoring_project.barangay = instance.barangay
                monitoring_project.project_cost = str(instance.project_cost) if instance.project_cost is not None else ''
                monitoring_project.source_of_funds = instance.source_of_funds
                monitoring_project.status = instance.status
                monitoring_project.latitude = instance.latitude or 0
                monitoring_project.longitude = instance.longitude or 0
                monitoring_project.start_date = instance.start_date
                monitoring_project.end_date = instance.end_date
                if instance.image:
                    monitoring_project.image = instance.image
                monitoring_project.save()
            # Sync assigned engineers
            if hasattr(monitoring_project, 'assigned_engineers'):
                monitoring_project.assigned_engineers.set(instance.assigned_engineers.all())
            else:
                print('Warning: MonitoringProject has no assigned_engineers field')
        print(f"SIGNAL: sync_projeng_to_monitoring completed for Project id={instance.id}, prn={instance.prn}")
    except Exception as e:
        print(f"SIGNAL ERROR: sync_projeng_to_monitoring failed for Project id={instance.id}, prn={instance.prn}: {e}")

@receiver(post_save, sender=Project)
def notify_project_updates(sender, instance, created, **kwargs):
    """Notify Head Engineers and Admins about project updates"""
    if created:
        message = f"New project created: {instance.name} (PRN: {instance.prn or 'N/A'}) by {instance.created_by.get_full_name() or instance.created_by.username}"
        notify_head_engineers(message)
        notify_admins(message)
    else:
        # For updates, we'll notify about any save operation
        message = f"Project updated: {instance.name} (PRN: {instance.prn or 'N/A'}) by {instance.created_by.get_full_name() or instance.created_by.username}"
        notify_head_engineers(message)
        notify_admins(message)

@receiver(post_save, sender=ProjectProgress)
def notify_progress_updates(sender, instance, created, **kwargs):
    """Notify Head Engineers and Admins about progress updates"""
    if created:
        message = f"Progress update added: {instance.project.name} - {instance.percentage_complete}% complete on {instance.date} by {instance.created_by.get_full_name() or instance.created_by.username}"
        notify_head_engineers(message)
        notify_admins(message)
    else:
        message = f"Progress update modified: {instance.project.name} - {instance.percentage_complete}% complete on {instance.date} by {instance.created_by.get_full_name() or instance.created_by.username}"
        notify_head_engineers(message)
        notify_admins(message)

@receiver(post_save, sender=ProjectCost)
def notify_cost_updates(sender, instance, created, **kwargs):
    """Notify Head Engineers and Admins about cost updates"""
    if created:
        message = f"Cost entry added: {instance.project.name} - {instance.get_cost_type_display()} cost of {instance.amount} on {instance.date} by {instance.created_by.get_full_name() or instance.created_by.username}"
        notify_head_engineers(message)
        notify_admins(message)
    else:
        message = f"Cost entry modified: {instance.project.name} - {instance.get_cost_type_display()} cost of {instance.amount} on {instance.date} by {instance.created_by.get_full_name() or instance.created_by.username}"
        notify_head_engineers(message)
        notify_admins(message)

@receiver(post_save, sender=ProjectDocument)
def notify_document_uploads(sender, instance, created, **kwargs):
    """Notify Head Engineers and Admins about document uploads"""
    if created:
        message = f"Document uploaded: {instance.name} for project {instance.project.name} by {instance.uploaded_by.get_full_name() if instance.uploaded_by else 'Unknown user'}"
        notify_head_engineers(message)
        notify_admins(message)

@receiver(post_delete, sender=ProjectProgress)
def notify_progress_deletion(sender, instance, **kwargs):
    """Notify Head Engineers and Admins about progress deletion"""
    message = f"Progress update deleted: {instance.project.name} - {instance.percentage_complete}% complete on {instance.date} by {instance.created_by.get_full_name() or instance.created_by.username}"
    notify_head_engineers(message)
    notify_admins(message)

@receiver(post_delete, sender=ProjectCost)
def notify_cost_deletion(sender, instance, **kwargs):
    """Notify Head Engineers and Admins about cost deletion"""
    message = f"Cost entry deleted: {instance.project.name} - {instance.get_cost_type_display()} cost of {instance.amount} on {instance.date} by {instance.created_by.get_full_name() or instance.created_by.username}"
    notify_head_engineers(message)
    notify_admins(message)

@receiver(post_delete, sender=ProjectDocument)
def notify_document_deletion(sender, instance, **kwargs):
    """Notify Head Engineers and Admins about document deletion"""
    message = f"Document deleted: {instance.name} for project {instance.project.name} by {instance.uploaded_by.get_full_name() if instance.uploaded_by else 'Unknown user'}"
    notify_head_engineers(message)
    notify_admins(message) 