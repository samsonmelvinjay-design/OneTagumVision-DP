from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

def dual_login(request):
    print("dual_login view received a request.") # Debug print at the very beginning
    error = None
    
    # If already logged in, redirect to appropriate dashboard
    if request.user.is_authenticated:
        print(f"User {request.user.username} is already authenticated, redirecting...")
        if request.user.is_superuser or request.user.groups.filter(name='Head Engineer').exists():
            return redirect('/dashboard/')
        elif request.user.groups.filter(name='Finance Manager').exists():
            return redirect('/dashboard/finance/dashboard/')
        elif request.user.groups.filter(name='Project Engineer').exists():
            return redirect('/projeng/dashboard/')
        else:
            return redirect('/dashboard/')
    
    if request.method == 'POST':
        username = request.POST['username'].strip()
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Allow superusers to bypass group checks
            if user.is_superuser:
                print(f"Authenticated superuser: {user.username}, redirecting to /dashboard/")
                login(request, user)
                request.session['show_login_success'] = True
                response = redirect('/dashboard/')
                return response
            # Debug: show user groups
            user_groups = list(user.groups.values_list('name', flat=True))
            print(f"Authenticated user: {user.username}, groups={user_groups}")
            if user.groups.filter(name='Finance Manager').exists():
                print(f"Finance Manager detected, redirecting to finance dashboard")
                login(request, user)
                request.session['show_login_success'] = True
                return redirect('/dashboard/finance/dashboard/')
            elif user.groups.filter(name='Head Engineer').exists():
                print(f"Head Engineer detected, redirecting to /dashboard/")
                login(request, user)
                request.session['show_login_success'] = True
                return redirect('/dashboard/')
            elif user.groups.filter(name='Project Engineer').exists():
                print(f"Project Engineer detected, redirecting to projeng dashboard")
                login(request, user)
                request.session['show_login_success'] = True
                return redirect('/projeng/dashboard/')
            else:
                error = 'You do not have permission to access the system.'
        else:
            error = 'Invalid username or password.'
    return render(request, 'registration/dual_login.html', {'error': error})

@require_http_methods(["POST"])
@csrf_exempt
def clear_login_success(request):
    """
    Clear the login success session flag after showing the modal
    """
    if 'show_login_success' in request.session:
        del request.session['show_login_success']
        request.session.save()
    return JsonResponse({'status': 'success'})

def custom_logout(request):
    """
    Secure logout that clears all session data and prevents back button access
    """
    # Log the logout action
    if request.user.is_authenticated:
        print(f"User {request.user.username} logged out")
    
    # Clear all session data
    request.session.flush()
    
    # Logout the user
    logout(request)
    
    # Create response with security headers
    response = redirect('/accounts/login/')
    
    # Add cache control headers to prevent back button access
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response