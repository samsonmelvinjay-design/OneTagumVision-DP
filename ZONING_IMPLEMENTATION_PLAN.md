# Map Zoning Integration - Implementation Plan

## Overview
Integrate map zoning to assist in smart urban planning by enabling administrative level insights, zoning, and strategic city development.

---

## Current System Analysis

### What We Have:
✅ Leaflet.js map with choropleth functionality  
✅ Project model with `barangay` field (CharField)  
✅ Barangay boundaries (GeoJSON)  
✅ Project markers and choropleth visualization  
✅ Basic barangay statistics (projects, costs, status)  
✅ **Head Engineers = Admins** (is_head_engineer checks for is_superuser)  
✅ Access control system with `@head_engineer_required` decorator

### What We Need:
❌ Barangay metadata/zoning database model  
❌ Zoning data (Urban/Rural, Economic, Elevation, Industrial Zones)  
❌ Zoning overlays on map  
❌ Zoning-based filters  
❌ Zoning analytics and insights

### Important Note:
**Head Engineers are Admins**: The system already treats Head Engineers as superusers (admins). This means:
- Head Engineers can access Django admin panel
- Head Engineers can manage all data including barangay metadata
- All admin features are accessible to Head Engineers
- No separate admin role needed  

---

## Implementation Phases

## **PHASE 1: Database Foundation** (Week 1)

### Step 1.1: Create BarangayMetadata Model

**File**: `projeng/models.py` (or create new `monitoring/models.py` if preferred)

```python
class BarangayMetadata(models.Model):
    # Basic Info
    name = models.CharField(max_length=255, unique=True, db_index=True)
    
    # Population & Demographics
    population = models.IntegerField(null=True, blank=True)
    land_area = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # km²
    density = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # people/km²
    growth_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # %
    
    # Zoning Classifications
    BARANGAY_CLASS_CHOICES = [
        ('urban', 'Urban'),
        ('rural', 'Rural'),
    ]
    barangay_class = models.CharField(
        max_length=10, 
        choices=BARANGAY_CLASS_CHOICES, 
        null=True, 
        blank=True
    )
    
    ECONOMIC_CLASS_CHOICES = [
        ('growth_center', 'Growth Center'),
        ('emerging', 'Emerging'),
        ('satellite', 'Satellite'),
    ]
    economic_class = models.CharField(
        max_length=20, 
        choices=ECONOMIC_CLASS_CHOICES, 
        null=True, 
        blank=True
    )
    
    ELEVATION_CHOICES = [
        ('highland', 'Highland/Rolling'),
        ('plains', 'Plains/Lowland'),
        ('coastal', 'Coastal'),
    ]
    elevation_type = models.CharField(
        max_length=20, 
        choices=ELEVATION_CHOICES, 
        null=True, 
        blank=True
    )
    
    # Industrial Zones (can be multiple)
    INDUSTRIAL_ZONE_CHOICES = [
        ('cbd', 'Central Business District'),
        ('urban_expansion', 'Urban Expansion Area'),
        ('commercial_expansion', 'Commercial Expansion Area'),
        ('institutional_recreational', 'Institutional & Recreational'),
        ('agro_industrial', 'Agro-Industrial'),
    ]
    industrial_zones = models.JSONField(
        default=list, 
        help_text="List of industrial zone types"
    )
    
    # Additional Metadata
    primary_industries = models.JSONField(
        default=list,
        help_text="List of primary industries (agriculture, tourism, etc.)"
    )
    special_features = models.JSONField(
        default=list,
        help_text="Special facilities (hospitals, markets, ports, etc.)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    data_source = models.CharField(
        max_length=255, 
        default="PSA-2020 CPH",
        help_text="Source of demographic data"
    )
    data_year = models.IntegerField(default=2020)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = "Barangay Metadata"
    
    def __str__(self):
        return f"{self.name} ({self.get_barangay_class_display()})"
    
    def get_zoning_summary(self):
        """Return a summary string of all zoning classifications"""
        parts = []
        if self.barangay_class:
            parts.append(self.get_barangay_class_display())
        if self.economic_class:
            parts.append(self.get_economic_class_display())
        if self.elevation_type:
            parts.append(self.get_elevation_type_display())
        return " | ".join(parts) if parts else "Unclassified"
```

