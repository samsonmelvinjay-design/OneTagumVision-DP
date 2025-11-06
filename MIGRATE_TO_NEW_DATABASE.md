# 🗄️ Create New Database & Migrate Data

This guide will help you create a new DigitalOcean database and import your local database.

## 📋 Steps

### Step 1: Create New Database in DigitalOcean

1. **On the "Managed Databases" page:**
   - Click **"Create Database Cluster"** (the blue button)
   - OR click **"PostgreSQL"** → **"Create →"**

2. **Configure Database:**
   - **Database Engine**: PostgreSQL
   - **Version**: 15 (recommended, matches your config)
   - **Datacenter Region**: Choose closest to you (Singapore `sgp` is in your config)
   - **Plan**: 
     - **Dev Database** ($7/month) - Good for development
     - **Basic** ($15/month) - Better for production
   - **Database Name**: `gistagum` (or leave default)
   - **Project**: Select your project

3. **Click "Create Database Cluster"**
   - Wait 2-3 minutes for database to be created

---

### Step 2: Get Database Connection String

After database is created:

1. **Click on your new database** in the list
2. **Go to "Connection Details" tab**
3. **Copy the "Connection String"** (looks like):
   ```
   postgresql://doadmin:password@host:port/dbname?sslmode=require
   ```
4. **Save this connection string** - you'll need it!

---

### Step 3: Export Your Local Database

Run this command to export your local database:

```powershell
# Export local database
pg_dump -h localhost -U postgres -d gistagumnew -F p -f local_backup.sql
```

**Or use the migration script:**

```powershell
.\migrate_database_to_cloud.ps1
```

When prompted:
- Choose option **3** (DigitalOcean)
- Paste your NEW database connection string
- The script will export and import automatically!

---

### Step 4: Import to New DigitalOcean Database

**Option A: Using Migration Script (Easiest)**

```powershell
.\migrate_database_to_cloud.ps1
```
- Choose option 3 (DigitalOcean)
- Paste your NEW database connection string
- Script handles everything!

**Option B: Manual Import**

```powershell
# Import to new database
psql "your-new-digitalocean-connection-string" < local_backup.sql
```

---

### Step 5: Verify Import

Test the connection:

```powershell
.\test_cloud_database.ps1
```

Paste your new database connection string when prompted.

---

### Step 6: Connect Database to Your App

Your `.do/app.yaml` is already configured to automatically connect the new database!

**The database will be:**
- Automatically created during app deployment
- Automatically connected via `DATABASE_URL`
- Ready to use!

**If you need to set it manually:**

1. Go to your App → **Settings** → **Environment Variables**
2. Find `DATABASE_URL` (should be auto-set)
3. If not, add it with your connection string
4. Mark as **SECRET** type

---

## ✅ After Migration

1. **Run Django migrations:**
   ```bash
   python manage.py migrate
   ```
   (This runs automatically during deployment)

2. **Create superuser:**
   ```bash
   python manage.py createsuperuser
   ```
   (Do this in App Console after deployment)

3. **Test your app!**

---

## 🎯 Quick Summary

1. ✅ Create new PostgreSQL database in DigitalOcean
2. ✅ Get connection string
3. ✅ Export local database: `pg_dump ... > backup.sql`
4. ✅ Import to new database: `psql "connection-string" < backup.sql`
5. ✅ Deploy app (database auto-connects via `.do/app.yaml`)
6. ✅ Create superuser and test!

---

## 💡 Pro Tips

- **Database name**: Use `gistagum` or `defaultdb` (DigitalOcean default)
- **Version**: PostgreSQL 15 matches your config
- **Plan**: Dev Database ($7/month) is fine for now
- **Region**: Choose closest to your users

---

**Ready? Start with Step 1 - Create the database!** 🚀

