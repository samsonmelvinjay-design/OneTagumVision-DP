import os
from pathlib import Path
from urllib.parse import urlparse, parse_qsl

try:
    import dj_database_url  # type: ignore
except Exception:  # linter-safe optional dependency
    dj_database_url = None

# Build paths: BASE_DIR = backend/, PROJECT_ROOT = repo root (for frontend & shared assets)
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
# Frontend assets: prefer frontend/ if present, else project root (templates/, static/)
FRONTEND_DIR = PROJECT_ROOT / 'frontend'
if (FRONTEND_DIR / 'templates').exists():
    TEMPLATES_DIR = FRONTEND_DIR / 'templates'
    STATIC_SOURCE_DIR = FRONTEND_DIR / 'static'
else:
    TEMPLATES_DIR = PROJECT_ROOT / 'templates'
    STATIC_SOURCE_DIR = PROJECT_ROOT / 'static'
MEDIA_ROOT_DIR = PROJECT_ROOT / 'media'
COORD_DIR = PROJECT_ROOT / 'coord'
GEOJSON_WHOLETAGUM = PROJECT_ROOT / 'wholetagumexport.geojson'


def get_env_int(var_name: str, default: int) -> int:
    """Safely parse environment variable as int with a default fallback."""
    value = os.environ.get(var_name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_env_bool(var_name: str, default: bool) -> bool:
    """Return boolean interpretation for environment values like 'true', '1', 'yes'."""
    value = os.environ.get(var_name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'insecure-dev-key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'true').lower() == 'true'

# NOTE:
# DigitalOcean App Platform sometimes ends up not applying env vars the way you expect
# (app-level vs component-level). To avoid downtime from DisallowedHost, we provide a
# safe production fallback host list when ALLOWED_HOSTS is missing/empty.
raw_allowed_hosts = os.environ.get('ALLOWED_HOSTS', '').strip()
if not raw_allowed_hosts:
    # Prefer a configurable primary domain if provided.
    primary_domain = os.environ.get('PRIMARY_DOMAIN', '').strip()
    default_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '.ondigitalocean.app']
    if primary_domain:
        default_hosts.extend([primary_domain, f'www.{primary_domain}'])
    else:
        # Project default domain (can still be overridden by ALLOWED_HOSTS env var)
        default_hosts.extend(['onetagumvision.com', 'www.onetagumvision.com'])
    raw_allowed_hosts = ','.join(default_hosts)
# Split by comma, trim, and normalize wildcard notation.
# Django supports leading-dot notation for subdomains (e.g. ".ondigitalocean.app"),
# but does NOT treat "*.example.com" specially. Many platforms/documentation use "*.",
# so we normalize "*.example.com" -> ".example.com".
ALLOWED_HOSTS = []
for host in raw_allowed_hosts.split(','):
    h = host.strip()
    if not h:
        continue
    if h.startswith('*.') and len(h) > 2:
        h = f".{h[2:]}"
    ALLOWED_HOSTS.append(h)

# De-duplicate while preserving order
seen_hosts = set()
ALLOWED_HOSTS = [h for h in ALLOWED_HOSTS if not (h in seen_hosts or seen_hosts.add(h))]

# Production safety net:
# Always allow the primary domain + www + DigitalOcean app subdomains in production,
# even if env vars are misapplied (app-level vs component-level overrides).
if not DEBUG:
    primary_domain = os.environ.get('PRIMARY_DOMAIN', '').strip() or 'onetagumvision.com'
    must_allow = [
        primary_domain,
        f'www.{primary_domain}',
        '.ondigitalocean.app',
    ]
    for h in must_allow:
        if h and h not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(h)

# Print effective ALLOWED_HOSTS for easy debugging in App Platform logs (no secrets).
print(f"Effective ALLOWED_HOSTS: {ALLOWED_HOSTS}")

# CSRF Trusted Origins - critical for multi-user access
csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if csrf_origins:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_origins.split(',') if origin.strip()]
else:
    # Development: build from ALLOWED_HOSTS.
    # Production: prefer explicit origins; provide a safe fallback for the primary domain.
    if DEBUG:
        CSRF_TRUSTED_ORIGINS = []
        for host in ALLOWED_HOSTS:
            if host and host not in ['localhost', '127.0.0.1', '0.0.0.0']:
                # Skip leading-dot hosts (e.g. ".ondigitalocean.app") — not a valid origin.
                if host.startswith('.'):
                    continue
                CSRF_TRUSTED_ORIGINS.append(f'https://{host}')
                CSRF_TRUSTED_ORIGINS.append(f'http://{host}')
    else:
        primary_domain = os.environ.get('PRIMARY_DOMAIN', '').strip() or 'onetagumvision.com'
        CSRF_TRUSTED_ORIGINS = [
            f'https://{primary_domain}',
            f'https://www.{primary_domain}',
            'https://*.ondigitalocean.app',
        ]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # For human-readable number formatting (intcomma, etc.)
    'whitenoise.runserver_nostatic',
    'tailwind',
    'onetagumvision',
    'theme',
    'django_browser_reload',
    'monitoring',
    # 'django.contrib.gis',  # Temporarily disabled due to GDAL issues
    'projeng',
    'django_extensions',
]

