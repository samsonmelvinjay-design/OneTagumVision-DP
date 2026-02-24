# Populate Zoning & Barangay Data for City Overview

The **City Overview** map view types (Barangay Boundaries, Urban/Rural, Economic Classification, Elevation Type, Zone Type) require **barangay metadata** in the database. If you see console errors like:

- `⚠️ CRITICAL: Zoning data is empty!`
- `The database has no barangay metadata.`

follow the steps below.

## Quick fix

1. **Open a terminal** (Command Prompt or PowerShell).

2. **Go to the project directory:**
   ```bash
   cd c:\xampp\htdocs\OneTagumVision-DP
   ```

3. **Run the populate command:**
   ```bash
   python manage.py populate_barangay_metadata
   ```

4. **Refresh the City Overview page** in your browser. The view types should now load and the Zoning Control checkboxes (Barangay Boundaries, Urban/Rural, Economic Classification, Elevation Type, Zone Type) will work.

## If you get a Celery error

If the command fails with a Celery-related import error:

1. Open `backend/gistagum/__init__.py`.
2. Temporarily comment out the Celery import:
   ```python
   # from .celery import app as celery_app
   # __all__ = ('celery_app',)
   ```
3. Run the command again:
   ```bash
   python manage.py populate_barangay_metadata
   ```
4. Restore the lines in `backend/gistagum/__init__.py` (uncomment the Celery import).

## What the command does

- Populates the **BarangayMetadata** table with Tagum City barangays (from PSA-2020 CPH–style infographic data).
- Each record includes: `name`, `barangay_class` (urban/rural), `economic_class`, `elevation_type`, `industrial_zones`, and related fields.
- The City Overview map reads this via `/projeng/api/barangay-metadata/` and uses it to color the map by the selected view type.

## View types

| View type                 | Source field(s)     | Description                          |
|---------------------------|---------------------|--------------------------------------|
| Barangay Boundaries       | (outline only)      | Barangay outlines from GeoJSON       |
| Urban / Rural             | `barangay_class`    | Urban vs rural classification        |
| Economic Classification   | `economic_class`    | Growth center, emerging, satellite   |
| Elevation Type            | `elevation_type`    | Highland, plains, coastal            |
| Zone Type                 | zone data / metadata| Dominant zone (R-1, C-1, etc.)       |

After populating, all of these options in the Zoning Control panel should work when data exists for the visible barangays.