**Action Items:**
- [ ] Add model to `projeng/models.py`
- [ ] Create migration: `python manage.py makemigrations`
- [ ] Review migration file
- [ ] Run migration: `python manage.py migrate`

---

### Step 1.2: Create Data Population Script

**File**: `projeng/management/commands/populate_barangay_metadata.py`

```python
from django.core.management.base import BaseCommand
from projeng.models import BarangayMetadata

class Command(BaseCommand):
    help = 'Populate barangay metadata from the infographic data'
    
    def handle(self, *args, **options):
        # Data from the infographic
        barangay_data = [
            {
                'name': 'Apokon',
                'population': 37984,
                'land_area': None,  # Need to calculate or find
                'density': 4895,
                'growth_rate': 5.30,
                'barangay_class': 'urban',
                'economic_class': 'growth_center',
                'elevation_type': 'plains',
                'industrial_zones': ['institutional_recreational'],
                'primary_industries': ['institutional', 'recreation', 'shopping', 'residential'],
                'special_features': ['university', 'regional_hospital', 'ngas', 'churches', 'e_park']
            },
            {
                'name': 'Bincungan',
                'population': None,  # Not in top list
                'barangay_class': 'rural',
                'economic_class': 'satellite',
                'elevation_type': 'coastal',
                'industrial_zones': ['agro_industrial'],
                'primary_industries': ['fishery', 'eco_tourism', 'coconut'],
                'special_features': ['mangrove_forest', 'marine_protected_area', 'cemetery']
            },
            # ... Add all 23 barangays
        ]
        
        for data in barangay_data:
            barangay, created = BarangayMetadata.objects.update_or_create(
                name=data['name'],
                defaults=data
            )
            status = "Created" if created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(f'{status}: {barangay.name}')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully populated {len(barangay_data)} barangays')
        )
```

**Action Items:**
- [ ] Extract all 23 barangays' data from the image
- [ ] Create management command
- [ ] Populate initial data
- [ ] Verify data in admin panel

---

### Step 1.3: Add Admin Interface

**File**: `projeng/admin.py`

```python
from django.contrib import admin
from .models import BarangayMetadata
from gistagum.access_control import is_head_engineer

@admin.register(BarangayMetadata)
class BarangayMetadataAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'barangay_class', 
        'economic_class', 
        'elevation_type',
        'population',
        'density',
        'growth_rate'
    ]
    list_filter = [
        'barangay_class',
        'economic_class',
        'elevation_type'
    ]
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    # Note: Head Engineers are admins (is_head_engineer checks for is_superuser)
    # So they automatically have access to Django admin
    # No additional permission checks needed
```

**Action Items:**
- [ ] Register model in admin
- [ ] Test admin interface (Head Engineers can access as admins)
- [ ] Verify CRUD operations
- [ ] Confirm Head Engineers can manage barangay metadata

---

## **PHASE 2: API & Backend Integration** (Week 2)

### Step 2.1: Create API Endpoints

**File**: `projeng/views.py` (or create `projeng/api_views.py`)

