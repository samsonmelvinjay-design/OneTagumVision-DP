// Simple Choropleth Map implementation for Tagum City Barangays
// Version: 2.0 - Includes zoning functionality (switchView, loadZoningData, createZoningLayer)
// Set window.DEBUG_CHOROPLETH = true or ?debug=1 to show map debug logs.
var DEBUG_CHOROPLETH = typeof window !== 'undefined' && (window.DEBUG_CHOROPLETH === true || /[?&]debug=1/.test((window.location && window.location.search) || ''));

class SimpleChoropleth {
    constructor(map, geojsonUrl, projectsData = null, legendContainerId = null, cityBoundaryUrl = null) {
        this.map = map;
        this.geojsonUrl = geojsonUrl;
        this.projectsData = projectsData || [];
        this.legendContainerId = legendContainerId; // Optional: render legend into this DOM element instead of Leaflet control
        this.cityBoundaryUrl = cityBoundaryUrl; // Optional: GeoJSON URL for whole Tagum City boundary (OSM admin boundary)
        this.choroplethLayer = null; // Kept for backward compat; use choroplethLayers when multiple views
        this.choroplethLayers = {};   // viewType -> L.layer; allows multiple view types on at once
        this.cityBoundaryLayer = null; // Blue outline of whole Tagum City when choropleth is off
        this.showCityOutline = false;  // Off by default; user enables via "City outline only" in Zoning Control
        this.legend = null;
        this.summaryPanel = null;
        this.barangayData = [];
        this.barangayStats = {};
        // Phase 3: Zoning support
        this.zoningData = null;
        this.zoneData = null; // Phase 5: Detailed zone data (R-1, R-2, etc.)
        this.currentView = 'projects'; // 'projects', 'urban_rural', 'economic', 'elevation', 'zone_type'
        this.zoningLayers = {
            urbanRural: null,
            economic: null,
            elevation: null
        };
        
        if (DEBUG_CHOROPLETH) console.log('SimpleChoropleth constructor - projectsData:', this.projectsData ? this.projectsData.length : 0, 'projects');
    }
    
    // Method to update projects data and recalculate stats
    updateProjectsData(projectsData) {
        if (DEBUG_CHOROPLETH) console.log('Updating projects data:', projectsData ? projectsData.length : 0, 'projects');
        this.projectsData = projectsData || [];
        // Recalculate stats if barangay data is already loaded
        if (this.barangayData && this.barangayData.length > 0) {
            this.calculateBarangayStats();
            // If a layer is already created, we might want to refresh it
            // But for now, just recalculate stats
        }
    }

