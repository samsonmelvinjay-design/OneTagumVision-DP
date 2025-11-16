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
    print("WARNING: WebSocket broadcasting not available (SSE still works)")

def format_project_display(project):
    """Helper function to format project display name consistently"""
    project_name = project.name.strip() if project.name else "Unnamed Project"
    if project.prn:
        return f"{project_name} (PRN: {project.prn})"
    return project_name

# Track syncing projects to prevent recursion
_syncing_projects = set()

@receiver(post_save, sender=Project)
def sync_projeng_to_monitoring(sender, instance, created, **kwargs):
    # Prevent recursion: if we're already syncing this project, skip
    if instance.id in _syncing_projects:
        return
    
    # Skip sync if this is a new project being created (optimize performance)
    # The sync can happen asynchronously or on-demand
    # Only sync on updates to avoid blocking project creation
    if created:
        # For new projects, skip immediate sync to improve performance
        # Can be synced later if needed via a background task or manual sync
        return
    
    print(f"SIGNAL: sync_projeng_to_monitoring called for Project id={instance.id}, prn={instance.prn}")
    try:
        if instance.prn:
            # Mark this project as being synced
            if instance.id:
                _syncing_projects.add(instance.id)
            
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
                # Use update_fields to prevent triggering signals that might cause recursion
                monitoring_project.save(update_fields=[
                    'name', 'description', 'barangay', 'project_cost', 'source_of_funds',
                    'status', 'latitude', 'longitude', 'start_date', 'end_date', 'image', 'updated_at'
                ])
            # Sync assigned engineers
            if hasattr(monitoring_project, 'assigned_engineers'):
                monitoring_project.assigned_engineers.set(instance.assigned_engineers.all())
            else:
                print('Warning: MonitoringProject has no assigned_engineers field')
            
            # Remove from syncing set after completion
            if instance.id:
                _syncing_projects.discard(instance.id)
        print(f"SIGNAL: sync_projeng_to_monitoring completed for Project id={instance.id}, prn={instance.prn}")
    except Exception as e:
        # Remove from syncing set on error
        if instance.id:
            _syncing_projects.discard(instance.id)
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
        
        # Build project display name - ensure it's not empty
        project_display = format_project_display(instance)
        
        # Get assigned engineer names
        assigned_engineers = instance.assigned_engineers.all()
        engineer_names = []
        for engineer in assigned_engineers:
            engineer_name = engineer.get_full_name() or engineer.username
            engineer_names.append(engineer_name)
        
        # Build notification message with assigned engineers
        if engineer_names:
            if len(engineer_names) == 1:
                engineers_text = engineer_names[0]
                message = f"New project created: {project_display} by {creator_name} - Assigned engineer: {engineers_text}"
            else:
                engineers_text = ", ".join(engineer_names)
                message = f"New project created: {project_display} by {creator_name} - Assigned engineers: {engineers_text}"
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
                print(f"WARNING:  WebSocket broadcast failed (SSE still works): {e}")
        
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
                
                project_display = format_project_display(instance)
                
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
            
            project_display = format_project_display(instance)
            
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
                        print(f"WARNING:  WebSocket broadcast failed (SSE still works): {e}")
            # Check if cost changed significantly
            elif old_state.get('project_cost') != instance.project_cost and instance.project_cost:
                # Convert to float for formatting (handle both string and numeric types)
                try:
                    old_cost = float(old_state.get('project_cost') or 0)
                except (ValueError, TypeError):
                    old_cost = 0
                try:
                    new_cost = float(instance.project_cost or 0)
                except (ValueError, TypeError):
                    new_cost = 0
                message = f"Project budget updated: {project_display} changed from ₱{old_cost:,.2f} to ₱{new_cost:,.2f} by {updater_name}"
                notify_head_engineers(message)
                notify_admins(message)
                
                # Phase 3: Also broadcast via WebSocket (parallel to SSE)
                if WEBSOCKET_AVAILABLE:
                    try:
                        broadcast_project_updated(instance, changes={'project_cost': {'old': old_cost, 'new': new_cost}})
                    except Exception as e:
                        print(f"WARNING:  WebSocket broadcast failed (SSE still works): {e}")
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
            project_display = format_project_display(instance)
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
                print(f"WARNING:  WebSocket broadcast failed (SSE still works): {e}")
    # Skip notifications for progress modifications to reduce noise