```python
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Sum, Q
from .models import BarangayMetadata, Project
from gistagum.access_control import is_head_engineer

@require_http_methods(["GET"])
def barangay_metadata_api(request):
    """
    Return all barangay metadata.
    Accessible to Head Engineers (who are admins) and authenticated users.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    barangays = BarangayMetadata.objects.all()
    data = []
    for barangay in barangays:
        data.append({
            'name': barangay.name,
            'population': barangay.population,
            'land_area': float(barangay.land_area) if barangay.land_area else None,
            'density': float(barangay.density) if barangay.density else None,
            'growth_rate': float(barangay.growth_rate) if barangay.growth_rate else None,
            'barangay_class': barangay.barangay_class,
            'economic_class': barangay.economic_class,
            'elevation_type': barangay.elevation_type,
            'industrial_zones': barangay.industrial_zones,
            'primary_industries': barangay.primary_industries,
            'special_features': barangay.special_features,
            'zoning_summary': barangay.get_zoning_summary(),
        })
    return JsonResponse({'barangays': data})

@require_http_methods(["GET"])
def barangay_zoning_stats_api(request):
    """
    Return zoning statistics with project counts.
    Accessible to Head Engineers (who are admins).
    """
    if not is_head_engineer(request.user):
        return JsonResponse({'error': 'Head Engineer access required'}, status=403)
    
    # Get project counts per barangay
    project_counts = Project.objects.values('barangay').annotate(
        total_projects=Count('id'),
        total_cost=Sum('project_cost'),
        completed=Count('id', filter=Q(status='completed')),
        ongoing=Count('id', filter=Q(status__in=['in_progress', 'ongoing'])),
        planned=Count('id', filter=Q(status='planned')),
    )
    
    # Combine with metadata
    stats = {}
    for barangay in BarangayMetadata.objects.all():
        project_data = next(
            (p for p in project_counts if p['barangay'] == barangay.name),
            {}
        )
        stats[barangay.name] = {
            'metadata': {
                'barangay_class': barangay.barangay_class,
                'economic_class': barangay.economic_class,
                'elevation_type': barangay.elevation_type,
                'population': barangay.population,
                'density': float(barangay.density) if barangay.density else None,
            },
            'projects': {
                'total': project_data.get('total_projects', 0),
                'completed': project_data.get('completed', 0),
                'ongoing': project_data.get('ongoing', 0),
                'planned': project_data.get('planned', 0),
                'total_cost': float(project_data.get('total_cost', 0)) if project_data.get('total_cost') else 0,
            }
        }
    
    return JsonResponse({'stats': stats})
```

**File**: `projeng/urls.py`

```python
from gistagum.access_control import head_engineer_required

urlpatterns = [
    # ... existing patterns
    path('api/barangay-metadata/', views.barangay_metadata_api, name='barangay_metadata_api'),
    path('api/barangay-zoning-stats/', head_engineer_required(views.barangay_zoning_stats_api), name='barangay_zoning_stats_api'),
]
```

**Note**: 
- `barangay_metadata_api` - Accessible to all authenticated users (for map display)
- `barangay_zoning_stats_api` - Restricted to Head Engineers only (for analytics dashboard)

**Action Items:**
- [ ] Create API endpoints
- [ ] Add URL routes with appropriate access control
- [ ] Test endpoints with Postman/curl
- [ ] Verify Head Engineers can access stats API
- [ ] Verify JSON response format

---

### Step 2.2: Enhance Project Model Relationship

**File**: `projeng/models.py`

```python
class Project(models.Model):
    # ... existing fields ...
    barangay = models.CharField(max_length=255, blank=True, null=True)
    
    # Add method to get metadata
    def get_barangay_metadata(self):
        """Get related BarangayMetadata if barangay name matches"""
        if not self.barangay:
            return None
        try:
            return BarangayMetadata.objects.get(name=self.barangay)
        except BarangayMetadata.DoesNotExist:
            return None
```

**Action Items:**
- [ ] Add helper method to Project model
- [ ] Test relationship
- [ ] Update existing queries if needed

---

## **PHASE 3: Frontend Map Integration** (Week 3)

### Step 3.1: Enhance Choropleth Map with Zoning

**File**: `static/js/choropleth_map.js` or create new `static/js/zoning_map.js`

