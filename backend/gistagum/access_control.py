"""
Centralized Access Control System
Provides decorators and utilities for role-based access control
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.core.exceptions import PermissionDenied


def is_head_engineer(user):
    """Check if user is Head Engineer or superuser"""
    return user.is_authenticated and (
        user.is_superuser or 
        user.groups.filter(name='Head Engineer').exists()
    )


def is_project_engineer(user):
    """Check if user is Project Engineer"""
    return user.is_authenticated and user.groups.filter(name='Project Engineer').exists()


def is_finance_manager(user):
    """Check if user is Finance Manager"""
    return user.is_authenticated and user.groups.filter(name='Finance Manager').exists()


def is_project_or_head_engineer(user):
    """Check if user is Project Engineer or Head Engineer"""
    return is_project_engineer(user) or is_head_engineer(user)


def is_finance_or_head_engineer(user):
    """Check if user is Finance Manager or Head Engineer"""
    return is_finance_manager(user) or is_head_engineer(user)


def get_user_dashboard_url(user):
    """Get the appropriate dashboard URL for a user based on their role"""
    if is_head_engineer(user):
        return '/dashboard/'
    elif is_finance_manager(user):
        return '/dashboard/finance/dashboard/'
    elif is_project_engineer(user):
        return '/projeng/dashboard/'
    else:
        return '/dashboard/'  # Default fallback


def head_engineer_required(view_func):
    """
    Decorator to restrict access to Head Engineers and Admins only.
    Redirects other users to their appropriate dashboard.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if not is_head_engineer(request.user):
            # Redirect based on user role
            if is_project_engineer(request.user):
                messages.error(request, "You don't have permission to access this page. Project Engineers have their own dashboard.")
                return redirect('/projeng/dashboard/')
            elif is_finance_manager(request.user):
                messages.error(request, "You don't have permission to access this page.")
                return redirect('/dashboard/finance/dashboard/')
            else:
                messages.error(request, "You don't have permission to access this page.")
                return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def project_engineer_required(view_func):
    """
    Decorator to restrict access to Project Engineers only.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if not is_project_engineer(request.user):
            if is_head_engineer(request.user):
                messages.error(request, "This page is for Project Engineers only.")
                return redirect('/dashboard/')
            elif is_finance_manager(request.user):
                messages.error(request, "This page is for Project Engineers only.")
                return redirect('/dashboard/finance/dashboard/')
            else:
                messages.error(request, "You don't have permission to access this page.")
                return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def finance_manager_required(view_func):
    """
    Decorator to restrict access to Finance Managers and Head Engineers.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if not is_finance_or_head_engineer(request.user):
            if is_project_engineer(request.user):
                messages.error(request, "You don't have permission to access this page.")
                return redirect('/projeng/dashboard/')
            else:
                messages.error(request, "You don't have permission to access this page.")
                return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def prevent_project_engineer_access(view_func):
    """
    Decorator to prevent Project Engineers from accessing Head Engineer pages.
    Allows Head Engineers and Finance Managers.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Block Project Engineers (unless they're also Head Engineers)
        if is_project_engineer(request.user) and not is_head_engineer(request.user):
            messages.error(request, "This section is restricted to Head Engineers and Finance Managers only.")
            return redirect('/projeng/dashboard/')
        
        return view_func(request, *args, **kwargs)
    return wrapper