    calculateBarangayStats() {
        // Calculate statistics for each barangay
        this.barangayStats = {};
        
        if (DEBUG_CHOROPLETH) console.log('=== calculateBarangayStats START ===');
        if (DEBUG_CHOROPLETH) console.log('Projects data length:', this.projectsData ? this.projectsData.length : 0);
        if (DEBUG_CHOROPLETH) console.log('Barangay data length:', this.barangayData ? this.barangayData.length : 0);
        
        // Normalize barangay names from GeoJSON for matching
        const normalizedBarangayNames = new Map();
        if (this.barangayData && this.barangayData.length > 0) {
            this.barangayData.forEach(feature => {
                const name = feature.properties.name;
                if (name) {
                    // Store normalized version (lowercase, trimmed) -> original name
                    const normalized = name.toLowerCase().trim();
                    normalizedBarangayNames.set(normalized, name);
                }
            });
            if (DEBUG_CHOROPLETH) console.log('GeoJSON barangay names:', Array.from(normalizedBarangayNames.values()));
        } else {
            if (DEBUG_CHOROPLETH) console.warn('No barangay data available for normalization!');
        }
        
        if (!this.projectsData || this.projectsData.length === 0) {
            if (DEBUG_CHOROPLETH) console.warn('No projects data available!');
            return;
        }
        
        let projectsWithBarangay = 0;
        let projectsWithoutBarangay = 0;
        const unmatchedBarangays = new Set();
        
        this.projectsData.forEach(project => {
            let barangay = project.barangay;
            if (!barangay) {
                projectsWithoutBarangay++;
                return;
            }
            
            projectsWithBarangay++;
            
            // Normalize project barangay name for matching
            const normalizedProjectBarangay = barangay.toLowerCase().trim();
            
            // Try to find matching barangay name from GeoJSON (case-insensitive)
            let matchedBarangay = null;
            
            // First, try exact match (case-insensitive)
            if (normalizedBarangayNames.has(normalizedProjectBarangay)) {
                matchedBarangay = normalizedBarangayNames.get(normalizedProjectBarangay);
            } else {
                // Try removing spaces and special characters for matching
                const normalizedNoSpaces = normalizedProjectBarangay.replace(/\s+/g, '').toLowerCase();
                
                // Try to find by partial match or fuzzy match
                for (const [normalized, original] of normalizedBarangayNames.entries()) {
                    const normalizedGeoNoSpaces = normalized.replace(/\s+/g, '').toLowerCase();
                    
                    // Exact match after removing spaces
                    if (normalizedGeoNoSpaces === normalizedNoSpaces) {
                        matchedBarangay = original;
                        break;
                    }
                    
                    // Check if names are similar (one contains the other or vice versa)
                    if (normalized.includes(normalizedProjectBarangay) || normalizedProjectBarangay.includes(normalized)) {
                        matchedBarangay = original;
                        break;
                    }
                    
                    // Check without spaces
                    if (normalizedGeoNoSpaces.includes(normalizedNoSpaces) || normalizedNoSpaces.includes(normalizedGeoNoSpaces)) {
                        matchedBarangay = original;
                        break;
                    }
                    
                    // Also try removing common suffixes/prefixes
                    const normalizedClean = normalized.replace(/^(barangay|brgy|brg)\s*/i, '').trim();
                    const projectClean = normalizedProjectBarangay.replace(/^(barangay|brgy|brg)\s*/i, '').trim();
                    if (normalizedClean === projectClean || normalizedClean.includes(projectClean) || projectClean.includes(normalizedClean)) {
                        matchedBarangay = original;
                        break;
                    }
                }
            }
            
            // Always use the matched GeoJSON barangay name as the key
            // This ensures consistency when looking up stats in popups
            const statsKey = matchedBarangay || null;
            
            if (!matchedBarangay) {
                unmatchedBarangays.add(barangay);
                // Skip projects that don't match any GeoJSON barangay
                // This prevents stats from being stored with incorrect keys
                if (DEBUG_CHOROPLETH) console.warn(`Project ${project.id} (${project.name}) has barangay "${barangay}" which doesn't match any GeoJSON barangay`);
                return; // Skip this project
            }
            
            if (!this.barangayStats[statsKey]) {
                this.barangayStats[statsKey] = {
                    totalProjects: 0,
                    totalCost: 0,
                    completedProjects: 0,
                    ongoingProjects: 0,
                    plannedProjects: 0,
                    delayedProjects: 0
                };
            }
            
            this.barangayStats[statsKey].totalProjects++;
            
            // Parse project cost
            let cost = 0;
            if (project.project_cost) {
                // Remove currency symbols and commas, then parse
                const costStr = project.project_cost.toString().replace(/[₱,]/g, '').trim();
                cost = parseFloat(costStr) || 0;
            }
            this.barangayStats[statsKey].totalCost += cost;
            
            // Count by status - handle all possible status values
            const status = (project.status || '').toLowerCase().trim();
            if (status === 'completed' || status === 'complete') {
                this.barangayStats[statsKey].completedProjects++;
            } else if (status === 'ongoing' || status === 'in_progress' || status === 'in-progress' || status === 'in progress') {
                this.barangayStats[statsKey].ongoingProjects++;
            } else if (status === 'planned' || status === 'pending' || status === 'not started') {
                this.barangayStats[statsKey].plannedProjects++;
            } else if (status === 'delayed') {
                this.barangayStats[statsKey].delayedProjects++;
            }
            
            // Debug: Log successful match
            if (matchedBarangay !== barangay.trim()) {
                if (DEBUG_CHOROPLETH) console.log(`Matched project barangay "${barangay}" to GeoJSON barangay "${matchedBarangay}"`);
            }
        });
        
        if (DEBUG_CHOROPLETH) console.log('Projects with barangay:', projectsWithBarangay);
        if (DEBUG_CHOROPLETH) console.log('Projects without barangay:', projectsWithoutBarangay);
        if (unmatchedBarangays.size > 0) {
            if (DEBUG_CHOROPLETH) console.warn('Unmatched barangay names from projects:', Array.from(unmatchedBarangays));
            if (DEBUG_CHOROPLETH) console.warn('These projects will not be counted in barangay statistics');
        }
        if (DEBUG_CHOROPLETH) console.log('Barangay statistics calculated:', this.barangayStats);
        if (DEBUG_CHOROPLETH) console.log('Total barangays with stats:', Object.keys(this.barangayStats).length);
        
        // Log detailed stats for first few barangays
        const statsEntries = Object.entries(this.barangayStats);
        if (statsEntries.length > 0) {
            if (DEBUG_CHOROPLETH) console.log('Sample stats (first 5 barangays):');
            statsEntries.slice(0, 5).forEach(([name, stats]) => {
                if (DEBUG_CHOROPLETH) console.log(`  ${name}: ${stats.totalProjects} projects, ${stats.completedProjects} completed, ${stats.ongoingProjects} ongoing, ${stats.plannedProjects} planned, ${stats.delayedProjects} delayed, Cost: ${this.formatCurrency(stats.totalCost)}`);
            });
        } else {
            if (DEBUG_CHOROPLETH) console.warn('⚠️ WARNING: No barangay statistics were calculated!');
            if (DEBUG_CHOROPLETH) console.warn('This could mean:');
            if (DEBUG_CHOROPLETH) console.warn('  1. Projects don\'t have barangay values set');
            if (DEBUG_CHOROPLETH) console.warn('  2. Barangay names in projects don\'t match GeoJSON barangay names');
            if (DEBUG_CHOROPLETH) console.warn('  3. Projects data is empty or not loaded');
        }
        if (DEBUG_CHOROPLETH) console.log('=== calculateBarangayStats END ===');
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
            if (DEBUG_CHOROPLETH) console.log('Loading GeoJSON data from:', this.geojsonUrl);
            const response = await fetch(this.geojsonUrl);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            if (DEBUG_CHOROPLETH) console.log('GeoJSON data loaded:', data);
            
            this.barangayData = data.features || [];
            if (DEBUG_CHOROPLETH) console.log(`Loaded ${this.barangayData.length} barangay features`);
            
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

        // Calculate barangay statistics if not already calculated
        if (!this.barangayStats || Object.keys(this.barangayStats).length === 0) {
            this.calculateBarangayStats();
        }

        // Create choropleth layer (caller adds to map; used for single or multiple views)
        const barangayColors = ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1', '#14b8a6', '#a855f7'];
        const colorByBarangay = new Map();
        let colorIdx = 0;
        this.barangayData.forEach(f => {
            const name = f.properties?.name;
            if (name && !colorByBarangay.has(name)) {
                colorByBarangay.set(name, f.properties.color || barangayColors[colorIdx++ % barangayColors.length]);
            }
        });
        const geoJsonLayer = L.geoJSON(this.barangayData, {
            style: (feature) => {
                const name = feature.properties?.name;
                const color = (name && colorByBarangay.get(name)) || feature.properties.color || '#FF6B6B';
                return {
                    fillColor: color,
                    weight: 1,
                    opacity: 0.9,
                    color: '#374151',
                    fillOpacity: 0.7
                };
            },
            onEachFeature: (feature, layer) => {
                const name = feature.properties.name || 'Unknown';
                
                // Try to find stats with case-insensitive matching
                let stats = this.barangayStats[name];
                if (!stats) {
                    // Try case-insensitive match
                    const normalizedName = name.toLowerCase().trim();
                    const matchingKey = Object.keys(this.barangayStats).find(key => 
                        key.toLowerCase().trim() === normalizedName
                    );
                    stats = matchingKey ? this.barangayStats[matchingKey] : null;
                }
                
                // Default to zeros if no stats found
                if (!stats) {
                    stats = {
                        totalProjects: 0,
                        totalCost: 0,
                        completedProjects: 0,
                        ongoingProjects: 0,
                        plannedProjects: 0,
                        delayedProjects: 0
                    };
                }
                
                const barangay = this.zoningData ? this.zoningData[name] : null;
                
                // Use enhanced popup with zoning info
                const popupContent = this.createZoningPopup(name, barangay, stats);
                
                layer.bindPopup(popupContent, { maxWidth: 400 });
                
                // Add hover effects (geoJsonLayer.resetStyle is on the GeoJSON group, not the polygon)
                layer.on({
                    mouseover: (e) => {
                        const target = e.target;
                        target.setStyle({
                            weight: 1,
                            fillOpacity: 0.9
                        });
                        target.bringToFront();
                    },
                    mouseout: (e) => {
                        if (geoJsonLayer.resetStyle) geoJsonLayer.resetStyle(e.target);
                    }
                });
            }
        });

        if (DEBUG_CHOROPLETH) console.log('Choropleth layer created (projects)');
        return geoJsonLayer;
    }

