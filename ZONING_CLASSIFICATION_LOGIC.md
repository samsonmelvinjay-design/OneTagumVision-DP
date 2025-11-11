# Zoning Classification Logic Documentation

## Overview

The zoning classification system categorizes Tagum City's 23 barangays using multiple dimensions to enable smart urban planning and strategic city development. Each barangay can be classified along **4 main dimensions**:

1. **Barangay Class** (Urban/Rural)
2. **Economic Classification** (Growth Center/Emerging/Satellite)
3. **Elevation Type** (Highland/Plains/Coastal)
4. **Industrial Zones** (Multiple zones possible)

---

## 1. Barangay Class (Urban/Rural)

### Logic
- **Urban**: Densely populated areas with developed infrastructure, commercial activity, and institutional facilities
- **Rural**: Less densely populated areas, typically agricultural or with natural resources

### Color Coding (Urban/Rural View)
```javascript
'urban' → #ef4444 (Red)
'rural' → #fbbf24 (Yellow)
'unclassified' → #cccccc (Gray)
```

### Criteria (from data analysis)
- **Urban**: High population density, presence of commercial centers, institutional facilities
- **Rural**: Lower density, agricultural focus, natural resource areas

### Examples
- **Urban**: Apokon, Magugpo Poblacion, Visayan Village, Mankilam
- **Rural**: Bincungan, Busaon, New Balamban, Nueva Fuerza

---

## 2. Economic Classification

### Logic
Three-tier economic development classification:

1. **Growth Center** (`growth_center`)
   - Primary economic hubs
   - High commercial activity
   - Major institutional presence
   - Strategic development areas

2. **Emerging** (`emerging`)
   - Developing areas with growth potential
   - Moderate commercial activity
   - Transitioning from rural to urban

3. **Satellite** (`satellite`)
   - Support areas for growth centers
   - Lower economic activity
   - Often agricultural or resource-based

### Color Coding (Economic View)
```javascript
'growth_center' → #3b82f6 (Blue)
'emerging' → #10b981 (Green)
'satellite' → #fbbf24 (Yellow)
'unclassified' → #cccccc (Gray)
```

### Examples
- **Growth Center**: Apokon, Magugpo Poblacion, San Miguel, Visayan Village, Mankilam
- **Emerging**: La Filipina, Madaum, Magdum, San Agustin
- **Satellite**: Bincungan, Busaon, Canocotan, Cuambogan

---

## 3. Elevation Type

### Logic
Geographic classification based on terrain:

1. **Highland/Rolling** (`highland`)
   - Elevated terrain
   - Different engineering challenges (drainage, slope stability)
   - Often agricultural or forested

2. **Plains/Lowland** (`plains`)
   - Flat terrain
   - Standard infrastructure requirements
   - Most urban areas

3. **Coastal** (`coastal`)
   - Near water bodies
   - Special engineering considerations (corrosion, flooding, marine protection)
   - Often tourism or fishery-based

### Color Coding (Elevation View)
```javascript
'highland' → #8b5cf6 (Purple)
'plains' → #84cc16 (Lime Green)
'coastal' → #06b6d4 (Cyan)
'unclassified' → #cccccc (Gray)
```

### Examples
- **Highland**: San Agustin, Pandapan
- **Plains**: Apokon, Magugpo Poblacion, Visayan Village, Mankilam
- **Coastal**: Bincungan, Busaon, Liboganon, Madaum

---

## 4. Industrial Zones

### Logic
**Multiple zones possible per barangay** (stored as JSON array)

### Zone Types

1. **Central Business District (CBD)** (`cbd`)
   - Core commercial areas
   - High-density development
   - Mixed-use zones

2. **Urban Expansion Area** (`urban_expansion`)
   - Areas designated for urban growth
   - Future development zones

3. **Commercial Expansion Area** (`commercial_expansion`)
   - Expanding commercial districts
   - Retail and service zones

4. **Institutional & Recreational** (`institutional_recreational`)
   - Government facilities
   - Educational institutions
   - Parks and recreational areas

