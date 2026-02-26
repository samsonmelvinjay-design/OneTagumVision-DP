from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.views import PasswordResetView
from django.core.mail import send_mail
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
    """Custom password reset view with error logging"""
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    template_name = 'registration/password_reset_form.html'
    success_url = '/accounts/login/'  # Redirect to login page instead of done page
    
    def form_valid(self, form):
        from django.contrib import messages
        from django.shortcuts import redirect
        
        email = form.cleaned_data['email']
        print(f"📧 Password reset requested for email: {email}")
        
        try:
            # Call parent's form_valid which sends the email
            # We override to add a success message and redirect to login
            opts = {
                'use_https': self.request.is_secure(),
                'token_generator': self.token_generator,
                'from_email': self.from_email,
                'email_template_name': self.email_template_name,
                'subject_template_name': self.subject_template_name,
                'request': self.request,
                'html_email_template_name': self.html_email_template_name,
                'extra_email_context': self.extra_email_context,
            }
            form.save(**opts)
            print(f"✅ Password reset email sent successfully to: {email}")
            # Debug: Print the generated reset URL format
            from django.contrib.auth.tokens import default_token_generator
            from django.utils.encoding import force_bytes
            from django.utils.http import urlsafe_base64_encode
            try:
                user = form.get_users(email).__next__()
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                from django.contrib.sites.shortcuts import get_current_site
                site = get_current_site(self.request)
                protocol = 'https' if self.request.is_secure() else 'http'
                reset_url = f"{protocol}://{site.domain}/accounts/reset/{uid}/{token}/"
                print(f"🔗 Generated reset URL format: {reset_url}")
                print(f"   uid length: {len(uid)}, token length: {len(token)}")
            except Exception as e:
                print(f"   ⚠️ Could not generate debug URL: {e}")
            
            # Add success message and redirect to login
            messages.success(
                self.request,
                'If an account exists with that email, you will receive password reset instructions shortly. Please check your inbox and spam folder.'
            )
            return redirect(self.success_url)
        except Exception as e:
            # Log the error
            error_msg = f"❌ ERROR sending password reset email to {email}: {str(e)}"
            print(error_msg)
            import traceback
            print(f"Full traceback:\n{traceback.format_exc()}")
            logging.error(error_msg, exc_info=True)
            # Still show success message (for security, don't reveal if email exists)
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
    
    print(f"🔐 Password reset confirm - uidb64: {uidb64}, token: {token[:30]}... (full length: {len(token)})")
    
    # Decode the user ID
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        print(f"   👤 User found: {user.username}")
    except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
        user = None
        print(f"   ❌ Invalid uidb64 '{uidb64}': {str(e)}")
    
    # Check if token is valid
    if user is not None:
        if default_token_generator.check_token(user, token):
            validlink = True
            print(f"   ✅ Token is VALID for user: {user.username}")
        else:
            print(f"   ❌ Token is INVALID for user: {user.username}")
            print(f"   🔍 Token check failed - token might be expired or already used")
    else:
        print(f"   ❌ User not found for uidb64: {uidb64}")
    
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
