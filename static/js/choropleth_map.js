// Choropleth Map functionality for Tagum City Barangays
class ChoroplethMap {
    constructor(mapContainer, projectsData) {
        this.map = null;
        this.mapContainer = mapContainer;
        this.projectsData = projectsData;
        this.barangayData = {};
        this.choroplethLayer = null;
        this.legend = null;
        this.init();
    }

    init() {
        // Initialize the map
        this.map = L.map(this.mapContainer).setView([7.4475, 125.8096], 13);
        
        // Add base tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);

        // Process project data to aggregate by barangay
        this.processBarangayData();
        
        // Load barangay boundaries and create choropleth
        this.loadBarangayBoundaries();
    }

    processBarangayData() {
        // Aggregate project data by barangay
        this.barangayData = {};
        
        this.projectsData.forEach(project => {
            const barangay = project.barangay;
            if (!barangay) return;

            if (!this.barangayData[barangay]) {
                this.barangayData[barangay] = {
                    total_projects: 0,
                    completed_projects: 0,
                    ongoing_projects: 0,
                    planned_projects: 0,
                    total_cost: 0,
                    avg_progress: 0,
                    progress_sum: 0
                };
            }

            this.barangayData[barangay].total_projects++;
            
            // Count by status
            const status = (project.status || '').toLowerCase();
            if (status === 'completed') {
                this.barangayData[barangay].completed_projects++;
            } else if (status === 'ongoing' || status === 'in_progress') {
                this.barangayData[barangay].ongoing_projects++;
            } else if (status === 'planned' || status === 'pending') {
                this.barangayData[barangay].planned_projects++;
            }

            // Sum project costs
            if (project.project_cost) {
                const cost = parseFloat(project.project_cost.replace(/[^\d.-]/g, ''));
                if (!isNaN(cost)) {
                    this.barangayData[barangay].total_cost += cost;
                }
            }

            // Sum progress for average calculation
            if (project.progress !== undefined) {
                this.barangayData[barangay].progress_sum += parseInt(project.progress) || 0;
            }
        });

        // Calculate average progress
        Object.keys(this.barangayData).forEach(barangay => {
            if (this.barangayData[barangay].total_projects > 0) {
                this.barangayData[barangay].avg_progress = 
                    Math.round(this.barangayData[barangay].progress_sum / this.barangayData[barangay].total_projects);
            }
        });

        console.log('Processed barangay data:', this.barangayData);
    }

