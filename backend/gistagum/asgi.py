"""
ASGI config for gistagum project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gistagum.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Phase 2: Add WebSocket routing (parallel to SSE - safe addition)
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from projeng import routing

application = ProtocolTypeRouter({
    # HTTP requests still handled by Django (works with Gunicorn)
    "http": django_asgi_app,
    
    # WebSocket connections handled by Channels (works with Daphne)
    # This runs parallel to SSE - both systems work together
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(routing.websocket_urlpatterns)
        )
    ),
})

