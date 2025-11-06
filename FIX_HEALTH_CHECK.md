# 🔧 Fix Health Check Error

## Problem
Health checks are failing with:
```
Readiness probe failed: dial tcp 10.244.2.90:8080: connect: connection refused
```

## Root Cause
- DigitalOcean is trying to check port **8080**
- Your app is running on port **8000** (or PORT env var)
- The app might not be starting fast enough
- Health check might be happening before the app is ready

## Solutions Applied

### 1. Updated Health Check Configuration
Added health check settings to `.do/app.yaml`:
- `initial_delay_seconds: 30` - Wait 30 seconds before first check
- `period_seconds: 10` - Check every 10 seconds
- `timeout_seconds: 5` - Timeout after 5 seconds
- `success_threshold: 1` - Need 1 success to mark healthy
- `failure_threshold: 3` - Need 3 failures to mark unhealthy

### 2. Verify PORT Environment Variable
DigitalOcean should automatically set `PORT` environment variable. Your Dockerfile uses:
```bash
gunicorn ... --bind 0.0.0.0:${PORT:-8000}
```
This means it will use the `PORT` env var if set, or default to 8000.

## Additional Checks

### Check 1: Verify App is Starting
Look at the runtime logs to see if:
- Migrations are running
- Static files are being collected
- Gunicorn is starting

### Check 2: Verify PORT is Set
In DigitalOcean:
1. Go to your app → Settings → Environment Variables
2. Check if `PORT` is set (it should be auto-set by DigitalOcean)
3. If not, you might need to add it (though it should be automatic)

### Check 3: Check Runtime Logs
Look for:
- "Starting Gunicorn..." message
- Any errors during startup
- Database connection issues

## Manual Fix (If Needed)

If the issue persists, you can:

1. **Add PORT explicitly** (though it should be automatic):
   ```yaml
   envs:
   - key: PORT
     scope: RUN_TIME
     value: "8000"
   ```

2. **Check if app is actually running**:
   - Go to Runtime Logs
   - Look for "Starting Gunicorn..." message
   - Check for any errors

3. **Increase initial delay** (already done in the fix above)

## Next Steps

1. ✅ Health check config updated
2. Commit and push:
   ```powershell
   git add .do/app.yaml
   git commit -m "Fix health check configuration"
   git push origin main
   ```
3. DigitalOcean will auto-redeploy
4. Monitor the deployment logs

## Expected Behavior

After the fix:
- App starts and runs migrations
- Waits 30 seconds before first health check
- Health checks run every 10 seconds
- Should pass after app is ready

---

**The health check should work now!** 🚀

