from .models import Notification

def notifications_context(request):
    """Context processor to provide notifications data to all templates"""
    if request.user.is_authenticated:
        # Show notifications for Head Engineers, Finance Managers, and Admins
        is_head_engineer = request.user.groups.filter(name='Head Engineer').exists()
        is_finance_manager = request.user.groups.filter(name='Finance Manager').exists()
        is_admin = request.user.is_superuser
        
        if is_head_engineer or is_finance_manager or is_admin:
            unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
            return {
                'unread_notifications_count': unread_count
            }
    return {
        'unread_notifications_count': 0
    } 