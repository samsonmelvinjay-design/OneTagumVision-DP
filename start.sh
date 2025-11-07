#!/bin/sh
# Startup script that detects if we should run as web service or worker

# DigitalOcean App Platform behavior:
# - For web services: CMD is executed (this script runs normally)
# - For workers: run_command should override CMD completely
# 
# However, if run_command is not properly set or fails, it falls back to CMD
# So we need to handle both cases

# Method 1: Check CELERY_WORKER environment variable
if [ -n "$CELERY_WORKER" ]; then
    echo "Starting as Celery worker (detected via CELERY_WORKER env var)..."
    # Check if DATABASE_URL is set (needed for Django settings)
    if [ -z "$DATABASE_URL" ]; then
        echo "WARNING: DATABASE_URL not set. Worker may fail to initialize Django."
    fi
    # Run celery worker - DigitalOcean should pass run_command, but if not, use default
    exec celery -A gistagum worker --loglevel=info --concurrency=2
fi

# Method 2: Check if command arguments contain "celery"
# This handles the case where DigitalOcean passes run_command as arguments
if [ $# -gt 0 ]; then
    # Check if any argument is "celery" or contains "celery"
    for arg in "$@"; do
        if echo "$arg" | grep -q "celery"; then
            echo "Starting as Celery worker (detected via command: $*)..."
            exec "$@"
        fi
    done
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
