# Fixing Zoning Classification Issue

## Problem
The console shows `switchView method not available on choroplethMap`, even though the methods are defined in `simple_choropleth.js`.

## Root Cause
The browser is likely caching an **old version** of `simple_choropleth.js` that doesn't include the zoning methods (`switchView`, `loadZoningData`, `createZoningLayer`).

## Solution

### 1. Hard Refresh Browser
**Most Important Step:**
- **Chrome/Edge**: Press `Ctrl + Shift + R` or `Ctrl + F5`
- **Firefox**: Press `Ctrl + Shift + R` or `Ctrl + F5`
- This forces the browser to reload all JavaScript files

### 2. Clear Browser Cache
If hard refresh doesn't work:
1. Open DevTools (F12)
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"

### 3. Verify Methods Are Loaded
After refreshing, check the console. You should see:
```
✓ SimpleChoropleth class loaded
✓ switchView method exists: true
✓ loadZoningData method exists: true
✓ createZoningLayer method exists: true
✓ All methods: ['calculateBarangayStats', 'formatCurrency', 'loadData', 'createChoropleth', 'createLegend', 'createSummaryPanel', 'cleanup', 'initialize', 'loadZoningData', 'switchView', 'createZoningLayer', 'createZoningPopup']
```

### 4. If Methods Still Not Available
If after hard refresh the methods still don't exist, check:

1. **Network Tab**: 
   - Open DevTools → Network tab
   - Refresh page
   - Find `simple_choropleth.js` in the list
   - Check if it loaded successfully (status 200)
   - Check the file size (should be around 20-25 KB)
   - Click on it and check the Response tab to see if it contains `switchView`

2. **Check File on Server**:
   - Verify `static/js/simple_choropleth.js` exists on the server
   - Verify it contains the methods (lines 385-597)

3. **Check for JavaScript Errors**:
   - Look for any red errors in the console
   - JavaScript errors earlier in the file can prevent methods from being defined

## Expected Behavior After Fix

Once the correct file loads:

1. **Check "Show Zoning Overlay"** → Zoning view selector appears
2. **Select "Urban / Rural"** → Barangays colored red (urban) or yellow (rural)
3. **Select "Economic Classification"** → Barangays colored blue (growth center), green (emerging), or yellow (satellite)
4. **Select "Elevation Type"** → Barangays colored purple (highland), green (plains), or cyan (coastal)
5. **Click on barangay** → Popup shows both project stats AND zoning information

## Color Scheme Reference

### Urban/Rural
- **Red (#ef4444)**: Urban barangays
- **Yellow (#fbbf24)**: Rural barangays

### Economic Classification
- **Blue (#3b82f6)**: Growth Center
- **Green (#10b981)**: Emerging
- **Yellow (#fbbf24)**: Satellite

### Elevation Type
- **Purple (#8b5cf6)**: Highland/Rolling
- **Green (#84cc16)**: Plains/Lowland
- **Cyan (#06b6d4)**: Coastal

## Troubleshooting

### Issue: Methods still not available after hard refresh
**Solution**: Check if there are multiple versions of the file or if a CDN/proxy is caching it.

### Issue: Zoning data not loading
**Solution**: 
- Check Network tab for `/projeng/api/barangay-metadata/` request
- Verify you're logged in (401 error = not authenticated)
- Check if API returns data (should have 23 barangays)

### Issue: Barangays not coloring correctly
**Solution**:
- Check console for "Zoning data loaded: X barangays" (should be 23)
- Check console for "Colored barangays: X" when switching views
- Verify barangay names in API match GeoJSON feature names exactly

## Files Modified
- `static/js/simple_choropleth.js` - Contains all zoning methods
- `templates/monitoring/map.html` - Loads script with cache busting

## Next Steps
1. Hard refresh the browser (Ctrl+Shift+R)
2. Check console for method verification messages
3. Test zoning overlay toggle
4. Test different zoning view types
5. Verify barangays are colored correctly

