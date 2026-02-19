# ✅ How to Add REDIS_URL Correctly

## Method 1: Via DigitalOcean UI (Easiest) ⭐

### Step 1: Navigate to Your App
1. Go to **DigitalOcean Dashboard**
2. Click **"App Platform"** (left sidebar)
3. Click your app: **"one-tagumvision"**

### Step 2: Go to Settings
1. Click **"Settings"** tab (top menu)
2. Scroll down to **"Environment Variables"** section

### Step 3: Add the Variable
1. Click **"Edit"** button (right side of Environment Variables section)
2. Click **"Add Variable"** or **"+"** button
3. Fill in the form:

   **Key:**
   ```
   REDIS_URL
   ```
   - Must be exactly: `REDIS_URL` (all caps, underscore)
   - No spaces, no hyphens

   **Value:**
   ```
   redis://default:password@host:port
   ```
   - Paste your **complete connection string** from Valkey
   - Must start with `redis://`
   - Example: `redis://default:abc123@valkey-123.db.ondigitalocean.com:25061`

   **Type:**
   ```
   SECRET
   ```
   - Select **"SECRET"** from dropdown
   - This hides the value (important for security!)

   **Scope:**
   ```
   RUN_AND_BUILD_TIME
   ```
   - Select **"RUN_AND_BUILD_TIME"** from dropdown
   - App needs this during both build and runtime

4. Click **"Save"** button

### Step 4: Verify
- ✅ `REDIS_URL` appears in the list
- ✅ Type shows as **SECRET** (value hidden)
- ✅ Scope shows as **RUN_AND_BUILD_TIME**

---

## Method 2: Via .do/app.yaml File (Alternative)

If you prefer to manage via code, you can add it to `.do/app.yaml`:

### Step 1: Edit .do/app.yaml

Add this to the `envs` section (around line 50):

```yaml
  envs:
  - key: DJANGO_SETTINGS_MODULE
    scope: RUN_AND_BUILD_TIME
    value: gistagum.settings
  - key: DJANGO_SECRET_KEY
    scope: RUN_AND_BUILD_TIME
    type: SECRET
  - key: DEBUG
    scope: RUN_AND_BUILD_TIME
    value: "false"
  - key: ALLOWED_HOSTS
    scope: RUN_AND_BUILD_TIME
    value: '*.ondigitalocean.app'
  - key: CSRF_TRUSTED_ORIGINS
    scope: RUN_AND_BUILD_TIME
    value: https://*.ondigitalocean.app
  - key: DATABASE_URL
    scope: RUN_AND_BUILD_TIME
    value: ${gistagum-db.DATABASE_URL}
    type: SECRET
  - key: REDIS_URL                    # ← ADD THIS
    scope: RUN_AND_BUILD_TIME         # ← ADD THIS
    value: redis://default:password@host:port  # ← ADD THIS (your connection string)
    type: SECRET                      # ← ADD THIS
```

### Step 2: Get Connection String from Valkey

1. Go to **Databases** → Your Valkey database
2. Click **"Connection Details"** tab
3. Copy the **Connection String**
4. Replace `redis://default:password@host:port` with your actual string

### Step 3: Push to GitHub

```bash
git add .do/app.yaml
git commit -m "Add REDIS_URL environment variable"
git push origin main
```

**Note:** DigitalOcean will automatically deploy when you push!

---

## Where to Get Connection String

### From Valkey Database:

1. **Go to Databases** (left sidebar in DigitalOcean)
2. **Click your Valkey database**
3. **Click "Connection Details" tab**
4. **Copy the "Connection String"**
   - It looks like: `redis://default:password@host:port`
   - Copy the ENTIRE string

### Example Connection String:
```
redis://default:AVNS_abc123xyz@valkey-12345-abc.db.ondigitalocean.com:25061
```

---

## Important: Exact Format Required

### ✅ Correct Format:
```
Key: REDIS_URL
Value: redis://default:password@host:port
Type: SECRET
Scope: RUN_AND_BUILD_TIME
```

### ❌ Common Mistakes:
- Key: `redis_url` (lowercase) → ❌ Wrong
- Key: `REDIS-URL` (hyphen) → ❌ Wrong
- Type: `Plain Text` → ❌ Wrong (use SECRET)
- Scope: `RUN_TIME` → ❌ Wrong (use RUN_AND_BUILD_TIME)
- Value: Missing `redis://` → ❌ Wrong
- Value: Has spaces → ❌ Wrong

---

## After Adding REDIS_URL

### What Happens:

1. **Automatic Deployment**
   - DigitalOcean detects the new variable
   - Triggers new deployment automatically
   - Takes 2-5 minutes

2. **Check Status**
   - Go to **Deployments** tab
   - You'll see a new deployment starting
   - Wait for green checkmark ✅

3. **Verify It Works**
   - Go to **Runtime Logs** tab
   - Look for: No errors about Redis/Valkey
   - App should start normally

---

## Quick Checklist

Before saving, verify:
- [ ] Key is exactly: `REDIS_URL` (all caps)
- [ ] Value starts with: `redis://`
- [ ] Value is complete (no missing parts)
- [ ] Type is: `SECRET`
- [ ] Scope is: `RUN_AND_BUILD_TIME`
- [ ] No extra spaces
- [ ] Valkey database is "Online"

---

## Troubleshooting

### Problem: Can't find Environment Variables
**Solution:**
- Make sure you're in **Settings** tab
- Scroll down to find the section
- Look for "App-Level Environment Variables"

### Problem: Save button not working
**Solution:**
- Make sure all fields are filled
- Check for errors (red text)
- Try refreshing the page

### Problem: Deployment fails
**Solution:**
- Check **Runtime Logs** for errors
- Verify connection string format
- Make sure Valkey database is "Online"
- Check if connection string is accessible

---

## Recommendation

**Use Method 1 (UI)** - It's easier and you can see the result immediately!

**Steps:**
1. App → Settings → Environment Variables
2. Edit → Add Variable
3. Fill: `REDIS_URL`, connection string, SECRET, RUN_AND_BUILD_TIME
4. Save
5. Done! ✅

**Time:** ~2 minutes

