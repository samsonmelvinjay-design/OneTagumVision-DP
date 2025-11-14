# 🔧 Fix: Dashboard Showing Empty Suitability Data

## Problem
The Land Suitability Analysis dashboard was showing "No suitability analyses available" even though there are 27 projects in the system.

## Root Cause
1. **Only 10 projects had suitability analyses** - The analysis was only run for projects in the `projeng` app
2. **API was only querying projeng projects** - The dashboard API endpoint was only checking `projeng.models.Project`, not `monitoring.models.Project`
3. **Missing analyses** - 17 projects didn't have suitability analyses yet

## Solution

### 1. Fixed API to Handle Both Project Models
Updated `suitability_dashboard_data_api` in `projeng/views.py` to:
- Check both `projeng` and `monitoring` projects
- Find corresponding projects by PRN
- Automatically create analyses for projects that don't have them yet

### 2. Run Analysis for All Projects
Run the management command to analyze all projects:
```bash
python manage.py analyze_land_suitability --all --force --save
```

This will:
- Find all projects with location data (latitude, longitude, barangay)
- Create suitability analyses for projects that don't have them
- Update existing analyses if `--force` is used

## Files Changed
- `projeng/views.py` - Updated `suitability_dashboard_data_api` to handle both project models
- `projeng/utils.py` - Fixed `Project` import errors in notification handling

## Next Steps
1. ✅ Run analysis command for all projects
2. ✅ Refresh dashboard - should now show all 27 projects' suitability data
3. ✅ Verify widgets are displaying correctly

## Verification
After running the analysis command, check:
- Total analyses count should match number of projects with location data
- Dashboard should show suitability distribution chart
- Risk summary should show any projects with risks
- Overview card should show total analyses count

