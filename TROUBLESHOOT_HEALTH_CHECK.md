# 🔍 Troubleshoot Health Check Error

## Error Analysis

```
ERROR failed health checks after 14 attempts with error 
Readiness probe failed: dial tcp 10.244.2.90:8080: connect: connection refused
```

**This means:**
- Health check is trying to connect to port 8080
- Nothing is listening on that port (connection refused)
- The app might not be starting, or it's crashing

## Possible Causes

### 1. App Not Starting
- Check if Gunicorn is actually starting
- Look for "Starting Gunicorn..." in logs
- Check for errors during startup

### 2. Database Connection Issue
- If `DATABASE_URL` is not set, the app exits before starting
- Check if migrations are running successfully

### 3. Port Mismatch
- DigitalOcean might be using port 8080 for health checks
- App should listen on `PORT` env var (auto-set by DigitalOcean)

## How to Debug

### Step 1: Check Runtime Logs
In DigitalOcean:
1. Go to your app → **Runtime Logs** tab
2. Look for:
   - "Starting application..."
   - "Running migrations..."
   - "Collecting static files..."
   - "Starting Gunicorn..."
   - Any ERROR messages

### Step 2: Check Build Logs
1. Go to **Deployments** tab
2. Click on the latest deployment
3. Check **Build Logs** for errors

### Step 3: Verify Environment Variables
1. Go to **Settings** → **Environment Variables**
2. Verify:
   - `DATABASE_URL` is set (and correct)
   - `DJANGO_SECRET_KEY` is set
   - `PORT` should be auto-set by DigitalOcean

### Step 4: Check Console
1. Go to **Console** tab
2. Try to connect:
   ```bash
   python manage.py dbshell
   ```
   This tests database connection

## Quick Fixes

### Fix 1: Verify DATABASE_URL
Make sure `DATABASE_URL` is set correctly in environment variables.

### Fix 2: Check if App Crashes
Look at runtime logs - if you see the app starting but then stopping, there's a crash.

### Fix 3: Test Health Endpoint Locally
The `/health/` endpoint should return "OK". If it doesn't, that's the issue.

## What I Fixed

✅ Added health check timing configuration:
- `initial_delay_seconds: 30` - Wait 30 seconds before checking
- `period_seconds: 10` - Check every 10 seconds
- `timeout_seconds: 5` - 5 second timeout
- `failure_threshold: 3` - Allow 3 failures before marking unhealthy

This gives the app more time to start before health checks begin.

## Next Steps

1. **Commit the fix:**
   ```powershell
   git add .do/app.yaml
   git commit -m "Fix health check timing"
   git push origin main
   ```

2. **Monitor the deployment:**
   - Watch Runtime Logs
   - Check if app starts successfully
   - Verify health checks pass

3. **If still failing:**
   - Share the Runtime Logs output
   - Check for specific error messages
   - Verify DATABASE_URL is correct

---

**Check your Runtime Logs to see what's happening during startup!** 🔍

