# 🔗 Using Your Existing DigitalOcean Database

You have an existing database `tagumdb` that you want to use. Here's how to connect it to your app.

## ✅ Your Database Connection String

From your `setup_database.ps1`, your connection string is:

```
postgresql://doadmin:AVNS_TQ6zrWJ4RA10DtzCT9t@tagumdb-do-user-28669441-0.j.db.ondigitalocean.com:25060/defaultdb?sslmode=require
```

## 🚀 Steps to Connect Existing Database

### Option 1: During App Creation (Recommended)

1. **Go back to App Platform creation:**
   - Navigate back to your app creation flow
   - When you see "Add a database" screen
   - Click **"Skip"** or **"I'll add it later"** (don't create a new one)

2. **Continue with app deployment**
   - Set your `DJANGO_SECRET_KEY`
   - Complete the deployment

3. **After deployment, add DATABASE_URL:**
   - Go to your App → **Settings** → **Environment Variables**
   - Add new variable:
     - **Key**: `DATABASE_URL`
     - **Value**: `postgresql://doadmin:AVNS_TQ6zrWJ4RA10DtzCT9t@tagumdb-do-user-28669441-0.j.db.ondigitalocean.com:25060/defaultdb?sslmode=require`
     - **Type**: SECRET
   - Save

4. **Redeploy** (automatic after saving env vars)

### Option 2: Find Your Existing Database

1. **On the Databases page:**
   - Look for a list/view of existing databases
   - Your `tagumdb` should be listed there
   - Click on it to see details

2. **Get connection details:**
   - Go to **Connection Details** tab
   - Copy the connection string

3. **Use it in your app** (same as Option 1, step 3)

## 📝 Quick Setup Script

Run this to get your connection string ready:

```powershell
.\setup_database.ps1
```

This will copy your connection string to clipboard and show you where to paste it.

## ⚠️ Important Notes

- **Don't create a new database** - you already have one!
- **Use the existing `tagumdb`** database
- **Set `DATABASE_URL` manually** in environment variables
- The `.do/app.yaml` is already configured to not create a new database

## 🔄 After Connecting

Once `DATABASE_URL` is set:

1. **Migrate your local data:**
   ```powershell
   .\migrate_database_to_cloud.ps1
   ```
   - Choose option 3 (DigitalOcean)
   - Paste your connection string

2. **Run migrations:**
   - App → Console → `python manage.py migrate`

3. **Create superuser:**
   - App → Console → `python manage.py createsuperuser`

## ✅ That's It!

Your app will now use your existing `tagumdb` database!

