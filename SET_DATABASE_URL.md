# 🔗 Set DATABASE_URL in DigitalOcean App Platform

Your connection string:
```
postgresql://doadmin:AVNS_rPtuYR8ArkLXUmGotVs@tagumclusterdb-do-user-28669441-0.j.db.ondigitalocean.com:25060/defaultdb?sslmode=require
```

## 📋 Steps to Add DATABASE_URL

### Method 1: During App Creation (If Still Creating)

1. **In the app creation flow:**
   - When you see "Environment Variables" section
   - Find or add `DATABASE_URL`
   - Paste your connection string
   - Mark it as **SECRET** type
   - Continue with deployment

### Method 2: After App is Created (Recommended)

1. **Go to DigitalOcean Dashboard:**
   - Navigate to your app: `one-tagumvision`
   - Click on it to open

2. **Go to Settings:**
   - Click **"Settings"** tab (left sidebar)
   - Scroll down to **"Environment Variables"** section

3. **Add DATABASE_URL:**
   - Click **"Edit"** or **"Add Variable"** button
   - **Key**: `DATABASE_URL`
   - **Value**: Paste your connection string:
     ```
     postgresql://doadmin:AVNS_rPtuYR8ArkLXUmGotVs@tagumclusterdb-do-user-28669441-0.j.db.ondigitalocean.com:25060/defaultdb?sslmode=require
     ```
   - **Type**: Select **"SECRET"** (important for security!)
   - **Scope**: RUN_AND_BUILD_TIME (or just RUN_TIME)
   - Click **"Save"**

4. **Redeploy:**
   - DigitalOcean will automatically redeploy after saving
   - Or go to **"Deployments"** tab → **"Create Deployment"**

---

## ✅ Verify It's Set

1. **Check Environment Variables:**
   - Go to Settings → Environment Variables
   - You should see `DATABASE_URL` listed
   - It should show as "SECRET" type (value hidden)

2. **Check Runtime Logs:**
   - Go to **"Runtime Logs"** tab
   - Look for database connection messages
   - Should see successful connection

3. **Test in Console:**
   - Go to **"Console"** tab
   - Run: `python manage.py dbshell`
   - Should connect successfully

---

## 🔄 Alternative: Update .do/app.yaml

If you want the connection string in your config file (not recommended for secrets, but possible):

**Note:** Your `.do/app.yaml` currently uses `${gistagum-db.DATABASE_URL}` which auto-connects if the database is created through the app. Since you're using an existing database, you'll need to set it manually in the dashboard instead.

---

## 🎯 Quick Copy-Paste

Here's your connection string ready to paste:

```
postgresql://doadmin:AVNS_rPtuYR8ArkLXUmGotVs@tagumclusterdb-do-user-28669441-0.j.db.ondigitalocean.com:25060/defaultdb?sslmode=require
```

**Steps:**
1. Copy the string above
2. Go to App → Settings → Environment Variables
3. Add `DATABASE_URL` with the value above
4. Mark as SECRET
5. Save

---

## ⚠️ Important Notes

- **Keep it secret**: Never commit connection strings to Git
- **Use SECRET type**: This encrypts the value
- **Redeploy after adding**: App will restart with new variable
- **Test connection**: Verify it works after setting

---

**After setting DATABASE_URL, your app will automatically connect to the database!** 🚀

