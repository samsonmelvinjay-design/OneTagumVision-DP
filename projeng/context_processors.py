from .models import Notification

def notifications_context(request):
    """Context processor to provide notifications data to all templates"""
    if request.user.is_authenticated and (request.user.groups.filter(name='Head Engineer').exists() or request.user.is_superuser):
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return {
            'unread_notifications_count': unread_count
        }
    return {
        'unread_notifications_count': 0
    } 