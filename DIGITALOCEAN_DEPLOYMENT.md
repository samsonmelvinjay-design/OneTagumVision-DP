# 🌊 Complete DigitalOcean Deployment Guide

This is your step-by-step guide to deploy GISTAGUM to DigitalOcean App Platform.

## 📋 Prerequisites

Before starting, make sure you have:

- [x] **GitHub account** with your code repository
- [x] **DigitalOcean account** (sign up at https://cloud.digitalocean.com)
- [x] **Local database** ready to migrate (you have: `gistagumnew`)
- [ ] **Generated secret key** (run `python generate_secret_key.py`)

---

## 🚀 Step-by-Step Deployment

### Step 1: Prepare Your Code

1. **Generate Django Secret Key**
   ```powershell
   python generate_secret_key.py
   ```
   **Copy the secret key** - you'll need it in Step 5!

2. **Commit and Push to GitHub**
   ```powershell
   git add .
   git commit -m "Ready for DigitalOcean deployment"
   git push origin main
   ```

3. **Verify Your Repository**
   - Make sure your code is on GitHub
   - Repository should be: `kennethkeeen/GISONETAGUMVISION`
   - Branch: `main`

---

### Step 2: Sign Up / Login to DigitalOcean

1. Go to https://cloud.digitalocean.com
2. Sign up (if new) or log in
3. You'll get $200 free credit for 60 days! 🎉

---

### Step 3: Create App from GitHub

1. **In DigitalOcean Dashboard:**
   - Click **"Create"** button (top right)
   - Select **"Apps"**

2. **Connect GitHub:**
   - Click **"GitHub"** tab
   - Authorize DigitalOcean to access your GitHub
   - Select repository: **`GISONETAGUMVISION`**
   - Select branch: **`main`**

3. **Choose Deployment Method:**
   - DigitalOcean will detect your `.do/app.yaml` file ✅
   - Click **"Edit Plan"** or **"Next"** to continue

---

### Step 4: Review App Configuration

Your `.do/app.yaml` file is already configured! Here's what it includes:

- ✅ **Database**: PostgreSQL (Dev Database - $7/month)
- ✅ **Service**: Docker-based deployment
- ✅ **Health Check**: `/health/` endpoint
- ✅ **Environment Variables**: Pre-configured
- ✅ **Media Storage**: 2GB volume for uploaded files

**You can customize:**
- **Region**: Currently `sgp` (Singapore) - change if needed
- **Instance Size**: Currently `apps-s-1vcpu-1gb` (Basic - $5/month)
- **Database Plan**: Currently `db-s-dev-database` ($7/month)

**Total Cost**: ~$12/month (App $5 + Database $7)

---

### Step 5: Set Secret Key

**IMPORTANT**: You need to set your `DJANGO_SECRET_KEY` manually!

1. **In the App Configuration screen:**
   - Scroll to **"Environment Variables"** section
   - Find `DJANGO_SECRET_KEY` (it will be marked as needing a value)
   - Click **"Edit"** or **"Set Value"**
   - Paste your secret key from Step 1
   - Make sure it's marked as **"SECRET"** (encrypted)

2. **Verify Other Variables:**
   - `DJANGO_SETTINGS_MODULE` = `gistagum.settings` ✅
   - `DEBUG` = `false` ✅
   - `ALLOWED_HOSTS` = `*.ondigitalocean.app` ✅
   - `CSRF_TRUSTED_ORIGINS` = `https://*.ondigitalocean.app` ✅
   - `DATABASE_URL` = Auto-set from database ✅

---

### Step 6: Review Resources

1. **App Service:**
   - Name: `gisonetagumvision`
   - Instance: Basic ($5/month)
   - Region: Singapore (or your choice)

2. **Database:**
   - Name: `gistagum-db`
   - Type: PostgreSQL 15
   - Plan: Dev Database ($7/month)

3. **Storage:**
   - Volume: `media-storage`
   - Size: 2GB
   - Mount: `/app/media`

---

### Step 7: Deploy!

1. **Review everything** one more time
2. Click **"Create Resources"** or **"Deploy"**
3. **Wait for deployment** (5-10 minutes)
   - DigitalOcean will:
     - Build your Docker image
     - Create the database
     - Set up networking
     - Deploy your app

4. **Watch the build logs:**
   - You'll see the build progress
   - Look for any errors (usually none!)

---

### Step 8: Get Your App URL

After deployment completes:

1. **Your app URL will be:**
   ```
   https://gisonetagumvision-xxxxx.ondigitalocean.app
   ```
   (The `xxxxx` is a unique identifier)

2. **Save this URL** - you'll need it!

---

### Step 9: Migrate Your Database

Your database is created, but it's empty! Let's migrate your data:

#### Option A: Using the Migration Script (Easiest)

1. **Get Database Connection String:**
   - In DigitalOcean dashboard → Your App → **"Resources"** tab
   - Click on **`gistagum-db`** database
   - Go to **"Connection Details"** tab
   - Copy the **"Connection String"** (looks like):
     ```
     postgresql://doadmin:password@host:port/dbname?sslmode=require
     ```

2. **Run Migration Script:**
   ```powershell
   .\migrate_database_to_cloud.ps1
   ```
   - Choose option **3** (DigitalOcean)
   - Paste your connection string when prompted
   - The script will export and import automatically!

#### Option B: Manual Migration

1. **Export Local Database:**
   ```powershell
   pg_dump -h localhost -U postgres -d gistagumnew > backup.sql
   ```

2. **Import to DigitalOcean:**
   ```powershell
   psql "your-digitalocean-connection-string" < backup.sql
   ```

3. **Test Connection:**
   ```powershell
   .\test_cloud_database.ps1
   ```

---

### Step 10: Run Django Migrations

1. **In DigitalOcean Dashboard:**
   - Go to your App → **"Runtime Logs"** tab
   - Check if migrations ran automatically (they should have!)

2. **If migrations didn't run, use Console:**
   - Go to your App → **"Console"** tab
   - Run:
     ```bash
     python manage.py migrate
     ```

---

### Step 11: Create Superuser

1. **In DigitalOcean Dashboard:**
   - Go to your App → **"Console"** tab
   - Run:
     ```bash
     python manage.py createsuperuser
     ```
   - Enter username, email, and password

---

### Step 12: Test Your App!

1. **Visit your app URL:**
   ```
   https://gisonetagumvision-xxxxx.ondigitalocean.app
   ```

2. **Test these:**
   - [ ] App loads successfully
   - [ ] Can login with superuser
   - [ ] Admin panel works (`/admin/`)
   - [ ] Dashboard loads (`/dashboard/`)
   - [ ] Map view works (`/dashboard/map/`)
   - [ ] Media files upload correctly
   - [ ] Static files (CSS/JS) load

---

## 🔧 Post-Deployment Configuration

### Update Domain (If You Have One)

If you have a custom domain:

1. **In DigitalOcean Dashboard:**
   - Go to your App → **"Settings"** → **"Domains"**
   - Add your domain
   - Follow DNS configuration instructions

2. **Update Environment Variables:**
   - Go to **"Settings"** → **"Environment Variables"**
   - Update `ALLOWED_HOSTS`:
     ```
     *.ondigitalocean.app,yourdomain.com,www.yourdomain.com
     ```
   - Update `CSRF_TRUSTED_ORIGINS`:
     ```
     https://*.ondigitalocean.app,https://yourdomain.com,https://www.yourdomain.com
     ```

3. **Redeploy** (automatic after saving)

---

## 📊 Monitoring & Logs

### View Logs:
- **Runtime Logs**: App → "Runtime Logs" tab
- **Build Logs**: App → "Deployments" → Click deployment → "Build Logs"

### Monitor Performance:
- **Metrics**: App → "Metrics" tab
- **Database**: Database → "Metrics" tab

---

## 🔄 Updating Your App

### Automatic Updates (Recommended):
- Your `.do/app.yaml` has `deploy_on_push: true`
- **Just push to GitHub:**
  ```powershell
  git add .
  git commit -m "Update app"
  git push origin main
  ```
- DigitalOcean will automatically redeploy!

### Manual Updates:
- Go to App → "Deployments" → "Create Deployment"
- Select branch/commit to deploy

---

## 🗄️ Database Management

### Access Database:
1. **Via Console:**
   - App → "Console" → `python manage.py dbshell`

2. **Via External Tool:**
   - Database → "Connection Details"
   - Use pgAdmin, DBeaver, or any PostgreSQL client

### Backup Database:
```powershell
# Export from DigitalOcean
pg_dump "your-connection-string" > backup.sql
```

### Restore Database:
```powershell
# Import to DigitalOcean
psql "your-connection-string" < backup.sql
```

---

## 🐛 Troubleshooting

### Issue: App won't start
- **Check logs**: App → "Runtime Logs"
- **Common causes:**
  - Missing `DJANGO_SECRET_KEY`
  - Database connection failed
  - Build errors

### Issue: Database connection errors
- **Verify `DATABASE_URL`** is set correctly
- **Check database** is running (Database → "Overview")
- **Test connection**: Use `test_cloud_database.ps1`

### Issue: Static files not loading
- **Check build logs** for `collectstatic` errors
- **Verify** `STATIC_ROOT` and `STATIC_URL` in settings
- **Check** WhiteNoise is configured

### Issue: Media files not saving
- **Verify volume** is mounted: App → "Settings" → "Components"
- **Check** `MEDIA_ROOT` path is `/app/media`
- **Verify** volume size is sufficient

### Issue: 502 Bad Gateway
- **Check health endpoint**: `https://your-app.ondigitalocean.app/health/`
- **Review logs** for application errors
- **Verify** database is accessible

---

## 💰 Cost Breakdown

**Monthly Costs:**
- **App Service** (Basic): $5/month
- **PostgreSQL Database** (Dev): $7/month
- **Storage** (2GB): ~$0.20/month
- **Total**: ~$12.20/month

**Free Credits:**
- New accounts get $200 free credit (60 days)
- Enough for ~16 months of free hosting! 🎉

---

## ✅ Deployment Checklist

Use this to track your progress:

- [ ] Generated Django secret key
- [ ] Code pushed to GitHub
- [ ] DigitalOcean account created
- [ ] App created from GitHub
- [ ] Secret key set in environment variables
- [ ] App deployed successfully
- [ ] Database connection string obtained
- [ ] Local database migrated to cloud
- [ ] Django migrations ran
- [ ] Superuser created
- [ ] App tested and working
- [ ] Custom domain configured (optional)

---

## 🎉 You're Done!

Your app is now live on DigitalOcean! 

**Next Steps:**
- Share your app URL with users
- Set up monitoring/alerts
- Configure backups
- Scale resources as needed

**Need Help?**
- Check DigitalOcean docs: https://docs.digitalocean.com/products/app-platform/
- Review logs for errors
- See `DEPLOYMENT_GUIDE.md` for general deployment info

---

## 📝 Quick Reference

**App URL Format:**
```
https://gisonetagumvision-xxxxx.ondigitalocean.app
```

**Database Connection:**
- Get from: App → Resources → Database → Connection Details

**Environment Variables:**
- Location: App → Settings → Environment Variables

**Logs:**
- Runtime: App → Runtime Logs
- Build: App → Deployments → Build Logs

**Console Access:**
- App → Console tab

**Redeploy:**
- Push to GitHub (auto) or App → Deployments → Create Deployment

---

Good luck with your deployment! 🚀

