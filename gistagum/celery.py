"""
Celery configuration for background task processing
"""
import os
import ssl
import sys
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gistagum.settings')

try:
    app = Celery('gistagum')
    
    # Using a string here means the worker doesn't have to serialize
    # the configuration object to child processes.
    # - namespace='CELERY' means all celery-related configuration keys
    #   should have a `CELERY_` prefix.
    app.config_from_object('django.conf:settings', namespace='CELERY')
    
    # Configure SSL for Redis/Valkey if using rediss://
    # This must be done AFTER config_from_object to override settings
    REDIS_URL = os.environ.get('REDIS_URL', None)
    
    # Skip SSL configuration if REDIS_URL is placeholder or empty
    if REDIS_URL and REDIS_URL.strip() and not REDIS_URL.startswith('redis://default:YOUR_PASSWORD'):
        if REDIS_URL.startswith('rediss://'):
            # Method 1: Append ssl_cert_reqs to URL (most reliable for Celery 5.x)
            if 'ssl_cert_reqs' not in REDIS_URL:
                # Add ssl_cert_reqs parameter to URL
                separator = '&' if '?' in REDIS_URL else '?'
                REDIS_URL = f"{REDIS_URL}{separator}ssl_cert_reqs=none"
                # Update broker and result backend URLs
                app.conf.broker_url = REDIS_URL
                app.conf.result_backend = REDIS_URL
            
            # Method 2: Also configure SSL options directly (backup method)
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
            
            # Also set connection options
            app.conf.broker_connection_retry_on_startup = True
    
    # Load task modules from all registered Django apps.
    app.autodiscover_tasks()
    
except Exception as e:
    # Print error to stderr so it shows in logs
    print(f"ERROR: Failed to configure Celery: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    # Re-raise to fail fast
    raise


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

