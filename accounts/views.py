from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.core.mail import send_mail
import logging

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

class CustomPasswordResetView(PasswordResetView):
    """Custom password reset view with error logging"""
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    template_name = 'registration/password_reset_form.html'
    success_url = '/accounts/password_reset/done/'
    
    def form_valid(self, form):
        email = form.cleaned_data['email']
        print(f"📧 Password reset requested for email: {email}")
        
        try:
            # Call parent's form_valid which sends the email
            result = super().form_valid(form)
            print(f"✅ Password reset email sent successfully to: {email}")
            return result
        except Exception as e:
            # Log the error
            error_msg = f"❌ ERROR sending password reset email to {email}: {str(e)}"
            print(error_msg)
            import traceback
            print(f"Full traceback:\n{traceback.format_exc()}")
            logging.error(error_msg, exc_info=True)
            # Still redirect to done page (Django's default behavior)
            # but the error is now logged
            return super().form_valid(form)

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """Custom password reset confirm view with logging"""
    template_name = 'registration/password_reset_confirm.html'
    success_url = '/accounts/reset/done/'
    
    def dispatch(self, *args, **kwargs):
        uidb64 = kwargs.get('uidb64', '')
        token = kwargs.get('token', '')
        print(f"🔐 Password reset confirm - uidb64: {uidb64}, token: {token[:20]}...")
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        result = super().get(request, *args, **kwargs)
        if hasattr(self, 'validlink'):
            print(f"   Valid link: {self.validlink}")
        return result