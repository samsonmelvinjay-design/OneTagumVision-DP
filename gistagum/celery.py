"""
Celery configuration for background task processing
"""
import os
import ssl
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gistagum.settings')

app = Celery('gistagum')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Configure SSL for Redis/Valkey if using rediss://
# This must be done AFTER config_from_object to override settings
REDIS_URL = os.environ.get('REDIS_URL', None)
if REDIS_URL and REDIS_URL.startswith('rediss://'):
    # Configure SSL options for Celery Redis backend
    # For Celery 5.x, we need to set broker_connection_ssl and result_backend_transport_options
    ssl_options = {
        'ssl_cert_reqs': ssl.CERT_NONE,  # DigitalOcean Valkey doesn't require cert verification
        'ssl_ca_certs': None,
        'ssl_certfile': None,
        'ssl_keyfile': None,
    }
    
    # Set SSL options for broker connection
    app.conf.broker_connection_ssl = ssl_options
    
    # Set SSL options for result backend
    app.conf.result_backend_transport_options = {
        'ssl_cert_reqs': ssl.CERT_NONE,
        'ssl_ca_certs': None,
        'ssl_certfile': None,
        'ssl_keyfile': None,
    }
    
    # Also set connection options (alternative method)
    app.conf.broker_connection_retry_on_startup = True

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

