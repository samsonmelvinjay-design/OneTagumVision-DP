# 📍 Land Suitability Analysis Section Location

## Where to Find It

The **Land Suitability Analysis** section is located on the Head Engineer dashboard at:

**Path:** `/dashboard/` (Head Engineer Dashboard)

**Location on Page:**
1. Scroll down past the **"Analytics & Insights"** section (the 6 charts)
2. You'll see the **"Land Suitability Analysis"** section header
3. Below that are 3 widgets in a row:
   - **Suitability Overview** (left)
   - **Suitability Distribution Chart** (middle)
   - **Risk Summary** (right)

---

## Visual Location

```
Dashboard Page Structure:
├── Welcome Header
├── 5 Summary Cards (Total, Completed, In Progress, Planned, Delayed)
├── Recent Projects & Quick Stats
├── Analytics & Insights Section
│   ├── Chart 1: Project Status Overview
│   ├── Chart 2: Projects per Barangay
│   ├── Chart 3: Projects per Status
│   ├── Chart 4: Budget Utilization
│   ├── Chart 5: Cost Breakdown by Type
│   └── Chart 6: Monthly Spending Trend
│
├── 🎯 Land Suitability Analysis Section ← HERE!
│   ├── Suitability Overview Card
│   ├── Suitability Distribution Chart
│   └── Risk Summary Card
│
└── Zone Analytics Section
    ├── Zone Cost Distribution Chart
    └── Zone Projects Chart
```

---

## If You Don't See It

### **1. Scroll Down**
The section is below the 6 charts. Scroll down past the "Analytics & Insights" section.

### **2. Check Browser Console**
Open browser console (F12) and check for JavaScript errors:
- Look for errors related to `suitability_dashboard_data_api`
- Check if the API endpoint is accessible

### **3. Check Data Availability**
If you see "No suitability analyses available", it means:
- No projects have been analyzed yet
- You need to create projects with location data first
- Or run the management command to analyze existing projects

### **4. Verify URL**
Make sure you're on the Head Engineer dashboard:
- URL should be: `/dashboard/`
- You must be logged in as a Head Engineer

---

## How to See Data

### **Option 1: Create a New Project**
1. Go to Projects → Create Project
2. Add a project with:
   - Location (latitude/longitude)
   - Barangay
   - Zone type
3. The suitability analysis will be created automatically
4. Refresh the dashboard to see the data

### **Option 2: Analyze Existing Projects**
Run the management command:
```bash
python manage.py analyze_land_suitability --all --save
```

This will analyze all existing projects that have location data.

---

## Section Details

### **Suitability Overview Card:**
- Total Analyses count
- Highly Suitable count
- Suitable count
- Moderate count
- Not Suitable count (if any)

### **Suitability Distribution Chart:**
- Interactive doughnut chart
- Shows distribution of suitability categories
- Color-coded by category

### **Risk Summary Card:**
- Total projects with risks
- Flood Risk count
- Slope Risk count
- Zoning Conflict count
- Infrastructure Gap count

---

## Troubleshooting

### **Section Not Visible:**
1. ✅ Check if you're on the Head Engineer dashboard
2. ✅ Scroll down past the charts
3. ✅ Check browser console for errors
4. ✅ Verify the template is loaded (view page source)

### **Shows "No suitability analyses available":**
1. ✅ Create a project with location data
2. ✅ Or run: `python manage.py analyze_land_suitability --all --save`
3. ✅ Refresh the dashboard

### **Shows "Loading suitability data...":**
1. ✅ Check browser console for API errors
2. ✅ Verify you're logged in as Head Engineer
3. ✅ Check if the API endpoint is accessible: `/projeng/api/suitability/dashboard-data/`

---

## Quick Test

To quickly test if the section is working:

1. **Open browser console** (F12)
2. **Run this JavaScript:**
   ```javascript
   fetch('/projeng/api/suitability/dashboard-data/')
     .then(r => r.json())
     .then(d => console.log('Suitability Data:', d))
     .catch(e => console.error('Error:', e));
   ```

3. **Check the response:**
   - If you see data: The API is working, section should load
   - If you see an error: Check authentication/permissions
   - If you see `{total_analyses: 0}`: No data yet, need to analyze projects

---

## Summary

**Location:** Below the "Analytics & Insights" section, above "Zone Analytics"  
**URL:** `/dashboard/` (Head Engineer only)  
**Requires:** Projects with location data and suitability analysis

**If not visible:** Scroll down or check browser console for errors! 🔍