    createLegend(activeViewTypes) {
        // activeViewTypes: optional array e.g. ['projects', 'urban_rural']; if not passed, use this.currentView (single)
        const viewTypes = Array.isArray(activeViewTypes) ? activeViewTypes : (this.currentView && this.currentView !== 'none' ? [this.currentView] : []);
        const buildLegendHtmlForView = (viewType) => {
            let html = '';
            if (viewType === 'urban_rural') {
                html = '<h4 style="margin: 0 0 10px 0; color: #333; font-size: 13px; font-weight: 600;">Urban / Rural</h4>';
                html += `
                    <div style="margin: 4px 0; display: flex; align-items: center;">
                        <i style="background: #ef4444; width: 16px; height: 16px; margin-right: 8px; border: 1px solid #333; flex-shrink: 0; border-radius: 3px;"></i>
                        <span style="font-size: 12px;">Urban</span>
                    </div>
                    <div style="margin: 4px 0; display: flex; align-items: center;">
                        <i style="background: #fbbf24; width: 16px; height: 16px; margin-right: 8px; border: 1px solid #333; flex-shrink: 0; border-radius: 3px;"></i>
                        <span style="font-size: 12px;">Rural</span>
                    </div>
                `;
            } else if (viewType === 'economic') {
                html = '<h4 style="margin: 0 0 10px 0; color: #333; font-size: 13px; font-weight: 600;">Economic Classification</h4>';
                html += `
                    <div style="margin: 4px 0; display: flex; align-items: center;">
                        <i style="background: #3b82f6; width: 16px; height: 16px; margin-right: 8px; border: 1px solid #333; flex-shrink: 0; border-radius: 3px;"></i>
                        <span style="font-size: 12px;">Growth Center</span>
                    </div>
                    <div style="margin: 4px 0; display: flex; align-items: center;">
                        <i style="background: #10b981; width: 16px; height: 16px; margin-right: 8px; border: 1px solid #333; flex-shrink: 0; border-radius: 3px;"></i>
                        <span style="font-size: 12px;">Emerging</span>
                    </div>
                    <div style="margin: 4px 0; display: flex; align-items: center;">
                        <i style="background: #fbbf24; width: 16px; height: 16px; margin-right: 8px; border: 1px solid #333; flex-shrink: 0; border-radius: 3px;"></i>
                        <span style="font-size: 12px;">Satellite</span>
                    </div>
                `;
            } else if (viewType === 'elevation') {
                html = '<h4 style="margin: 0 0 10px 0; color: #333; font-size: 13px; font-weight: 600;">Elevation Type</h4>';
                html += `
                    <div style="margin: 4px 0; display: flex; align-items: center;">
                        <i style="background: #8b5cf6; width: 16px; height: 16px; margin-right: 8px; border: 1px solid #333; flex-shrink: 0; border-radius: 3px;"></i>
                        <span style="font-size: 12px;">Highland</span>
                    </div>
                    <div style="margin: 4px 0; display: flex; align-items: center;">
                        <i style="background: #84cc16; width: 16px; height: 16px; margin-right: 8px; border: 1px solid #333; flex-shrink: 0; border-radius: 3px;"></i>
                        <span style="font-size: 12px;">Plains</span>
                    </div>
                    <div style="margin: 4px 0; display: flex; align-items: center;">
                        <i style="background: #06b6d4; width: 16px; height: 16px; margin-right: 8px; border: 1px solid #333; flex-shrink: 0; border-radius: 3px;"></i>
                        <span style="font-size: 12px;">Coastal</span>
                    </div>
                `;
            } else if (viewType === 'zone_type') {
                html = '<h4 style="margin: 0 0 10px 0; color: #333; font-size: 13px; font-weight: 600;">TAG Zone Type</h4>';
                const zoneTypes = ['R-1', 'R-2', 'R-3', 'SHZ', 'C-1', 'C-2', 'I-1', 'I-2', 'AGRO', 'INS-1', 'PARKS', 'AGRICULTURAL', 'ECO-TOURISM', 'SPECIAL'];
                zoneTypes.forEach(zoneType => {
                    const color = this.getZoneTypeColor(zoneType);
                    const displayName = this.getZoneTypeDisplayName(zoneType);
                    html += `
                        <div style="margin: 4px 0; display: flex; align-items: center;">
                            <i style="background: ${color}; width: 16px; height: 16px; margin-right: 8px; border: 1px solid #333; flex-shrink: 0; border-radius: 3px;"></i>
                            <span style="font-size: 12px;">${zoneType}: ${displayName}</span>
                        </div>
                    `;
                });
            } else {
                html = '<h4 style="margin: 0 0 10px 0; color: #333; font-size: 13px; font-weight: 600;">Tagum City Barangays</h4>';
                if (!this.barangayData || this.barangayData.length === 0) {
                    html += '<p style="font-size: 12px; color: #6b7280; margin: 4px 0;">No data loaded yet.</p>';
                } else {
                    const barangayColors = ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1', '#14b8a6', '#a855f7'];
                    const uniqueBarangays = new Map();
                    let colorIndex = 0;
                    this.barangayData.forEach(feature => {
                        const name = feature.properties.name;
                        if (!uniqueBarangays.has(name)) {
                            const color = feature.properties.color || barangayColors[colorIndex++ % barangayColors.length];
                            uniqueBarangays.set(name, color);
                        }
                    });
                    const sortedBarangays = Array.from(uniqueBarangays.entries()).sort((a, b) => a[0].localeCompare(b[0]));
                    sortedBarangays.forEach(([name, color]) => {
                        html += `
                            <div style="margin: 4px 0; display: flex; align-items: center;">
                                <i style="background: ${color}; width: 16px; height: 16px; margin-right: 8px; border: 1px solid #333; flex-shrink: 0; border-radius: 3px;"></i>
                                <span style="font-size: 12px;">${name}</span>
                            </div>
                        `;
                    });
                }
            }
            return html;
        };
        let legendHtml = '';
        viewTypes.forEach(vt => {
            legendHtml += buildLegendHtmlForView(vt);
            if (legendHtml && !legendHtml.endsWith('</div>')) legendHtml += '<div style="margin-top: 8px;"></div>';
        });

        // When nothing is active (view 'none'), remove legend entirely - no choropleth legend shown
        if (!legendHtml) {
            if (this.legendContainerId) {
                const container = document.getElementById(this.legendContainerId);
                if (container) container.innerHTML = '';
            }
            if (this.legend) {
                try { this.map.removeControl(this.legend); } catch (e) { /* ignore */ }
                this.legend = null;
            }
            return;
        }

        // If custom legend container is provided, render there (inside zoning panel)
        if (this.legendContainerId) {
            const container = document.getElementById(this.legendContainerId);
            if (container) {
                container.innerHTML = legendHtml;
                if (this.legend) {
                    try { this.map.removeControl(this.legend); } catch (e) { /* ignore */ }
                    this.legend = null;
                }
                return;
            }
        }

        // Fallback: Leaflet control
        if (this.legend) {
            this.map.removeControl(this.legend);
        }
        this.legend = L.control({ position: 'bottomright' });
        this.legend.onAdd = () => {
            const div = L.DomUtil.create('div', 'info legend');
            div.style.backgroundColor = 'white';
            div.style.padding = '14px 16px';
            div.style.border = '2px solid #ccc';
            div.style.borderRadius = '8px';
            div.style.fontSize = '13px';
            div.style.minWidth = '220px';
            div.style.maxWidth = '280px';
            div.style.maxHeight = '500px';
            div.style.overflowY = 'auto';
            div.style.overflowX = 'hidden';
            div.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
            div.innerHTML = legendHtml;
            return div;
        };
        this.legend.addTo(this.map);
    }

