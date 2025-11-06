# ✅ Quick Deployment Checklist

Use this checklist to ensure you're ready to deploy.

## Before You Start

- [ ] Code is committed and pushed to Git repository (GitHub/GitLab/Bitbucket)
- [ ] Generated a new Django secret key (run: `python manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- [ ] Reviewed `DEPLOYMENT_GUIDE.md` and chosen a platform

## Platform Setup

### If using Render.com:
- [ ] Created Render account and connected GitHub
- [ ] Created Blueprint from `render.yaml`
- [ ] Verified database service is created
- [ ] Set environment variables:
  - [ ] `DJANGO_SECRET_KEY`
  - [ ] `DEBUG=false`
  - [ ] `ALLOWED_HOSTS` (with your Render URL)
  - [ ] `CSRF_TRUSTED_ORIGINS` (with your Render URL)
- [ ] Verified `DATABASE_URL` is auto-set from database service

### If using DigitalOcean:
- [ ] Created DigitalOcean account
- [ ] Created App from GitHub repository
- [ ] Added PostgreSQL database
- [ ] Set environment variables (see `ENV_VARS_FOR_DO.txt`)
- [ ] Added volume mount for `/app/media` (2GB minimum)

### If using Railway:
- [ ] Created Railway account
- [ ] Created project from GitHub
- [ ] Added PostgreSQL database
- [ ] Set environment variables
- [ ] Verified `DATABASE_URL` is auto-set

### If using Heroku:
- [ ] Installed Heroku CLI
- [ ] Created Heroku app
- [ ] Added PostgreSQL addon
- [ ] Set all environment variables via CLI

## Post-Deployment

- [ ] App is accessible at the provided URL
- [ ] Database migrations ran successfully (check logs)
- [ ] Created superuser account (`python manage.py createsuperuser`)
- [ ] Tested login/logout functionality
- [ ] Verified static files are loading (CSS, JS, images)
- [ ] Tested media file uploads (if applicable)
- [ ] Checked admin panel is accessible
- [ ] Verified map/geospatial features are working
- [ ] Tested main application features

## Security

- [ ] `DEBUG=False` in production
- [ ] Strong secret key is set (not the default)
- [ ] `ALLOWED_HOSTS` includes your domain
- [ ] `CSRF_TRUSTED_ORIGINS` includes your HTTPS URL
- [ ] Database credentials are secure (not hardcoded)
- [ ] HTTPS is enabled (automatic on most platforms)

## Optional Enhancements

- [ ] Set up custom domain
- [ ] Configured error monitoring (Sentry, etc.)
- [ ] Set up database backups
- [ ] Configured email settings (for password resets, etc.)
- [ ] Set up CI/CD for automatic deployments
- [ ] Migrated media files to cloud storage (S3, etc.)

## Troubleshooting

If something doesn't work:
1. Check platform logs for errors
2. Verify all environment variables are set correctly
3. Ensure database is accessible
4. Check that migrations ran successfully
5. Verify static files were collected
6. Review `DEPLOYMENT_GUIDE.md` troubleshooting section

---

**Ready to deploy?** Follow the steps in `DEPLOYMENT_GUIDE.md` for your chosen platform!

