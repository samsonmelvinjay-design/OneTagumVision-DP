import os
from pathlib import Path
from urllib.parse import urlparse, parse_qsl

try:
    import dj_database_url  # type: ignore
except Exception:  # linter-safe optional dependency
    dj_database_url = None

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'insecure-dev-key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'true').lower() == 'true'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0').split(',')
# Clean up ALLOWED_HOSTS - remove empty strings
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS if host.strip()]

# CSRF Trusted Origins - critical for multi-user access
csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if csrf_origins:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_origins.split(',') if origin.strip()]
else:
    # Default: allow all origins from ALLOWED_HOSTS (for development)
    # In production, set CSRF_TRUSTED_ORIGINS explicitly
    CSRF_TRUSTED_ORIGINS = []
    for host in ALLOWED_HOSTS:
        if host and host not in ['localhost', '127.0.0.1', '0.0.0.0']:
            # Add both http and https versions
            CSRF_TRUSTED_ORIGINS.append(f'https://{host}')
            CSRF_TRUSTED_ORIGINS.append(f'http://{host}')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'whitenoise.runserver_nostatic',
    'tailwind',
    'onetagumvision',
    'theme',
    'django_browser_reload',
    'monitoring',
    # 'django.contrib.gis',  # Temporarily disabled due to GDAL issues
    'projeng',
    'django_extensions',
    # 'channels',  # Temporarily commented for management commands
]

# ASGI Application for WebSocket support (Phase 1: Safe addition)
# This allows Django to handle WebSocket connections via Daphne
# Gunicorn (WSGI) will still work for HTTP requests
ASGI_APPLICATION = 'gistagum.asgi.application'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'gistagum.middleware.SecurityHeadersMiddleware',  # Custom security middleware
]

if DEBUG:
    MIDDLEWARE.append('django_browser_reload.middleware.BrowserReloadMiddleware')

ROOT_URLCONF = 'gistagum.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'projeng.context_processors.notifications_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'gistagum.wsgi.application'

# Database
DATABASE_URL = os.environ.get('DATABASE_URL', '')

# Handle empty or invalid DATABASE_URL gracefully
if DATABASE_URL and DATABASE_URL.strip():
    # Use Postgres when DATABASE_URL is provided (production/staging)
    try:
        if dj_database_url:
            DATABASES = {
                'default': dj_database_url.config(default=DATABASE_URL)
            }
        else:
            tmp = urlparse(DATABASE_URL)
            DATABASES = {
                'default': {
                    'ENGINE': 'django.db.backends.postgresql',
                    'NAME': tmp.path.lstrip('/') or 'postgres',
                    'USER': tmp.username or 'postgres',
                    'PASSWORD': tmp.password or '',
                    'HOST': tmp.hostname or 'localhost',
                    'PORT': tmp.port or 5432,
                    'OPTIONS': dict(parse_qsl(tmp.query)) if tmp.query else {},
                }
            }
    except (ValueError, Exception) as e:
        # If DATABASE_URL is invalid/empty, fall back to SQLite
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Invalid DATABASE_URL: {e}. Falling back to SQLite.")
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
else:
    # Use local Postgres for development when no DATABASE_URL is set
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'gistagumnew',
            'USER': 'postgres',
            'PASSWORD': '0613',  # Your local Postgres password
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
# Timezone: Set to Philippine Standard Time (PST/Asia/Manila) for accurate real-time timestamps
# Tagum City, Philippines is in UTC+8 timezone
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# TailwindCSS configuration
TAILWIND_APP_NAME = 'onetagumvision'

NPM_BIN_PATH = r"C:\Program Files\nodejs\npm.cmd"

# Media files (user uploaded files)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Redirect after login
LOGIN_REDIRECT_URL = '/dashboard/'

# Redirect to dual login after logout
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HTTPS and SSL Settings (for production)
if not DEBUG:
    SECURE_SSL_REDIRECT = True  # Redirect HTTP to HTTPS
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    CSRF_COOKIE_SECURE = True  # Only send CSRF cookie over HTTPS
else:
    # In development, allow HTTP for CSRF cookies
    CSRF_COOKIE_SECURE = False

# Session Security - Configured for multi-user support
SESSION_COOKIE_SECURE = not DEBUG  # True in production with HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 1800  # 30 minutes
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Allow sessions to persist across browser restarts for better UX
SESSION_SAVE_EVERY_REQUEST = True  # Save session on every request to prevent expiration issues

# CSRF Cookie Settings - Critical for multi-user access
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript to access CSRF token (needed for AJAX)
CSRF_COOKIE_SAMESITE = 'Lax'  # Allow cross-site requests from same site
CSRF_USE_SESSIONS = False  # Use cookies instead of sessions for CSRF (better for multiple users)

