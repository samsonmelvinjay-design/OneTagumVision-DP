# 🚀 GISTAGUM Deployment Guide

This guide will help you deploy your Django application to various cloud platforms.

## 📋 Pre-Deployment Checklist

Before deploying, ensure you have:

- [ ] A Git repository (GitHub, GitLab, or Bitbucket)
- [ ] Your code pushed to the repository
- [ ] **A PostgreSQL database** (see `DATABASE_MIGRATION_GUIDE.md` for setup)
- [ ] **Migrated your local database to cloud** (see `DATABASE_MIGRATION_GUIDE.md`)
- [ ] Generated a new Django secret key for production
- [ ] Reviewed and updated environment variables

> **📌 IMPORTANT**: Your database needs to be online too! See `DATABASE_MIGRATION_GUIDE.md` for complete database setup instructions.

## 🔑 Generate Django Secret Key

Run this command locally to generate a secure secret key:

```bash
python manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Save this key** - you'll need it for all deployment platforms.

---

## 🌐 Option 1: Deploy to Render.com (Easiest)

Render.com is the easiest option since you already have a `render.yaml` file configured.

### Steps:

1. **Sign up/Login to Render**
   - Go to https://render.com
   - Sign up or log in with GitHub

2. **Create a New Blueprint**
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will automatically detect `render.yaml`

3. **Configure Environment Variables**
   - After the blueprint is created, go to your web service
   - Navigate to "Environment" tab
   - Add/update these variables:
     ```
     DJANGO_SECRET_KEY=<your-generated-secret-key>
     DEBUG=false
     ALLOWED_HOSTS=gistagum-web.onrender.com
     CSRF_TRUSTED_ORIGINS=https://gistagum-web.onrender.com
     ```
   - The `DATABASE_URL` will be automatically set from the database service

4. **Deploy**
   - Render will automatically deploy when you push to your main branch
   - Or click "Manual Deploy" → "Deploy latest commit"

5. **Access Your App**
   - Your app will be available at: `https://gistagum-web.onrender.com`
   - Update `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` with your actual URL

### Render.com Pricing:
- **Free tier**: Web service sleeps after 15 min inactivity, database limited
- **Starter plan**: $7/month for always-on web service + $7/month for database

---

## 🌊 Option 2: Deploy to DigitalOcean App Platform

### Steps:

1. **Sign up/Login to DigitalOcean**
   - Go to https://cloud.digitalocean.com
   - Sign up or log in

2. **Create App**
   - Click "Create" → "Apps"
   - Connect your GitHub repository
   - Select the repository and branch

3. **Configure App**
   - **Build Command**: (leave empty, Docker handles it)
   - **Run Command**: (leave empty, Docker handles it)
   - **Dockerfile Path**: `./Dockerfile`
   - **Environment**: Docker

4. **Add PostgreSQL Database**
   - Click "Add Resource" → "Database" → "PostgreSQL"
   - Choose a plan (Basic $15/month or Dev Database $7/month)

5. **Set Environment Variables**
   - Go to "Settings" → "Environment Variables"
   - Add these variables (see `ENV_VARS_FOR_DO.txt` for reference):
     ```
     DJANGO_SETTINGS_MODULE=gistagum.settings
     DJANGO_SECRET_KEY=<your-generated-secret-key>
     DEBUG=false
     ALLOWED_HOSTS=*.ondigitalocean.app
     CSRF_TRUSTED_ORIGINS=https://*.ondigitalocean.app
     DATABASE_URL=<auto-populated-from-database>
     ```

6. **Add Persistent Storage (for media files)**
   - Go to "Settings" → "Components"
   - Add a volume mount:
     - **Mount Path**: `/app/media`
     - **Size**: 2GB (or as needed)

7. **Deploy**
   - Click "Create Resources"
   - DigitalOcean will build and deploy your app

### DigitalOcean Pricing:
- **Basic App**: $5/month
- **PostgreSQL Database**: $7-15/month
- **Storage**: $0.10/GB/month

---

## 🚂 Option 3: Deploy to Railway

Railway is another great option with a simple setup.

### Steps:

1. **Sign up/Login to Railway**
   - Go to https://railway.app
   - Sign up with GitHub

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

3. **Add PostgreSQL Database**
   - Click "+ New" → "Database" → "PostgreSQL"
   - Railway will automatically create it

4. **Configure Environment Variables**
   - Click on your web service → "Variables"
   - Add:
     ```
     DJANGO_SECRET_KEY=<your-generated-secret-key>
     DEBUG=false
     ALLOWED_HOSTS=*.railway.app
     CSRF_TRUSTED_ORIGINS=https://*.railway.app
     ```
   - `DATABASE_URL` is automatically set by Railway

5. **Deploy**
   - Railway auto-deploys on git push
   - Or click "Deploy" manually

### Railway Pricing:
- **Hobby Plan**: $5/month + usage-based pricing
- **Database**: Included in plan

---

## ☁️ Option 4: Deploy to Heroku

### Steps:

