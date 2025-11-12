# 🌐 Connect Hostinger Domain to DigitalOcean App

## Your Domain
- **Domain:** `onetagumvision.com`
- **Registrar:** Hostinger
- **Status:** Active ✅

## Step-by-Step Instructions

### Step 1: Update Nameservers in Hostinger

1. **Log in to Hostinger:**
   - Go to https://www.hostinger.com
   - Log in to your account

2. **Navigate to Domain Management:**
   - Click **"Domain portfolio"** (or go to your domain management page)
   - Find **`onetagumvision.com`**
   - Click **"Manage"** button

3. **Find Nameserver Settings:**
   - Look for **"DNS"** or **"Nameservers"** section
   - You might see it under **"Advanced DNS"** or **"DNS Zone"**

4. **Change Nameservers:**
   - Change from Hostinger's nameservers to DigitalOcean's:
   ```
   ns1.digitalocean.com
   ns2.digitalocean.com
   ns3.digitalocean.com
   ```
   - **Remove** any existing nameservers
   - **Add** the three DigitalOcean nameservers above

5. **Save Changes:**
   - Click **"Save"** or **"Update"**
   - ⏱️ Wait 24-72 hours for DNS propagation (usually 1-2 hours)

### Step 2: Add Domain in DigitalOcean

1. **Go to DigitalOcean Dashboard:**
   - Navigate to your app: `onetagumvision`
   - Click **Settings** → **Domains**

2. **Add Domain:**
   - Click **"Add domain"** button
   - Enter: `onetagumvision.com`
   - Select **"We manage your domain"** (recommended)
   - Click **"Add domain"**

3. **Copy Nameservers (if needed):**
   - DigitalOcean will show you the nameservers
   - Make sure they match what you entered in Hostinger:
     - `ns1.digitalocean.com`
     - `ns2.digitalocean.com`
     - `ns3.digitalocean.com`

### Step 3: Update Environment Variables in DigitalOcean

**Critical Step!** Your Django app needs to know about the new domain.

1. **Go to DigitalOcean Dashboard:**
   - Your App → **Settings** → **Environment Variables**

2. **Update `ALLOWED_HOSTS`:**
   - Find `ALLOWED_HOSTS` variable
   - Update value to:
   ```
   onetagumvision-48sp6.ondigitalocean.app,*.ondigitalocean.app,onetagumvision.com,www.onetagumvision.com
   ```
   - Or use wildcard (simpler):
   ```
   *.ondigitalocean.app,onetagumvision.com,www.onetagumvision.com
   ```

3. **Update `CSRF_TRUSTED_ORIGINS`:**
   - Find `CSRF_TRUSTED_ORIGINS` variable
   - Update value to:
   ```
   https://onetagumvision-48sp6.ondigitalocean.app,https://*.ondigitalocean.app,https://onetagumvision.com,https://www.onetagumvision.com
   ```
   - Or use wildcard:
   ```
   https://*.ondigitalocean.app,https://onetagumvision.com,https://www.onetagumvision.com
   ```

4. **Save:**
   - Click **"Save"** or **"Update"**
   - Your app will automatically redeploy

### Step 4: Verify Everything Works

1. **Check DNS Propagation:**
   - Wait 1-2 hours after updating nameservers
   - Use online tools:
     - https://www.whatsmydns.net/#NS/onetagumvision.com
     - https://dnschecker.org/#NS/onetagumvision.com
   - Look for `ns1.digitalocean.com`, `ns2.digitalocean.com`, `ns3.digitalocean.com`

2. **Test Your Domain:**
   - Visit: `https://onetagumvision.com`
   - Should see your app! 🎉

3. **Check SSL Certificate:**
   - DigitalOcean automatically provisions SSL certificates
   - HTTPS should work automatically
   - Look for the padlock icon in your browser

---

## Troubleshooting

### Domain Not Working After 72 Hours?

1. **Verify Nameservers:**
   - Go back to Hostinger
   - Check if nameservers are correctly set to DigitalOcean's
   - Make sure all 3 nameservers are added

2. **Check Environment Variables:**
   - In DigitalOcean → Settings → Environment Variables
   - Verify `ALLOWED_HOSTS` includes `onetagumvision.com`
   - Verify `CSRF_TRUSTED_ORIGINS` includes `https://onetagumvision.com`

3. **Check Domain Status in DigitalOcean:**
   - Go to Settings → Domains
   - Should show domain as "Active" or "Verified"

4. **Clear Browser Cache:**
   - Try incognito/private browsing mode
   - Or clear browser cache

### Still Having Issues?

- **DNS Propagation:** Can take up to 72 hours globally
- **SSL Certificate:** DigitalOcean auto-provisions, but may take 24-48 hours after DNS
- **Contact Support:** If issues persist after 72 hours

---

## Quick Reference: Environment Variables

**Copy and paste these into DigitalOcean → Settings → Environment Variables:**

```
ALLOWED_HOSTS=*.ondigitalocean.app,onetagumvision.com,www.onetagumvision.com
CSRF_TRUSTED_ORIGINS=https://*.ondigitalocean.app,https://onetagumvision.com,https://www.onetagumvision.com
DEBUG=false
```

---

**That's it! Once DNS propagates, your domain will be live!** 🚀

