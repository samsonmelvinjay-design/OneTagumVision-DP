import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-your-secret-key-here'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tailwind',
    'onetagumvision',
    'theme',
    'django_browser_reload',
    'monitoring',
    'django.contrib.gis',
    'projeng',
    'django_extensions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_browser_reload.middleware.BrowserReloadMiddleware',
]

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
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'gistagum',
        'USER': 'postgres',         # or your actual postgres username
        'PASSWORD': '0613',# replace with your actual password
        'HOST': 'localhost',
        'PORT': '5432',             # default PostgreSQL port
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

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# TailwindCSS configuration
TAILWIND_APP_NAME = 'onetagumvision'

NPM_BIN_PATH = r"C:\Program Files\nodejs\npm.cmd"

# Media files (user uploaded files)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Redirect after login
LOGIN_REDIRECT_URL = '/'

# Redirect to dual login after logout
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Specify the path to the GDAL and GEOS libraries if auto-detection fails
# Replace 'C:/OSGeo4W/bin/' with the actual path to your OSGeo4W bin directory
if os.name == 'nt':  # Check if the operating system is Windows
    GDAL_LIBRARY_PATH = r'C:\OSGeo4W\bin\gdal310.dll'
    GEOS_LIBRARY_PATH = r'C:\OSGeo4W\bin\geos_c.dll' 