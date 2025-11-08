from django.db.models.signals import pre_save, post_save, post_delete, m2m_changed
from django.db.models import Q
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Project, ProjectProgress, ProjectCost, ProjectDocument, Notification
from monitoring.models import Project as MonitoringProject
from .utils import notify_head_engineers, notify_admins, notify_finance_managers, notify_head_engineers_and_finance

# Phase 3: Import WebSocket broadcasting utilities (parallel to SSE)
try:
    from .channels_utils import (
        broadcast_notification_to_user,
        broadcast_project_created,
        broadcast_project_updated,
        broadcast_project_deleted,
        broadcast_project_status_change,
        broadcast_cost_update,
        broadcast_progress_update,
    )
    WEBSOCKET_AVAILABLE = True
except ImportError:
    # WebSocket not available - fail gracefully, SSE still works
    WEBSOCKET_AVAILABLE = False
    print("⚠️  WebSocket broadcasting not available (SSE still works)")

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
                'assigned_engineers': set(old_instance.assigned_engineers.values_list('id', flat=True)),
                'description': old_instance.description,
                'start_date': old_instance.start_date,
                'end_date': old_instance.end_date,
                'name': old_instance.name,
                'barangay': old_instance.barangay,
            }
        except Project.DoesNotExist:
            pass