# Session Backend - Use database sessions for better multi-user support
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Database-backed sessions (default, but explicit)

# Cache Control for Security
CACHE_CONTROL_SECURE = True

# Caching Configuration
# Use in-memory cache for development, Redis for production (if available)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
            'CULL_FREQUENCY': 3,
        }
    }
}

# If Redis/Valkey is available in production, use it
# Note: Valkey is Redis-compatible, so REDIS_URL works for both
# REDIS_URL is now configured in the Celery section below for better organization
# This section uses the same REDIS_URL for caching
REDIS_URL_FOR_CACHE = os.environ.get('REDIS_URL', '').strip()
if REDIS_URL_FOR_CACHE and not REDIS_URL_FOR_CACHE.startswith('redis://default:YOUR_PASSWORD') and not DEBUG:
    # Use Redis/Valkey for caching
    # Connection errors will be handled gracefully by Django's cache framework
    # If connection fails, Django will raise an exception that can be caught
    try:
        CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.redis.RedisCache',
                'LOCATION': REDIS_URL_FOR_CACHE,
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                    'SSL_CERT_REQS': None,  # For DigitalOcean SSL connections (rediss://)
                    'CONNECTION_POOL_KWARGS': {
                        'ssl_cert_reqs': None,  # Additional SSL setting
                        'socket_connect_timeout': 5,  # 5 second connection timeout
                        'socket_timeout': 5,  # 5 second socket timeout
                        'retry_on_timeout': True,
                    },
                    'SOCKET_CONNECT_TIMEOUT': 5,
                    'SOCKET_TIMEOUT': 5,
                },
                'KEY_PREFIX': 'gistagum',
                'TIMEOUT': 300,  # 5 minutes default timeout
            }
        }
    except Exception as e:
        # If there's an error configuring Redis/Valkey, fall back to in-memory cache
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to configure Redis/Valkey cache: {e}. Using in-memory cache.")
        CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                'LOCATION': 'unique-snowflake',
            }
        }


# WhiteNoise Configuration for Better Performance
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG
WHITENOISE_MAX_AGE = 31536000 if not DEBUG else 0  # 1 year cache in production

# Static Files Caching Headers
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    # Add cache headers for static files
    WHITENOISE_MANIFEST_STRICT = False

# Performance Settings
# Disable debug toolbar and other dev tools in production
if not DEBUG:
    # Remove debug middleware
    if 'django_browser_reload.middleware.BrowserReloadMiddleware' in MIDDLEWARE:
        MIDDLEWARE.remove('django_browser_reload.middleware.BrowserReloadMiddleware')

# Database Query Logging (only in DEBUG mode)
if DEBUG:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            'django.db.backends': {
                'level': 'DEBUG',
                'handlers': ['console'],
            },
        },
    }

# Database Connection Pooling (applied after DATABASES is set)
if DATABASE_URL and not DEBUG:
    # Add connection pooling to existing database config
    if 'default' in DATABASES:
        DATABASES['default']['CONN_MAX_AGE'] = 600  # 10 minutes connection pooling
        if 'OPTIONS' not in DATABASES['default']:
            DATABASES['default']['OPTIONS'] = {}
        # Preserve existing options
        existing_options = DATABASES['default']['OPTIONS'].copy()
        existing_options.update({
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000',  # 30 second query timeout
        })
        DATABASES['default']['OPTIONS'] = existing_options

# ============================================================================
# Redis/Valkey Configuration - Handles both secure (rediss://) and plain (redis://) connections
# ============================================================================
import ssl
from urllib.parse import urlparse

REDIS_URL = os.environ.get('REDIS_URL', '').strip()

# Initialize Redis configuration
REDIS_CONFIG = None
REDIS_SSL_CONFIG = None

if REDIS_URL and not REDIS_URL.startswith('redis://default:YOUR_PASSWORD'):
    # Determine if this is a secure (SSL) or plain connection
    is_secure = REDIS_URL.startswith('rediss://')
    
    if is_secure:
        # Secure Redis connection (SSL) - DigitalOcean Valkey uses this
        # CRITICAL: Celery requires ssl_cert_reqs parameter in the URL
        if 'ssl_cert_reqs' not in REDIS_URL:
            separator = '&' if '?' in REDIS_URL else '?'
            # Use 'none' for CERT_NONE (safer for DigitalOcean Valkey)
            # Change to 'required' if you have proper SSL certificates
            REDIS_URL = f"{REDIS_URL}{separator}ssl_cert_reqs=none"
        
        # Parse URL to extract connection details
        parsed = urlparse(REDIS_URL)
        
        # SSL Configuration for Celery
        cert_reqs = ssl.CERT_NONE if 'ssl_cert_reqs=none' in REDIS_URL else ssl.CERT_REQUIRED
        
        REDIS_SSL_CONFIG = {
            'ssl_cert_reqs': cert_reqs,
            'ssl_ca_certs': None,
            'ssl_certfile': None,
            'ssl_keyfile': None,
        }
        
        # Log successful SSL configuration (without exposing password)
        safe_url = REDIS_URL.split('@')[-1] if '@' in REDIS_URL else REDIS_URL
        print(f"Connected to Redis server {safe_url} using SSL")
    else:
        # Normal Redis connection (no SSL)
        print(f"Connected to Redis server (non-SSL)")
    
    # Store the configured URL
    REDIS_CONFIG = REDIS_URL
