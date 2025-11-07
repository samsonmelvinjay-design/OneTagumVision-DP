#!/bin/sh
# Startup script that detects if we should run as web service or worker

# DigitalOcean App Platform behavior:
# - For web services: CMD is executed (this script runs normally)
# - For workers: run_command overrides CMD, but we still need to handle it
# 
# When CELERY_WORKER env var is set, we know we're a worker
# In that case, we should run celery directly

# Check if we should run as Celery worker
if [ -n "$CELERY_WORKER" ]; then
    echo "Starting as Celery worker (detected via CELERY_WORKER env var)..."
    # Run celery worker directly
    # DigitalOcean will pass run_command, but if not, use default
    if [ $# -gt 0 ]; then
        # Arguments were passed (from run_command)
        exec "$@"
    else
        # No arguments, use default celery command
        exec celery -A gistagum worker --loglevel=info --concurrency=2
    fi
fi

# Check if command arguments contain "celery" (fallback detection)
if [ $# -gt 0 ] && echo "$*" | grep -q "celery"; then
    echo "Starting as Celery worker (detected via command arguments)..."
    exec "$@"
fi

# Otherwise, run as web service
echo "Starting application as web service..."
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL environment variable is not set!"
    exit 1
fi

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn with optimized config..."
exec gunicorn gistagum.wsgi:application --config gunicorn_config.py