```javascript
class ZoningChoroplethMap {
    constructor(mapContainer, projectsData, zoningData) {
        this.map = null;
        this.mapContainer = mapContainer;
        this.projectsData = projectsData;
        this.zoningData = zoningData; // From API
        this.currentZoningLayer = null;
        this.currentView = 'projects'; // 'projects', 'urban_rural', 'economic', 'elevation'
        this.filters = {
            barangay_class: [],
            economic_class: [],
            elevation_type: [],
            industrial_zones: []
        };
        this.init();
    }

    init() {
        // Initialize map (similar to existing)
        this.map = L.map(this.mapContainer).setView([7.4475, 125.8096], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);
        
        // Load zoning data
        this.loadZoningData();
    }

    async loadZoningData() {
        try {
            const response = await fetch('/api/barangay-metadata/');
            const data = await response.json();
            this.zoningData = data.barangays;
            this.createZoningLayers();
        } catch (error) {
            console.error('Error loading zoning data:', error);
        }
    }

    createZoningLayers() {
        // Create different layer groups for different zoning views
        this.urbanRuralLayer = this.createBarangayClassLayer();
        this.economicLayer = this.createEconomicClassLayer();
        this.elevationLayer = this.createElevationLayer();
        
        // Default to projects view
        this.showProjectsView();
    }

    createBarangayClassLayer() {
        // Color code by Urban/Rural
        const geoJSON = this.getBarangayGeoJSON();
        
        return L.geoJSON(geoJSON, {
            style: (feature) => {
                const barangay = this.zoningData.find(b => b.name === feature.properties.name);
                const color = barangay?.barangay_class === 'urban' ? '#ef4444' : '#fbbf24'; // Red for urban, yellow for rural
                return {
                    fillColor: color,
                    weight: 2,
                    opacity: 1,
                    color: '#333',
                    fillOpacity: 0.6
                };
            },
            onEachFeature: (feature, layer) => {
                const barangay = this.zoningData.find(b => b.name === feature.properties.name);
                const popup = this.createZoningPopup(feature, barangay);
                layer.bindPopup(popup);
            }
        });
    }

    createEconomicClassLayer() {
        // Color code by Economic Classification
        const geoJSON = this.getBarangayGeoJSON();
        
        return L.geoJSON(geoJSON, {
            style: (feature) => {
                const barangay = this.zoningData.find(b => b.name === feature.properties.name);
                let color = '#ccc'; // Default
                if (barangay) {
                    switch(barangay.economic_class) {
                        case 'growth_center': color = '#3b82f6'; break; // Blue
                        case 'emerging': color = '#10b981'; break; // Green
                        case 'satellite': color = '#fbbf24'; break; // Yellow
                    }
                }
                return {
                    fillColor: color,
                    weight: 2,
                    opacity: 1,
                    color: '#333',
                    fillOpacity: 0.6
                };
            },
            onEachFeature: (feature, layer) => {
                const barangay = this.zoningData.find(b => b.name === feature.properties.name);
                const popup = this.createZoningPopup(feature, barangay);
                layer.bindPopup(popup);
            }
        });
    }

    createElevationLayer() {
        // Color code by Elevation Type
        const geoJSON = this.getBarangayGeoJSON();
        
        return L.geoJSON(geoJSON, {
            style: (feature) => {
                const barangay = this.zoningData.find(b => b.name === feature.properties.name);
                let color = '#ccc';
                if (barangay) {
                    switch(barangay.elevation_type) {
                        case 'highland': color = '#8b5cf6'; break; // Purple
                        case 'plains': color = '#84cc16'; break; // Green
                        case 'coastal': color = '#06b6d4'; break; // Cyan
                    }
                }
                return {
                    fillColor: color,
                    weight: 2,
                    opacity: 1,
                    color: '#333',
                    fillOpacity: 0.6
                };
            },
            onEachFeature: (feature, layer) => {
                const barangay = this.zoningData.find(b => b.name === feature.properties.name);
                const popup = this.createZoningPopup(feature, barangay);
                layer.bindPopup(popup);
            }
        });
    }

    createZoningPopup(feature, barangay) {
        if (!barangay) {
            return `<h3>${feature.properties.name}</h3><p>No zoning data available</p>`;
        }
        
        return `
            <div style="min-width: 250px;">
                <h3 style="margin: 0 0 10px 0;">${feature.properties.name}</h3>
                <div style="margin: 5px 0;">
                    <strong>Classification:</strong> ${barangay.barangay_class || 'N/A'}
                </div>
                <div style="margin: 5px 0;">
                    <strong>Economic Type:</strong> ${barangay.economic_class || 'N/A'}
                </div>
                <div style="margin: 5px 0;">
                    <strong>Elevation:</strong> ${barangay.elevation_type || 'N/A'}
                </div>
                <div style="margin: 5px 0;">
                    <strong>Population:</strong> ${barangay.population?.toLocaleString() || 'N/A'}
                </div>
                <div style="margin: 5px 0;">
                    <strong>Density:</strong> ${barangay.density?.toLocaleString() || 'N/A'} /km²
                </div>
                <div style="margin: 5px 0;">
                    <strong>Growth Rate:</strong> ${barangay.growth_rate || 'N/A'}%
                </div>
            </div>
        `;
    }

    switchView(viewType) {
        // Remove current layer
        if (this.currentZoningLayer) {
            this.map.removeLayer(this.currentZoningLayer);
        }
        
        // Add new layer based on view
        switch(viewType) {
            case 'urban_rural':
                this.currentZoningLayer = this.urbanRuralLayer;
                break;
            case 'economic':
                this.currentZoningLayer = this.economicLayer;
                break;
            case 'elevation':
                this.currentZoningLayer = this.elevationLayer;
                break;
            case 'projects':
                // Show projects choropleth (existing functionality)
                this.showProjectsView();
                return;
        }
        
        this.currentZoningLayer.addTo(this.map);
        this.currentView = viewType;
    }

    showProjectsView() {
        // Use existing choropleth functionality
        // This would integrate with your existing SimpleChoropleth class
    }
}
```