    async fetchOverallMetrics() {
        try {
            const response = await fetch('/dashboard/api/overall-project-metrics/', {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'Accept': 'application/json',
                }
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            if (data.success && data.metrics) {
                return data.metrics;
            }
            return null;
        } catch (error) {
            console.error('Error fetching overall metrics:', error);
            return null;
        }
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
            if (DEBUG_CHOROPLETH) console.warn('Delayed projects not shown on the map (missing coords or invalid barangay):', delayedMissing);
        }

        // Calculate metrics from visible projects (fallback)
        const totalProjects = visibleProjects.length;
        const completedProjects = visibleProjects.filter(p => {
            const status = p.status?.toLowerCase() || p.calculated_status?.toLowerCase();
            return status === 'completed';
        }).length;
        const ongoingProjects = visibleProjects.filter(p => {
            const status = p.status?.toLowerCase() || p.calculated_status?.toLowerCase();
            return status === 'ongoing' || status === 'in_progress';
        }).length;
        const plannedProjects = visibleProjects.filter(p => {
            const status = p.status?.toLowerCase() || p.calculated_status?.toLowerCase();
            return status === 'planned' || status === 'pending';
        }).length;
        const delayedProjects = visibleProjects.filter(p => {
            const status = p.status?.toLowerCase() || p.calculated_status?.toLowerCase();
            return status === 'delayed';
        }).length;

        // Fetch overall metrics from API (includes ALL projects, not just visible ones)
        this.fetchOverallMetrics().then(metrics => {
            if (metrics) {
                // Update panel with API metrics
                this.updateSummaryPanel(metrics);
            } else {
                // Use fallback metrics from visible projects
                this.updateSummaryPanel({
                    total_projects: totalProjects,
                    completed: completedProjects,
                    in_progress: ongoingProjects,
                    planned: plannedProjects,
                    delayed: delayedProjects
                });
            }
        }).catch(() => {
            // On error, use fallback metrics
            this.updateSummaryPanel({
                total_projects: totalProjects,
                completed: completedProjects,
                in_progress: ongoingProjects,
                planned: plannedProjects,
                delayed: delayedProjects
            });
        });

        // Create initial panel with fallback metrics (will be updated if API call succeeds)
        this.updateSummaryPanel({
            total_projects: totalProjects,
            completed: completedProjects,
            in_progress: ongoingProjects,
            planned: plannedProjects,
            delayed: delayedProjects
        });
    }