    loadBarangayBoundaries() {
        // Sample GeoJSON structure for Tagum City barangays
        // In a real implementation, you would load this from a file or API
        const barangayGeoJSON = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "name": "Apokon",
                        "id": "apokon"
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[125.75, 7.4], [125.8, 7.4], [125.8, 7.45], [125.75, 7.45], [125.75, 7.4]]]
                    }
                },
                // Add more barangay boundaries here
            ]
        };

        // For now, we'll create a sample implementation
        this.createChoroplethLayer(barangayGeoJSON);
    }

    createChoroplethLayer(geoJSON) {
        // Determine the metric to visualize (can be changed via UI)
        const metric = 'total_projects'; // or 'avg_progress', 'total_cost', etc.
        
        // Create color scale
        const colors = ['#f7fafc', '#e2e8f0', '#cbd5e0', '#a0aec0', '#718096', '#4a5568'];
        
        // Get min and max values for the metric
        const values = Object.values(this.barangayData).map(data => data[metric] || 0);
        const min = Math.min(...values);
        const max = Math.max(...values);

        // Create choropleth layer
        this.choroplethLayer = L.choropleth(geoJSON, {
            valueProperty: metric,
            scale: colors,
            steps: 6,
            mode: 'q',
            style: {
                color: '#fff',
                weight: 2,
                fillOpacity: 0.8
            },
            onEachFeature: (feature, layer) => {
                const barangayName = feature.properties.name;
                const data = this.barangayData[barangayName] || {};
                
                layer.bindPopup(`
                    <div class="p-3">
                        <h3 class="font-bold text-lg mb-2">${barangayName}</h3>
                        <div class="text-sm">
                            <p><strong>Total Projects:</strong> ${data.total_projects || 0}</p>
                            <p><strong>Completed:</strong> ${data.completed_projects || 0}</p>
                            <p><strong>Ongoing:</strong> ${data.ongoing_projects || 0}</p>
                            <p><strong>Planned:</strong> ${data.planned_projects || 0}</p>
                            <p><strong>Average Progress:</strong> ${data.avg_progress || 0}%</p>
                            <p><strong>Total Cost:</strong> ₱${(data.total_cost || 0).toLocaleString()}</p>
                        </div>
                    </div>
                `);
            }
        }).addTo(this.map);

        // Add a simple marker for debugging
        L.marker([7.4265, 125.7575]).addTo(this.map).bindPopup('Test Marker');

        // Add a polygon and fit map to its bounds
        const testPolygonLatLng = [
          [7.425, 125.755],
          [7.428, 125.755],
          [7.428, 125.760],
          [7.425, 125.760]
        ];
        const poly = L.polygon(testPolygonLatLng, {
          color: 'magenta',
          fillColor: 'lime',
          fillOpacity: 1.0,
          weight: 8
        }).addTo(this.map).bindPopup('FitBounds Polygon');
        this.map.fitBounds(poly.getBounds());
        console.log('Test polygon added and fitBounds called.');

        // Add a simple polygon for debugging
        L.polygon([
          [7.425, 125.755],
          [7.428, 125.755],
          [7.428, 125.760],
          [7.425, 125.760]
        ], {
          color: 'red',
          fillColor: 'orange',
          fillOpacity: 0.8,
          weight: 4
        }).addTo(this.map).bindPopup('Test Polygon [lat, lng]');

        // Add another test polygon in Apokon (east Tagum City)
        L.polygon([
          [7.444, 125.820],
          [7.447, 125.820],
          [7.447, 125.825],
          [7.444, 125.825]
        ], {
          color: 'blue',
          fillColor: 'cyan',
          fillOpacity: 0.8,
          weight: 4
        }).addTo(this.map).bindPopup('Test Polygon Apokon [lat, lng]');

        // Add a polygon with [lng, lat] order (should NOT appear if Leaflet expects [lat, lng])
        L.polygon([
          [125.755, 7.425],
          [125.755, 7.428],
          [125.760, 7.428],
          [125.760, 7.425]
        ], {
          color: 'green',
          fillColor: 'yellow',
          fillOpacity: 0.8,
          weight: 4
        }).addTo(this.map).bindPopup('Test Polygon [lng, lat]');

        // Add government properties GeoJSON layer
        fetch('/static/data/gov_properties_sample.geojson')
          .then(response => response.json())
          .then(data => {
            L.geoJSON(data, {
              style: function (feature) {
                return {
                  color: '#8e24aa',      // Violet border
                  fillColor: '#ce93d8',  // Light violet fill
                  fillOpacity: 0.95,     // More opaque
                  weight: 6              // Thicker border
                };
              },
              onEachFeature: function (feature, layer) {
                let props = feature.properties;
                layer.bindPopup(
                  `<strong>${props.name}</strong><br/>
                   ${props.description}<br/>
                   Barangay: ${props.barangay}`
                );
                // Ensure this layer is always in front
                layer.on('add', function() { layer.bringToFront(); });
                // Add a marker at the center for debugging
                if (props.center) {
                  L.marker([props.center[1], props.center[0]], {
                    title: props.name,
                    alt: props.name,
                    riseOnHover: true
                  }).addTo(layer._map || layer._leaflet_id && L.DomUtil.get(layer._leaflet_id));
                }
              }
            }).addTo(this.map);
          });

        // Add legend
        this.addLegend(colors, min, max, metric);
    }

    addLegend(colors, min, max, metric) {
        const legend = L.control({ position: 'bottomright' });

        legend.onAdd = function() {
            const div = L.DomUtil.create('div', 'info legend');
            const grades = [];
            const step = (max - min) / colors.length;
            
            for (let i = 0; i < colors.length; i++) {
                const from = Math.round(min + i * step);
                const to = Math.round(min + (i + 1) * step);
                grades.push(`${from}${i === colors.length - 1 ? '+' : ` - ${to}`}`);
            }

            div.innerHTML = '<h4>' + this.getMetricLabel(metric) + '</h4>';
            
            for (let i = 0; i < grades.length; i++) {
                div.innerHTML +=
                    '<i style="background:' + colors[i] + '"></i> ' +
                    grades[i] + '<br>';
            }
            
            return div;
        }.bind(this);

        legend.addTo(this.map);
        this.legend = legend;
    }

    getMetricLabel(metric) {
        const labels = {
            'total_projects': 'Total Projects',
            'completed_projects': 'Completed Projects',
            'ongoing_projects': 'Ongoing Projects',
            'planned_projects': 'Planned Projects',
            'avg_progress': 'Average Progress (%)',
            'total_cost': 'Total Cost (₱)'
        };
        return labels[metric] || metric;
    }

    updateChoropleth(metric) {
        if (this.choroplethLayer) {
            this.map.removeLayer(this.choroplethLayer);
        }
        if (this.legend) {
            this.map.removeControl(this.legend);
        }
        
        // Reload with new metric
        this.loadBarangayBoundaries();
    }

    // Method to load actual GeoJSON data from server
    loadGeoJSONFromServer(url) {
        fetch(url)
            .then(response => response.json())
            .then(data => {
                this.createChoroplethLayer(data);
            })
            .catch(error => {
                console.error('Error loading GeoJSON:', error);
            });
    }
}

// Export for use in other files
window.ChoroplethMap = ChoroplethMap; 