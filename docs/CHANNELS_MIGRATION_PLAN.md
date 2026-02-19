# Django Channels Migration Plan - Safe & Incremental

## 🎯 Goal
Add real-time WebSocket support using Django Channels **without breaking** the existing SSE system.

## ✅ Safety Guarantees
- ✅ Current SSE system keeps working
- ✅ No downtime during migration
- ✅ Can rollback at any step
- ✅ All existing features remain functional
- ✅ Test each step before proceeding

---

## 📋 Phase 1: Preparation & Setup (No Breaking Changes)

### Step 1.1: Install Dependencies
**Status:** Safe - Just adding packages, no code changes yet

```bash
# Add to requirements.txt
channels==4.0.0
channels-redis==4.1.0
daphne==4.0.0
```

**What happens:**
- Packages installed
- No code changes
- System still runs on Gunicorn + SSE
- ✅ **Zero risk**

### Step 1.2: Update settings.py (Add Channels Config)
**Status:** Safe - Adding config, not removing anything

```python
# Add to INSTALLED_APPS (keep everything else)
INSTALLED_APPS = [
    # ... existing apps ...
    'channels',
]

# Add ASGI application (keep WSGI)
ASGI_APPLICATION = 'gistagum.asgi.application'

# Add Channel Layers (uses existing Redis/Valkey)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [os.environ.get('REDIS_URL', 'redis://localhost:6379')],
        },
    },
}
```

**What happens:**
- Channels configured
- SSE still works
- Can still use Gunicorn
- ✅ **Zero risk** - just configuration

### Step 1.3: Create asgi.py
**Status:** Safe - New file, doesn't affect existing code

Create `gistagum/asgi.py`:
```python
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gistagum.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# For now, only HTTP - WebSocket routing added later
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    # "websocket": ... (added in Phase 2)
})
```

**What happens:**
- New file created
- Existing code unchanged
- Still runs on Gunicorn
- ✅ **Zero risk**

### Step 1.4: Test Phase 1
**Action:** Deploy and verify
- ✅ System still works exactly as before
- ✅ SSE notifications still work
- ✅ No errors in logs
- ✅ All features functional

**If anything breaks:** Remove Channels config, system returns to normal

---

## 📋 Phase 2: Add WebSocket Support (Parallel to SSE)

### Step 2.1: Create Consumer (Real-time Handler)
**Status:** Safe - New code, doesn't touch existing SSE

Create `projeng/consumers.py`:
```python
from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async
from projeng.models import Notification, Project

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            # Join user-specific group
            self.group_name = f"user_{self.scope['user'].id}_notifications"
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def send_notification(self, event):
        """Send notification to WebSocket"""
        await self.send(text_data=json.dumps(event["data"]))


class ProjectUpdateConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            # Join project updates group
            self.group_name = "project_updates"
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def send_update(self, event):
        """Send project update to WebSocket"""
        await self.send(text_data=json.dumps(event["data"]))
```

**What happens:**
- New WebSocket handlers created
- SSE still works independently
- ✅ **Zero risk** - parallel system

### Step 2.2: Add WebSocket Routing
**Status:** Safe - Adds routing, doesn't remove HTTP

Update `gistagum/asgi.py`:
```python
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gistagum.settings')
django_asgi_app = get_asgi_application()

# Import routing (created in next step)
from projeng import routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(routing.websocket_urlpatterns)
        )
    ),
})
```

Create `projeng/routing.py`:
```python
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/projects/$', consumers.ProjectUpdateConsumer.as_asgi()),
]
```

**What happens:**
- WebSocket routes added
- HTTP/SSE still works
- Both systems run in parallel
- ✅ **Zero risk**

### Step 2.3: Update Dockerfile for Daphne (Optional - Can Test Locally First)
**Status:** Safe - Can test locally before deploying

Update `Dockerfile` to support both Gunicorn and Daphne:
```dockerfile
# ... existing Dockerfile ...

# Install Daphne
RUN pip install daphne

# Update start.sh to detect if we should use Daphne
# For now, keep Gunicorn as default
```

Update `start.sh`:
```bash
#!/bin/sh

# Check if we should use Daphne (for WebSocket support)
if [ "$USE_DAPHNE" = "true" ]; then
    echo "Starting with Daphne (WebSocket support)..."
    exec daphne -b 0.0.0.0 -p ${PORT:-8000} gistagum.asgi:application
fi

# Default: Use Gunicorn (existing system)
# ... rest of existing start.sh ...
```

**What happens:**
- Can test Daphne locally
- Production still uses Gunicorn
- SSE still works
- ✅ **Zero risk** - optional change

### Step 2.4: Test Phase 2
**Action:** Test WebSocket connection
- ✅ SSE still works
- ✅ Can connect via WebSocket (test with browser console)
- ✅ No errors
- ✅ Both systems functional

---

## 📋 Phase 3: Add WebSocket Broadcasting (Parallel to SSE)

### Step 3.1: Add Broadcast Helper Functions
**Status:** Safe - New functions, doesn't modify existing code

Create `projeng/channels_utils.py`:
```python
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import User

def broadcast_notification(user_id, notification_data):
    """Broadcast notification via WebSocket (parallel to SSE)"""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}_notifications",
            {
                "type": "send_notification",
                "data": notification_data
            }
        )
    except Exception as e:
        # Fail silently - SSE is still working
        print(f"WebSocket broadcast failed: {e}")


def broadcast_project_update(update_data):
    """Broadcast project update via WebSocket (parallel to SSE)"""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "project_updates",
            {
                "type": "send_update",
                "data": update_data
            }
        )
    except Exception as e:
        # Fail silently - SSE is still working
        print(f"WebSocket broadcast failed: {e}")
```

