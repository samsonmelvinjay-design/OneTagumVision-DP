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
    post_reset_login = False  # Don't auto-login after reset
    
    def dispatch(self, *args, **kwargs):
        uidb64 = kwargs.get('uidb64', '')
        token = kwargs.get('token', '')
        print(f"🔐 Password reset confirm - uidb64: {uidb64}, token: {token[:30]}... (full length: {len(token)})")
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        """Override get to prevent redirects and add detailed logging"""
        from django.contrib.auth.tokens import default_token_generator
        from django.contrib.auth.forms import SetPasswordForm
        from django.shortcuts import render
        
        self.validlink = False
        uidb64 = kwargs.get('uidb64', '')
        token = kwargs.get('token', '')
        
        try:
            # Try to get the user
            try:
                user = self.get_user(uidb64)
                print(f"   👤 User found: {user.username if user else 'None'}")
            except (TypeError, ValueError, OverflowError) as e:
                user = None
                print(f"   ❌ Invalid uidb64 '{uidb64}': {str(e)}")
            
            # Check if token is valid
            if user is not None:
                if default_token_generator.check_token(user, token):
                    self.validlink = True
                    print(f"   ✅ Token is VALID for user: {user.username}")
                else:
                    print(f"   ❌ Token is INVALID for user: {user.username}")
                    print(f"   🔍 Token check failed - token might be expired or already used")
            else:
                print(f"   ❌ User not found for uidb64: {uidb64}")
            
            # Set the user and validlink for the template
            self.user = user
            context = {
                'form': SetPasswordForm(user) if self.validlink else None,
                'validlink': self.validlink,
            }
            
            # Render the template directly (no redirect)
            return render(request, self.template_name, context)
            
        except Exception as e:
            print(f"   ❌ ERROR in get(): {str(e)}")
            import traceback
            print(traceback.format_exc())
            # Still render the template with error
            context = {
                'form': None,
                'validlink': False,
            }
            return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        """Handle form submission"""
        from django.contrib.auth.tokens import default_token_generator
        from django.contrib.auth.forms import SetPasswordForm
        from django.shortcuts import render, redirect
        from django.contrib import messages
        
        uidb64 = kwargs.get('uidb64', '')
        token = kwargs.get('token', '')
        
        try:
            user = self.get_user(uidb64)
            if user is None:
                messages.error(request, 'Invalid password reset link.')
                return redirect('password_reset')
            
            # Verify token is still valid
            if not default_token_generator.check_token(user, token):
                messages.error(request, 'Password reset link is invalid or has expired.')
                return redirect('password_reset')
            
            # Process the form
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Your password has been reset successfully.')
                return redirect(self.success_url)
            
            # Form is invalid, re-render with errors
            context = {
                'form': form,
                'validlink': True,
            }
            return render(request, self.template_name, context)
            
        except Exception as e:
            print(f"   ❌ ERROR in post(): {str(e)}")
            import traceback
            print(traceback.format_exc())
            messages.error(request, 'An error occurred while resetting your password.')
            return redirect('password_reset')