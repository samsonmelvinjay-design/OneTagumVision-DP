# 🔧 Fix Worker Deployment Error - Non-Zero Exit Code

## The Problem

The worker component (`gisonetagumvision2`) is failing with:
- **Error**: "Deploy Error: Non-Zero Exit Code"
- **Cause**: Container exits immediately with error code

## Root Cause Analysis

When DigitalOcean App Platform uses a **Worker** component:
1. The `run_command` in `.do/app.yaml` should override the Dockerfile `CMD`
2. However, if `run_command` is not properly set or the command fails, it falls back to `CMD`
3. Our `CMD` runs the startup script which expects to be a web service
4. The startup script checks for `DATABASE_URL` and fails if not set (or other issues)

## Solution Options

### Option 1: Direct Celery Command (Recommended)

Make sure the worker's `run_command` directly calls Celery without going through the startup script:

**In `.do/app.yaml`:**
```yaml
- name: gisonetagumvision-worker
  run_command: celery -A gistagum worker --loglevel=info --concurrency=2
```

**Problem**: If `DATABASE_URL` is not set, Celery/Django might still fail during initialization.

### Option 2: Make Startup Script Worker-Aware

Update `start.sh` to handle workers better:

```bash
#!/bin/sh
# If CELERY_WORKER is set, run celery directly
if [ -n "$CELERY_WORKER" ]; then
    exec celery -A gistagum worker --loglevel=info --concurrency=2
fi
# ... rest of web service startup
```

### Option 3: Separate Dockerfile for Worker

Create a separate Dockerfile for workers, but this is more complex.

## Recommended Fix

**Use Option 1 + Ensure DATABASE_URL is Set**

1. Make sure `run_command` directly calls Celery
2. Ensure `DATABASE_URL` is set in worker environment variables
3. The worker needs DATABASE_URL for Django settings, even though it doesn't run migrations

## Check These Things

1. **Is DATABASE_URL set for the worker?**
   - Go to App → Settings → Worker Component → Environment Variables
   - Verify `DATABASE_URL` is set to `${gistagum-db.DATABASE_URL}`

2. **Is the run_command correct?**
   - Should be: `celery -A gistagum worker --loglevel=info --concurrency=2`
   - Should NOT include `/app/start.sh`

3. **Check Deploy Logs**
   - Look for the actual error message
   - Common errors:
     - "DATABASE_URL not set"
     - "ModuleNotFoundError: celery"
     - "No module named 'gistagum.celery'"

## Quick Fix Steps

1. **Verify `.do/app.yaml`** has correct `run_command`:
   ```yaml
   run_command: celery -A gistagum worker --loglevel=info --concurrency=2
   ```

2. **Verify worker has DATABASE_URL**:
   ```yaml
   - key: DATABASE_URL
     value: ${gistagum-db.DATABASE_URL}
     type: SECRET
   ```

3. **Push and redeploy**

4. **Check deploy logs** for the actual error message

