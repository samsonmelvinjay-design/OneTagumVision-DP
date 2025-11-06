"""
Custom views for security and authentication
"""
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)

@require_http_methods(["GET", "POST"])
@never_cache
def secure_logout(request):
    """
    Secure logout that clears all session data and prevents back button access
    """
    # Log the logout action
    if request.user.is_authenticated:
        logger.info(f"User {request.user.username} logged out")
    
    # Clear all session data
    request.session.flush()
    
    # Logout the user
    logout(request)
    
    # Add a message for the user
    messages.success(request, "You have been successfully logged out.")
    
    # Redirect to login page
    return redirect('login')

@login_required
@never_cache
def secure_home(request):
    """
    Secure home view with proper cache control
    """
    # This view ensures proper authentication and cache control
    return redirect('/admin/')  # Redirect to admin or your main dashboard

@csrf_exempt
def health_check(request):
    """
    Simple health check endpoint for load balancers and monitoring
    Returns 200 OK if the app is running
    This endpoint should not require database access or authentication
    Bypasses all middleware checks for reliability
    """
    # Return a simple response - middleware will skip processing for /health/
    return HttpResponse("OK", status=200, content_type="text/plain")

def redirect_to_login(request):
    """
    Redirect root URL access based on authentication status
    """
    if request.user.is_authenticated:
        # Redirect authenticated users to their appropriate dashboard
        from django.contrib.auth.models import User
        user = request.user
        
        if user.is_superuser or user.groups.filter(name='Head Engineer').exists():
            return redirect('/dashboard/')
        elif user.groups.filter(name='Finance Manager').exists():
            return redirect('/dashboard/finance/dashboard/')
        elif user.groups.filter(name='Project Engineer').exists():
            return redirect('/projeng/dashboard/')
        else:
            return redirect('/dashboard/')
    else:
        # Redirect unauthenticated users to login
        return redirect('login')
