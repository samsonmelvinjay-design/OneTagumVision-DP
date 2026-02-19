# 🔧 Fix 400 Bad Request Error

## Problem
You're seeing "Bad Request (400)" which means Django is still rejecting the request.

## Common Causes

### 1. Environment Variables Not Applied
- Variables were updated but app hasn't redeployed
- Variables have wrong format
- Variables not saved properly

### 2. ALLOWED_HOSTS Still Wrong
- Missing your specific domain
- Has extra spaces or quotes
- Not split correctly

### 3. CSRF_TRUSTED_ORIGINS Missing
- Not set at all
- Missing `https://` prefix
- Wrong format

## Step-by-Step Fix

### Step 1: Verify Environment Variables

Go to DigitalOcean → Your App → Settings → Environment Variables

**Check these exist and have correct values:**

1. **ALLOWED_HOSTS**
   - Value should be: `onetagumvision-48sp6.ondigitalocean.app,*.ondigitalocean.app`
   - NO quotes around the value
   - NO spaces after commas (or minimal spaces)
   - Scope: RUN_AND_BUILD_TIME

2. **DEBUG**
   - Value should be: `false`
   - Lowercase, no quotes
   - Scope: RUN_AND_BUILD_TIME

3. **CSRF_TRUSTED_ORIGINS**
   - Value should be: `https://onetagumvision-48sp6.ondigitalocean.app,https://*.ondigitalocean.app`
   - Must start with `https://`
   - NO quotes around the value
   - Scope: RUN_AND_BUILD_TIME

### Step 2: Force Redeploy

After updating variables:
1. Go to **Deployments** tab
2. Click **"Create Deployment"**
3. Select **"Latest Commit"** or **"main"** branch
4. Click **"Create Deployment"**
5. Wait for deployment to complete

### Step 3: Check Deployment Logs

After redeploy:
1. Go to **Activity** tab
2. Click on the new deployment
3. Check **Deploy Logs**
4. Look for any errors

## Alternative: Update .do/app.yaml

If environment variables aren't working, update the config file:

```yaml
envs:
  - key: ALLOWED_HOSTS
    scope: RUN_AND_BUILD_TIME
    value: 'onetagumvision-48sp6.ondigitalocean.app,*.ondigitalocean.app'
  - key: DEBUG
    scope: RUN_AND_BUILD_TIME
    value: "false"
  - key: CSRF_TRUSTED_ORIGINS
    scope: RUN_AND_BUILD_TIME
    value: 'https://onetagumvision-48sp6.ondigitalocean.app,https://*.ondigitalocean.app'
```

Then commit and push:
```powershell
git add .do/app.yaml
git commit -m "Fix ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS"
git push origin main
```

## Quick Test

After redeploy, test the health endpoint:
```
https://onetagumvision-48sp6.ondigitalocean.app/health/
```

This should return "OK" if the app is working.

## Debug Steps

1. **Check if variables are set:**
   - Go to Console tab
   - Run: `echo $ALLOWED_HOSTS`
   - Should show your domain

2. **Check Django settings:**
   - Console tab: `python manage.py shell`
   - Run: `from django.conf import settings; print(settings.ALLOWED_HOSTS)`
   - Should show your domain in the list

---

**Most likely: Variables are set but app needs to be redeployed!** 🔄

