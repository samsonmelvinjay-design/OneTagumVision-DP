"""
Security decorators for preventing back button access
"""
from functools import wraps
from django.http import HttpResponse
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache

def secure_view(view_func):
    """
    Decorator to add security headers and prevent caching
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        
        # Add security headers to prevent back button access
        if hasattr(response, '__setitem__'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['X-XSS-Protection'] = '1; mode=block'
        
        return response
    return wrapper

def prevent_back_button(view_func):
    """
    Decorator specifically for preventing back button access after logout
    """
    @wraps(view_func)
    @login_required
    @never_cache
    def wrapper(request, *args, **kwargs):
        # Check if user is still authenticated
        if not request.user.is_authenticated:
            return redirect('login')
        
        response = view_func(request, *args, **kwargs)
        
        # Add headers to prevent caching
        if hasattr(response, '__setitem__'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response
    return wrapper
