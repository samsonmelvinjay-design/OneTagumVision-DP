# 🔧 Fix ALLOWED_HOSTS Error

## Problem
Your app is running, but getting:
```
DisallowedHost at /
Invalid HTTP_HOST header: 'onetagumvision-48sp6.ondigitalocean.app'
```

## Current Settings (Wrong)
- `ALLOWED_HOSTS`: `['localhost', '127.0.0.1', '0.0.0.0']`
- `DEBUG`: `True` (should be `False` in production)
- `CSRF_TRUSTED_ORIGINS`: `['http://localhost:8000', 'http://127.0.0.1:8000']`

## Your App URL
`onetagumvision-48sp6.ondigitalocean.app`

## Solution

### Option 1: Update Environment Variables in DigitalOcean (Recommended)

1. **Go to DigitalOcean Dashboard:**
   - Your App → **Settings** → **Environment Variables**

2. **Update `ALLOWED_HOSTS`:**
   - Find `ALLOWED_HOSTS`
   - Change value to: `onetagumvision-48sp6.ondigitalocean.app,*.ondigitalocean.app`
   - Or just: `*.ondigitalocean.app` (allows all DigitalOcean subdomains)

3. **Update `DEBUG`:**
   - Find `DEBUG`
   - Change value to: `false` (not `True`)

4. **Update `CSRF_TRUSTED_ORIGINS`:**
   - Find `CSRF_TRUSTED_ORIGINS`
   - Change value to: `https://onetagumvision-48sp6.ondigitalocean.app,https://*.ondigitalocean.app`
   - Or just: `https://*.ondigitalocean.app`

5. **Save** - App will auto-redeploy

### Option 2: Quick Fix - Add Your Specific Domain

**In DigitalOcean Environment Variables:**

```
ALLOWED_HOSTS=onetagumvision-48sp6.ondigitalocean.app,*.ondigitalocean.app
DEBUG=false
CSRF_TRUSTED_ORIGINS=https://onetagumvision-48sp6.ondigitalocean.app,https://*.ondigitalocean.app
```

## Why This Happened

The environment variables from `.do/app.yaml` might not have been applied, or the app is using default values from `settings.py`.

## After Fixing

1. ✅ App will redeploy automatically
2. ✅ Visit your app URL again
3. ✅ Should work now!

---

**Go to Settings → Environment Variables and update those 3 variables!** 🚀

