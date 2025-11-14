# 🗺️ Head Engineer Project Creation with Map Location Picker
## Implementation Plan

---

## 🎯 Requirements

1. **Only Head Engineers** can create projects
2. **Map-based location picker** - click on map to set coordinates
3. **Location is required** - cannot save without coordinates
4. **Visual feedback** - clear indication when location is set

---

## 📋 Implementation Steps

### **Step 1: Restrict Project Creation to Head Engineers Only**

#### 1.1 Update View Decorator
**File:** `monitoring/views/__init__.py`

**Current:**
```python
@login_required
@prevent_project_engineer_access  # Allows Head Engineers AND Finance Managers
def project_list(request):
```

**Change to:**
```python
@login_required
@head_engineer_required  # Only Head Engineers
def project_list(request):
```

#### 1.2 Update Form Validation
**File:** `monitoring/forms.py`

**Add location requirement:**
```python
class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'prn', 'name', 'description', 'barangay', 'project_cost', 'source_of_funds',
            'status', 'latitude', 'longitude', 'start_date', 'end_date', 'image', 'assigned_engineers'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ... existing code ...
        
        # Make location required
        self.fields['latitude'].required = True
        self.fields['longitude'].required = True
        self.fields['latitude'].help_text = 'Click "Set Map Location" to select coordinates'
        self.fields['longitude'].help_text = 'Click "Set Map Location" to select coordinates'
    
    def clean(self):
        cleaned_data = super().clean()
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        
        # Ensure both coordinates are provided
        if not latitude or not longitude:
            raise ValidationError({
                'latitude': 'Location is required. Please select a location on the map.',
                'longitude': 'Location is required. Please select a location on the map.'
            })
        
        # Validate coordinate ranges (Tagum City is approximately 7.3-7.5°N, 125.7-125.9°E)
        if latitude and (latitude < 7.0 or latitude > 8.0):
            raise ValidationError({
                'latitude': 'Latitude must be within Tagum City bounds (approximately 7.0-8.0°N)'
            })
        
        if longitude and (longitude < 125.0 or longitude > 126.0):
            raise ValidationError({
                'longitude': 'Longitude must be within Tagum City bounds (approximately 125.0-126.0°E)'
            })
        
        # ... rest of existing validation ...
        
        return cleaned_data
```

---

### **Step 2: Enhance Map Location Picker**

#### 2.1 Update Project Form Template
**File:** `templates/monitoring/project_list.html`

**Enhance the location section:**
```html
<!-- Column 3: Location, Dates & Image -->
<div class="flex flex-col gap-4">
    <!-- Location Section with Map Picker -->
    <div class="border-2 border-dashed border-blue-300 rounded-lg p-4 bg-blue-50">
        <label class="font-semibold text-blue-700 mb-2 block">
            📍 Project Location <span class="text-red-500">*</span>
        </label>
        <p class="text-sm text-gray-600 mb-3">
            Click the button below to select the exact location on the map
        </p>
        
        <!-- Location Display -->
        <div class="grid grid-cols-2 gap-3 mb-3">
            <div>
                <label class="text-xs font-medium text-gray-600">Latitude</label>
                <input 
                    type="number" 
                    step="any" 
                    name="latitude" 
                    id="latitude-input" 
                    class="w-full rounded-lg border-2 border-blue-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-400 focus:border-blue-400 outline-none bg-white" 
                    required
                    readonly
                    placeholder="Click map to set"
                />
            </div>
            <div>
                <label class="text-xs font-medium text-gray-600">Longitude</label>
                <input 
                    type="number" 
                    step="any" 
                    name="longitude" 
                    id="longitude-input" 
                    class="w-full rounded-lg border-2 border-blue-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-400 focus:border-blue-400 outline-none bg-white" 
                    required
                    readonly
                    placeholder="Click map to set"
                />
            </div>
        </div>
        
        <!-- Map Picker Button -->
        <button 
            type="button" 
            id="map-fullscreen-btn" 
            class="w-full bg-blue-700 hover:bg-blue-800 text-white font-semibold px-4 py-3 rounded-lg shadow-lg transition flex items-center justify-center gap-2 text-sm"
            title="Click to open map and select location"
        >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span id="map-btn-text">Select Location on Map</span>
        </button>
        
        <!-- Location Status Indicator -->
        <div id="location-status" class="mt-2 text-xs hidden">
            <span class="inline-flex items-center gap-1 px-2 py-1 rounded bg-green-100 text-green-700">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                Location selected
            </span>
        </div>
    </div>
    
    <!-- Rest of the form fields -->
    <label class="font-semibold text-gray-700">Start Date</label>
    <!-- ... existing fields ... -->
</div>
```

