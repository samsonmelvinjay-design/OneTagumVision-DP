# DigitalOcean Spaces Setup Guide

This guide walks you through setting up DigitalOcean Spaces for media file storage (progress photos, receipts, etc.) in OneTagumVision.

---

## Step 1: Create a Space

1. Log in to [DigitalOcean](https://cloud.digitalocean.com)
2. Go to **Spaces Object Storage** in the sidebar
3. Click **Create Space**
4. Choose:
   - **Datacenter region** (e.g. Singapore `sgp1`, New York `nyc3`)
   - **Space name** (e.g. `onetagumvision-media`) – lowercase, numbers, dashes only
   - **File listing** → **Public** (so uploaded images can be viewed in browsers)
5. Click **Create a Space**

---

## Step 2: Create Spaces API Keys

1. Go to **API** in the left sidebar
2. Click **Spaces Keys** tab
3. Click **Generate New Key**
4. Name it (e.g. `GISTAGUM Spaces`)
5. Click **Generate Key**
6. **Copy and save** the Access Key and Secret Key – the Secret is shown only once

---

## Step 3: Configure Environment Variables

### Local development (`.env`)

Edit your `.env` file in the project root:

```env
USE_SPACES=true
AWS_ACCESS_KEY_ID=your-access-key-from-step-2
AWS_SECRET_ACCESS_KEY=your-secret-key-from-step-2
AWS_STORAGE_BUCKET_NAME=your-space-name-from-step-1
AWS_S3_ENDPOINT_URL=https://sgp1.digitaloceanspaces.com
AWS_S3_REGION_NAME=sgp1
AWS_S3_CUSTOM_DOMAIN=
```

- Replace `sgp1` with your Space’s region if different (e.g. `nyc3`, `ams3`)
- `AWS_S3_ENDPOINT_URL` format: `https://<region>.digitaloceanspaces.com`

### DigitalOcean App Platform (production)

1. Open your app in the DigitalOcean dashboard
2. Go to **Settings** → **App-Level Environment Variables**
3. Add the same variables as above

---

## Step 4: Install Dependencies

```bash
pip install python-dotenv
```

Or install all project dependencies:

```bash
pip install -r requirements.txt
```

---

## Step 5: Configure CORS (for browser uploads)

If uploads fail from the browser, configure CORS on your Space:

1. Open your Space in DigitalOcean
2. Go to **Settings** → **CORS Configurations**
3. Add:

   - **Origin:** your app URL (e.g. `https://onetagumvision.com` or `http://localhost:8000`)
   - **Allowed Methods:** `GET`, `PUT`, `POST`, `DELETE`, `HEAD`
   - **Allowed Headers:** `*`
   - **Max Age:** `3600`

4. Save

---

## Step 6: Test

1. Start the app: `python manage.py runserver`
2. Add a progress update with photos
3. Check the console for: `DigitalOcean Spaces configured for media storage`
4. Verify images in your Space under the `progress_photos/` folder

---

## Optional: Enable CDN

1. Open your Space → **Settings** → **CDN**
2. Enable CDN
3. Optionally set a custom subdomain (e.g. `cdn.yourdomain.com`)
4. Add to `.env`:

   ```env
   AWS_S3_CUSTOM_DOMAIN=cdn.yourdomain.com
   ```

---

## Migrating Existing Images to Spaces

If you have project images in a local `media/` folder (e.g. from before Spaces was enabled) and need to upload them:

1. Ensure `.env` has Spaces credentials and `USE_SPACES=true`
2. Run:
   ```bash
   python manage.py sync_media_to_spaces
   ```
3. Or specify the media folder: `python manage.py sync_media_to_spaces --media-dir ./media`
4. Use `--dry-run` to preview without uploading

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Images not loading | Ensure `File listing` is **Public** on the Space |
| Upload fails | Check CORS; add your app origin |
| `USE_SPACES` ignored | Ensure all Spaces env vars are set |
| Wrong region | Match `AWS_S3_REGION_NAME` and region in `AWS_S3_ENDPOINT_URL` |