**What happens:**
- New broadcast functions
- Existing SSE code unchanged
- Both systems send updates
- ✅ **Zero risk** - additive only

### Step 3.2: Add WebSocket Broadcasts to Signals
**Status:** Safe - Adds WebSocket, keeps SSE

Update `projeng/signals.py`:
```python
# Add import at top
from .channels_utils import broadcast_notification, broadcast_project_update

# In notify_project_updates signal, add:
@receiver(post_save, sender=Project)
def notify_project_updates(sender, instance, created, **kwargs):
    # ... existing SSE notification code ...
    
    # ADD: Also broadcast via WebSocket (parallel to SSE)
    try:
        broadcast_project_update({
            'type': 'project_updated',
            'project_id': instance.id,
            'name': instance.name,
            'status': instance.status,
        })
    except:
        pass  # SSE still works if WebSocket fails
```

**What happens:**
- WebSocket broadcasts added
- SSE notifications still sent
- Both work in parallel
- ✅ **Zero risk** - failsafe design

### Step 3.3: Add Frontend WebSocket Client (Optional)
**Status:** Safe - Can test alongside SSE

Create `static/js/websocket_client.js`:
```javascript
class WebSocketManager {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
        };
        
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            // Handle notification
            console.log('WebSocket notification:', data);
            // Update UI (same as SSE handler)
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        this.socket.onclose = () => {
            console.log('WebSocket disconnected');
            // Reconnect logic
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                setTimeout(() => this.connect(), 3000);
            }
        };
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }
}

// Initialize (can run alongside SSE)
// window.wsManager = new WebSocketManager();
// window.wsManager.connect();
```

**What happens:**
- New WebSocket client code
- SSE client still works
- Can test both
- ✅ **Zero risk** - optional

### Step 3.4: Test Phase 3
**Action:** Test both systems
- ✅ SSE still works
- ✅ WebSocket receives updates
- ✅ Both send notifications
- ✅ No conflicts

---

## 📋 Phase 4: Gradual Migration (User Choice)

### Step 4.1: Add Feature Flag
**Status:** Safe - Users can choose

Add to `settings.py`:
```python
# Feature flag - can enable/disable WebSocket
USE_WEBSOCKETS = os.environ.get('USE_WEBSOCKETS', 'false').lower() == 'true'
```

Update frontend to use WebSocket if flag is set, otherwise use SSE.

**What happens:**
- Can toggle between systems
- Easy rollback
- Test with subset of users
- ✅ **Zero risk**

### Step 4.2: Monitor & Compare
**Action:** Run both systems
- Monitor performance
- Compare user experience
- Gather feedback
- Decide which is better

---

## 📋 Phase 5: Full Migration (Only When Ready)

### Step 5.1: Switch Default to WebSocket
**Status:** Can rollback easily

- Set `USE_WEBSOCKETS = True` by default
- Keep SSE code as fallback
- Monitor for issues

### Step 5.2: Remove SSE (Only After Confirmation)
**Status:** Final step - only after everything works

- Remove SSE code
- Keep WebSocket only
- Clean up unused files

---

## 🛡️ Safety Checklist (Before Each Phase)

- [ ] Current system works perfectly
- [ ] All tests pass
- [ ] Can rollback easily
- [ ] No data loss risk
- [ ] No downtime
- [ ] Tested locally first

---

## 🔄 Rollback Plan (If Anything Goes Wrong)

### Quick Rollback Steps:
1. **Remove Channels config** from `settings.py`
2. **Revert Dockerfile** to Gunicorn only
3. **Remove WebSocket code** (keep SSE)
4. **Deploy** - system returns to original state

### Time to Rollback: < 5 minutes

---

## 📊 Progress Tracking

- [ ] Phase 1: Preparation (Safe - No risk)
- [ ] Phase 2: WebSocket Support (Safe - Parallel)
- [ ] Phase 3: Broadcasting (Safe - Additive)
- [ ] Phase 4: Gradual Migration (Safe - Optional)
- [ ] Phase 5: Full Migration (Only when ready)

---

## 💡 Key Principles

1. **Never remove working code** until new code is proven
2. **Always have a fallback** (SSE stays until WebSocket works)
3. **Test incrementally** at each step
4. **Can stop at any phase** if needed
5. **Zero downtime** throughout migration

---

## 🎯 Expected Timeline

- **Phase 1:** 1-2 hours (setup, no risk)
- **Phase 2:** 2-3 hours (WebSocket support, parallel)
- **Phase 3:** 2-3 hours (broadcasting, additive)
- **Phase 4:** 1-2 weeks (testing, gradual)
- **Phase 5:** When ready (full migration)

**Total Active Development:** ~6-8 hours
**Testing Period:** 1-2 weeks
**Risk Level:** Minimal (can rollback at any point)

---

## ✅ Ready to Start?

This plan ensures:
- ✅ Your system stays safe
- ✅ No breaking changes
- ✅ Easy rollback
- ✅ Incremental progress
- ✅ Test at each step

**Would you like to start with Phase 1?** It's completely safe - just adding configuration, no code changes yet.