else:
    print("WARNING: REDIS_URL not configured. Using database fallback for Celery.")

# ============================================================================
# Celery Configuration for Background Tasks
# ============================================================================
if REDIS_CONFIG:
    # Use Redis/Valkey as Celery broker and result backend
    CELERY_BROKER_URL = REDIS_CONFIG
    CELERY_RESULT_BACKEND = REDIS_CONFIG
    
    # Configure SSL options if using secure connection
    if REDIS_SSL_CONFIG:
        CELERY_BROKER_CONNECTION_OPTIONS = REDIS_SSL_CONFIG.copy()
        CELERY_RESULT_BACKEND_CONNECTION_OPTIONS = REDIS_SSL_CONFIG.copy()
    else:
        # For non-SSL Redis connections
        CELERY_BROKER_CONNECTION_OPTIONS = {}
        CELERY_RESULT_BACKEND_CONNECTION_OPTIONS = {}
    
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_TIMEZONE = 'Asia/Manila'  # Match Django timezone for accurate timestamps
    CELERY_TASK_TRACK_STARTED = True
    CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes max per task
    CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes soft limit
    CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Prevents worker from hoarding tasks
    CELERY_TASK_ACKS_LATE = True  # Tasks acknowledged after completion
else:
    # Fallback: Use database as broker (not recommended for production, but works)
    print("WARNING: Using database as Celery broker (fallback mode)")
    CELERY_BROKER_URL = 'db+postgresql://'  # Will use DATABASE_URL
    CELERY_RESULT_BACKEND = 'db+postgresql://'  # Will use DATABASE_URL
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_TIMEZONE = 'Asia/Manila'  # Match Django timezone for accurate timestamps

# ============================================================================
# Django Channels Configuration (Phase 1: Safe addition - uses existing Redis)
# ============================================================================
# Channels is now installed and configured
# This uses the same Redis/Valkey connection as Celery
try:
    import channels_redis
    import ssl
    
    # Channels is available
    if REDIS_CONFIG:
        # Configure Channel Layers for WebSocket support
        if REDIS_CONFIG.startswith('rediss://'):
            # Secure Redis connection for Channels (DigitalOcean Valkey)
            CHANNEL_LAYERS = {
                "default": {
                    "BACKEND": "channels_redis.core.RedisChannelLayer",
                    "CONFIG": {
                        "hosts": [{
                            "address": REDIS_CONFIG,
                            "ssl": True,
                            "ssl_cert_reqs": ssl.CERT_NONE,  # Match Celery config
                        }],
                    },
                },
            }
            print("Django Channels configured with SSL Redis connection")
        else:
            # Plain Redis connection for Channels
            CHANNEL_LAYERS = {
                "default": {
                    "BACKEND": "channels_redis.core.RedisChannelLayer",
                    "CONFIG": {
                        "hosts": [REDIS_CONFIG],
                    },
                },
            }
            print("Django Channels configured with Redis connection")
    else:
        print("WARNING: Django Channels not configured (REDIS_URL not set)")
        # Set a default in-memory channel layer for development (not for production)
        CHANNEL_LAYERS = {
            "default": {
                "BACKEND": "channels.layers.InMemoryChannelLayer"
            }
        }
        print("WARNING: Using in-memory channel layer (development only)")
except ImportError:
    # Channels not installed - that's okay, it's optional
    # This should not happen in Phase 1, but fail gracefully
    print("WARNING: channels-redis not installed - Channels will use in-memory layer")
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }

# Specify the path to the GDAL and GEOS libraries if auto-detection fails
if os.name == 'nt':  # Check if the operating system is Windows
    GDAL_LIBRARY_PATH = r'C:\OSGeo4W\bin\gdal310.dll'
    GEOS_LIBRARY_PATH = r'C:\OSGeo4W\bin\geos_c.dll'
    os.environ['PATH'] = r'C:\OSGeo4W\bin;' + os.environ['PATH']