**Action Items:**
- [ ] Create new ZoningChoroplethMap class
- [ ] Integrate with existing map
- [ ] Test zoning layer switching
- [ ] Verify popup information

---

### Step 3.2: Add Zoning Controls UI

**File**: `templates/monitoring/map_choropleth.html` (or wherever map is displayed)

```html
<!-- Zoning Controls Panel -->
<div id="zoning-controls" class="bg-white p-4 rounded-lg shadow-lg mb-4">
    <h3 class="text-lg font-semibold mb-3">Zoning View</h3>
    
    <!-- View Type Selector -->
    <div class="mb-4">
        <label class="block text-sm font-medium mb-2">View Type</label>
        <select id="zoning-view-selector" class="w-full border rounded px-3 py-2">
            <option value="projects">Projects (Default)</option>
            <option value="urban_rural">Urban / Rural</option>
            <option value="economic">Economic Classification</option>
            <option value="elevation">Elevation Type</option>
        </select>
    </div>
    
    <!-- Filters -->
    <div class="mb-4">
        <label class="block text-sm font-medium mb-2">Filters</label>
        
        <!-- Barangay Class Filter -->
        <div class="mb-2">
            <label class="text-xs text-gray-600">Barangay Class</label>
            <div class="flex gap-2 mt-1">
                <label class="flex items-center">
                    <input type="checkbox" class="zoning-filter" data-type="barangay_class" value="urban">
                    <span class="ml-1 text-sm">Urban</span>
                </label>
                <label class="flex items-center">
                    <input type="checkbox" class="zoning-filter" data-type="barangay_class" value="rural">
                    <span class="ml-1 text-sm">Rural</span>
                </label>
            </div>
        </div>
        
        <!-- Economic Class Filter -->
        <div class="mb-2">
            <label class="text-xs text-gray-600">Economic Class</label>
            <div class="flex flex-col gap-1 mt-1">
                <label class="flex items-center">
                    <input type="checkbox" class="zoning-filter" data-type="economic_class" value="growth_center">
                    <span class="ml-1 text-sm">Growth Center</span>
                </label>
                <label class="flex items-center">
                    <input type="checkbox" class="zoning-filter" data-type="economic_class" value="emerging">
                    <span class="ml-1 text-sm">Emerging</span>
                </label>
                <label class="flex items-center">
                    <input type="checkbox" class="zoning-filter" data-type="economic_class" value="satellite">
                    <span class="ml-1 text-sm">Satellite</span>
                </label>
            </div>
        </div>
        
        <!-- Elevation Filter -->
        <div class="mb-2">
            <label class="text-xs text-gray-600">Elevation</label>
            <div class="flex flex-col gap-1 mt-1">
                <label class="flex items-center">
                    <input type="checkbox" class="zoning-filter" data-type="elevation_type" value="highland">
                    <span class="ml-1 text-sm">Highland</span>
                </label>
                <label class="flex items-center">
                    <input type="checkbox" class="zoning-filter" data-type="elevation_type" value="plains">
                    <span class="ml-1 text-sm">Plains</span>
                </label>
                <label class="flex items-center">
                    <input type="checkbox" class="zoning-filter" data-type="elevation_type" value="coastal">
                    <span class="ml-1 text-sm">Coastal</span>
                </label>
            </div>
        </div>
    </div>
    
    <!-- Legend -->
    <div id="zoning-legend" class="text-xs">
        <!-- Dynamically populated based on selected view -->
    </div>
</div>
```

