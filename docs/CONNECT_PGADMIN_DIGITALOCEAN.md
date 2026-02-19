# 🔌 Connect to DigitalOcean Database in pgAdmin

Your pgAdmin shows the server but it's not connected. Here's how to connect:

## 📋 Steps to Connect

### Step 1: Connect to the Server
1. **In pgAdmin, left panel:**
   - Find **"DigitalOcean tagumdb"** server
   - **Right-click** on it
   - Click **"Connect Server"** (or just double-click it)

### Step 2: Enter Password (if prompted)
- If it asks for a password, enter your DigitalOcean database password
- This is the password from your connection string:
  ```
  postgresql://doadmin:AVNS_rPtuYR8ArkLXUmGotVs@...
  ```
  Password: `AVNS_rPtuYR8ArkLXUmGotVs`

### Step 3: Verify Connection
- The server icon should change (no red X, or shows as connected)
- You should be able to expand "Databases" and see `defaultdb`
- The dashboard should show data instead of "Please connect..."

---

## 🔧 If Connection Fails

### Check Server Properties
1. **Right-click "DigitalOcean tagumdb"** → **"Properties"**
2. **Go to "Connection" tab:**
   - **Host**: Should be `tagumclusterdb-do-user-28669441-0.j.db.ondigitalocean.com`
   - **Port**: `25060`
   - **Database**: `defaultdb`
   - **Username**: `doadmin`
   - **Password**: (should be saved, or enter it)
3. **Go to "SSL" tab:**
   - **SSL Mode**: Should be **"Require"**
4. Click **"Save"**

### If You Need to Create New Server Connection

If the existing connection doesn't work, create a new one:

1. **Right-click "Servers"** → **"Create"** → **"Server"**

2. **General Tab:**
   - **Name**: `DigitalOcean tagumclusterdb` (or any name)

3. **Connection Tab:**
   - **Host**: `tagumclusterdb-do-user-28669441-0.j.db.ondigitalocean.com`
   - **Port**: `25060`
   - **Database**: `defaultdb`
   - **Username**: `doadmin`
   - **Password**: `AVNS_rPtuYR8ArkLXUmGotVs`
   - ✅ **Save password**: Check this box

4. **SSL Tab:**
   - **SSL Mode**: Select **"Require"**

5. Click **"Save"**

---

## ✅ After Connecting

Once connected:
- You'll see the database `defaultdb` under "Databases"
- Dashboard will show live data
- You can run SQL queries
- You can import your backup file

---

## 📥 Import Your Database

After connecting, you can import your local backup:

1. **Right-click on `defaultdb`** → **"Restore"**
2. **Select your backup file**: `local_backup_20251106_192637.sql`
3. **Or use command line** (easier):
   ```powershell
   .\import_to_digitalocean.ps1
   ```

---

**Try connecting first - just double-click "DigitalOcean tagumdb" and enter the password!** 🔌