def check_budget_thresholds(project, cost_entry=None):
    """
    Check project budget against thresholds and trigger appropriate notifications.
    
    Thresholds:
    - 80%: Warning to Head Engineers
    - 95%: Critical alert to Head Engineers
    - 100%+: Over budget alert to Head Engineers
    
    Args:
        project: Project instance
        cost_entry: Optional ProjectCost instance that triggered the check
    """
    from django.db.models import Sum
    from .models import ProjectCost
    from .utils import notify_head_engineers, notify_admins
    
    # Only check if project has a budget set
    if not project.project_cost:
        return
    
    # Calculate total costs for the project
    total_costs = ProjectCost.objects.filter(project=project).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Convert to float for comparison
    try:
        total_costs_float = float(total_costs)
        project_budget_float = float(project.project_cost)
    except (ValueError, TypeError):
        return  # Skip if conversion fails
    
    # Calculate utilization percentage
    utilization_percentage = (total_costs_float / project_budget_float) * 100 if project_budget_float > 0 else 0
    
    # Format amounts
    formatted_total = f"₱{total_costs_float:,.2f}"
    formatted_budget = f"₱{project_budget_float:,.2f}"
    formatted_remaining = f"₱{max(0, project_budget_float - total_costs_float):,.2f}"
    
    # Build project display name
    project_display = format_project_display(project)
    
    # Get cost entry creator name if available
    creator_name = "System"
    if cost_entry and cost_entry.created_by:
        creator_name = cost_entry.created_by.get_full_name() or cost_entry.created_by.username
    
    # Check thresholds and notify accordingly
    # 100%+ threshold: Over budget
    if total_costs_float > project_budget_float:
        overage_amount = total_costs_float - project_budget_float
        overage_percentage = ((total_costs_float / project_budget_float) - 1) * 100
        formatted_overage = f"₱{overage_amount:,.2f}"
        
        message = (
            f"🚨 URGENT: {project_display} is OVER BUDGET by {formatted_overage} "
            f"({overage_percentage:.1f}% over). "
            f"Total spent: {formatted_total} | Budget: {formatted_budget}. "
            f"Cost entry by: {creator_name}. "
            f"Immediate review required."
        )
        notify_head_engineers(message, check_duplicates=True)
        notify_admins(message, check_duplicates=True)
    
    # 95% threshold: Critical alert
    elif utilization_percentage >= 95:
        message = (
            f"⚠️ CRITICAL: {project_display} is at {utilization_percentage:.1f}% of budget. "
            f"Spent: {formatted_total} | Budget: {formatted_budget} | Remaining: {formatted_remaining}. "
            f"Cost entry by: {creator_name}. "
            f"Project may exceed budget soon. Review recommended."
        )
        notify_head_engineers(message, check_duplicates=True)
        notify_admins(message, check_duplicates=True)
    
    # 80% threshold: Warning
    elif utilization_percentage >= 80:
        message = (
            f"⚠️ WARNING: {project_display} is at {utilization_percentage:.1f}% of budget. "
            f"Spent: {formatted_total} | Budget: {formatted_budget} | Remaining: {formatted_remaining}. "
            f"Cost entry by: {creator_name}. "
            f"Monitor spending closely."
        )
        notify_head_engineers(message, check_duplicates=True)
        notify_admins(message, check_duplicates=True)