#### 2.2 Enhance Map Popup Modal
**File:** `templates/monitoring/project_list.html`

**Update the map popup modal:**
```html
<!-- Map Popup Modal -->
<div id="map-popup-modal" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60 overflow-y-auto hidden">
    <div class="bg-white rounded-2xl shadow-2xl w-full max-w-5xl p-6 relative mx-4 my-4">
        <button type="button" id="close-map-popup" class="absolute top-4 right-4 z-30 w-10 h-10 flex items-center justify-center bg-blue-700 text-white text-2xl rounded-full border-4 border-white shadow-lg hover:bg-blue-800 focus:outline-none focus:ring-4 focus:ring-blue-300 transition-all duration-200">&times;</button>
        
        <div class="mb-4">
            <h2 class="text-2xl font-bold text-gray-800 mb-2">📍 Select Project Location</h2>
            <p class="text-gray-600 text-sm">
                Click anywhere on the map to set the project location. The marker will show your selected point.
            </p>
        </div>
        
        <div id="popup-map" style="min-height:400px; height:70vh; background:#eee;" class="rounded-lg border-2 border-blue-300 w-full mb-4"></div>
        
        <div class="flex items-center justify-between bg-blue-50 p-4 rounded-lg mb-4">
            <div>
                <p class="text-sm font-medium text-gray-700">Selected Coordinates:</p>
                <p class="text-lg font-mono text-blue-700">
                    <span id="selected-lat-display">--</span>°N, 
                    <span id="selected-lng-display">--</span>°E
                </p>
            </div>
            <button 
                type="button" 
                id="use-current-location-btn" 
                class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg shadow transition flex items-center gap-2 text-sm"
            >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
                </svg>
                Use My Location
            </button>
        </div>
        
        <div class="flex justify-end gap-4">
            <button type="button" id="close-map-popup-btn" class="px-6 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold rounded-lg shadow transition">Cancel</button>
            <button type="button" id="confirm-location-btn" class="px-6 py-2 bg-blue-700 hover:bg-blue-800 text-white font-semibold rounded-lg shadow transition flex items-center gap-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
                Confirm Location
            </button>
        </div>
    </div>
</div>
```

#### 2.3 Enhance JavaScript for Map Picker
**File:** `templates/monitoring/project_list.html`

