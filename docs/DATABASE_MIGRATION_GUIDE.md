# 🗄️ Database Migration Guide - Moving Your Database Online

This guide will help you migrate your local PostgreSQL database to a cloud database service.

## 📋 Current Database Setup

You currently have:
- **Local PostgreSQL database**: `gistagumnew` (on localhost)
- **SQL backup files**: `GISTAGUMDBNEW.sql`, `gistagumdb.sql`, etc.
- **SQLite file**: `db.sqlite3` (if you were using SQLite before)

---

## 🌐 Option 1: Render.com Database (Easiest - Already Configured!)

If you're deploying to Render, the database is **automatically created** by your `render.yaml` file!

### Steps:

1. **Deploy Your App to Render**
   - Follow the Render deployment steps in `DEPLOYMENT_GUIDE.md`
   - The database service will be created automatically

2. **Get Your Database Connection String**
   - In Render dashboard, go to your database service (`gistagum-db`)
   - Click "Connections" tab
   - Copy the "Internal Database URL" (for your app) or "External Connection String" (for local access)

3. **Migrate Your Data** (see "Migrating Your Data" section below)

---

## ☁️ Option 2: Neon (Free PostgreSQL - Recommended for Beginners)

Neon offers a **free tier** with 3GB storage - perfect for getting started!

### Steps:

1. **Sign Up for Neon**
   - Go to https://neon.tech
   - Sign up with GitHub (free)

2. **Create a New Project**
   - Click "Create Project"
   - Choose a name: `gistagum-production`
   - Select region closest to you
   - PostgreSQL version: 15 or 16 (both work)

3. **Get Your Connection String**
   - After creation, you'll see a connection string like:
     ```
     postgresql://username:password@ep-xxx-xxx.region.aws.neon.tech/dbname?sslmode=require
     ```
   - **Copy this connection string** - you'll need it!

4. **Add to Your Deployment Platform**
   - **Render**: Add as environment variable `DATABASE_URL`
   - **DigitalOcean**: Add as environment variable `DATABASE_URL`
   - **Railway**: Add as environment variable `DATABASE_URL`
   - **Heroku**: Run `heroku config:set DATABASE_URL=your-connection-string`

5. **Migrate Your Data** (see section below)

### Neon Pricing:
- **Free tier**: 3GB storage, 0.5GB RAM, perfect for small apps
- **Launch plan**: $19/month for more resources

---

## 🌊 Option 3: DigitalOcean Managed Database

If deploying to DigitalOcean, use their managed database.

### Steps:

1. **Create Database in DigitalOcean**
   - Go to your DigitalOcean dashboard
   - Click "Create" → "Databases" → "PostgreSQL"
   - Choose plan (Basic $15/month or Dev $7/month)
   - Select region
   - Choose database name: `gistagum`

2. **Get Connection String**
   - Go to your database → "Connection Details"
   - Copy the connection string or use the format:
     ```
     postgresql://username:password@host:port/dbname?sslmode=require
     ```

3. **Connect to Your App**
   - In your App Platform app, go to "Settings" → "Environment Variables"
   - Add `DATABASE_URL` with your connection string

4. **Migrate Your Data** (see section below)

---

## 🚂 Option 4: Railway Database

Railway provides databases that auto-connect to your app.

### Steps:

1. **Add Database to Railway Project**
   - In your Railway project, click "+ New"
   - Select "Database" → "PostgreSQL"
   - Railway automatically creates it

2. **Connection is Automatic**
   - Railway automatically sets `DATABASE_URL` for your app
   - No manual configuration needed!

3. **Get External Connection String** (for data migration)
   - Click on your database service
   - Go to "Connect" tab
   - Copy the connection string

4. **Migrate Your Data** (see section below)

---

## 🔄 Migrating Your Data to Cloud Database

You have several SQL backup files. Here's how to migrate your data:

### Method 1: Using pg_dump and psql (Recommended)

#### Step 1: Export from Local Database

```powershell
# Export your local database to a SQL file
pg_dump -h localhost -U postgres -d gistagumnew -F c -f gistagum_backup.dump

# OR export as SQL (if you prefer SQL format)
pg_dump -h localhost -U postgres -d gistagumnew > gistagum_backup.sql
```

#### Step 2: Import to Cloud Database

**Option A: Using psql command line**

```powershell
# For Neon, Railway, or any PostgreSQL
psql "postgresql://username:password@host:port/dbname?sslmode=require" < gistagum_backup.sql

# OR if you have the connection string in an environment variable
$env:DATABASE_URL = "your-connection-string-here"
psql $env:DATABASE_URL < gistagum_backup.sql
```

**Option B: Using pg_restore (for .dump files)**

```powershell
pg_restore -d "postgresql://username:password@host:port/dbname?sslmode=require" gistagum_backup.dump
```

### Method 2: Using Your Existing SQL Files

If you already have SQL backup files (`GISTAGUMDBNEW.sql`, `gistagumdb.sql`):

```powershell
# Connect and import
psql "your-cloud-database-connection-string" < GISTAGUMDBNEW.sql
```

### Method 3: Using Django Management Commands

This method exports/imports data in Django's format (preserves relationships better):

#### Step 1: Export from Local Database

```powershell
# Make sure you're connected to local database
python manage.py dumpdata --exclude auth.permission --exclude contenttypes > data_backup.json
```

#### Step 2: Import to Cloud Database