**Action Items:**
- [ ] Add UI controls to map template
- [ ] Style controls panel
- [ ] Connect JavaScript event handlers
- [ ] Test filter functionality

---

### Step 3.3: Add Zoning Legend

**File**: `static/js/zoning_map.js` (add to existing class)

```javascript
createZoningLegend(viewType) {
    if (this.legend) {
        this.map.removeControl(this.legend);
    }
    
    this.legend = L.control({ position: 'bottomright' });
    
    this.legend.onAdd = (map) => {
        const div = L.DomUtil.create('div', 'info legend');
        div.style.backgroundColor = 'white';
        div.style.padding = '10px';
        div.style.borderRadius = '5px';
        
        let html = '<h4 style="margin: 0 0 8px 0;">Legend</h4>';
        
        switch(viewType) {
            case 'urban_rural':
                html += '<div><i style="background: #ef4444; width: 16px; height: 16px; display: inline-block; margin-right: 5px;"></i> Urban</div>';
                html += '<div><i style="background: #fbbf24; width: 16px; height: 16px; display: inline-block; margin-right: 5px;"></i> Rural</div>';
                break;
            case 'economic':
                html += '<div><i style="background: #3b82f6; width: 16px; height: 16px; display: inline-block; margin-right: 5px;"></i> Growth Center</div>';
                html += '<div><i style="background: #10b981; width: 16px; height: 16px; display: inline-block; margin-right: 5px;"></i> Emerging</div>';
                html += '<div><i style="background: #fbbf24; width: 16px; height: 16px; display: inline-block; margin-right: 5px;"></i> Satellite</div>';
                break;
            case 'elevation':
                html += '<div><i style="background: #8b5cf6; width: 16px; height: 16px; display: inline-block; margin-right: 5px;"></i> Highland</div>';
                html += '<div><i style="background: #84cc16; width: 16px; height: 16px; display: inline-block; margin-right: 5px;"></i> Plains</div>';
                html += '<div><i style="background: #06b6d4; width: 16px; height: 16px; display: inline-block; margin-right: 5px;"></i> Coastal</div>';
                break;
        }
        
        div.innerHTML = html;
        return div;
    };
    
    this.legend.addTo(this.map);
}
```

**Action Items:**
- [ ] Add legend creation method
- [ ] Update legend on view change
- [ ] Style legend appropriately

---

## **PHASE 4: Analytics & Dashboard** (Week 4)

**Note**: All analytics and dashboard features are for **Head Engineers only** (who are admins).  
Access control is already handled by `@head_engineer_required` decorator on dashboard views.

### Step 4.1: Add Zoning Analytics Charts

**File**: `HEAD_ENGINEER_CHART_RECOMMENDATIONS.md` (update with new charts)

**New Charts to Add:**

#### Chart 13: **Project Distribution by Zoning Type**
- Type: Stacked Bar Chart
- X-axis: Zoning categories (Urban/Rural, Economic Class, Elevation)
- Y-axis: Number of projects or budget
- Stack by: Project status

#### Chart 14: **Population Density vs. Project Investment**
- Type: Scatter Plot
- X-axis: Population density
- Y-axis: Total project investment
- Color: Zoning classification

#### Chart 15: **Growth Rate vs. Project Allocation**
- Type: Dual-Axis Chart
- Primary: Population growth rate
- Secondary: Number of planned projects

**Action Items:**
- [ ] Create chart data endpoints
- [ ] Add charts to dashboard
- [ ] Style and position charts
- [ ] Test chart interactivity

---

### Step 4.2: Create Zoning Insights Panel

**File**: `templates/monitoring/dashboard.html` (or wherever dashboard is)

