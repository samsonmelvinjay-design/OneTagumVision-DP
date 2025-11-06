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
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if os.environ.get('CSRF_TRUSTED_ORIGINS') else []

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
]

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

if DATABASE_URL:
    # Use Postgres when DATABASE_URL is provided (production/staging)
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
TIME_ZONE = 'UTC'
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

# Session Security
SESSION_COOKIE_SECURE = not DEBUG  # True in production with HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 1800  # 30 minutes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

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
REDIS_URL = os.environ.get('REDIS_URL', None)
if REDIS_URL and not DEBUG:
    try:
        CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.redis.RedisCache',
                'LOCATION': REDIS_URL,
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                    'SSL_CERT_REQS': None,  # For DigitalOcean SSL connections
                },
                'KEY_PREFIX': 'gistagum',
                'TIMEOUT': 300,  # 5 minutes default timeout
            }
        }
    except Exception as e:
        # If Redis/Valkey connection fails, fall back to in-memory cache
        print(f"Warning: Redis/Valkey connection failed: {e}. Using in-memory cache.")
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

# Specify the path to the GDAL and GEOS libraries if auto-detection fails
if os.name == 'nt':  # Check if the operating system is Windows
    GDAL_LIBRARY_PATH = r'C:\OSGeo4W\bin\gdal310.dll'
    GEOS_LIBRARY_PATH = r'C:\OSGeo4W\bin\geos_c.dll'
    os.environ['PATH'] = r'C:\OSGeo4W\bin;' + os.environ['PATH']