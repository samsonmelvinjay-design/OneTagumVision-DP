// Simple Choropleth Map implementation for Tagum City Barangays
class SimpleChoropleth {
    constructor(map, geojsonUrl, projectsData = null) {
        this.map = map;
        this.geojsonUrl = geojsonUrl;
        this.projectsData = projectsData || [];
        this.choroplethLayer = null;
        this.legend = null;
        this.summaryPanel = null;
        this.barangayData = [];
        this.barangayStats = {};
    }

    calculateBarangayStats() {
        // Calculate statistics for each barangay
        this.barangayStats = {};
        
        this.projectsData.forEach(project => {
            const barangay = project.barangay;
            if (!barangay) return;
            
            if (!this.barangayStats[barangay]) {
                this.barangayStats[barangay] = {
                    totalProjects: 0,
                    totalCost: 0,
                    completedProjects: 0,
                    ongoingProjects: 0,
                    plannedProjects: 0
                };
            }
            
            this.barangayStats[barangay].totalProjects++;
            
            // Parse project cost
            let cost = 0;
            if (project.project_cost) {
                // Remove currency symbols and commas, then parse
                const costStr = project.project_cost.toString().replace(/[₱,]/g, '');
                cost = parseFloat(costStr) || 0;
            }
            this.barangayStats[barangay].totalCost += cost;
            
            // Count by status
            const status = project.status?.toLowerCase();
            if (status === 'completed') {
                this.barangayStats[barangay].completedProjects++;
            } else if (status === 'ongoing' || status === 'in_progress') {
                this.barangayStats[barangay].ongoingProjects++;
            } else if (status === 'planned' || status === 'pending') {
                this.barangayStats[barangay].plannedProjects++;
            }
        });
        
        console.log('Barangay statistics calculated:', this.barangayStats);
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-PH', {
            style: 'currency',
            currency: 'PHP',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount);
    }

    async loadData() {
        try {
            console.log('Loading GeoJSON data from:', this.geojsonUrl);
            const response = await fetch(this.geojsonUrl);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('GeoJSON data loaded:', data);
            
            this.barangayData = data.features || [];
            console.log(`Loaded ${this.barangayData.length} barangay features`);
            
            return data;
        } catch (error) {
            console.error('Error loading GeoJSON data:', error);
            throw error;
        }
    }

    createChoropleth() {
        if (!this.barangayData.length) {
            console.error('No barangay data available');
            return;
        }

        // Calculate barangay statistics
        this.calculateBarangayStats();

        // Clear existing choropleth layer
        if (this.choroplethLayer) {
            this.map.removeLayer(this.choroplethLayer);
        }

        // Create choropleth layer
        this.choroplethLayer = L.geoJSON(this.barangayData, {
            style: (feature) => {
                const color = feature.properties.color || '#FF6B6B';
                return {
                    fillColor: color,
                    weight: 2,
                    opacity: 1,
                    color: '#333',
                    fillOpacity: 0.7
                };
            },
            onEachFeature: (feature, layer) => {
                const name = feature.properties.name || 'Unknown';
                const stats = this.barangayStats[name] || {
                    totalProjects: 0,
                    totalCost: 0,
                    completedProjects: 0,
                    ongoingProjects: 0,
                    plannedProjects: 0
                };
                
                const popupContent = `
                    <div style="min-width: 200px;">
                        <h3 style="margin: 0 0 10px 0; color: #333;">${name}</h3>
                        <div style="margin: 5px 0;">
                            <strong>Total Projects:</strong> ${stats.totalProjects}
                        </div>
                        <div style="margin: 5px 0;">
                            <strong>Total Cost:</strong> ${this.formatCurrency(stats.totalCost)}
                        </div>
                        <div style="margin: 5px 0;">
                            <strong>Completed:</strong> ${stats.completedProjects}
                        </div>
                        <div style="margin: 5px 0;">
                            <strong>Ongoing:</strong> ${stats.ongoingProjects}
                        </div>
                        <div style="margin: 5px 0;">
                            <strong>Planned:</strong> ${stats.plannedProjects}
                        </div>
                    </div>
                `;
                
                layer.bindPopup(popupContent);
                
                // Add hover effects
                layer.on({
                    mouseover: (e) => {
                        const layer = e.target;
                        layer.setStyle({
                            weight: 3,
                            fillOpacity: 0.9
                        });
                        layer.bringToFront();
                    },
                    mouseout: (e) => {
                        this.choroplethLayer.resetStyle(e.target);
                    }
                });
            }
        });

        // Add to map
        this.choroplethLayer.addTo(this.map);
        console.log('Choropleth layer added to map');

        // Create legend and summary panel
        this.createLegend();
        this.createSummaryPanel();

        // Fit map to choropleth bounds
        if (this.choroplethLayer.getBounds().isValid()) {
            this.map.fitBounds(this.choroplethLayer.getBounds());
        } else {
            // Fallback center for Tagum City
            this.map.setView([7.4475, 125.8096], 12);
        }
    }

    createLegend() {
        // Remove existing legend
        if (this.legend) {
            this.map.removeControl(this.legend);
        }

        // Create legend
        this.legend = L.control({ position: 'bottomright' });

        this.legend.onAdd = (map) => {
            const div = L.DomUtil.create('div', 'info legend');
            div.style.backgroundColor = 'white';
            div.style.padding = '10px';
            div.style.border = '2px solid #ccc';
            div.style.borderRadius = '5px';
            div.style.fontSize = '11px';
            div.style.minWidth = '180px';
            div.style.maxHeight = 'none';
            div.style.overflowY = 'visible';
            
            div.innerHTML = '<h4 style="margin: 0 0 8px 0; color: #333; font-size: 13px;">Tagum City Barangays</h4>';
            
            // Get unique barangays with their colors
            const uniqueBarangays = new Map();
            this.barangayData.forEach(feature => {
                const name = feature.properties.name;
                const color = feature.properties.color || '#FF6B6B';
                if (!uniqueBarangays.has(name)) {
                    uniqueBarangays.set(name, color);
                }
            });

            // Sort barangays alphabetically
            const sortedBarangays = Array.from(uniqueBarangays.entries()).sort();

            sortedBarangays.forEach(([name, color]) => {
                div.innerHTML += `
                    <div style="margin: 2px 0; display: flex; align-items: center;">
                        <i style="background: ${color}; width: 16px; height: 16px; margin-right: 6px; border: 1px solid #333; flex-shrink: 0;"></i>
                        <span>${name}</span>
                    </div>
                `;
            });

            return div;
        };

        this.legend.addTo(this.map);
        console.log('Legend created with', this.barangayData.length, 'barangays');
    }

    createSummaryPanel() {
        // Remove existing summary panel
        if (this.summaryPanel) {
            this.map.removeControl(this.summaryPanel);
        }

        // Filter projects to only those with valid coordinates and a barangay in the geojson
        const validBarangays = new Set(this.barangayData.map(f => f.properties.name));
        const visibleProjects = this.projectsData.filter(p => {
            const hasCoords = p.latitude && !isNaN(parseFloat(p.latitude)) && p.longitude && !isNaN(parseFloat(p.longitude));
            return hasCoords && validBarangays.has(p.barangay);
        });

        // Debug: List delayed projects not shown on the map
        const delayedAll = this.projectsData.filter(p => p.status?.toLowerCase() === 'delayed');
        const delayedVisible = visibleProjects.filter(p => p.status?.toLowerCase() === 'delayed');
        const delayedMissing = delayedAll.filter(p => !delayedVisible.includes(p));
        if (delayedMissing.length > 0) {
            console.warn('Delayed projects not shown on the map (missing coords or invalid barangay):', delayedMissing);
        }

        const totalProjects = visibleProjects.length;
        const completedProjects = visibleProjects.filter(p => p.status?.toLowerCase() === 'completed').length;
        const ongoingProjects = visibleProjects.filter(p => p.status?.toLowerCase() === 'ongoing' || p.status?.toLowerCase() === 'in_progress').length;
        const plannedProjects = visibleProjects.filter(p => p.status?.toLowerCase() === 'planned' || p.status?.toLowerCase() === 'pending').length;
        const delayedProjects = visibleProjects.filter(p => p.status?.toLowerCase() === 'delayed').length;

        // Create summary panel
        this.summaryPanel = L.control({ position: 'topleft' });

        this.summaryPanel.onAdd = (map) => {
            const div = L.DomUtil.create('div', 'info summary-panel');
            div.style.backgroundColor = 'white';
            div.style.padding = '18px 18px 10px 18px';
            div.style.border = '2px solid #ccc';
            div.style.borderRadius = '10px';
            div.style.fontSize = '14px';
            div.style.minWidth = '240px';
            div.style.boxShadow = '0 2px 8px rgba(0,0,0,0.07)';
            div.innerHTML = `
                <div style="font-size:18px;font-weight:bold;margin-bottom:12px;color:#222;">Overall Project Metrics</div>
                <div style="background:#e8f0fe;border-radius:8px;padding:10px 12px;margin-bottom:8px;display:flex;align-items:center;gap:10px;">
                  <span style="color:#3b82f6;font-size:20px;">&#128202;</span>
                  <span style="font-size:20px;font-weight:bold;">${totalProjects}</span>
                  <span style="color:#333;">Total Projects</span>
                </div>
                <div style="background:#d1fae5;border-radius:8px;padding:10px 12px;margin-bottom:8px;display:flex;align-items:center;gap:10px;">
                  <span style="color:#10b981;font-size:20px;">&#10003;</span>
                  <span style="font-size:20px;font-weight:bold;">${completedProjects}</span>
                  <span style="color:#333;">Completed</span>
                </div>
                <div style="background:#fef3c7;border-radius:8px;padding:10px 12px;margin-bottom:8px;display:flex;align-items:center;gap:10px;">
                  <span style="color:#f59e0b;font-size:20px;">&#9201;</span>
                  <span style="font-size:20px;font-weight:bold;">${ongoingProjects}</span>
                  <span style="color:#333;">In Progress</span>
                </div>
                <div style="background:#ede9fe;border-radius:8px;padding:10px 12px;margin-bottom:8px;display:flex;align-items:center;gap:10px;">
                  <span style="color:#8b5cf6;font-size:20px;">&#128197;</span>
                  <span style="font-size:20px;font-weight:bold;">${plannedProjects}</span>
                  <span style="color:#333;">Planned</span>
                </div>
                <div style="background:#fee2e2;border-radius:8px;padding:10px 12px;margin-bottom:0;display:flex;align-items:center;gap:10px;">
                  <span style="color:#ef4444;font-size:20px;">&#128337;</span>
                  <span style="font-size:20px;font-weight:bold;">${delayedProjects}</span>
                  <span style="color:#333;">Delayed</span>
                </div>
            `;
            return div;
        };

        this.summaryPanel.addTo(this.map);
        console.log('Summary panel created');
    }

    cleanup() {
        console.log('Cleaning up choropleth...');
        
        // Remove choropleth layer
        if (this.choroplethLayer) {
            this.map.removeLayer(this.choroplethLayer);
            this.choroplethLayer = null;
        }

        // Remove legend
        if (this.legend) {
            this.map.removeControl(this.legend);
            this.legend = null;
        }

        // Remove summary panel
        if (this.summaryPanel) {
            this.map.removeControl(this.summaryPanel);
            this.summaryPanel = null;
        }

        console.log('Choropleth cleanup completed');
    }

    async initialize() {
        try {
            console.log('Initializing choropleth...');
            await this.loadData();
            this.createChoropleth();
            console.log('Choropleth initialized successfully');
        } catch (error) {
            console.error('Failed to initialize choropleth:', error);
        }
    }
}

// Export for use in other files
window.SimpleChoropleth = SimpleChoropleth; 