"""
Custom security middleware to prevent back button access after logout
"""
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers and prevent back button access
    """
    
    def process_response(self, request, response):
        """
        Add security headers to prevent caching and back button access
        """
        # Skip health check endpoint - it needs to work without any middleware interference
        if request.path == '/health/' or request.path == '/health':
            return response
        
        # Add cache control headers to prevent back button access
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Add Strict-Transport-Security for HTTPS (uncomment in production)
        # response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Check if user is accessing a protected page without authentication
        if not request.user.is_authenticated:
            # For protected URLs, ensure they redirect to login
            protected_paths = ['/admin/', '/monitoring/', '/projeng/']
            if any(request.path.startswith(path) for path in protected_paths):
                # Clear any existing session data
                request.session.flush()
                return redirect('login')
        
        return response
    
    def process_request(self, request):
        """
        Check session validity and handle logout scenarios
        """
        # Skip health check endpoint - don't process requests to it
        if request.path == '/health/' or request.path == '/health':
            return None
        
        # If user is not authenticated but has session data, clear it
        if not request.user.is_authenticated and request.session:
            # Clear session data for unauthenticated users
            request.session.flush()
        
        return None
