"""
WebSocket broadcasting utilities (parallel to SSE fallback).
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


logger = logging.getLogger(__name__)


def broadcast_notification(user_id, notification_data):
    """
    Broadcast notification via WebSocket to a specific user.
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"user_{user_id}_notifications",
                {
                    "type": "send_notification",
                    "data": notification_data,
                },
            )
            logger.debug("WebSocket notification broadcast to user_%s", user_id)
    except Exception as exc:
        # Fail silently in-app; SSE remains active.
        logger.warning("WebSocket notification broadcast failed (SSE still works): %s", exc)


def broadcast_notification_to_user(user, message, notification_id=None):
    """
    Convenience function to broadcast notification to a user.
    """
    notification_data = {
        "type": "notification",
        "message": message,
        "notification_id": notification_id,
    }
    broadcast_notification(user.id, notification_data)


def broadcast_project_update(update_data):
    """
    Broadcast project update via WebSocket to all authorized users.
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "project_updates",
                {
                    "type": "send_project_update",
                    "data": update_data,
                },
            )
            logger.debug(
                "WebSocket project update broadcast: %s",
                update_data.get("type", "unknown"),
            )
    except Exception as exc:
        # Fail silently in-app; SSE remains active.
        logger.warning("WebSocket project update broadcast failed (SSE still works): %s", exc)


def broadcast_project_created(project):
    """
    Broadcast when a new project is created.
    """
    broadcast_project_update(
        {
            "type": "project_created",
            "project_id": project.id,
            "name": project.name,
            "prn": project.prn,
            "status": project.status,
            "barangay": project.barangay,
        }
    )


def broadcast_project_updated(project, changes=None):
    """
    Broadcast when a project is updated.
    """
    update_data = {
        "type": "project_updated",
        "project_id": project.id,
        "name": project.name,
        "prn": project.prn,
        "status": project.status,
        "barangay": project.barangay,
    }
    if changes:
        update_data["changes"] = changes

    broadcast_project_update(update_data)


def broadcast_project_deleted(project_name, project_prn=None):
    """
    Broadcast when a project is deleted.
    """
    broadcast_project_update(
        {
            "type": "project_deleted",
            "name": project_name,
            "prn": project_prn,
        }
    )


def broadcast_project_status_change(project, old_status, new_status):
    """
    Broadcast when project status changes.
    """
    broadcast_project_update(
        {
            "type": "project_status_changed",
            "project_id": project.id,
            "name": project.name,
            "prn": project.prn,
            "old_status": old_status,
            "new_status": new_status,
        }
    )


def broadcast_cost_update(project, cost_data):
    """
    Broadcast when a cost entry is added/updated.
    """
    broadcast_project_update(
        {
            "type": "cost_updated",
            "project_id": project.id,
            "project_name": project.name,
            "cost_data": cost_data,
        }
    )


def broadcast_progress_update(project, progress_data):
    """
    Broadcast when project progress is updated.
    """
    broadcast_project_update(
        {
            "type": "progress_updated",
            "project_id": project.id,
            "project_name": project.name,
            "progress_data": progress_data,
        }
    )
