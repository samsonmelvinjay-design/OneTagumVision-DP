# Zone Recommendations: Making Them Available and Accurate

## Overview

The Zone Compatibility Recommendation System uses Multi-Criteria Decision Analysis (MCDA) to suggest optimal zones for projects. For recommendations to appear and be accurate, the system needs proper data configuration.

---

## Why Recommendations Don't Appear

### Common Issues:

1. **No ZoneAllowedUse Data** - The system needs relationships between project types and zones
2. **Missing Project Type** - The selected project type doesn't exist in the database
3. **No ZoningZone Data** - Zone definitions are missing
4. **Incomplete BarangayMetadata** - Location-specific scoring requires barangay data
5. **API Errors** - Check browser console for API call failures

---

## Step 1: Verify Required Data

### Check Current Data Status

Run these commands in Django shell:

```python
from projeng.models import ProjectType, ZoneAllowedUse, ZoningZone, BarangayMetadata

# Check project types
print(f"Project Types: {ProjectType.objects.count()}")
for pt in ProjectType.objects.all():
    print(f"  - {pt.code}: {pt.name}")

# Check zone allowed uses (CRITICAL - this is what makes recommendations work)
print(f"\nZone Allowed Uses: {ZoneAllowedUse.objects.count()}")
if ZoneAllowedUse.objects.count() == 0:
    print("  ⚠️  NO ZONE ALLOWED USES FOUND - This is why recommendations don't appear!")

# Check zones
print(f"\nZoning Zones: {ZoningZone.objects.count()}")

# Check barangay metadata
print(f"\nBarangay Metadata: {BarangayMetadata.objects.count()}")
```

---

## Step 2: Populate Zone Allowed Uses

### Option A: Use Management Command (Recommended)

If you have a management command to populate zone allowed uses:

```bash
python manage.py populate_zone_allowed_uses
```

### Option B: Manual Population via Django Admin