**Update the map picker JavaScript:**
```javascript
// --- Enhanced Popup Map Modal Logic ---
let popupMap = null;
let popupMarker = null;
const mapPopupModal = document.getElementById('map-popup-modal');
const popupMapDiv = document.getElementById('popup-map');
const closeMapPopup = document.getElementById('close-map-popup');
const closeMapPopupBtn = document.getElementById('close-map-popup-btn');
const mapFullscreenBtn = document.getElementById('map-fullscreen-btn');
const latInput = document.getElementById('latitude-input');
const lngInput = document.getElementById('longitude-input');
const locationStatus = document.getElementById('location-status');
const mapBtnText = document.getElementById('map-btn-text');
const selectedLatDisplay = document.getElementById('selected-lat-display');
const selectedLngDisplay = document.getElementById('selected-lng-display');
const confirmLocationBtn = document.getElementById('confirm-location-btn');
const useCurrentLocationBtn = document.getElementById('use-current-location-btn');

// Update location status indicator
function updateLocationStatus() {
    const hasLocation = latInput.value && lngInput.value;
    if (hasLocation) {
        locationStatus.classList.remove('hidden');
        mapBtnText.textContent = 'Change Location';
        latInput.classList.remove('border-red-300');
        lngInput.classList.remove('border-red-300');
        latInput.classList.add('border-green-400');
        lngInput.classList.add('border-green-400');
    } else {
        locationStatus.classList.add('hidden');
        mapBtnText.textContent = 'Select Location on Map';
        latInput.classList.remove('border-green-400');
        lngInput.classList.remove('border-green-400');
        latInput.classList.add('border-red-300');
        lngInput.classList.add('border-red-300');
    }
}

// Update coordinate displays
function updateCoordinateDisplays() {
    if (latInput.value && lngInput.value) {
        selectedLatDisplay.textContent = parseFloat(latInput.value).toFixed(6);
        selectedLngDisplay.textContent = parseFloat(lngInput.value).toFixed(6);
    } else {
        selectedLatDisplay.textContent = '--';
        selectedLngDisplay.textContent = '--';
    }
}

function showPopupMap() {
    if (mapPopupModal) {
        mapPopupModal.classList.remove('hidden');
        setTimeout(() => {
            let lat = parseFloat(latInput.value) || 7.4475; // Default to Tagum City center
            let lng = parseFloat(lngInput.value) || 125.8078;
            let zoom = 13;

            // Use barangay coordinates if a barangay is selected
            const selectedBarangay = modalBarangaySelect.value;
            if (selectedBarangay && barangayCoordinates[selectedBarangay]) {
                [lat, lng] = barangayCoordinates[selectedBarangay];
                zoom = 14;
            } else if (latInput.value && lngInput.value) {
                lat = parseFloat(latInput.value);
                lng = parseFloat(lngInput.value);
                zoom = 15; // Zoom in more if coordinates exist
            }

            // Initialize map
            if (!popupMap) {
                if (L.DomUtil.get('popup-map')) {
                    L.DomUtil.get('popup-map')._leaflet_id = null;
                }
                popupMap = L.map('popup-map').setView([lat, lng], zoom);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '© OpenStreetMap contributors'
                }).addTo(popupMap);
                
                // Add click listener to update coordinates
                popupMap.on('click', function(e) {
                    const clickedLat = e.latlng.lat;
                    const clickedLng = e.latlng.lng;
                    
                    // Update inputs
                    latInput.value = clickedLat.toFixed(6);
                    lngInput.value = clickedLng.toFixed(6);
                    
                    // Update displays
                    updateCoordinateDisplays();
                    
                    // Update marker
                    if (popupMarker) {
                        popupMarker.setLatLng([clickedLat, clickedLng]);
                    } else {
                        popupMarker = L.marker([clickedLat, clickedLng], {
                            draggable: true
                        }).addTo(popupMap);
                        
                        // Allow dragging marker
                        popupMarker.on('dragend', function(e) {
                            const pos = popupMarker.getLatLng();
                            latInput.value = pos.lat.toFixed(6);
                            lngInput.value = pos.lng.toFixed(6);
                            updateCoordinateDisplays();
                        });
                    }
                    
                    // Show popup with coordinates
                    popupMarker.bindPopup(`
                        <div class="text-center">
                            <strong>Selected Location</strong><br>
                            ${clickedLat.toFixed(6)}°N, ${clickedLng.toFixed(6)}°E
                        </div>
                    `).openPopup();
                });
            } else {
                popupMap.setView([lat, lng], zoom);
            }

            // Remove existing marker
            if (popupMarker) {
                popupMap.removeLayer(popupMarker);
                popupMarker = null;
            }

            // Add marker if coordinates exist
            if (latInput.value && lngInput.value) {
                const markerLat = parseFloat(latInput.value);
                const markerLng = parseFloat(lngInput.value);
                popupMarker = L.marker([markerLat, markerLng], {
                    draggable: true
                }).addTo(popupMap);
                
                popupMarker.bindPopup(`
                    <div class="text-center">
                        <strong>Current Location</strong><br>
                        ${markerLat.toFixed(6)}°N, ${markerLng.toFixed(6)}°E
                    </div>
                `).openPopup();
                
                // Allow dragging
                popupMarker.on('dragend', function(e) {
                    const pos = popupMarker.getLatLng();
                    latInput.value = pos.lat.toFixed(6);
                    lngInput.value = pos.lng.toFixed(6);
                    updateCoordinateDisplays();
                });
            }
            
            updateCoordinateDisplays();
            setTimeout(() => { popupMap.invalidateSize(); }, 350);
        }, 100);
    }
}

function hidePopupMap() {
    if (mapPopupModal) {
        mapPopupModal.classList.add('hidden');
        updateLocationStatus();
    }
}

// Use current location (browser geolocation)
if (useCurrentLocationBtn) {
    useCurrentLocationBtn.addEventListener('click', function() {
        if (!navigator.geolocation) {
            alert('Geolocation is not supported by your browser.');
            return;
        }
        
        useCurrentLocationBtn.disabled = true;
        useCurrentLocationBtn.textContent = 'Getting location...';
        
        navigator.geolocation.getCurrentPosition(
            function(position) {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                
                // Check if within Tagum City bounds (approximate)
                if (lat >= 7.0 && lat <= 8.0 && lng >= 125.0 && lng <= 126.0) {
                    latInput.value = lat.toFixed(6);
                    lngInput.value = lng.toFixed(6);
                    
                    if (popupMap) {
                        popupMap.setView([lat, lng], 16);
                        
                        if (popupMarker) {
                            popupMarker.setLatLng([lat, lng]);
                        } else {
                            popupMarker = L.marker([lat, lng], {
                                draggable: true
                            }).addTo(popupMap);
                            
                            popupMarker.on('dragend', function(e) {
                                const pos = popupMarker.getLatLng();
                                latInput.value = pos.lat.toFixed(6);
                                lngInput.value = pos.lng.toFixed(6);
                                updateCoordinateDisplays();
                            });
                        }
                        
                        popupMarker.bindPopup(`
                            <div class="text-center">
                                <strong>Your Location</strong><br>
                                ${lat.toFixed(6)}°N, ${lng.toFixed(6)}°E
                            </div>
                        `).openPopup();
                    }
                    
                    updateCoordinateDisplays();
                } else {
                    alert('Your location is outside Tagum City. Please select a location on the map.');
                }
                
                useCurrentLocationBtn.disabled = false;
                useCurrentLocationBtn.innerHTML = `
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
                    </svg>
                    Use My Location
                `;
            },
            function(error) {
                alert('Unable to get your location: ' + error.message);
                useCurrentLocationBtn.disabled = false;
                useCurrentLocationBtn.innerHTML = `
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
                    </svg>
                    Use My Location
                `;
            }
        );
    });
}

// Confirm location button
if (confirmLocationBtn) {
    confirmLocationBtn.addEventListener('click', function() {
        if (latInput.value && lngInput.value) {
            hidePopupMap();
        } else {
            alert('Please select a location on the map first.');
        }
    });
}

// Event listeners
if (mapFullscreenBtn) {
    mapFullscreenBtn.addEventListener('click', showPopupMap);
}
if (closeMapPopup) closeMapPopup.addEventListener('click', hidePopupMap);
if (closeMapPopupBtn) closeMapPopupBtn.addEventListener('click', hidePopupMap);

// Close modal when clicking outside
if (mapPopupModal) {
    mapPopupModal.addEventListener('mousedown', function(e) {
        if (e.target === mapPopupModal) {
            hidePopupMap();
        }
    });
}

// Update location status on page load
updateLocationStatus();

// Update location status when inputs change
if (latInput) latInput.addEventListener('input', updateLocationStatus);
if (lngInput) lngInput.addEventListener('input', updateLocationStatus);

// Validate location before form submission
if (projectForm) {
    projectForm.addEventListener('submit', function(e) {
        if (!latInput.value || !lngInput.value) {
            e.preventDefault();
            alert('⚠️ Please select a location on the map before saving the project.');
            showPopupMap();
            return false;
        }
    });
}
```

