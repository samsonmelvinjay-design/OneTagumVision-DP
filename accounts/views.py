from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.views import PasswordResetView
from django.core.mail import send_mail
from django.conf import settings
import logging
from gistagum.access_control import is_head_engineer, is_finance_manager, is_project_engineer

def dual_login(request):
    print("dual_login view received a request.") # Debug print at the very beginning
    error = None
    
    # If already logged in, redirect to appropriate dashboard
    if request.user.is_authenticated:
        print(f"User {request.user.username} is already authenticated, redirecting...")
        if is_head_engineer(request.user):
            return redirect('/dashboard/')
        elif is_finance_manager(request.user):
            return redirect('/dashboard/finance/dashboard/')
        elif is_project_engineer(request.user):
            return redirect('/projeng/dashboard/')
        else:
            return redirect('/dashboard/')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        if not username or not password:
            error = 'Please enter both username and password.'
            return render(request, 'registration/dual_login.html', {'error': error})
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
            if is_finance_manager(user):
                print(f"Finance Manager detected, redirecting to finance dashboard")
                login(request, user)
                request.session['show_login_success'] = True
                return redirect('/dashboard/finance/dashboard/')
            elif is_head_engineer(user):
                print(f"Head Engineer detected, redirecting to /dashboard/")
                login(request, user)
                request.session['show_login_success'] = True
                return redirect('/dashboard/')
            elif is_project_engineer(user):
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
    """Custom password reset view with production-safe link generation."""
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    template_name = 'registration/password_reset_form.html'
    success_url = '/accounts/login/'  # Redirect to login page instead of done page

    def form_valid(self, form):
        from django.contrib import messages
        from django.shortcuts import redirect

        email = form.cleaned_data['email']
        logger = logging.getLogger(__name__)
        logger.info("Password reset requested for email: %s", email)

        # If PASSWORD_RESET_DOMAIN is set (recommended on Droplet), force reset links
        # to your public domain instead of the incoming request host.
        domain_override = (getattr(settings, 'PASSWORD_RESET_DOMAIN', '') or '').strip() or None
        use_https = self.request.is_secure()
        if domain_override is not None:
            use_https = bool(getattr(settings, 'PASSWORD_RESET_USE_HTTPS', True))

        try:
            opts = {
                'use_https': use_https,
                'token_generator': self.token_generator,
                'from_email': self.from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                'email_template_name': self.email_template_name,
                'subject_template_name': self.subject_template_name,
                'request': self.request,
                'html_email_template_name': self.html_email_template_name,
                'extra_email_context': self.extra_email_context,
                'domain_override': domain_override,
            }
            form.save(**opts)
            logger.info("Password reset email request handled for: %s", email)

            messages.success(
                self.request,
                'If an account exists with that email, you will receive password reset instructions shortly. Please check your inbox and spam folder.'
            )
            return redirect(self.success_url)
        except Exception as e:
            logger.error(
                "Error sending password reset email to %s: %s",
                email,
                str(e),
                exc_info=True,
            )
            # Keep same response for security (do not reveal account existence)
            messages.success(
                self.request,
                'If an account exists with that email, you will receive password reset instructions shortly. Please check your inbox and spam folder.'
            )
            return redirect(self.success_url)

def password_reset_confirm(request, uidb64, token):
    """Completely custom password reset confirm view - no inheritance from Django's view"""
    from django.contrib.auth.tokens import default_token_generator
    from django.contrib.auth.forms import SetPasswordForm
    from django.contrib import messages
    from django.utils.encoding import force_str
    from django.utils.http import urlsafe_base64_decode
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    validlink = False
    user = None
    
    print(f"ðŸ” Password reset confirm - uidb64: {uidb64}, token: {token[:30]}... (full length: {len(token)})")
    
    # Decode the user ID
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        print(f"   ðŸ‘¤ User found: {user.username}")
    except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
        user = None
        print(f"   âŒ Invalid uidb64 '{uidb64}': {str(e)}")
    
    # Check if token is valid
    if user is not None:
        if default_token_generator.check_token(user, token):
            validlink = True
            print(f"   âœ… Token is VALID for user: {user.username}")
        else:
            print(f"   âŒ Token is INVALID for user: {user.username}")
            print(f"   ðŸ” Token check failed - token might be expired or already used")
    else:
        print(f"   âŒ User not found for uidb64: {uidb64}")
    
    # Handle POST request (form submission)
    if request.method == 'POST':
        if not validlink:
            messages.error(request, 'Password reset link is invalid or has expired.')
            return redirect('password_reset')
        
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your password has been reset successfully. You can now log in with your new password.')
            return redirect('password_reset_complete')
        
        # Form is invalid, re-render with errors
        context = {
            'form': form,
            'validlink': True,
        }
        return render(request, 'registration/password_reset_confirm.html', context)
    
    # Handle GET request (display form)
    context = {
        'form': SetPasswordForm(user) if validlink else None,
        'validlink': validlink,
    }
    return render(request, 'registration/password_reset_confirm.html', context)
