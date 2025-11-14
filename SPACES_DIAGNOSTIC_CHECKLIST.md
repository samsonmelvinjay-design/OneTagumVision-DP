# 🔍 Spaces Upload Diagnostic Checklist

## Issue: Image URL is correct but file not in Spaces bucket

The URL `https://gistagum-media-2025.sgp1.cdn.digitaloceanspaces.com/project_images/...` is being generated, but the file isn't actually in Spaces.

---

## Step 1: Check App Logs ⚠️ CRITICAL

**In DigitalOcean App Platform:**
1. Go to your app → **Runtime Logs**
2. Look for these messages on startup:
   ```
   ✅ DigitalOcean Spaces configured for media storage
      Bucket: gistagum-media-2025
      Region: sgp1
      Endpoint: https://sgp1.digitaloceanspaces.com
      CDN Domain: gistagum-media-2025.sgp1.cdn.digitaloceanspaces.com
   ```

**If you DON'T see this message:**
- Spaces is NOT configured
- Check environment variables

**If you see a WARNING instead:**
- Environment variables are missing or incorrect

---

## Step 2: Verify Environment Variables

**In DigitalOcean App Platform → Settings → Environment Variables:**

Check these 7 variables are set:

1. ✅ `USE_SPACES=true` (lowercase!)
2. ✅ `AWS_ACCESS_KEY_ID=DO801ANXMNHPDR` (marked as SECRET)
3. ✅ `AWS_SECRET_ACCESS_KEY=20r/qqXoIhaatGUX6Se/10acUHJCrbJ8E9RF1a` (marked as SECRET)
4. ✅ `AWS_STORAGE_BUCKET_NAME=gistagum-media-2025`
5. ✅ `AWS_S3_ENDPOINT_URL=https://sgp1.digitaloceanspaces.com`
6. ✅ `AWS_S3_REGION_NAME=sgp1`
7. ✅ `AWS_S3_CUSTOM_DOMAIN=gistagum-media-2025.sgp1.cdn.digitaloceanspaces.com`

**Common Issues:**
- `USE_SPACES` is `True` or `1` instead of `true` (lowercase!)
- Missing quotes around values
- Access keys not marked as SECRET
- Typos in variable names

---

## Step 3: Check Deployment Status

1. Go to your app → **Activity** tab
2. Check if latest deployment completed successfully
3. If deployment failed, check the error logs

**If deployment is still in progress:**
- Wait for it to complete
- Then check logs again

---

## Step 4: Test Upload with Error Logging

When you upload an image, check the **Runtime Logs** for:
- Any error messages
- Upload failures
- Permission errors
- Connection errors

**Common errors:**
- `403 Forbidden` → Access keys don't have permission
- `404 Not Found` → Bucket name is wrong
- `Connection timeout` → Network issue
- `Invalid credentials` → Access keys are wrong

---

## Step 5: Verify Spaces Bucket Settings

**In DigitalOcean Spaces:**
1. Go to your Space → **Settings** tab
2. Check **File Listing**: Should be "Private" or "Public"
3. Check **CDN**: Should be "Enabled"
4. Check **CORS**: May need to configure if you get CORS errors

---

## Step 6: Test Direct Upload

Try uploading a file directly to Spaces:
1. Go to Spaces → `gistagum-media-2025` → **Files** tab
2. Click **Upload**
3. Upload a test image
4. If this works, the issue is with Django upload, not Spaces

---

## Most Likely Issues:

### Issue 1: Deployment Not Complete
**Solution:** Wait for deployment to finish, then try again

### Issue 2: Environment Variables Not Set
**Solution:** Double-check all 7 variables are set correctly

### Issue 3: USE_SPACES is not lowercase
**Solution:** Change `USE_SPACES=True` to `USE_SPACES=true`

### Issue 4: Access Keys Don't Have Permission
**Solution:** 
- Go to Spaces → Access Keys
- Check your key has "Read/Write/Delete" permissions
- If not, create a new key with full permissions

### Issue 5: Upload Happening Before Spaces Configured
**Solution:** Re-upload the image after Spaces is confirmed working

---

## Quick Test:

1. **Check logs** - Do you see the ✅ message?
2. **Check env vars** - Are all 7 set correctly?
3. **Check deployment** - Is it complete?
4. **Re-upload image** - Try uploading again

---

**Start with Step 1 (check logs) - that will tell us exactly what's wrong!**

