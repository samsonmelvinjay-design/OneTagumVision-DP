from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView, PasswordResetCompleteView, PasswordResetDoneView
from django.views.generic import RedirectView
from accounts.views import dual_login, custom_logout, clear_login_success, CustomPasswordResetView, password_reset_confirm
from gistagum.views import secure_logout, redirect_to_login, health_check
from monitoring import views as monitoring_views
from django.shortcuts import redirect
from projeng.views import engineer_projects_api
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('admin/', admin.site.urls),
    path('__reload__/', include('django_browser_reload.urls')),
    path('health/', health_check, name='health_check'),  # Health check endpoint
    path('logout/', secure_logout, name='logout'),
    path('accounts/login/', dual_login, name='login'),
    path('accounts/logout/', custom_logout, name='logout'),
    path('accounts/clear-login-success/', clear_login_success, name='clear_login_success'),
    # Password reset URLs (must be before django.contrib.auth.urls to override defaults)
    path('accounts/password_reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('accounts/password_reset/done/', PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/', password_reset_confirm, name='password_reset_confirm'),
    path('accounts/reset/done/', PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('api/engineer-projects/<int:engineer_id>/', engineer_projects_api, name='engineer_projects_api'),
    path('projeng/', include(('projeng.urls', 'projeng'), namespace='projeng')),
    path('', redirect_to_login, name='home'),
    path('dashboard/', include('monitoring.urls')),
    # Redirect /finance/* URLs to /dashboard/finance/* for backward compatibility
    path('finance/dashboard/', RedirectView.as_view(url='/dashboard/finance/dashboard/', permanent=False), name='finance_dashboard_redirect'),
    path('finance/', RedirectView.as_view(url='/dashboard/finance/dashboard/', permanent=False)),
]

# This is only needed when running in development mode.
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 