5. **Agro-Industrial** (`agro_industrial`)
   - Agricultural processing
   - Food production
   - Rural industrial zones

### Examples
- **CBD**: Magugpo Poblacion, Visayan Village
- **Institutional & Recreational**: Apokon (university, hospital), Mankilam (sports complex)
- **Agro-Industrial**: Cuambogan (plywood, banana chips), Magdum (NESTLE, demo farm)
- **Commercial Expansion**: La Filipina, San Miguel

---

## Implementation Logic

### Data Structure
```python
class BarangayMetadata(models.Model):
    name = CharField  # Unique identifier
    barangay_class = CharField  # 'urban' or 'rural'
    economic_class = CharField  # 'growth_center', 'emerging', 'satellite'
    elevation_type = CharField  # 'highland', 'plains', 'coastal'
    industrial_zones = JSONField  # List of zone types
    # ... other fields
```

### Map Visualization Logic

The system uses a **switchView** mechanism to display different zoning classifications:

```javascript
switchView(viewType) {
    // viewType can be:
    // - 'projects' (default - shows project density)
    // - 'urban_rural' (shows urban/rural classification)
    // - 'economic' (shows economic classification)
    // - 'elevation' (shows elevation type)
}
```

### Color Assignment Logic

```javascript
createZoningLayer(viewType) {
    // For each barangay feature:
    const barangay = zoningData[barangayName];
    
    switch(viewType) {
        case 'urban_rural':
            color = barangay.barangay_class === 'urban' ? '#ef4444' : '#fbbf24';
            break;
        case 'economic':
            if (barangay.economic_class === 'growth_center') color = '#3b82f6';
            else if (barangay.economic_class === 'emerging') color = '#10b981';
            else if (barangay.economic_class === 'satellite') color = '#fbbf24';
            break;
        case 'elevation':
            if (barangay.elevation_type === 'highland') color = '#8b5cf6';
            else if (barangay.elevation_type === 'plains') color = '#84cc16';
            else if (barangay.elevation_type === 'coastal') color = '#06b6d4';
            break;
    }
}
```

---

## Use Cases for Smart Urban Planning

### 1. **Project Prioritization**
- **Growth Centers**: Prioritize high-impact infrastructure projects
- **Emerging Areas**: Focus on development-supporting projects
- **Satellite Areas**: Basic infrastructure maintenance

### 2. **Resource Allocation**
- **Urban Areas**: Complex infrastructure (utilities, transportation)
- **Rural Areas**: Agricultural infrastructure (irrigation, roads)
- **Coastal Areas**: Marine protection, flood control

### 3. **Strategic Development**
- **CBD Zones**: Commercial and mixed-use development
- **Urban Expansion**: Plan for future growth
- **Agro-Industrial**: Support agricultural economy

### 4. **Risk Assessment**
- **Coastal Areas**: Flood risk, corrosion concerns
- **Highland Areas**: Slope stability, drainage
- **High Density**: Infrastructure capacity planning

---

## Data Source

- **Primary Source**: PSA-2020 CPH (Philippine Statistics Authority - 2020 Census of Population and Housing)
- **Data Year**: 2020
- **Classification Basis**: Official government classifications and geographic data

---

## API Endpoints

### Get All Barangay Metadata
```
GET /projeng/api/barangay-metadata/
```
Returns all barangays with their zoning classifications.

### Get Zoning Statistics (Head Engineers Only)
```
GET /projeng/api/barangay-zoning-stats/
```
Returns zoning data combined with project statistics for analytics.

---

## Summary

The zoning classification system provides a **multi-dimensional view** of Tagum City's barangays, enabling:

1. **Visual Analysis**: Color-coded maps for quick identification
2. **Strategic Planning**: Data-driven decision making
3. **Resource Optimization**: Allocate resources based on classification
4. **Risk Management**: Identify areas with special requirements
5. **Growth Planning**: Plan for future development

Each classification dimension provides unique insights, and combining them gives a comprehensive understanding of each barangay's characteristics and development needs.

