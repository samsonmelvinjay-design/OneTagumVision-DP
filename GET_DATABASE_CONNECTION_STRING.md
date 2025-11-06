# 🔗 Step 2: Get Database Connection String from DigitalOcean

Follow these steps to get your database connection string.

## 📋 Step-by-Step Instructions

### Step 1: Find Your Database

1. **In DigitalOcean Dashboard:**
   - Look at the left sidebar
   - Click on **"Databases"** (under MANAGE section)
   - You should see a list of your databases

2. **Find your new database:**
   - Look for the database you just created
   - It might be named `gistagum-db` or have a default name
   - Click on it to open the database details

---

### Step 2: Open Connection Details

1. **In the database details page:**
   - Look for tabs at the top: Overview, Users & Databases, Connection Details, Settings, etc.
   - Click on **"Connection Details"** tab

---

### Step 3: Copy Connection String

1. **In Connection Details tab, you'll see:**
   - **Connection String** section
   - It looks like this:
     ```
     postgresql://doadmin:AVNS_xxxxx@host-name.db.ondigitalocean.com:25060/defaultdb?sslmode=require
     ```

2. **Copy the connection string:**
   - Click the **copy icon** (📋) next to the connection string
   - OR select all the text and copy it (Ctrl+C)
   - **Save it somewhere safe** - you'll need it!

---

## 🎯 What the Connection String Looks Like

```
postgresql://doadmin:PASSWORD@HOST:PORT/DATABASE?sslmode=require
```

**Example:**
```
postgresql://doadmin:AVNS_abc123xyz@db-postgresql-sgp1-12345.db.ondigitalocean.com:25060/defaultdb?sslmode=require
```

---

## ✅ After You Have the Connection String

Once you have it, you can:

1. **Import your database:**
   ```powershell
   .\migrate_database_to_cloud.ps1
   ```
   - Choose option 3 (DigitalOcean)
   - Paste your connection string

2. **OR import manually:**
   ```powershell
   $CONN = "your-connection-string-here"
   psql $CONN < local_backup_20251106_192637.sql
   ```

---

## 🆘 Can't Find Connection Details?

**Alternative ways to get it:**

1. **From Database Overview:**
   - Go to database → Overview tab
   - Look for "Connection Information" section
   - Click "Show Connection String"

2. **From Users & Databases tab:**
   - Go to "Users & Databases" tab
   - You'll see connection info there too

3. **Check the database settings:**
   - Sometimes connection info is in Settings → Connection Pooling

---

## 🔒 Security Note

- The connection string contains your password
- Keep it secret!
- Don't commit it to Git
- Use it only for migration

---

**Once you have the connection string, let me know and we'll import your data!** 🚀

