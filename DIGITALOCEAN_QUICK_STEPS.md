# ⚡ DigitalOcean Quick Steps (Cheat Sheet)

Quick reference for deploying to DigitalOcean. For detailed instructions, see `DIGITALOCEAN_DEPLOYMENT.md`.

## 🎯 5-Minute Quick Start

### 1. Generate Secret Key
```powershell
python generate_secret_key.py
# Copy the key!
```

### 2. Push to GitHub
```powershell
git add .
git commit -m "Deploy to DigitalOcean"
git push origin main
```

### 3. Create App on DigitalOcean
- Go to https://cloud.digitalocean.com
- Click "Create" → "Apps"
- Connect GitHub → Select `GISONETAGUMVISION` repo
- DigitalOcean auto-detects `.do/app.yaml` ✅

### 4. Set Secret Key
- In app config → Environment Variables
- Find `DJANGO_SECRET_KEY` → Set value (paste your key)
- Mark as SECRET

### 5. Deploy!
- Click "Create Resources"
- Wait 5-10 minutes

### 6. Migrate Database
```powershell
# Get connection string from: App → Resources → Database → Connection Details
.\migrate_database_to_cloud.ps1
# Choose option 3 (DigitalOcean), paste connection string
```

### 7. Create Superuser
- App → Console tab
- Run: `python manage.py createsuperuser`

### 8. Test!
- Visit your app URL (shown after deployment)
- Login and test features

---

## 🔑 Key Information

**App URL Format:**
```
https://gisonetagumvision-xxxxx.ondigitalocean.app
```

**Database Connection:**
- App → Resources → `gistagum-db` → Connection Details

**Environment Variables:**
- App → Settings → Environment Variables

**Cost:** ~$12/month (App $5 + DB $7)

**Auto-Deploy:** Enabled (pushes to `main` branch auto-deploy)

---

## 🆘 Quick Troubleshooting

**App won't start?**
- Check: App → Runtime Logs
- Verify: `DJANGO_SECRET_KEY` is set

**Database errors?**
- Verify: `DATABASE_URL` is set
- Test: `.\test_cloud_database.ps1`

**Static files missing?**
- Check: Build logs for `collectstatic`
- Verify: WhiteNoise is working

---

That's it! 🚀