# Keep old function name for backward compatibility (deprecated)
def check_budget_over_utilization(project):
    """
    DEPRECATED: Use check_budget_thresholds() instead.
    Kept for backward compatibility.
    """
    check_budget_thresholds(project)

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
        
        # Check if budget thresholds are crossed after this cost entry
        check_budget_thresholds(instance.project, cost_entry=instance)
        
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
                print(f"WARNING:  WebSocket broadcast failed (SSE still works): {e}")
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
    
    project_display = format_project_display(instance)
    
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
            print(f"WARNING:  WebSocket broadcast failed (SSE still works): {e}")

# Track if we've already updated notifications for a project to prevent duplicates
_notification_update_flags = {}

@receiver(m2m_changed, sender=Project.assigned_engineers.through)
def notify_engineer_assignment(sender, instance, action, pk_set, **kwargs):
    """
    Notify engineers when they are assigned to a project.
    This handles ManyToMany field changes which occur after the main object is saved.
    Also updates head engineer notifications if project was just created.
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
        
        project_display = format_project_display(instance)
        
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
        
        # If project was just created (within last 30 seconds), update head engineer notifications
        # to show assigned engineers
        # Use a flag to prevent multiple updates if signal fires multiple times
        project_created_recently = instance.created_at and (timezone.now() - instance.created_at).total_seconds() < 30
        
        if project_created_recently:
            # Check if we've already updated notifications for this project
            update_key = f"project_{instance.id}_notifications_updated"
            if update_key in _notification_update_flags:
                # Check if the flag is still valid (within 30 seconds)
                flag_time = _notification_update_flags[update_key]
                if (timezone.now() - flag_time).total_seconds() < 30:
                    # Already updated recently, skip to avoid duplicates
                    return
            # Get all currently assigned engineers
            all_assigned_engineers = instance.assigned_engineers.all()
            engineer_names = []
            for engineer in all_assigned_engineers:
                engineer_name = engineer.get_full_name() or engineer.username
                engineer_names.append(engineer_name)
            
            # Build updated message
            creator_name = instance.created_by.get_full_name() or instance.created_by.username if instance.created_by else 'Unknown'
            
            if engineer_names:
                if len(engineer_names) == 1:
                    engineers_text = engineer_names[0]
                    updated_message = f"New project created: {project_display} by {creator_name} - Assigned engineer: {engineers_text}"
                else:
                    engineers_text = ", ".join(engineer_names)
                    updated_message = f"New project created: {project_display} by {creator_name} - Assigned engineers: {engineers_text}"
            else:
                updated_message = f"New project created: {project_display} by {creator_name} - No engineers assigned"
            
            # Delete ALL recent notifications about this project creation to avoid duplicates
            # Delete notifications that match the project creation pattern (with or without engineers)
            from .utils import notify_head_engineers, notify_admins
            
            # Get head engineers and admins
            head_engineers = User.objects.filter(groups__name='Head Engineer')
            admins = User.objects.filter(is_superuser=True)
            all_recipients = list(head_engineers) + list(admins)
            
            # Delete any existing notifications about this project creation for these users
            # This prevents duplicates when the signal fires multiple times
            project_creation_pattern = f"New project created: {project_display} by {creator_name}"
            Notification.objects.filter(
                recipient__in=all_recipients,
                message__startswith=project_creation_pattern,
                created_at__gte=instance.created_at - timedelta(seconds=10)
            ).delete()
            
            # Create updated notification with engineer names
            # Use check_duplicates=True as a safety measure
            notify_head_engineers(updated_message, check_duplicates=True)
            notify_admins(updated_message, check_duplicates=True)
            
            # Set flag to prevent duplicate updates
            _notification_update_flags[update_key] = timezone.now()
            
            # Clean up old flags (older than 1 minute)
            current_time = timezone.now()
            keys_to_remove = [
                key for key, flag_time in _notification_update_flags.items()
                if (current_time - flag_time).total_seconds() > 60
            ]
            for key in keys_to_remove:
                del _notification_update_flags[key]