1. Go to Django Admin → `Projeng` → `Zone Allowed Uses`
2. Click "Add Zone Allowed Use"
3. For each project type and zone combination:
   - Select `Zone Type` (e.g., R1, R3, C1, C2, etc.)
   - Select `Project Type` (e.g., Road/Highway, Apartment Building, etc.)
   - Set `Is Primary Use` = True (if it's a primary allowed use)
   - Set `Is Conditional` = True (if it requires special permit)
   - Add any `Conditions`, `Max Density`, or `Max Height` restrictions

### Option C: Create Data Migration

Create a migration file to populate based on CITY ORDINANCE NO. 45, S-2002:

```python
# projeng/migrations/XXXX_populate_zone_allowed_uses_from_ordinance.py

from django.db import migrations

def populate_zone_allowed_uses(apps, schema_editor):
    ProjectType = apps.get_model('projeng', 'ProjectType')
    ZoneAllowedUse = apps.get_model('projeng', 'ZoneAllowedUse')
    
    # Example mappings (adjust based on your ordinance)
    mappings = [
        # Format: (zone_type, project_type_code, is_primary, is_conditional)
        ('R1', 'road_highway', True, False),
        ('R2', 'road_highway', True, False),
        ('R3', 'road_highway', True, False),
        ('C1', 'road_highway', True, False),
        ('C2', 'road_highway', True, False),
        # Add more mappings based on your zone compatibility matrix
    ]
    
    for zone_type, project_type_code, is_primary, is_conditional in mappings:
        try:
            project_type = ProjectType.objects.get(code=project_type_code)
            ZoneAllowedUse.objects.get_or_create(
                zone_type=zone_type,
                project_type=project_type,
                defaults={
                    'is_primary_use': is_primary,
                    'is_conditional': is_conditional,
                }
            )
        except ProjectType.DoesNotExist:
            print(f"Warning: Project type {project_type_code} not found")

def reverse_populate(apps, schema_editor):
    # Optional: remove populated data
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('projeng', '0018_zonealloweduse_zonerecommendation'),  # Adjust to your latest migration
    ]

    operations = [
        migrations.RunPython(populate_zone_allowed_uses, reverse_populate),
    ]
```

---

## Step 3: Ensure Project Types Are Populated

Verify project types exist:

```bash
python manage.py populate_project_types
```

Or check in Django Admin → `Projeng` → `Project Types`

---

## Step 4: Populate Barangay Metadata (For Accuracy)

Barangay metadata improves recommendation accuracy by providing:
- Population density
- Barangay class (Urban/Rural)
- Economic class
- Special features (roads, transportation)

```bash
# If you have a command to populate barangay data
python manage.py populate_barangay_data_from_infographics
```

Or manually add in Django Admin → `Projeng` → `Barangay Metadata`

---

## Step 5: Test Recommendations

### Test via API

```bash
# Test with a project type code
curl "http://localhost:8000/projeng/api/zone-recommendation/?project_type_code=road_highway&limit=5"
```

### Test in Browser

1. Open the Create Project modal
2. Select a **Project Type** (e.g., "Road/Highway")
3. Select a **Barangay** (optional but improves accuracy)
4. Recommendations should appear automatically

---

## Step 6: Improve Accuracy

### A. Enhance Scoring Factors

The MCDA algorithm uses these weights (in `projeng/zone_recommendation.py`):

```python
WEIGHT_ZONING_COMPLIANCE = 0.40  # 40% - Is project type allowed?
WEIGHT_LAND_AVAILABILITY = 0.20  # 20% - How much land is available?
WEIGHT_ACCESSIBILITY = 0.20      # 20% - How accessible is the zone?
WEIGHT_COMMUNITY_IMPACT = 0.10   # 10% - Positive community impact?
WEIGHT_INFRASTRUCTURE = 0.10     # 10% - Infrastructure support?
```

**To improve accuracy:**

1. **Add more ZoneAllowedUse entries** - More complete zone compatibility matrix
2. **Populate BarangayMetadata** - Better location-specific scoring
3. **Add ZoningZone data** - Zone-specific characteristics
4. **Adjust weights** - Based on your city's priorities

### B. Add Location Data

If a location (latitude/longitude) is selected:

1. The system can use actual coordinates for:
   - Flood risk assessment
   - Proximity to infrastructure
   - Elevation data
   - Existing project density

2. Enhance `score_land_availability()` to use actual coordinates:
   ```python
   # Count projects within X km radius
   # Check actual land use from GIS data
   # Consider flood zones
   ```

### C. Integrate Real-Time Data

For maximum accuracy, integrate:

1. **GIS Data** - Actual zone boundaries
2. **Flood Risk Maps** - From local government
3. **Infrastructure Maps** - Roads, utilities, transportation
4. **Land Use Data** - Current land use patterns
5. **Population Density** - Real-time census data

---

## Step 7: Debugging

### Check Browser Console

Open browser DevTools (F12) → Console tab:

```javascript
// Check if API is being called
// Look for errors like:
// - "Failed to fetch zone recommendations"
// - "project_type_code parameter is required"
// - 400/500 errors
```

### Check Django Logs

```bash
# In development
python manage.py runserver

# Check for errors in terminal output
```

### Test API Directly

```python
# Django shell
python manage.py shell

from projeng.zone_recommendation import ZoneCompatibilityEngine

engine = ZoneCompatibilityEngine()

# Test with a project type
result = engine.recommend_zones(
    project_type_code='road_highway',
    barangay='Madaum',
    limit=5
)

print(f"Found {len(result['recommendations'])} recommendations")
for rec in result['recommendations']:
    print(f"  {rec['rank']}. {rec['zone_type']}: {rec['overall_score']:.1f}")
```

---

## Step 8: Verify Frontend Integration

### Check Event Listeners

In `templates/monitoring/map.html`, verify:

1. **Project Type Change** triggers `fetchZoneRecommendations()`
2. **Zone Type Change** triggers `fetchZoneRecommendations()`
3. **Barangay Change** triggers `fetchZoneRecommendations()`
4. **Location Change** triggers `fetchZoneRecommendations()`

### Check API URL

The frontend should call:
```
/projeng/api/zone-recommendation/?project_type_code=ROAD_HIGHWAY&barangay=Madaum&limit=5
```

---

## Quick Fix Checklist

- [ ] Run `populate_zone_allowed_uses` command
- [ ] Verify `ZoneAllowedUse.objects.count() > 0`
- [ ] Verify `ProjectType.objects.count() > 0`
- [ ] Select a project type in the modal
- [ ] Check browser console for API errors
- [ ] Test API endpoint directly
- [ ] Verify frontend event listeners are attached
- [ ] Check that recommendation section is not hidden

---

## Expected Behavior

### When Working Correctly:

1. **User selects Project Type** → Recommendations appear automatically
2. **User selects Zone Type** → Validation message appears (allowed/not allowed)
3. **User selects Barangay** → Recommendations update with location-specific scores
4. **User selects Location** → Recommendations update with coordinate-based scoring

### Recommendation Display:

- **Top 5 zones** ranked by overall score
- **Score breakdown** (Zoning, Land, Access, Infrastructure)
- **Advantages** and **Constraints** for each zone
- **"Select This Zone"** button to auto-fill zone type

---

## Next Steps for Maximum Accuracy

1. **Populate complete zone compatibility matrix** from CITY ORDINANCE NO. 45, S-2002
2. **Add all barangay metadata** from infographics
3. **Integrate GIS data** for actual zone boundaries
4. **Add flood risk data** for location-specific warnings
5. **Implement machine learning** to learn from historical project approvals
6. **Add user feedback** mechanism to improve recommendations over time

---

## Support

If recommendations still don't appear after following this guide:

1. Check Django logs for errors
2. Verify database migrations are applied
3. Test API endpoint directly
4. Check browser console for JavaScript errors
5. Verify CSRF token is included in API requests

