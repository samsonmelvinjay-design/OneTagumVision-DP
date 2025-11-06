# 🚀 Step-by-Step: Setting Up Valkey

## Current Step: Eviction Policy

You're on **Step 3: Eviction Policy**. Here's what to do:

### ✅ **Select: "allkeys-lru" (RECOMMENDED)**

**Why this one?**
- ✅ **Recommended** by DigitalOcean
- ✅ **Best for caching** - removes least recently used data
- ✅ **Prevents errors** - automatically manages memory
- ✅ **Perfect for your app** - cache can be regenerated

**What it does:**
- When memory is full, removes oldest cached data
- Your app continues working (no errors)
- Cache automatically refreshes when needed

### Action:
1. **Click the radio button** for **"allkeys-lru"** (it says "RECOMMENDED")
2. **Click "Continue"** button (blue button at bottom)

---

## Step 4: Connection Details

After clicking Continue, you'll see connection details.

### What to Do:
1. **Wait for database to finish creating** (2-3 minutes)
2. **Copy the connection string** - it looks like:
   ```
   redis://default:password@host:port
   ```
3. **Save it somewhere safe** (you'll need it next)

**Note:** The connection string might be shown as:
- **Connection String** (full URL)
- Or separate: **Host**, **Port**, **Password**

If separate, you'll need to construct it:
```
redis://default:PASSWORD@HOST:PORT
```

---

## Step 5: Add to Your App

### Step 5.1: Go to Your App Settings

1. Go to **DigitalOcean Dashboard**
2. Click **App Platform** (left sidebar)
3. Click on your app: **"one-tagumvision"** (or "gisonetagumvision")
4. Click **Settings** tab (top menu)

### Step 5.2: Add Environment Variable

1. Scroll down to **"Environment Variables"** section
2. Click **"Edit"** or **"Add Variable"** button
3. Add new variable:
   - **Key**: `REDIS_URL`
   - **Value**: (paste the connection string from Step 4)
   - **Type**: Select **"SECRET"** (important!)
   - **Scope**: Select **"RUN_AND_BUILD_TIME"**
4. Click **"Save"** or **"Add"**

### Step 5.3: Verify

You should now see:
- `REDIS_URL` in your environment variables list
- It should show as **SECRET** type (hidden value)

---

## Step 6: Deploy (Automatic!)

### What Happens:
1. DigitalOcean **automatically detects** the new environment variable
2. **Triggers a new deployment**
3. Your app will **restart** with Valkey support
4. Takes **2-5 minutes**

### How to Check:
1. Go to **App** → **Deployments** tab
2. You should see a new deployment starting
3. Wait for it to complete (green checkmark)

---

## Step 7: Verify It's Working

### Check Logs:
1. Go to **App** → **Runtime Logs** tab
2. Look for:
   - No errors about Redis/Valkey
   - App starting normally
   - Gunicorn workers booting

### Test Cache (Optional):
You can test if caching is working by:
1. Visit your dashboard
2. Visit it again immediately
3. Second visit should be faster (served from cache)

---

## Quick Reference

### Current Step (You're Here):
- ✅ **Select**: `allkeys-lru` (RECOMMENDED)
- ✅ **Click**: "Continue"

### Next Steps:
1. **Copy connection string** from Step 4
2. **Add REDIS_URL** to app environment variables
3. **Wait for deployment** (automatic)
4. **Done!** Your app now uses Valkey for caching

---

## Troubleshooting

### If Connection String Not Showing:
- Wait a few more minutes for database to fully create
- Refresh the page
- Check "Connection Details" tab

### If Environment Variable Not Saving:
- Make sure you selected **SECRET** type
- Check if you have permission to edit app settings
- Try refreshing the page

### If Deployment Fails:
- Check **Runtime Logs** for errors
- Verify `REDIS_URL` is set correctly
- Make sure connection string starts with `redis://`

---

## Summary

**Right Now:**
1. ✅ Select **"allkeys-lru"** (RECOMMENDED)
2. ✅ Click **"Continue"**

**Then:**
3. Copy connection string
4. Add `REDIS_URL` to app environment variables
5. Wait for automatic deployment
6. Enjoy faster app! 🚀

**Total Time:** ~10 minutes
**Cost:** $15/month
**Performance Gain:** 50-70% faster! ⚡