# Add optional dependencies only if installed
try:
    import storages
    INSTALLED_APPS.append('storages')  # Django Storages for DigitalOcean Spaces (S3-compatible storage)
except ImportError:
    # Storages not installed - that's okay, it's optional
    pass

try:
    import channels
    INSTALLED_APPS.append('channels')  # Django Channels for WebSocket support (Phase 1: Safe addition)
except ImportError:
    # Channels not installed - that's okay, it's optional
    pass

# ASGI Application for WebSocket support (Phase 1: Safe addition)
# This allows Django to handle WebSocket connections via Daphne
# Gunicorn (WSGI) will still work for HTTP requests
try:
    import channels
    ASGI_APPLICATION = 'gistagum.asgi.application'
except ImportError:
    # Channels not installed - ASGI not needed
    ASGI_APPLICATION = None

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
        'DIRS': [str(TEMPLATES_DIR)],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'projeng.context_processors.notifications_context',
                'gistagum.context_processors.login_success_modal',
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
    # Local development when no DATABASE_URL is set.
    # Prefer local Postgres only if credentials are provided; otherwise fall back to SQLite
    # so the project can run out-of-the-box.
    # IMPORTANT: Do not hardcode local DB credentials in the repo.
    db_password = os.environ.get('DB_PASSWORD', '').strip()
    if db_password:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': os.environ.get('DB_NAME', 'gistagumnew'),
                'USER': os.environ.get('DB_USER', 'postgres'),
                'PASSWORD': db_password,
                'HOST': os.environ.get('DB_HOST', 'localhost'),
                'PORT': os.environ.get('DB_PORT', '5432'),
            }
        }
    else:
        # SQLite fallback (recommended for quick local runs)
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
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
STATICFILES_DIRS = [str(STATIC_SOURCE_DIR)]
STATIC_ROOT = str(BASE_DIR / 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# TailwindCSS configuration
TAILWIND_APP_NAME = 'onetagumvision'

NPM_BIN_PATH = r"C:\Program Files\nodejs\npm.cmd"

# Media files (user uploaded files)
# ============================================================================
# DigitalOcean Spaces Configuration (S3-compatible storage)
# ============================================================================
# If Spaces credentials are provided, use Spaces for media storage
# Otherwise, fall back to local file storage
USE_SPACES = os.environ.get('USE_SPACES', 'false').lower() == 'true'
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')
AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL', '')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'sgp1')
AWS_S3_CUSTOM_DOMAIN = os.environ.get('AWS_S3_CUSTOM_DOMAIN', '')

# Check if Spaces is configured (all required variables are set)
SPACES_CONFIGURED = (
    USE_SPACES and
    AWS_ACCESS_KEY_ID and
    AWS_SECRET_ACCESS_KEY and
    AWS_STORAGE_BUCKET_NAME and
    AWS_S3_ENDPOINT_URL
)

if SPACES_CONFIGURED:
    # Use DigitalOcean Spaces for media storage
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    
    # Spaces-specific settings (removed - moved below to include ACL)
    
    # Use custom domain if provided (CDN endpoint), otherwise use endpoint URL
    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'
    else:
        # Use endpoint URL directly
        MEDIA_URL = f'{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/'
    
    # Don't use query string authentication (Spaces doesn't need it)
    AWS_QUERYSTRING_AUTH = False
    
    # Make files publicly accessible (required for CDN to work)
    # Note: For DigitalOcean Spaces, use 'public-read' for public access
    AWS_DEFAULT_ACL = 'public-read'
    
    # Additional Spaces settings for proper file uploads
    AWS_S3_FILE_OVERWRITE = False  # Don't overwrite files with same name
    AWS_S3_VERIFY = True  # Verify SSL certificates
    
    # Force ACL on upload (important for Spaces)
    # Note: ACL in OBJECT_PARAMETERS might not work with all versions of django-storages
    # We'll rely on AWS_DEFAULT_ACL instead
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',  # Cache for 1 day
    }
    
    # Add error logging for uploads
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Spaces storage backend configured with ACL: public-read")
    
    # Important: Set location to empty string so files go to root of bucket
    # The upload_to parameter in models will create the folder structure
    AWS_LOCATION = ''
    
    # Set MEDIA_ROOT to empty since we're using Spaces
    MEDIA_ROOT = ''
    
    print("DigitalOcean Spaces configured for media storage")
    print(f"   Bucket: {AWS_STORAGE_BUCKET_NAME}")
    print(f"   Region: {AWS_S3_REGION_NAME}")
    print(f"   Endpoint: {AWS_S3_ENDPOINT_URL}")
    print(f"   CDN Domain: {AWS_S3_CUSTOM_DOMAIN or 'Not set'}")