---

### **Step 3: Hide "Add Project" Button for Non-Head Engineers**

**File:** `templates/monitoring/project_list.html`

**Update the add button visibility:**
```html
{% if request.user.is_superuser or request.user.groups.all.0.name == 'Head Engineer' %}
<button id="add-project-btn" class="bg-blue-700 hover:bg-blue-800 text-white font-semibold px-6 py-3 rounded-lg shadow-lg transition flex items-center gap-2">
    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
    </svg>
    Add New Project
</button>
{% endif %}
```

---

### **Step 4: Add Visual Feedback**

**File:** `templates/monitoring/project_list.html`

**Add CSS for location status:**
```html
<style>
    #location-status {
        animation: fadeIn 0.3s ease-in;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-5px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    #latitude-input:invalid,
    #longitude-input:invalid {
        border-color: #ef4444;
    }
    
    #latitude-input:valid,
    #longitude-input:valid {
        border-color: #10b981;
    }
</style>
```

---

## ✅ Summary of Changes

### **Files to Modify:**

1. **`monitoring/views/__init__.py`**
   - Change `@prevent_project_engineer_access` to `@head_engineer_required`

2. **`monitoring/forms.py`**
   - Make latitude/longitude required
   - Add coordinate validation
   - Add helpful error messages

3. **`templates/monitoring/project_list.html`**
   - Enhance location section UI
   - Improve map popup modal
   - Add location status indicator
   - Add "Use My Location" button
   - Add form validation before submit
   - Hide "Add Project" button for non-Head Engineers

---

## 🎯 Features

✅ **Head Engineer Only** - Only Head Engineers can create projects  
✅ **Map-Based Selection** - Click on map to set location  
✅ **Required Location** - Cannot save without coordinates  
✅ **Visual Feedback** - Clear indicators when location is set  
✅ **Draggable Marker** - Can drag marker to adjust location  
✅ **Use My Location** - Optional browser geolocation  
✅ **Coordinate Validation** - Ensures coordinates are within Tagum City bounds  
✅ **User-Friendly** - Clear instructions and helpful UI

---

## 🚀 Testing Checklist

- [ ] Only Head Engineers can see "Add Project" button
- [ ] Finance Managers cannot access project creation
- [ ] Project Engineers cannot access project creation
- [ ] Map opens when clicking "Select Location on Map"
- [ ] Clicking map sets coordinates
- [ ] Dragging marker updates coordinates
- [ ] "Use My Location" button works (if browser supports it)
- [ ] Location status indicator shows when location is set
- [ ] Form validation prevents saving without location
- [ ] Coordinate validation works for out-of-bounds values
- [ ] Coordinates are saved correctly to database

---

**Ready to implement? Let's start!** 🎯