@receiver(post_save, sender=Project)
def notify_project_updates(sender, instance, created, **kwargs):
    """Notify Head Engineers, Finance Managers, and Admins about project updates"""
    from django.contrib.auth.models import User
    from .models import Notification
    
    if created:
        # New project created
        creator_name = instance.created_by.get_full_name() or instance.created_by.username if instance.created_by else 'Unknown'
        project_display = f"{instance.name}" + (f" (PRN: {instance.prn})" if instance.prn else "")
        
        # Get assigned engineer names
        assigned_engineers = instance.assigned_engineers.all()
        engineer_names = []
        for engineer in assigned_engineers:
            engineer_name = engineer.get_full_name() or engineer.username
            engineer_names.append(engineer_name)
        
        # Build notification message with assigned engineers
        if engineer_names:
            engineers_text = ", ".join(engineer_names)
            message = f"New project created: {project_display} by {creator_name} - Assigned to: {engineers_text}"
        else:
            message = f"New project created: {project_display} by {creator_name} - No engineers assigned"
        
        # Notify Head Engineers and Admins about project creation
        notify_head_engineers(message)
        notify_admins(message)
        
        # Notify assigned engineers that they have been assigned to this project
        for engineer in instance.assigned_engineers.all():
            engineer_message = f"You have been assigned to project '{project_display}' by {creator_name}"
            Notification.objects.create(
                recipient=engineer,
                message=engineer_message
            )
        
        # Phase 3: Also broadcast via WebSocket (parallel to SSE)
        if WEBSOCKET_AVAILABLE:
            try:
                broadcast_project_created(instance)
            except Exception as e:
                print(f"⚠️  WebSocket broadcast failed (SSE still works): {e}")
    else:
        # Project updated - check if it's a significant update
        old_state = _old_project_state.pop(instance.pk, None) if instance.pk else None
        
        # Check if assigned engineers changed
        if old_state:
            old_assigned_ids = old_state.get('assigned_engineers', set())
            new_assigned_ids = set(instance.assigned_engineers.values_list('id', flat=True))
            
            # Find newly assigned engineers
            newly_assigned_ids = new_assigned_ids - old_assigned_ids
            if newly_assigned_ids:
                # Get the user who made the assignment (try to get from request if available)
                assigner_name = getattr(instance, '_updated_by_username', None)
                if not assigner_name and instance.created_by:
                    assigner_name = instance.created_by.get_full_name() or instance.created_by.username
                if not assigner_name:
                    assigner_name = 'Unknown'
                
                project_display = f"{instance.name}" + (f" (PRN: {instance.prn})" if instance.prn else "")
                
                # Notify newly assigned engineers (only them, not head engineers)
                from django.contrib.auth.models import User
                newly_assigned_engineers = User.objects.filter(id__in=newly_assigned_ids)
                for engineer in newly_assigned_engineers:
                    engineer_message = f"You have been assigned to project '{project_display}' by {assigner_name}"
                    Notification.objects.create(
                        recipient=engineer,
                        message=engineer_message
                    )
        
        if old_state:
            # Get the user who made the update (try to get from request if available)
            updater_name = getattr(instance, '_updated_by_username', None)
            if not updater_name and instance.created_by:
                updater_name = instance.created_by.get_full_name() or instance.created_by.username
            if not updater_name:
                updater_name = 'Unknown'
            
            project_display = f"{instance.name}" + (f" (PRN: {instance.prn})" if instance.prn else "")
            
            # Check if status changed
            if old_state.get('status') != instance.status:
                old_status_display = dict(Project.STATUS_CHOICES).get(old_state.get('status'), old_state.get('status', 'Unknown'))
                new_status_display = instance.get_status_display()
                message = f"Project status updated: {project_display} changed from '{old_status_display}' to '{new_status_display}' by {updater_name}"
                notify_head_engineers(message)
                notify_admins(message)
                
                # Phase 3: Also broadcast via WebSocket (parallel to SSE)
                if WEBSOCKET_AVAILABLE:
                    try:
                        broadcast_project_status_change(instance, old_state.get('status'), instance.status)
                    except Exception as e:
                        print(f"⚠️  WebSocket broadcast failed (SSE still works): {e}")
            # Check if cost changed significantly
            elif old_state.get('project_cost') != instance.project_cost and instance.project_cost:
                old_cost = old_state.get('project_cost') or 0
                new_cost = instance.project_cost or 0
                message = f"Project budget updated: {project_display} changed from ₱{old_cost:,.2f} to ₱{new_cost:,.2f} by {updater_name}"
                notify_head_engineers(message)
                notify_admins(message)
                
                # Phase 3: Also broadcast via WebSocket (parallel to SSE)
                if WEBSOCKET_AVAILABLE:
                    try:
                        broadcast_project_updated(instance, changes={'project_cost': {'old': old_cost, 'new': new_cost}})
                    except Exception as e:
                        print(f"⚠️  WebSocket broadcast failed (SSE still works): {e}")
            # Check if description changed
            elif old_state.get('description') != instance.description:
                message = f"Project description updated: {project_display} by {updater_name}"
                notify_head_engineers(message)
                notify_admins(message)
            # Check if dates changed
            elif old_state.get('start_date') != instance.start_date or old_state.get('end_date') != instance.end_date:
                date_changes = []
                if old_state.get('start_date') != instance.start_date:
                    date_changes.append(f"start date from {old_state.get('start_date') or 'N/A'} to {instance.start_date or 'N/A'}")
                if old_state.get('end_date') != instance.end_date:
                    date_changes.append(f"end date from {old_state.get('end_date') or 'N/A'} to {instance.end_date or 'N/A'}")
                message = f"Project dates updated: {project_display} - {', '.join(date_changes)} by {updater_name}"
                notify_head_engineers(message)
                notify_admins(message)
            # Check if name or location changed
            elif old_state.get('name') != instance.name or old_state.get('barangay') != instance.barangay:
                changes = []
                if old_state.get('name') != instance.name:
                    changes.append(f"name from '{old_state.get('name')}' to '{instance.name}'")
                if old_state.get('barangay') != instance.barangay:
                    changes.append(f"location from '{old_state.get('barangay') or 'N/A'}' to '{instance.barangay or 'N/A'}'")
                message = f"Project information updated: {project_display} - {', '.join(changes)} by {updater_name}"
                notify_head_engineers(message)
                notify_admins(message)
        # If explicit notification flag is set, notify
        elif hasattr(instance, '_notify_update') and instance._notify_update:
            updater_name = getattr(instance, '_updated_by_username', None)
            if not updater_name and instance.created_by:
                updater_name = instance.created_by.get_full_name() or instance.created_by.username
            if not updater_name:
                updater_name = 'Unknown'
            project_display = f"{instance.name}" + (f" (PRN: {instance.prn})" if instance.prn else "")
            message = f"Project updated: {project_display} by {updater_name}"
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
        
        # Phase 3: Also broadcast via WebSocket (parallel to SSE)
        if WEBSOCKET_AVAILABLE:
            try:
                # Safely handle date - it might be a string or date object
                date_value = None
                if instance.date:
                    if isinstance(instance.date, str):
                        # If date is a string, try to parse it
                        try:
                            from datetime import datetime
                            date_value = datetime.strptime(instance.date, '%Y-%m-%d').date().isoformat()
                        except (ValueError, AttributeError):
                            date_value = str(instance.date)
                    else:
                        # If date is a date object, use isoformat
                        try:
                            date_value = instance.date.isoformat()
                        except AttributeError:
                            date_value = str(instance.date)
                
                broadcast_progress_update(instance.project, {
                    'percentage_complete': instance.percentage_complete,
                    'date': date_value,
                    'created_by': creator_name,
                })
            except Exception as e:
                print(f"⚠️  WebSocket broadcast failed (SSE still works): {e}")
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
        
        # Safely format date - handle both string and date object
        try:
            if isinstance(instance.date, str):
                # If date is a string, try to parse and format it
                from datetime import datetime
                try:
                    date_obj = datetime.strptime(instance.date, '%Y-%m-%d').date()
                    date_str = date_obj.strftime('%B %d, %Y')
                except (ValueError, AttributeError):
                    date_str = instance.date  # Fallback to string
            else:
                # If date is a date object, format it
                date_str = instance.date.strftime('%B %d, %Y')
        except (AttributeError, ValueError):
            date_str = str(instance.date)  # Fallback to string representation
        
        message = f"Cost entry added: {instance.project.name} - {instance.get_cost_type_display()} {formatted_amount} on {date_str} by {creator_name}"
        # Notify head engineers when finance managers or project engineers add costs
        notify_head_engineers(message)
        notify_admins(message)
        
        # Phase 3: Also broadcast via WebSocket (parallel to SSE)
        if WEBSOCKET_AVAILABLE:
            try:
                # Safely handle date - it might be a string or date object
                date_value = None
                if instance.date:
                    if isinstance(instance.date, str):
                        # If date is a string, try to parse it
                        try:
                            from datetime import datetime
                            date_value = datetime.strptime(instance.date, '%Y-%m-%d').date().isoformat()
                        except (ValueError, AttributeError):
                            date_value = str(instance.date)
                    else:
                        # If date is a date object, use isoformat
                        try:
                            date_value = instance.date.isoformat()
                        except AttributeError:
                            date_value = str(instance.date)
                
                broadcast_cost_update(instance.project, {
                    'amount': float(instance.amount),
                    'formatted_amount': formatted_amount,
                    'cost_type': instance.get_cost_type_display(),
                    'date': date_value,
                    'created_by': creator_name,
                })
            except Exception as e:
                print(f"⚠️  WebSocket broadcast failed (SSE still works): {e}")
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
    from django.utils import timezone
    from datetime import timedelta
    
    # Safely format amount
    try:
        if isinstance(instance.amount, str):
            amount_value = float(instance.amount)
        else:
            amount_value = float(instance.amount)
        formatted_amount = f"₱{amount_value:,.2f}"
    except (ValueError, TypeError):
        formatted_amount = f"₱{instance.amount}"
    
    # Format date safely
    try:
        if isinstance(instance.date, str):
            date_str = instance.date
        else:
            date_str = str(instance.date)
    except:
        date_str = str(instance.date)
    
    message = f"Cost entry deleted: {instance.project.name} - {instance.get_cost_type_display()} cost of {formatted_amount} on {date_str} by {instance.created_by.get_full_name() or instance.created_by.username}"
    
    # Check for duplicates before creating notifications
    # Look for similar notifications created in the last 10 seconds
    recent_time = timezone.now() - timedelta(seconds=10)
    project_name = instance.project.name
    
    # Check if a similar notification already exists
    # Use Q objects to check for messages containing key identifiers
    existing_notifications = Notification.objects.filter(
        Q(message__icontains=f"Cost entry deleted: {project_name}") &
        Q(message__icontains=formatted_amount) &
        Q(created_at__gte=recent_time)
    ).exists()
    
    # Only create notifications if no duplicates exist
    if not existing_notifications:
        notify_head_engineers(message)
        notify_admins(message)

