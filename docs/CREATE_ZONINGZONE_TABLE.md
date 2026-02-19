# 🔧 Create ZoningZone Table

## Problem
Error: `relation "projeng_zoningzone" does not exist`

The `ZoningZone` table wasn't created when we manually added the columns.

## Solution: Create the Table Manually

### Step 1: Open Django Shell
```bash
python manage.py shell
```

### Step 2: Run This Code
When you see `>>>`, paste this:

```python
from django.db import connection
c = connection.cursor()

# Create ZoningZone table
c.execute("""
CREATE TABLE IF NOT EXISTS projeng_zoningzone (
    id BIGSERIAL PRIMARY KEY,
    zone_type VARCHAR(20) NOT NULL,
    barangay VARCHAR(255) NOT NULL,
    location_description TEXT NOT NULL,
    keywords JSONB DEFAULT '[]'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
)
""")
print("✅ Created projeng_zoningzone table")

# Create indexes
c.execute("""
CREATE INDEX IF NOT EXISTS projeng_zon_baranga_8c8025_idx 
ON projeng_zoningzone(barangay, zone_type)
""")
c.execute("""
CREATE INDEX IF NOT EXISTS projeng_zon_is_acti_1819c4_idx 
ON projeng_zoningzone(is_active)
""")
print("✅ Created indexes")

print("Done!")
exit()
```

### Step 3: Now Run Populate Command
```bash
python manage.py populate_zoning_zones
```

---

## Alternative: One-Liner

If you prefer, run this single command:

```bash
python manage.py shell -c "from django.db import connection; c = connection.cursor(); c.execute('CREATE TABLE IF NOT EXISTS projeng_zoningzone (id BIGSERIAL PRIMARY KEY, zone_type VARCHAR(20) NOT NULL, barangay VARCHAR(255) NOT NULL, location_description TEXT NOT NULL, keywords JSONB DEFAULT \\'[]\\'::jsonb, is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW())'); c.execute('CREATE INDEX IF NOT EXISTS projeng_zon_baranga_8c8025_idx ON projeng_zoningzone(barangay, zone_type)'); c.execute('CREATE INDEX IF NOT EXISTS projeng_zon_is_acti_1819c4_idx ON projeng_zoningzone(is_active)'); print('Table created')"
```

Then:
```bash
python manage.py populate_zoning_zones
```

---

**After creating the table, the populate command should work!** ✅

