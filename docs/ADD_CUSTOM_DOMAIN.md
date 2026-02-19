# 🌐 How to Add Custom Domain to DigitalOcean App

## Step-by-Step Guide

### 1. Add Domain in DigitalOcean Dashboard

1. Go to **DigitalOcean Dashboard** → Your App (`onetagumvision`)
2. Click **Settings** → **Domains**
3. Click **"Add domain"** button
4. Enter your domain: `onetagumvision.com`
5. Select **"We manage your domain"** (recommended - easier)
6. Click **"Add domain"**

### 2. Update DNS Nameservers at Your Domain Registrar

**If you selected "We manage your domain":**

1. Go to your domain registrar (where you bought the domain):
   - GoDaddy
   - Namecheap
   - Google Domains
   - Cloudflare
   - etc.

2. Find **DNS Settings** or **Nameserver Settings**

3. Replace existing nameservers with DigitalOcean's:
   ```
   ns1.digitalocean.com
   ns2.digitalocean.com
   ns3.digitalocean.com
   ```

4. **Save changes**

5. ⏱️ **Wait 24-72 hours** for DNS propagation (usually faster, 1-2 hours)

### 3. Update Environment Variables in DigitalOcean

**After adding the domain, update your app's environment variables:**

1. Go to **DigitalOcean Dashboard** → Your App → **Settings** → **Environment Variables**

2. **Update `ALLOWED_HOSTS`:**
   ```
   onetagumvision-48sp6.ondigitalocean.app,*.ondigitalocean.app,onetagumvision.com,www.onetagumvision.com
   ```
   Or use wildcard:
   ```
   *.ondigitalocean.app,onetagumvision.com,www.onetagumvision.com
   ```

3. **Update `CSRF_TRUSTED_ORIGINS`:**
   ```
   https://onetagumvision-48sp6.ondigitalocean.app,https://*.ondigitalocean.app,https://onetagumvision.com,https://www.onetagumvision.com
   ```
   Or use wildcard:
   ```
   https://*.ondigitalocean.app,https://onetagumvision.com,https://www.onetagumvision.com
   ```

4. **Save** - App will auto-redeploy

### 4. Verify Domain is Working

1. Wait for DNS propagation (check with: `nslookup onetagumvision.com`)
2. Visit `https://onetagumvision.com` in your browser
3. Should see your app! 🎉

### 5. SSL Certificate (Automatic)

- DigitalOcean automatically provisions **free SSL certificates** via Let's Encrypt
- HTTPS will work automatically once DNS is configured
- No manual SSL setup needed!

---

## Alternative: "You manage your domain"

If you selected **"You manage your domain"**:

1. Keep your existing nameservers at your registrar
2. Add these DNS records at your DNS provider:
   - **A Record**: Point to DigitalOcean's IP (if provided)
   - **CNAME Record**: Point `www` to `onetagumvision-48sp6.ondigitalocean.app`
   - Or follow DigitalOcean's specific instructions shown in the dashboard

---

## Troubleshooting

### Domain not working after 72 hours?

1. **Check DNS propagation:**
   ```bash
   nslookup onetagumvision.com
   dig onetagumvision.com
   ```

2. **Verify environment variables:**
   - Make sure `ALLOWED_HOSTS` includes your domain
   - Make sure `CSRF_TRUSTED_ORIGINS` includes `https://yourdomain.com`

3. **Check DigitalOcean domain status:**
   - Go to Settings → Domains
   - Should show "Active" or "Verified"

4. **Clear browser cache** and try again

### SSL Certificate Issues?

- DigitalOcean auto-provisions SSL certificates
- If SSL fails, wait 24-48 hours after DNS propagation
- Check domain status in DigitalOcean dashboard

---

## Current Environment Variables (Update These!)

**In DigitalOcean → Settings → Environment Variables:**

```
ALLOWED_HOSTS=onetagumvision-48sp6.ondigitalocean.app,*.ondigitalocean.app,onetagumvision.com,www.onetagumvision.com
CSRF_TRUSTED_ORIGINS=https://onetagumvision-48sp6.ondigitalocean.app,https://*.ondigitalocean.app,https://onetagumvision.com,https://www.onetagumvision.com
DEBUG=false
```

---

**That's it! Your custom domain will be live once DNS propagates.** 🚀

