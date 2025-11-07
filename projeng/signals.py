from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Project, ProjectProgress, ProjectCost, ProjectDocument, Notification
from monitoring.models import Project as MonitoringProject
from .utils import notify_head_engineers, notify_admins, notify_finance_managers, notify_head_engineers_and_finance

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

# Store old instance state before save
_old_project_state = {}

@receiver(pre_save, sender=Project)
def store_old_project_state(sender, instance, **kwargs):
    """Store the old state of the project before save to detect changes"""
    if instance.pk:
        try:
            old_instance = Project.objects.get(pk=instance.pk)
            _old_project_state[instance.pk] = {
                'status': old_instance.status,
                'project_cost': old_instance.project_cost,
            }
        except Project.DoesNotExist:
            pass

@receiver(post_save, sender=Project)
def notify_project_updates(sender, instance, created, **kwargs):
    """Notify Head Engineers, Finance Managers, and Admins about project updates"""
    from django.contrib.auth.models import User
    
    if created:
        # New project created
        creator_name = instance.created_by.get_full_name() or instance.created_by.username if instance.created_by else 'Unknown'
        message = f"New project created: {instance.name} (PRN: {instance.prn or 'N/A'}) by {creator_name}"
        notify_head_engineers(message)
        notify_admins(message)
    else:
        # Project updated - check if it's a significant update
        old_state = _old_project_state.pop(instance.pk, None) if instance.pk else None
        
        if old_state:
            # Check if status changed
            if old_state.get('status') != instance.status:
                # Get the user who made the update (try to get from request if available)
                updater_name = getattr(instance, '_updated_by_username', None)
                if not updater_name and instance.created_by:
                    updater_name = instance.created_by.get_full_name() or instance.created_by.username
                if not updater_name:
                    updater_name = 'Unknown'
                
                old_status_display = dict(Project.STATUS_CHOICES).get(old_state.get('status'), old_state.get('status', 'Unknown'))
                new_status_display = instance.get_status_display()
                message = f"Project status updated: {instance.name} (PRN: {instance.prn or 'N/A'}) changed from '{old_status_display}' to '{new_status_display}' by {updater_name}"
                notify_head_engineers(message)
                notify_admins(message)
            # Check if cost changed significantly
            elif old_state.get('project_cost') != instance.project_cost and instance.project_cost:
                updater_name = getattr(instance, '_updated_by_username', None)
                if not updater_name and instance.created_by:
                    updater_name = instance.created_by.get_full_name() or instance.created_by.username
                if not updater_name:
                    updater_name = 'Unknown'
                
                old_cost = old_state.get('project_cost') or 0
                new_cost = instance.project_cost or 0
                message = f"Project budget updated: {instance.name} (PRN: {instance.prn or 'N/A'}) changed from ₱{old_cost:,.2f} to ₱{new_cost:,.2f} by {updater_name}"
                notify_head_engineers(message)
                notify_admins(message)
        # If explicit notification flag is set, notify
        elif hasattr(instance, '_notify_update') and instance._notify_update:
            updater_name = getattr(instance, '_updated_by_username', None)
            if not updater_name and instance.created_by:
                updater_name = instance.created_by.get_full_name() or instance.created_by.username
            if not updater_name:
                updater_name = 'Unknown'
            message = f"Project updated: {instance.name} (PRN: {instance.prn or 'N/A'}) by {updater_name}"
            notify_head_engineers(message)
            notify_admins(message)

@receiver(post_save, sender=ProjectProgress)
def notify_progress_updates(sender, instance, created, **kwargs):
    """Notify Head Engineers about progress updates from project engineers"""
    if created:
        creator_name = instance.created_by.get_full_name() or instance.created_by.username if instance.created_by else 'Unknown'
        message = f"Progress for project '{instance.project.name}' updated to {instance.percentage_complete}% by {creator_name}"
        # Only notify head engineers (not finance managers for every progress update to reduce noise)
        notify_head_engineers(message)
        notify_admins(message)
    # Skip notifications for progress modifications to reduce noise

@receiver(post_save, sender=ProjectCost)
def notify_cost_updates(sender, instance, created, **kwargs):
    """Notify Head Engineers and Finance Managers about cost updates"""
    if created:
        creator_name = instance.created_by.get_full_name() or instance.created_by.username if instance.created_by else 'Unknown'
        # Safely format amount - convert to float if it's a Decimal or string
        try:
            if isinstance(instance.amount, str):
                amount_value = float(instance.amount)
            else:
                amount_value = float(instance.amount)
            formatted_amount = f"₱{amount_value:,.2f}"
        except (ValueError, TypeError):
            formatted_amount = f"₱{instance.amount}"
        
        message = f"Cost entry added: {instance.project.name} - {instance.get_cost_type_display()} {formatted_amount} on {instance.date.strftime('%B %d, %Y')} by {creator_name}"
        # Notify head engineers when finance managers or project engineers add costs
        notify_head_engineers(message)
        notify_admins(message)
    # Skip notifications for cost modifications to reduce noise

@receiver(post_save, sender=ProjectDocument)
def notify_document_uploads(sender, instance, created, **kwargs):
    """Notify Head Engineers about document uploads"""
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