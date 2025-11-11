# Map Not Displaying - Troubleshooting Guide

## Issue
The map container appears empty on the `/dashboard/map/` page.

## Possible Causes & Solutions

### 1. **Leaflet Library Not Loading**
**Symptoms:** Map container is completely empty, no tiles visible

**Check:**
- Open browser console (F12)
- Look for errors like "L is not defined" or "Leaflet is not loaded"
- Check Network tab to see if `leaflet.js` and `leaflet.css` are loading

**Solution:**
- Verify Leaflet files exist in `static/leaflet/` directory
- Check if `base.html` includes Leaflet CSS and JS
- Clear browser cache and refresh

### 2. **Map Container Not Visible**
**Symptoms:** Map container exists but appears empty

**Check:**
- Inspect the `#map` element in browser DevTools
- Verify it has height: `height: 60vh` or `min-height: 300px`
- Check if container is hidden by CSS (`display: none`)

**Solution:**
- The container now has a gray background (`#f0f0f0`) - you should see this if container exists
- If you see gray background but no map, it's a Leaflet initialization issue

### 3. **Map Initialization Timing Issue**
**Symptoms:** Map initializes but doesn't render tiles

**Check:**
- Open browser console
- Look for "Map initialized successfully" message
- Check for any JavaScript errors

**Solution:**
- Added `invalidateSize()` calls after initialization
- Map should auto-resize when container becomes visible
- Try refreshing the page

### 4. **JavaScript Errors**
**Symptoms:** Console shows errors, map doesn't initialize

**Check:**
- Open browser console (F12)
- Look for red error messages
- Check if `window.projects` is defined

**Solution:**
- Fix any JavaScript errors shown in console
- Verify `projects-data` JSON script tag exists in template
- Check if projects data is being passed from view

### 5. **Network Issues**
**Symptoms:** Map container visible but no tiles loading

**Check:**
- Check Network tab for failed requests to `tile.openstreetmap.org`
- Verify internet connection
- Check if OpenStreetMap tiles are blocked

**Solution:**
- Check internet connection
- Verify firewall isn't blocking OpenStreetMap
- Try different tile provider if needed

## Debugging Steps

1. **Open Browser Console (F12)**
   - Look for any error messages
   - Check if you see "Map initialized successfully"
   - Check if you see "Leaflet loaded successfully"

2. **Inspect Map Container**
   - Right-click on empty map area → Inspect
   - Check if `#map` element exists
   - Verify it has proper dimensions (height > 0)

3. **Check Network Tab**
   - Verify Leaflet JS/CSS files load (status 200)
   - Check if tile requests are being made
   - Look for any failed requests

4. **Verify Data**
   - Check if `window.projects` is defined in console
   - Type `window.projects` in console to see project data
   - Verify projects have valid coordinates

## Quick Fixes Applied

✅ Added `invalidateSize()` calls after map initialization  
✅ Added background color to map container for visibility  
✅ Added better error handling and logging  
✅ Added Leaflet loading check with user-friendly error message  

## Next Steps

If map still doesn't show:

1. **Check Browser Console** - Share any error messages
2. **Verify Leaflet Files** - Ensure they exist in `static/leaflet/`
3. **Test in Different Browser** - Rule out browser-specific issues
4. **Check Server Logs** - Look for any backend errors

## Expected Behavior

When working correctly:
- Map container should show gray background initially
- Then OpenStreetMap tiles should load
- Markers should appear for projects with coordinates
- Map should be interactive (zoom, pan)

