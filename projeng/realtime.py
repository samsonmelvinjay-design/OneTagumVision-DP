"""
Real-time updates using Server-Sent Events (SSE)
Provides live notifications, dashboard updates, and project status changes
"""
from django.http import StreamingHttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.views.decorators.cache import never_cache
from django.utils import timezone
from datetime import timedelta
import json
import time
from .models import Notification, Project, ProjectProgress
from django.db.models import Q, Count
from django.db import close_old_connections


@login_required
@require_GET
@never_cache
def sse_notifications(request):
    """Server-Sent Events stream for real-time notifications - Professional, non-intrusive"""
    
    def event_stream():
        last_notification_id = None
        last_unread_count = None
        connection_start_time = timezone.now()  # Track when connection was established
        
        # Send initial unread count without notification details (to avoid showing old notifications)
        try:
            # Drop any stale DB connection before the first query
            close_old_connections()
            initial_unread_count = Notification.objects.filter(
                recipient=request.user,
                is_read=False
            ).count()
            last_unread_count = initial_unread_count
            # Send only count, no notification details on initial connection
            data = {
                'type': 'notification',
                'unread_count': initial_unread_count
            }
            yield f"data: {json.dumps(data)}\n\n"
        except:
            pass
        
        while True:
            try:
                # Ensure we don't reuse a dead database connection on long-lived streams
                close_old_connections()

                # Get unread notifications count
                unread_count = Notification.objects.filter(
                    recipient=request.user,
                    is_read=False
                ).count()
                
                # Only send update if count changed (new notification)
                if unread_count != last_unread_count:
                    last_unread_count = unread_count
                    
                    # Get latest notification if there are unread ones
                    # Only get notifications created AFTER the connection was established
                    latest = None
                    if unread_count > 0:
                        latest = Notification.objects.filter(
                            recipient=request.user,
                            is_read=False,
                            created_at__gte=connection_start_time  # Only notifications created after connection
                        ).order_by('-created_at').first()
                    
                    # Only send notification data if it's a NEW notification created after connection
                    if latest and latest.id != last_notification_id:
                        last_notification_id = latest.id
                        data = {
                            'type': 'notification',
                            'unread_count': unread_count,
                            'notification': {
                                'id': latest.id,
                                'message': latest.message,
                                'created_at': timezone.localtime(latest.created_at).isoformat()  # Convert to local timezone
                            }
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                    elif unread_count == 0:
                        # Send count update even if no new notification (for badge update)
                        data = {
                            'type': 'notification',
                            'unread_count': 0
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                    else:
                        # Count changed but no new notification (might have been read)
                        # Just send count update
                        data = {
                            'type': 'notification',
                            'unread_count': unread_count
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                
                # Send heartbeat every 30 seconds
                yield f": heartbeat\n\n"
                time.sleep(2)  # Check every 2 seconds for faster real-time updates
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                time.sleep(5)
    
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Disable buffering for nginx
    return response


@login_required
@require_GET
@never_cache
def sse_dashboard_updates(request):
    """Server-Sent Events stream for dashboard data updates"""
    
    def event_stream():
        last_update_time = timezone.now()
        while True:
            try:
                # Ensure DB connection is still valid for long-lived streams
                close_old_connections()

                # Check for project updates in the last 5 seconds
                recent_time = timezone.now() - timedelta(seconds=5)
                
                if request.user.groups.filter(name='Head Engineer').exists() or request.user.is_superuser:
                    # Head engineers see all projects
                    recent_projects = Project.objects.filter(
                        Q(updated_at__gte=recent_time) | Q(created_at__gte=recent_time)
                    )
                elif request.user.groups.filter(name='Project Engineer').exists():
                    # Project engineers see their assigned projects
                    recent_projects = Project.objects.filter(
                        assigned_engineers=request.user
                    ).filter(
                        Q(updated_at__gte=recent_time) | Q(created_at__gte=recent_time)
                    )
                else:
                    recent_projects = Project.objects.none()
                
                if recent_projects.exists():
                    # Get dashboard stats
                    if request.user.groups.filter(name='Project Engineer').exists():
                        all_projects = Project.objects.filter(assigned_engineers=request.user)
                    else:
                        all_projects = Project.objects.all()
                    
                    status_counts = {
                        'planned': all_projects.filter(status__in=['planned', 'pending']).count(),
                        'in_progress': all_projects.filter(status__in=['in_progress', 'ongoing']).count(),
                        'completed': all_projects.filter(status='completed').count(),
                        'delayed': all_projects.filter(status='delayed').count(),
                    }
                    
                    data = {
                        'type': 'dashboard_update',
                        'status_counts': status_counts,
                        'total_projects': all_projects.count(),
                        # Removed 'recent_updates' - was causing persistent banners
                        # Notifications are handled via the notification badge only
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    last_update_time = timezone.now()
                
                # Send heartbeat
                yield f": heartbeat\n\n"
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                time.sleep(5)
    
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@login_required
@require_GET
@never_cache
def sse_project_status(request, project_id=None):
    """Server-Sent Events stream for specific project status changes"""
    
    def event_stream():
        last_status = None
        last_progress = None
        
        try:
            close_old_connections()
            if project_id:
                project = Project.objects.get(id=project_id)
            else:
                # If no project_id, monitor all user's projects
                if request.user.groups.filter(name='Project Engineer').exists():
                    projects = Project.objects.filter(assigned_engineers=request.user)
                else:
                    projects = Project.objects.all()
        except Project.DoesNotExist:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Project not found'})}\n\n"
            return
        
        while True:
            try:
                # Ensure DB connection is still valid for long-lived streams
                close_old_connections()
                if project_id:
                    # Monitor single project
                    project = Project.objects.get(id=project_id)
                    latest_progress = ProjectProgress.objects.filter(
                        project=project
                    ).order_by('-date').first()
                    
                    if project.status != last_status or (
                        latest_progress and 
                        latest_progress.id != last_progress
                    ):
                        data = {
                            'type': 'project_status',
                            'project_id': project.id,
                            'status': project.status,
                            'progress': float(latest_progress.percentage_complete) if latest_progress else 0,
                            'updated_at': timezone.localtime(project.updated_at if hasattr(project, 'updated_at') else project.created_at).isoformat()  # Convert to local timezone
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                        last_status = project.status
                        if latest_progress:
                            last_progress = latest_progress.id
                else:
                    # Monitor all projects for status changes
                    if request.user.groups.filter(name='Project Engineer').exists():
                        projects = Project.objects.filter(assigned_engineers=request.user)
                    else:
                        projects = Project.objects.all()
                    
                    recent_time = timezone.now() - timedelta(seconds=10)
                    changed_projects = projects.filter(
                        Q(updated_at__gte=recent_time) | Q(created_at__gte=recent_time)
                    )
                    
                    if changed_projects.exists():
                        data = {
                            'type': 'project_status',
                            'projects': [
                                {
                                    'id': p.id,
                                    'name': p.name,
                                    'status': p.status,
                                    'description': p.description or '',
                                    'barangay': p.barangay or '',
                                    'start_date': p.start_date.isoformat() if p.start_date else None,
                                    'end_date': p.end_date.isoformat() if p.end_date else None,
                                    'updated_at': timezone.localtime(p.updated_at if hasattr(p, 'updated_at') else p.created_at).isoformat()  # Convert to local timezone
                                }
                                for p in changed_projects[:10]
                            ]
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                
                # Send heartbeat
                yield f": heartbeat\n\n"
                time.sleep(3)  # Check every 3 seconds
                
            except Project.DoesNotExist:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Project not found'})}\n\n"
                break
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                time.sleep(5)
    
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@login_required
@require_GET
def realtime_api_status(request):
    """API endpoint to check real-time connection status"""
    return JsonResponse({
        'status': 'connected',
        'user': request.user.username,
        'timestamp': timezone.localtime(timezone.now()).isoformat()  # Convert to local timezone
    })