    updateSummaryPanel(metrics) {
        const totalProjects = metrics.total_projects || 0;
        const completedProjects = metrics.completed || 0;
        const ongoingProjects = metrics.in_progress || 0;
        const plannedProjects = metrics.planned || 0;
        const delayedProjects = metrics.delayed || 0;

        // Create or update summary panel
        if (!this.summaryPanel) {
            this.summaryPanel = L.control({ position: 'topleft' });
            this.summaryPanel.onAdd = (map) => {
                const div = L.DomUtil.create('div', 'info summary-panel');
                div.id = 'summary-panel-content';
                div.style.backgroundColor = 'white';
                div.style.padding = '18px 18px 10px 18px';
                div.style.border = '2px solid #ccc';
                div.style.borderRadius = '10px';
                div.style.fontSize = '14px';
                div.style.minWidth = '240px';
                div.style.boxShadow = '0 2px 8px rgba(0,0,0,0.07)';
                return div;
            };
            this.summaryPanel.addTo(this.map);
        }

        // Update panel content
        const panelDiv = document.getElementById('summary-panel-content');
        if (panelDiv) {
            panelDiv.innerHTML = `
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
        }
        if (DEBUG_CHOROPLETH) console.log('Summary panel updated with metrics:', metrics);
    }

    cleanup() {
        if (DEBUG_CHOROPLETH) console.log('Cleaning up choropleth...');
        
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

        if (DEBUG_CHOROPLETH) console.log('Choropleth cleanup completed');
    }

    async initialize() {
        try {
            if (DEBUG_CHOROPLETH) console.log('=== SimpleChoropleth.initialize() START ===');
            if (DEBUG_CHOROPLETH) console.log('Projects data passed to constructor:', this.projectsData ? this.projectsData.length : 0, 'projects');
            
            await this.loadData();
            if (DEBUG_CHOROPLETH) console.log('GeoJSON data loaded:', this.barangayData.length, 'features');
            
            // Phase 3: Load zoning data
            await this.loadZoningData();
            // Phase 5: Load zone data (R-1, R-2, etc.)
            await this.loadZoneData();
            
            // Calculate barangay stats before creating any layer
            // This must happen after loadData() so we have barangay names for matching
            this.calculateBarangayStats();
            
            // Do NOT create choropleth here - only create the layer for the current view (e.g. city boundary when 'none')
            if (DEBUG_CHOROPLETH) console.log('Zoning data available:', this.zoningData ? Object.keys(this.zoningData).length + ' barangays' : 'none');
            if (DEBUG_CHOROPLETH) console.log('Barangay stats calculated for', Object.keys(this.barangayStats).length, 'barangays');
            if (DEBUG_CHOROPLETH) console.log('switchView method available:', typeof this.switchView === 'function');
            if (DEBUG_CHOROPLETH) console.log('=== SimpleChoropleth.initialize() END ===');
            return true; // Return success
        } catch (error) {
            console.error('Failed to initialize choropleth:', error);
            throw error; // Re-throw to allow promise rejection
        }
    }

    // Phase 3: Zoning functionality
    async loadZoningData() {
        try {
            const response = await fetch('/projeng/api/barangay-metadata/', {
                method: 'GET',
                credentials: 'same-origin', // Include cookies for authentication
                headers: {
                    'Accept': 'application/json',
                }
            });
            if (!response.ok) {
                if (response.status === 401) {
                    console.error('Authentication required. Please log in.');
                } else if (response.status === 403) {
                    console.error('Access forbidden. You may not have permission to view this data.');
                } else {
                    console.error(`HTTP error! status: ${response.status}`);
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            if (DEBUG_CHOROPLETH) console.log('API Response:', data);
            if (DEBUG_CHOROPLETH) console.log('Barangays array:', data.barangays);
            if (DEBUG_CHOROPLETH) console.log('Barangays count:', data.barangays ? data.barangays.length : 0);
            
            this.zoningData = {};
            if (data.barangays && Array.isArray(data.barangays)) {
                if (data.barangays.length === 0) {
                    console.error('========================================');
                    console.error('⚠️ CRITICAL: Zoning data is empty!');
                    console.error('========================================');
                    console.error('The database has no barangay metadata.');
                    console.error('');
                    console.error('TO FIX THIS:');
                    console.error('1. Open terminal/command prompt');
                    console.error('2. Navigate to project directory');
                    console.error('3. Run: python manage.py populate_barangay_metadata');
                    console.error('');
                    console.error('If you get a celery error:');
                    console.error('- Temporarily comment out: from .celery import app as celery_app');
                    console.error('- In file: gistagum/__init__.py');
                    console.error('- Then run the command again');
                    console.error('- Restore the import after');
                    console.error('');
                    console.error('See POPULATE_ZONING_DATA.md for detailed instructions.');
                    console.error('========================================');
                    
                    // Show user-friendly message in UI if possible
                    if (typeof alert !== 'undefined') {
                        if (DEBUG_CHOROPLETH) console.warn('Showing alert to user...');
                    }
                } else {
                    data.barangays.forEach(barangay => {
                        this.zoningData[barangay.name] = barangay;
                    });
                    if (DEBUG_CHOROPLETH) console.log('✓ Zoning data loaded:', Object.keys(this.zoningData).length, 'barangays');
                    // Log first few barangay names for verification
                    const names = Object.keys(this.zoningData).slice(0, 5);
                    if (DEBUG_CHOROPLETH) console.log('Sample barangay names:', names);
                }
            } else {
                console.error('❌ Unexpected data format:', data);
                console.error('Expected: {barangays: [...]}');
                console.error('Received:', Object.keys(data));
                this.zoningData = {};
            }
        } catch (error) {
            console.error('Error loading zoning data:', error);
            this.zoningData = {};
        }
    }

    // Phase 5: Load detailed zone data (R-1, R-2, C-1, etc.)
    async loadZoneData() {
        try {
            const response = await fetch('/projeng/api/barangay-zone-data/', {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'Accept': 'application/json',
                }
            });
            if (!response.ok) {
                if (DEBUG_CHOROPLETH) console.warn(`Failed to load zone data: HTTP ${response.status}`);
                this.zoneData = {};
                return;
            }
            const data = await response.json();
            if (DEBUG_CHOROPLETH) console.log('Zone data loaded:', data.count || 0, 'barangays');
            this.zoneData = data.barangay_zones || {};
        } catch (error) {
            console.error('Error loading zone data:', error);
            this.zoneData = {};
        }
    }

    // Phase 5: Get color for zone type
    // Updated to follow standard urban planning color conventions
    getZoneTypeColor(zoneType) {
        const zoneColors = {
            // Residential - Yellow/Beige tones (standard in urban planning)
            'R-1': '#fff9c4', // Very light yellow (low density residential)
            'R-2': '#fff59d', // Light yellow (medium density residential)
            'R-3': '#fdd835', // Yellow (high density residential)
            'SHZ': '#c5e1a5', // Light green-yellow (socialized housing)
            
            // Commercial - Orange/Red tones (standard)
            'C-1': '#ff6f00', // Deep orange (major commercial)
            'C-2': '#ffb74d', // Light orange (minor commercial)
            
            // Industrial - Purple/Gray tones (standard)
            'I-1': '#ba68c8', // Purple (heavy industrial)
            'I-2': '#ce93d8', // Light purple (light/medium industrial)
            'AGRO': '#9ccc65', // Light green (agro-industrial)
            
            // Institutional/Public - Purple/Blue tones
            'INS-1': '#7986cb', // Indigo/purple-blue (institutional)
            
            // Open Space/Parks - Green tones
            'PARKS': '#66bb6a', // Medium green (parks & open spaces)
            'AGRICULTURAL': '#81c784', // Green (agricultural/SAFDZ)
            'ECO-TOURISM': '#26a69a', // Teal (eco-tourism)
            
            // Special Uses - Brown/Gray/Teal tones
            'SPECIAL': '#a1887f', // Brown (special use)
        };
        return zoneColors[zoneType] || '#cccccc'; // Default gray
    }

    // Phase 5: Get zone type display name
    getZoneTypeDisplayName(zoneType) {
        const zoneNames = {
            'R-1': 'Low Density Residential',
            'R-2': 'Medium Density Residential',
            'R-3': 'High Density Residential',
            'SHZ': 'Socialized Housing',
            'C-1': 'Major Commercial',
            'C-2': 'Minor Commercial',
            'I-1': 'Heavy Industrial',
            'I-2': 'Light/Medium Industrial',
            'AGRO': 'Agro-Industrial',
            'INS-1': 'Institutional',
            'PARKS': 'Parks & Open Spaces',
            'AGRICULTURAL': 'Agricultural / SAFDZ',
            'ECO-TOURISM': 'Eco-tourism',
            'SPECIAL': 'Special Use',
        };
        return zoneNames[zoneType] || zoneType;
    }

    // Phase 5: Derive a fallback zone-type summary from BarangayMetadata
    // Used when we don't yet have detailed zoneData from /projeng/api/barangay-zone-data/
    getDerivedZoneInfoFromMetadata(barangayMeta) {
        if (!barangayMeta) return null;

        const zonesSet = new Set();
        const industrialZones = Array.isArray(barangayMeta.industrial_zones) ? barangayMeta.industrial_zones : [];

        industrialZones.forEach(z => {
            const key = (z || '').toString().toLowerCase();
            if (key.includes('agro')) zonesSet.add('AGRO');
            if (key.includes('institutional')) zonesSet.add('INS-1');
            if (key.includes('commercial') || key === 'cbd') zonesSet.add('C-1');
        });

        let zoneTypes = Array.from(zonesSet);

        // If no industrial zoning hints, fall back to simple urban/rural heuristic
        if (!zoneTypes.length) {
            const cls = (barangayMeta.barangay_class || '').toLowerCase();
            if (cls === 'urban') {
                zoneTypes = ['R-2']; // treat urban barangays as Medium Density Residential
            } else if (cls === 'rural') {
                zoneTypes = ['AGRICULTURAL'];
            }
        }

        if (!zoneTypes.length) return null;

        const dominant = zoneTypes[0];
        const zoneCounts = {};
        zoneCounts[dominant] = 1;

        return {
            dominant_zone: dominant,
            zone_counts: zoneCounts,
            total_projects: 0,
            zone_types: zoneTypes,
            available_zones: [],
        };
    }

    /**
     * Set which view types are active (multiple can be on). viewTypes: array e.g. ['projects', 'urban_rural', 'economic'].
     * Empty array = no choropleth layers (markers only, or city outline only if enabled).
     */
    setActiveViews(viewTypes) {
        if (!Array.isArray(viewTypes)) viewTypes = [];
        const order = ['projects', 'urban_rural', 'economic', 'elevation', 'zone_type'];
        const sorted = viewTypes.filter(v => order.indexOf(v) >= 0).sort((a, b) => order.indexOf(a) - order.indexOf(b));

        // Remove layers that are no longer active
        Object.keys(this.choroplethLayers).forEach(key => {
            if (sorted.indexOf(key) === -1) {
                try {
                    this.map.removeLayer(this.choroplethLayers[key]);
                } catch (e) { /* ignore */ }
                delete this.choroplethLayers[key];
            }
        });

        // Ensure zoning data for non-projects views
        const needsZoning = sorted.some(v => v !== 'projects');
        if (needsZoning && (!this.zoningData || Object.keys(this.zoningData).length === 0)) {
            this.loadZoningData().then(() => {
                this.setActiveViews(viewTypes);
            }).catch((err) => console.error('Failed to load zoning data:', err));
            return;
        }

        // Add layers for each active view type (in order, so last is on top)
        sorted.forEach(viewType => {
            if (this.choroplethLayers[viewType]) return;
            let layer = null;
            if (viewType === 'projects') {
                layer = this.createChoropleth();
            } else {
                layer = this.createZoningLayer(viewType);
            }
            if (layer) {
                this.choroplethLayers[viewType] = layer;
                layer.addTo(this.map);
            }
        });

        this.currentView = sorted.length ? sorted[sorted.length - 1] : 'none';
        this.choroplethLayer = this.choroplethLayers[this.currentView] || null;

        // City boundary: remove then re-add on top if enabled
        if (this.cityBoundaryLayer) {
            try { this.map.removeLayer(this.cityBoundaryLayer); } catch (e) {}
            this.cityBoundaryLayer = null;
        }
        if (this.showCityOutline) {
            this.createCityBoundaryLayer();
        }

        this.createLegend(sorted);
        if (sorted.indexOf('projects') >= 0) {
            if (!this.summaryPanel) this.createSummaryPanel();
        } else if (this.summaryPanel) {
            try { this.map.removeControl(this.summaryPanel); } catch (e) {}
            this.summaryPanel = null;
        }
        if (DEBUG_CHOROPLETH) console.log('setActiveViews:', sorted);
    }

    switchView(viewType) {
        this.currentView = viewType;
        if (viewType === 'none') {
            this.setActiveViews([]);
            if (this.showCityOutline) {
                this.createCityBoundaryLayer();
            }
            this.createLegend([]);
            return;
        }
        this.setActiveViews([viewType]);
    }

    /** Toggle city outline visibility from Zoning Control. Call from map page checkbox. */
    async setCityOutlineVisible(visible) {
        this.showCityOutline = !!visible;
        if (visible) {
            if (!this.cityBoundaryLayer) {
                await this.createCityBoundaryLayer();
            } else {
                try {
                    this.cityBoundaryLayer.addTo(this.map);
                } catch (e) {
                    if (DEBUG_CHOROPLETH) console.warn('Error re-adding city boundary:', e);
                }
            }
        } else {
            if (this.cityBoundaryLayer) {
                try {
                    this.map.removeLayer(this.cityBoundaryLayer);
                } catch (e) {
                    if (DEBUG_CHOROPLETH) console.warn('Error removing city boundary:', e);
                }
                this.cityBoundaryLayer = null;
            }
        }
    }

    async createCityBoundaryLayer() {
        const style = {
            fillColor: 'transparent',
            fillOpacity: 0,
            color: '#3b82f6',
            weight: 4,
            opacity: 1
        };
        const addBoundaryFromData = (data) => {
            const features = (data.features || []).filter(f => f.geometry && (f.geometry.type === 'Polygon' || f.geometry.type === 'MultiPolygon'));
            if (features.length === 0) return;
            this.cityBoundaryLayer = L.geoJSON({ type: 'FeatureCollection', features }, {
                style: () => style
            });
            if (this.showCityOutline) this.cityBoundaryLayer.addTo(this.map);
            if (DEBUG_CHOROPLETH) console.log('Tagum City boundary outline added');
        };
        if (this.cityBoundaryUrl) {
            try {
                const response = await fetch(this.cityBoundaryUrl);
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const data = await response.json();
                addBoundaryFromData(data);
                return;
            } catch (e) {
                if (DEBUG_CHOROPLETH) console.warn('Failed to load city boundary GeoJSON, falling back to barangay union:', e.message);
            }
        }
        if (!this.barangayData || this.barangayData.length === 0) {
            if (DEBUG_CHOROPLETH) console.warn('No city boundary URL and no barangay data');
            return;
        }
        if (typeof turf !== 'undefined') {
            try {
                const features = this.barangayData.filter(f => f.geometry && (f.geometry.type === 'Polygon' || f.geometry.type === 'MultiPolygon'));
                if (features.length === 0) return;
                let merged;
                try {
                    merged = turf.union(turf.featureCollection(features));
                } catch (unionErr) {
                    merged = turf.feature(features[0]);
                    for (let i = 1; i < features.length; i++) {
                        try {
                            const u = turf.union(turf.featureCollection([merged, turf.feature(features[i])]));
                            if (u) merged = u;
                        } catch (err) {
                            if (DEBUG_CHOROPLETH) console.warn('Union skip feature', i, err.message);
                        }
                    }
                }
                if (merged) {
                    this.cityBoundaryLayer = L.geoJSON(merged, { style: () => style });
                    if (this.showCityOutline) this.cityBoundaryLayer.addTo(this.map);
                    if (DEBUG_CHOROPLETH) console.log('Tagum City boundary (Turf union) added');
                    return;
                }
            } catch (e) {
                if (DEBUG_CHOROPLETH) console.warn('Turf union failed:', e.message);
            }
        }
        addBoundaryFromData({ features: this.barangayData });
        if (DEBUG_CHOROPLETH) console.log('Tagum City boundary (barangay outlines fallback) added');
        // addBoundaryFromData already checks showCityOutline before addTo(map)
    }

    createZoningLayer(viewType) {
        if (DEBUG_CHOROPLETH) console.log('=== createZoningLayer called ===');
        if (DEBUG_CHOROPLETH) console.log('viewType:', viewType);
        if (DEBUG_CHOROPLETH) console.log('barangayData length:', this.barangayData.length);
        if (DEBUG_CHOROPLETH) console.log('zoningData keys:', this.zoningData ? Object.keys(this.zoningData).length : 0);
        
        if (!this.barangayData.length) {
            console.error('No barangay data available');
            return;
        }

        if (!this.zoningData || Object.keys(this.zoningData).length === 0) {
            console.error('No zoning data available');
            return;
        }
        
        // Ensure stats are calculated before creating the layer
        if (!this.barangayStats || Object.keys(this.barangayStats).length === 0) {
            if (DEBUG_CHOROPLETH) console.log('Barangay stats not calculated yet, calculating now...');
            this.calculateBarangayStats();
        }

        // Create zoning layer (caller adds to map; used for single or multiple views)
        if (DEBUG_CHOROPLETH) console.log('Creating GeoJSON layer with zoning colors...', viewType);
        let coloredCount = 0;
        let defaultCount = 0;

        const geoJsonLayer = L.geoJSON(this.barangayData, {
            style: (feature) => {
                const barangayName = feature.properties.name;
                const barangay = this.zoningData[barangayName];
                let color = '#cccccc'; // Default gray
                
                if (barangay) {
                    switch(viewType) {
                        case 'urban_rural':
                            if (barangay.barangay_class === 'urban') {
                                color = '#ef4444'; // Red for urban
                                coloredCount++;
                            } else if (barangay.barangay_class === 'rural') {
                                color = '#fbbf24'; // Yellow for rural
                                coloredCount++;
                            } else {
                                defaultCount++;
                            }
                            break;
                        case 'economic':
                            if (barangay.economic_class === 'growth_center') {
                                color = '#3b82f6'; // Blue
                                coloredCount++;
                            } else if (barangay.economic_class === 'emerging') {
                                color = '#10b981'; // Green
                                coloredCount++;
                            } else if (barangay.economic_class === 'satellite') {
                                color = '#fbbf24'; // Yellow
                                coloredCount++;
                            } else {
                                defaultCount++;
                            }
                            break;
                        case 'elevation':
                            if (barangay.elevation_type === 'highland') {
                                color = '#8b5cf6'; // Purple
                                coloredCount++;
                            } else if (barangay.elevation_type === 'plains') {
                                color = '#84cc16'; // Green
                                coloredCount++;
                            } else if (barangay.elevation_type === 'coastal') {
                                color = '#06b6d4'; // Cyan
                                coloredCount++;
                            } else {
                                defaultCount++;
                            }
                            break;
                        case 'zone_type': {
                            // Phase 5: Use detailed zone data, or fall back to metadata-derived zone
                            let zoneInfo = this.zoneData && this.zoneData[barangayName];
                            if (!zoneInfo) {
                                zoneInfo = this.getDerivedZoneInfoFromMetadata(barangay);
                            }
                            if (zoneInfo && zoneInfo.dominant_zone) {
                                color = this.getZoneTypeColor(zoneInfo.dominant_zone);
                                coloredCount++;
                            } else {
                                defaultCount++;
                            }
                            break;
                        }
                        default:
                            defaultCount++;
                    }
                } else {
                    defaultCount++;
                    if (DEBUG_CHOROPLETH) console.log('No zoning data for barangay:', barangayName);
                }
                
                return {
                    fillColor: color,
                    weight: 1,
                    opacity: 0.9,
                    color: '#374151',
                    fillOpacity: 0.7 // Slightly more opaque for better visibility
                };
            },
            onEachFeature: (feature, layer) => {
                const name = feature.properties.name || 'Unknown';
                const barangay = this.zoningData[name];
                let zoneInfo = this.zoneData ? this.zoneData[name] : null;
                if (!zoneInfo && barangay) {
                    zoneInfo = this.getDerivedZoneInfoFromMetadata(barangay);
                }
                
                // Try to find stats with case-insensitive matching
                let stats = this.barangayStats[name];
                if (!stats) {
                    // Try case-insensitive match
                    const normalizedName = name.toLowerCase().trim();
                    const matchingKey = Object.keys(this.barangayStats).find(key => 
                        key.toLowerCase().trim() === normalizedName
                    );
                    stats = matchingKey ? this.barangayStats[matchingKey] : null;
                }
                
                // Default to zeros if no stats found
                if (!stats) {
                    stats = {
                        totalProjects: 0,
                        totalCost: 0,
                        completedProjects: 0,
                        ongoingProjects: 0,
                        plannedProjects: 0
                    };
                }
                
                // Create popup with both project stats and zoning info
                const popupContent = this.createZoningPopup(name, barangay, stats, zoneInfo, viewType);
                layer.bindPopup(popupContent, { maxWidth: 400 });
                
                // Add hover effects (geoJsonLayer.resetStyle is on the GeoJSON group, not the polygon)
                layer.on({
                    mouseover: (e) => {
                        const target = e.target;
                        target.setStyle({
                            weight: 1,
                            fillOpacity: 0.9
                        });
                        target.bringToFront();
                    },
                    mouseout: (e) => {
                        if (geoJsonLayer.resetStyle) geoJsonLayer.resetStyle(e.target);
                    }
                });
            }
        });

        if (DEBUG_CHOROPLETH) console.log('Zoning layer created:', viewType, 'Colored:', coloredCount, 'Default:', defaultCount);
        return geoJsonLayer;
    }

    createZoningPopup(name, barangay, stats, zoneInfo = null, viewType = 'projects') {
        const escapedName = (name || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        let content = `
            <div style="min-width: 280px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 12px 14px; border-radius: 10px 10px 0 0; display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: nowrap;">
                <h3 style="margin: 0; color: #ffffff; font-size: 18px; font-weight: 700; text-shadow: 0 1px 2px rgba(0,0,0,0.2); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis;">${escapedName}</h3>
                <button type="button" class="barangay-view-projects-btn" data-barangay="${escapedName}" style="flex-shrink: 0; padding: 6px 12px; font-size: 11px; font-weight: 600; background: rgba(255,255,255,0.95); color: #667eea; border: none; border-radius: 6px; cursor: pointer; white-space: nowrap; box-shadow: 0 1px 3px rgba(0,0,0,0.2);">View Projects</button>
            </div>
            <div style="background: #ffffff; padding: 12px; border-radius: 0 0 10px 10px; max-height: 400px; overflow-y: auto;">
        `;
        
        // Phase 5: Add zone type information if available
        if (viewType === 'zone_type' && zoneInfo) {
            content += `
                <div style="background: #f8fafc; border-radius: 8px; padding: 10px; margin-bottom: 10px; border-left: 3px solid #667eea;">
                    <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 8px;">
                        <span style="font-size: 14px;">📍</span>
                        <div style="font-weight: 600; color: #1e293b; font-size: 12px; text-transform: uppercase;">Zone Classification</div>
                    </div>
                    ${zoneInfo.dominant_zone ? `
                        <div style="background: white; border-radius: 6px; padding: 6px 8px; margin-bottom: 6px; font-size: 12px;">
                            <span style="color: #64748b; font-size: 10px;">Zone:</span> <strong style="color: #1e293b;">${zoneInfo.dominant_zone}</strong>
                        </div>
                    ` : ''}
                    ${zoneInfo.zone_types && zoneInfo.zone_types.length > 0 ? `
                        <div style="background: white; border-radius: 6px; padding: 6px 8px; margin-bottom: 6px; font-size: 12px;">
                            <span style="color: #64748b; font-size: 10px;">Types:</span> <strong style="color: #1e293b;">${zoneInfo.zone_types.join(', ')}</strong>
                        </div>
                    ` : ''}
                    ${zoneInfo.zone_counts && Object.keys(zoneInfo.zone_counts).length > 0 ? `
                        <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px;">
                            ${Object.entries(zoneInfo.zone_counts).map(([zone, count]) => 
                                `<span style="background: #667eea; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600;">${zone}: ${count}</span>`
                            ).join('')}
                        </div>
                    ` : ''}
                </div>
            `;
        }
        
        // Add zoning information if available
        if (barangay && viewType !== 'zone_type') {
            content += `
                <div style="background: #f8fafc; border-radius: 8px; padding: 10px; margin-bottom: 10px; border-left: 3px solid #10b981;">
                    <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 8px;">
                        <span style="font-size: 14px;">🏘️</span>
                        <div style="font-weight: 600; color: #1e293b; font-size: 12px; text-transform: uppercase;">Zoning Information</div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 11px;">
                        <div style="background: white; border-radius: 6px; padding: 6px 8px;">
                            <div style="color: #64748b; font-size: 9px; margin-bottom: 2px;">Classification</div>
                            <div style="font-weight: 600; color: #1e293b;">${barangay.barangay_class ? barangay.barangay_class.charAt(0).toUpperCase() + barangay.barangay_class.slice(1) : 'N/A'}</div>
                        </div>
                        <div style="background: white; border-radius: 6px; padding: 6px 8px;">
                            <div style="color: #64748b; font-size: 9px; margin-bottom: 2px;">Economic</div>
                            <div style="font-weight: 600; color: #1e293b; font-size: 10px;">${barangay.economic_class ? barangay.economic_class.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()) : 'N/A'}</div>
                        </div>
                        <div style="background: white; border-radius: 6px; padding: 6px 8px;">
                            <div style="color: #64748b; font-size: 9px; margin-bottom: 2px;">Elevation</div>
                            <div style="font-weight: 600; color: #1e293b;">${barangay.elevation_type ? barangay.elevation_type.charAt(0).toUpperCase() + barangay.elevation_type.slice(1) : 'N/A'}</div>
                        </div>
                        ${barangay.population ? `
                            <div style="background: white; border-radius: 6px; padding: 6px 8px;">
                                <div style="color: #64748b; font-size: 9px; margin-bottom: 2px;">Population</div>
                                <div style="font-weight: 600; color: #1e293b; font-size: 10px;">${barangay.population.toLocaleString()}</div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }
        
        // Add project statistics
        // Compute infrastructure share: this barangay's total / all barangays' total
        let infraShare = '0.00';
        try {
            const allTotals = Object.values(this.barangayStats || {}).reduce((sum, s) => {
                const val = s && typeof s.totalProjects === 'number' ? s.totalProjects : 0;
                return sum + val;
            }, 0);
            if (allTotals > 0 && stats && typeof stats.totalProjects === 'number') {
                infraShare = ((stats.totalProjects / allTotals) * 100).toFixed(2);
            }
        } catch (e) {
            if (DEBUG_CHOROPLETH) console.warn('Error computing infrastructure share for barangay popup:', e);
        }

        const delayedCount = typeof stats.delayedProjects === 'number' ? stats.delayedProjects : 0;
        const ongoingCount = typeof stats.ongoingProjects === 'number' ? stats.ongoingProjects : 0;
        const completedCount = typeof stats.completedProjects === 'number' ? stats.completedProjects : 0;
        const plannedCount = typeof stats.plannedProjects === 'number' ? stats.plannedProjects : 0;

        content += `
                <div style="background: #f8fafc; border-radius: 8px; padding: 10px; border-left: 3px solid #f59e0b;">
                    <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 8px;">
                        <span style="font-size: 14px;">📊</span>
                        <div style="font-weight: 600; color: #1e293b; font-size: 12px; text-transform: uppercase;">Project Statistics</div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px;">
                        <div style="background: white; border-radius: 6px; padding: 8px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                            <div style="font-size: 9px; color: #64748b; margin-bottom: 4px;">Total</div>
                            <div style="font-size: 16px; font-weight: 700; color: #1e293b;">${stats.totalProjects}</div>
                        </div>
                        <div style="background: white; border-radius: 6px; padding: 8px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                            <div style="font-size: 9px; color: #64748b; margin-bottom: 4px;">Cost</div>
                            <div style="font-size: 11px; font-weight: 700; color: #1e293b; word-break: break-word;">${this.formatCurrency(stats.totalCost)}</div>
                        </div>
                        <div style="background: #d1fae5; border-radius: 6px; padding: 8px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                            <div style="font-size: 9px; color: #059669; margin-bottom: 4px;">Completed</div>
                            <div style="font-size: 16px; font-weight: 700; color: #047857;">${completedCount}</div>
                        </div>
                        <div style="background: #dbeafe; border-radius: 6px; padding: 8px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                            <div style="font-size: 9px; color: #2563eb; margin-bottom: 4px;">Ongoing</div>
                            <div style="font-size: 16px; font-weight: 700; color: #1d4ed8;">${ongoingCount}</div>
                        </div>
                        <div style="background: #fee2e2; border-radius: 6px; padding: 8px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                            <div style="font-size: 9px; color: #b91c1c; margin-bottom: 4px;">Delayed</div>
                            <div style="font-size: 16px; font-weight: 700; color: #b91c1c;">${delayedCount}</div>
                        </div>
                        <div style="background: #ede9fe; border-radius: 6px; padding: 8px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                            <div style="font-size: 9px; color: #7c3aed; margin-bottom: 4px;">Planned</div>
                            <div style="font-size: 16px; font-weight: 700; color: #6d28d9;">${plannedCount}</div>
                        </div>
                        <div style="background: #f1f5f9; border-radius: 6px; padding: 6px 8px; grid-column: 1 / -1; text-align: left;">
                            <div style="font-size: 10px; color: #64748b; margin-bottom: 2px;">Infrastructure Share</div>
                            <div style="font-size: 13px; font-weight: 600; color: #0f172a;">
                                ${infraShare}% of all city projects
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        return content;
    }
}

// Export for use in other files
window.SimpleChoropleth = SimpleChoropleth; 