else:
    # Use local file storage (development or when Spaces is not configured)
    MEDIA_URL = '/media/'
    MEDIA_ROOT = str(MEDIA_ROOT_DIR)
    
    if USE_SPACES:
        print("WARNING: USE_SPACES is enabled but Spaces credentials are missing. Using local storage.")
    else:
        print("INFO: Using local file storage for media files")

# Redirect after login
LOGIN_REDIRECT_URL = '/dashboard/'

# Redirect to dual login after logout
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Password reset settings
PASSWORD_RESET_TIMEOUT = 604800  # 7 days in seconds (longer timeout for better UX)

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

# Email Configuration
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = get_env_int('EMAIL_PORT', 587)
EMAIL_USE_TLS = get_env_bool('EMAIL_USE_TLS', True)
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'noreply@onetagumvision.com')

EMAIL_CREDENTIALS_CONFIGURED = all([EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD])

# Debug email configuration
print(f"Email Configuration Check:")
print(f"   EMAIL_HOST: {'Set' if EMAIL_HOST else 'Missing'}")
print(f"   EMAIL_HOST_USER: {'Set' if EMAIL_HOST_USER else 'Missing'}")
print(f"   EMAIL_HOST_PASSWORD: {'Set' if EMAIL_HOST_PASSWORD else 'Missing'}")
print(f"   EMAIL_PORT: {EMAIL_PORT}")
print(f"   EMAIL_USE_TLS: {EMAIL_USE_TLS}")

if EMAIL_CREDENTIALS_CONFIGURED:
    EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
    print(f"   Using SMTP backend: {EMAIL_BACKEND}")
    print(f"   SMTP Server: {EMAIL_HOST}:{EMAIL_PORT}")
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    print(f"   WARNING: Email credentials not fully configured; using console email backend.")
    print(f"   Password reset emails will appear in server logs (not sent via SMTP).")
    if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("Email credentials not fully configured; using console email backend. "
                       "Password reset emails will appear in server logs.")

# CEO - Construction Division report footer (Individual Project Information)
# Used on the printed PDF report from the Project Engineer module.
CEO_REPORT_ADDRESS = os.environ.get('CEO_REPORT_ADDRESS', 'Municipal Tipes / Brgy. Mangagwa Viasi')
CEO_REPORT_PHONE = os.environ.get('CEO_REPORT_PHONE', '(084) 648-3800 / Local 805')
CEO_REPORT_EMAIL = os.environ.get('CEO_REPORT_EMAIL', 'ceo.constructionofh@gmail.com')

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
else:
    # Minimal production logging. Ensure DisallowedHost shows up in runtime logs
    # so host/ALLOWED_HOSTS issues are diagnosable in App Platform.
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {'class': 'logging.StreamHandler'},
        },
        'loggers': {
            'django.security.DisallowedHost': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False,
            },
            'django.request': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': True,
            },
        },
    }

# Database Connection Pooling & Health Checks
DB_CONN_MAX_AGE = get_env_int('DB_CONN_MAX_AGE', 600 if not DEBUG else 0)
DB_CONN_HEALTH_CHECKS = get_env_bool('DB_CONN_HEALTH_CHECKS', True)

if 'default' in DATABASES:
    DATABASES['default']['CONN_MAX_AGE'] = DB_CONN_MAX_AGE
    if DB_CONN_HEALTH_CHECKS and DB_CONN_MAX_AGE > 0:
        DATABASES['default']['CONN_HEALTH_CHECKS'] = True

# Add production-specific database options (DigitalOcean managed Postgres/Valkey)
if DATABASE_URL and not DEBUG and 'default' in DATABASES:
    db_options = DATABASES['default'].get('OPTIONS', {}).copy()
    db_options.setdefault('connect_timeout', 10)
    statement_timeout = '-c statement_timeout=30000'
    existing_options_value = db_options.get('options')
    if existing_options_value:
        if 'statement_timeout' not in existing_options_value:
            db_options['options'] = f"{existing_options_value.strip()} {statement_timeout}".strip()
    else:
        db_options['options'] = statement_timeout
    DATABASES['default']['OPTIONS'] = db_options

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