1. **Install Heroku CLI**
   - Download from https://devcenter.heroku.com/articles/heroku-cli

2. **Login to Heroku**
   ```bash
   heroku login
   ```

3. **Create Heroku App**
   ```bash
   heroku create your-app-name
   ```

4. **Add PostgreSQL Database**
   ```bash
   heroku addons:create heroku-postgresql:mini
   ```

5. **Set Environment Variables**
   ```bash
   heroku config:set DJANGO_SECRET_KEY=<your-generated-secret-key>
   heroku config:set DEBUG=false
   heroku config:set ALLOWED_HOSTS=your-app-name.herokuapp.com
   heroku config:set CSRF_TRUSTED_ORIGINS=https://your-app-name.herokuapp.com
   ```

6. **Deploy**
   ```bash
   git push heroku main
   ```

7. **Run Migrations**
   ```bash
   heroku run python manage.py migrate
   heroku run python manage.py createsuperuser
   ```

### Heroku Pricing:
- **Eco Dyno**: $5/month (sleeps after 30 min inactivity)
- **Basic Dyno**: $7/month (always on)
- **PostgreSQL**: $5/month (mini plan)

---

## 🔧 Post-Deployment Steps

After deploying to any platform:

1. **Run Database Migrations**
   - Most platforms run migrations automatically via the Dockerfile
   - If not, run: `python manage.py migrate`

2. **Create Superuser**
   - Access your app's console/terminal
   - Run: `python manage.py createsuperuser`

3. **Collect Static Files**
   - Usually handled automatically by the Dockerfile
   - If needed: `python manage.py collectstatic --noinput`

4. **Test Your Application**
   - Visit your deployed URL
   - Test login/logout
   - Verify media files are working
   - Check admin panel

5. **Set Up Custom Domain (Optional)**
   - In your platform's settings, add a custom domain
   - Update `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` with your domain
   - Configure DNS records as instructed by the platform

---

## 🗄️ Database Setup & Migration

**Your database needs to be online too!** See the complete guide: `DATABASE_MIGRATION_GUIDE.md`

### Quick Database Options:

1. **Render.com**: Database is auto-created from `render.yaml` ✅
2. **Neon** (Recommended): Free tier, easy setup - https://neon.tech
3. **Platform-provided**: DigitalOcean, Railway, Heroku all provide databases

### Quick Migration Steps:

1. **Create cloud database** (see `DATABASE_MIGRATION_GUIDE.md`)
2. **Export local database**:
   ```powershell
   # Use the migration script
   .\migrate_database_to_cloud.ps1
   
   # OR manually:
   pg_dump -h localhost -U postgres -d gistagumnew > backup.sql
   ```

3. **Import to cloud**:
   ```powershell
   psql "your-cloud-connection-string" < backup.sql
   ```

4. **Test connection**:
   ```powershell
   .\test_cloud_database.ps1
   ```

5. **Add DATABASE_URL** to your deployment platform

For detailed instructions, see `DATABASE_MIGRATION_GUIDE.md`

---

## 📁 Media Files Storage

Your app uses local media storage. For production, consider:

### Option 1: Platform Storage (Current Setup)
- Render: Uses disk mounts (configured in `render.yaml`)
- DigitalOcean: Use volume mounts
- Railway: Use volume mounts

### Option 2: Cloud Storage (Recommended for Scale)
Consider migrating to:
- **AWS S3** with `django-storages`
- **Cloudinary** for images
- **DigitalOcean Spaces**

---

## 🔒 Security Checklist

- [x] `DEBUG=False` in production
- [x] Strong `DJANGO_SECRET_KEY` generated
- [x] `ALLOWED_HOSTS` configured
- [x] `CSRF_TRUSTED_ORIGINS` configured
- [x] HTTPS enabled (automatic on most platforms)
- [x] Database credentials secured via environment variables
- [ ] Set up proper backup strategy for database
- [ ] Configure error monitoring (Sentry, etc.)

---

## 🐛 Troubleshooting

### Issue: Static files not loading
- Ensure `collectstatic` ran successfully
- Check `STATIC_ROOT` and `STATIC_URL` settings
- Verify WhiteNoise is configured correctly

### Issue: Database connection errors
- Verify `DATABASE_URL` is set correctly
- Check database is accessible from your app
- Ensure database credentials are correct

### Issue: Media files not accessible
- Check volume mounts are configured
- Verify `MEDIA_ROOT` and `MEDIA_URL` settings
- Ensure file permissions are correct

### Issue: GDAL errors
- The Dockerfile includes GDAL installation
- If issues persist, check GDAL version compatibility

---

## 📞 Need Help?

- Check platform-specific documentation
- Review Django deployment checklist: https://docs.djangoproject.com/en/stable/howto/deployment/checklist/
- Check your platform's logs for error messages

---

## 🎯 Recommended Platform

**For beginners**: **Render.com** (easiest setup, already configured)
**For production**: **DigitalOcean App Platform** (better performance, more control)
**For quick testing**: **Railway** (fastest deployment)

Good luck with your deployment! 🚀