@receiver(post_delete, sender=ProjectDocument)
def notify_document_deletion(sender, instance, **kwargs):
    """Notify Head Engineers and Admins about document deletion"""
    from django.utils import timezone
    from datetime import timedelta
    
    message = f"Document deleted: {instance.name} for project {instance.project.name} by {instance.uploaded_by.get_full_name() if instance.uploaded_by else 'Unknown user'}"
    
    # Check for duplicates before creating notifications
    # Look for similar notifications created in the last 10 seconds
    recent_time = timezone.now() - timedelta(seconds=10)
    document_name = instance.name
    project_name = instance.project.name
    
    # Check if a similar notification already exists
    # Use Q objects to combine multiple conditions on the same field
    existing_notifications = Notification.objects.filter(
        Q(message__icontains=f"Document deleted: {document_name}") &
        Q(message__icontains=f"for project {project_name}") &
        Q(created_at__gte=recent_time)
    ).exists()
    
    # Only create notifications if no duplicates exist
    if not existing_notifications:
        notify_head_engineers(message)
        notify_admins(message)

@receiver(post_delete, sender=Project)
def notify_project_deletion(sender, instance, **kwargs):
    """
    Notify all relevant users when a project is deleted.
    
    NOTE: This signal may create duplicate notifications if the view also creates them.
    The view (monitoring/views/__init__.py project_delete_api) handles notifications
    with better context (deleter name). This signal is kept as a backup for deletions
    that happen outside the view (e.g., admin panel, bulk delete).
    
    To prevent duplicates, we check if notifications were already created by checking
    for recent notifications with similar messages.
    """
    from django.utils import timezone
    from datetime import timedelta
    from django.contrib.auth.models import User
    
    project_display = f"{instance.name}" + (f" (PRN: {instance.prn})" if instance.prn else "")
    
    # Check if notifications were already created (likely by the view)
    # Look for notifications created in the last 10 seconds with similar content
    # Check for both "has been deleted" and "has been deleted by" patterns
    recent_time = timezone.now() - timedelta(seconds=10)
    existing_notifications = Notification.objects.filter(
        Q(message__icontains=project_display) &
        Q(message__icontains="has been deleted") &
        Q(created_at__gte=recent_time)
    ).exists()
    
    # If notifications already exist, skip creating duplicates
    if existing_notifications:
        return
    
    # Notify Head Engineers and Admins (only if not already notified)
    message = f"Project '{project_display}' has been deleted"
    notify_head_engineers(message)
    notify_admins(message)
    
    # Notify Finance Managers
    notify_finance_managers(message)
    
    # Notify assigned Project Engineers (with duplicate check)
    engineer_message = f"Project '{project_display}' that you were assigned to has been deleted"
    for engineer in instance.assigned_engineers.all():
        # Check for duplicates for each engineer
        engineer_duplicate = Notification.objects.filter(
            Q(recipient=engineer) &
            Q(message__icontains=project_display) &
            Q(message__icontains="that you were assigned to has been deleted") &
            Q(created_at__gte=recent_time)
        ).exists()
        
        if not engineer_duplicate:
            Notification.objects.create(
                recipient=engineer,
                message=engineer_message
            )
    
    # Phase 3: Also broadcast via WebSocket (parallel to SSE)
    if WEBSOCKET_AVAILABLE:
        try:
            broadcast_project_deleted(instance.name, instance.prn)
        except Exception as e:
            print(f"⚠️  WebSocket broadcast failed (SSE still works): {e}")

