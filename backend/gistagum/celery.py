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
    
    # SSL configuration is now handled in settings.py
    # The REDIS_URL is modified there to include ssl_cert_reqs=none
    # This ensures it's set before Celery tries to use it
    
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