```powershell
# Set your cloud DATABASE_URL temporarily
$env:DATABASE_URL = "your-cloud-connection-string"
python manage.py loaddata data_backup.json
```

### Method 4: Using pgAdmin or DBeaver (GUI Method)

1. **Download pgAdmin** (https://www.pgadmin.org/) or **DBeaver** (https://dbeaver.io/)
2. **Connect to your local database**
3. **Export data** (right-click database → Backup)
4. **Connect to your cloud database**
5. **Import data** (right-click database → Restore)

---

## 🔧 Step-by-Step: Complete Migration Process

### For Render.com:

1. **Deploy your app** (database is auto-created)
2. **Get database connection string** from Render dashboard
3. **Export local data**:
   ```powershell
   pg_dump -h localhost -U postgres -d gistagumnew > local_backup.sql
   ```
4. **Import to Render database**:
   ```powershell
   psql "your-render-database-connection-string" < local_backup.sql
   ```
5. **Run migrations** (usually automatic, but verify):
   ```powershell
   # In Render shell or via CLI
   python manage.py migrate
   ```

### For Neon (or any external database):

1. **Create Neon database** (get connection string)
2. **Set DATABASE_URL** in your deployment platform
3. **Export local data**:
   ```powershell
   pg_dump -h localhost -U postgres -d gistagumnew > local_backup.sql
   ```
4. **Import to Neon**:
   ```powershell
   psql "your-neon-connection-string" < local_backup.sql
   ```
5. **Deploy your app** (it will connect to Neon automatically)

---

## 🧪 Testing Your Database Connection

Before migrating all your data, test the connection:

### Test Script (PowerShell):

```powershell
# test_cloud_db.ps1
$DATABASE_URL = "your-cloud-connection-string-here"

# Test connection
psql $DATABASE_URL -c "SELECT version();"

# Create a test table
psql $DATABASE_URL -c "CREATE TABLE test_connection (id SERIAL PRIMARY KEY, message TEXT);"

# Insert test data
psql $DATABASE_URL -c "INSERT INTO test_connection (message) VALUES ('Connection successful!');"

# Verify
psql $DATABASE_URL -c "SELECT * FROM test_connection;"

# Clean up
psql $DATABASE_URL -c "DROP TABLE test_connection;"
```

### Test with Django:

```powershell
# Set DATABASE_URL temporarily
$env:DATABASE_URL = "your-cloud-connection-string"
python manage.py dbshell

# In the database shell, try:
SELECT version();
\q
```

---

## 📊 Database Size Considerations

Check your local database size:

```powershell
# Check database size
psql -h localhost -U postgres -d gistagumnew -c "SELECT pg_size_pretty(pg_database_size('gistagumnew'));"
```

**Free tier limits:**
- **Neon Free**: 3GB storage
- **Railway Free**: Limited (check current limits)
- **Render Free**: Limited database size

If your database is larger, consider:
- Upgrading to a paid plan
- Cleaning up old data
- Using database-specific optimizations

---

## 🔒 Security Best Practices

1. **Never commit connection strings to Git**
   - Always use environment variables
   - Your `.gitignore` already excludes `.env` files ✅

2. **Use SSL connections**
   - Most cloud databases require `?sslmode=require` in connection string
   - This is usually included automatically

3. **Rotate passwords regularly**
   - Change database passwords periodically
   - Update `DATABASE_URL` in your deployment platform

4. **Restrict database access**
   - Only allow connections from your app's IP (if possible)
   - Use strong passwords

---

## 🐛 Troubleshooting

### Issue: "Connection refused" or "Timeout"
- Check if your database allows external connections
- Verify firewall rules
- Ensure connection string is correct

### Issue: "SSL required"
- Add `?sslmode=require` to your connection string
- Most cloud databases require SSL

### Issue: "Authentication failed"
- Verify username and password
- Check if user has proper permissions
- Some platforms create users automatically

### Issue: "Database does not exist"
- Create the database first (usually auto-created)
- Verify database name in connection string

### Issue: "Migration errors"
- Run `python manage.py migrate` on cloud database
- Check for conflicting migrations
- Verify Django version compatibility

---

## 📝 Quick Reference: Connection String Format

```
postgresql://[username]:[password]@[host]:[port]/[database]?sslmode=require
```

**Example:**
```
postgresql://gistagum_user:mySecurePass123@ep-cool-name-123456.us-east-2.aws.neon.tech/gistagum?sslmode=require
```

---

## ✅ Post-Migration Checklist

After migrating your database:

- [ ] Database connection works (test with `python manage.py dbshell`)
- [ ] All tables migrated successfully
- [ ] Data is present (check a few records)
- [ ] Django migrations are up to date (`python manage.py migrate`)
- [ ] Can create superuser (`python manage.py createsuperuser`)
- [ ] App connects to database successfully
- [ ] Test CRUD operations in your app
- [ ] Backup strategy is in place

---

## 🎯 Recommended Approach

**For beginners**: Use **Neon** (free tier, easy setup)
**For Render deployment**: Use **Render's built-in database** (already configured)
**For production**: Use **DigitalOcean Managed Database** or **Neon paid plan**

---

## 🚀 Next Steps

1. Choose a database provider (Neon is recommended for free tier)
2. Create your cloud database
3. Export your local database
4. Import to cloud database
5. Update `DATABASE_URL` in your deployment platform
6. Test the connection
7. Deploy your app!

Good luck! 🎉