@receiver(m2m_changed, sender=Project.assigned_engineers.through)
def notify_engineer_assignment(sender, instance, action, pk_set, **kwargs):
    """
    Notify engineers when they are assigned to a project.
    This handles ManyToMany field changes which occur after the main object is saved.
    """
    if action == 'post_add' and pk_set:
        from django.utils import timezone
        from datetime import timedelta
        
        # Get the user who made the assignment (try to get from request if available)
        assigner_name = getattr(instance, '_updated_by_username', None)
        if not assigner_name and instance.created_by:
            assigner_name = instance.created_by.get_full_name() or instance.created_by.username
        if not assigner_name:
            assigner_name = 'Unknown'
        
        project_display = f"{instance.name}" + (f" (PRN: {instance.prn})" if instance.prn else "")
        
        # Notify newly assigned engineers (only them, not head engineers)
        # Check for duplicates to avoid double notifications
        recent_time = timezone.now() - timedelta(seconds=10)
        newly_assigned_engineers = User.objects.filter(id__in=pk_set)
        
        for engineer in newly_assigned_engineers:
            # Check for duplicates
            duplicate_exists = Notification.objects.filter(
                Q(recipient=engineer) &
                Q(message__icontains="You have been assigned to project") &
                Q(message__icontains=project_display) &
                Q(created_at__gte=recent_time)
            ).exists()
            
            if not duplicate_exists:
                engineer_message = f"You have been assigned to project '{project_display}' by {assigner_name}"
                Notification.objects.create(
                    recipient=engineer,
                    message=engineer_message
                )