```html
<!-- Zoning Insights Panel -->
<div class="bg-white p-6 rounded-lg shadow-lg">
    <h2 class="text-xl font-bold mb-4">Zoning Insights</h2>
    
    <!-- Key Metrics -->
    <div class="grid grid-cols-3 gap-4 mb-6">
        <div class="bg-blue-50 p-4 rounded">
            <div class="text-sm text-gray-600">Growth Centers</div>
            <div class="text-2xl font-bold" id="growth-center-projects">-</div>
            <div class="text-xs text-gray-500">projects</div>
        </div>
        <div class="bg-green-50 p-4 rounded">
            <div class="text-sm text-gray-600">Emerging Areas</div>
            <div class="text-2xl font-bold" id="emerging-projects">-</div>
            <div class="text-xs text-gray-500">projects</div>
        </div>
        <div class="bg-yellow-50 p-4 rounded">
            <div class="text-sm text-gray-600">Coastal Areas</div>
            <div class="text-2xl font-bold" id="coastal-projects">-</div>
            <div class="text-xs text-gray-500">projects</div>
        </div>
    </div>
    
    <!-- Alerts/Warnings -->
    <div id="zoning-alerts" class="space-y-2">
        <!-- Dynamically populated with insights like:
        - "High-density area with low project investment"
        - "Fast-growing area needs proactive planning"
        -->
    </div>
</div>
```

**Action Items:**
- [ ] Create insights panel
- [ ] Add API endpoint for insights
- [ ] Populate with real data
- [ ] Add alert styling

---

## **PHASE 5: Testing & Refinement** (Week 5)

### Step 5.1: Data Validation
- [ ] Verify all 23 barangays have metadata
- [ ] Check data accuracy against source
- [ ] Validate relationships between projects and barangays

### Step 5.2: Performance Testing
- [ ] Test map performance with all layers
- [ ] Optimize API queries
- [ ] Check page load times

### Step 5.3: User Testing
- [ ] Test zoning view switching
- [ ] Test filter combinations
- [ ] Verify popup information accuracy
- [ ] Check mobile responsiveness

### Step 5.4: Documentation
- [ ] Document API endpoints
- [ ] Create user guide for zoning features
- [ ] Update README with zoning information

---

## **Data Extraction Checklist**

From the infographic, extract for all 23 barangays:

- [ ] Apokon
- [ ] Bincungan
- [ ] Busaon
- [ ] Canocotan
- [ ] Cuambogan
- [ ] La Filipina
- [ ] Liboganon
- [ ] Madaum
- [ ] Magdum
- [ ] Magugpo East
- [ ] Magugpo North
- [ ] Magugpo Poblacion
- [ ] Magugpo South
- [ ] Magugpo West
- [ ] Mankilam
- [ ] New Balamban
- [ ] Nueva Fuerza
- [ ] Pagsabangan
- [ ] Pandapan
- [ ] San Agustin
- [ ] San Isidro
- [ ] San Miguel
- [ ] Visayan Village

For each barangay, extract:
- Population
- Land area
- Density
- Growth rate
- Barangay class (Urban/Rural)
- Economic class (Growth Center/Emerging/Satellite)
- Elevation type (Highland/Plains/Coastal)
- Industrial zones
- Primary industries
- Special features

---

## **Success Criteria**

✅ All 23 barangays have complete metadata  
✅ Map displays zoning overlays correctly  
✅ Users can switch between zoning views  
✅ Filters work correctly  
✅ Analytics charts show zoning insights  
✅ Performance is acceptable  
✅ Mobile responsive  

---

## **Timeline Summary**

- **Week 1**: Database foundation (Model, Migration, Data)
- **Week 2**: API endpoints and backend integration
- **Week 3**: Frontend map integration and controls
- **Week 4**: Analytics and dashboard enhancements
- **Week 5**: Testing, refinement, and documentation

**Total Estimated Time**: 5 weeks

---

## **Next Steps**

1. **Start with Phase 1**: Create the BarangayMetadata model
2. **Extract data**: Systematically extract all barangay data from the image
3. **Populate database**: Use management command to load data
4. **Test incrementally**: Test each phase before moving to next

Would you like me to start implementing Phase 1, or do you want to review this plan first?

