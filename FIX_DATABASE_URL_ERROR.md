# 🔧 Fix DATABASE_URL Error

## The Problem

Your app is failing to start because `DATABASE_URL` is not set. The error shows:
```
ERROR: DATABASE_URL environment variable is not set!
```

## Quick Fix: Set DATABASE_URL in DigitalOcean Dashboard

### Step 1: Get Your Database Connection String

1. **Go to DigitalOcean Dashboard**
2. **Click "Databases"** (left sidebar)
3. **Click on your PostgreSQL database** (`gistagum-db` or similar)
4. **Wait for it to be "Online"** (if still creating, wait 2-3 minutes)
5. **Click "Connection Details"** tab
6. **Copy the connection string**

It should look like:
```
postgresql://doadmin:PASSWORD@HOST:PORT/database?sslmode=require
```

### Step 2: Add DATABASE_URL to Your App

1. **Go to App Platform** → Your App → **Settings**
2. **Scroll to "Environment Variables"** section
3. **Find `DATABASE_URL`** (if it exists, click **Edit**; if not, click **Add Variable**)
4. **Set the values:**
   - **Key**: `DATABASE_URL`
   - **Value**: Paste your connection string from Step 1
   - **Type**: Select **"SECRET"** (important!)
   - **Scope**: Select **"RUN_AND_BUILD_TIME"**
5. **Click "Save"**
6. **Wait for automatic redeployment** (2-5 minutes)

### Step 3: Verify

1. **Go to "Runtime Logs"** tab
2. **Look for:**
   - ✅ "Starting application..."
   - ✅ "Running migrations..."
   - ✅ "Collecting static files..."
   - ✅ "Starting Gunicorn..."
3. **No more `DATABASE_URL` errors!**

---

## Alternative: Link Database in App Settings

If you want DigitalOcean to automatically set `DATABASE_URL`:

1. **Go to App Platform** → Your App → **Settings**
2. **Scroll to "Resource"** section
3. **Click "Link Resource"** or **"Add Resource"**
4. **Select your PostgreSQL database**
5. **DigitalOcean will automatically add `DATABASE_URL`**
6. **Save and redeploy**

---

## Why This Happened

The `.do/app.yaml` file has:
```yaml
- key: DATABASE_URL
  value: ${gistagum-db.DATABASE_URL}
```

This syntax only works if:
- The database is **linked** to the app in DigitalOcean
- The database name matches exactly (`gistagum-db`)

If the database isn't linked, the variable won't resolve, causing the error.

---

## After Fixing DATABASE_URL

Once `DATABASE_URL` is fixed, you can then:
1. **Set up Valkey** (if you want caching)
2. **Test your app** - it should start successfully

---

## Still Having Issues?

**Check:**
1. Database is **"Online"** (not "Creating")
2. Connection string is **correct** (no typos)
3. `DATABASE_URL` is set as **SECRET** type
4. App has **redeployed** after adding the variable

**Share:**
- Screenshot of Environment Variables section
- Any new error messages from Runtime Logs

