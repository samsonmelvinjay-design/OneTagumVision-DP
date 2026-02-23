from django.core.management.base import BaseCommand
import json
import os
from django.conf import settings

# Try to import pyproj for coordinate conversion (optional)
try:
    from pyproj import Transformer
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False

class Command(BaseCommand):
    help = 'Combine individual barangay GeoJSON files into one combined file'
    
    def handle(self, *args, **options):
        coord_dir = str(getattr(settings, 'COORD_DIR', settings.BASE_DIR / 'coord'))
        output_file = os.path.join(str(getattr(settings, 'STATIC_SOURCE_DIR', settings.BASE_DIR / 'static')), 'data', 'tagum_barangays.geojson')
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Barangay name mapping (file names to proper names)
        barangay_name_mapping = {
            'Apokon.geojson': 'Apokon',
            'Bincungan.geojson': 'Bincungan',
            'Busaon.geojson': 'Busaon',
            'Canocotan.geojson': 'Canocotan',
            'cuambogan.geojson': 'Cuambogan',
            'LaFilipina.geojson': 'La Filipina',
            'Liboganon.geojson': 'Liboganon',
            'Madaum.geojson': 'Madaum',
            'Magdum.geojson': 'Magdum',
            'MagugpoE.geojson': 'Magugpo East',
            'MagugpoN.geojson': 'Magugpo North',
            'MagugpoPoblacion.geojson': 'Magugpo Poblacion',
            'MagugpoS.geojson': 'Magugpo South',
            'MagugpoW.geojson': 'Magugpo West',
            'Mankilam.geojson': 'Mankilam',
            'newbalamban.geojson': 'New Balamban',
            'nueva fuerza.geojson': 'Nueva Fuerza',
            'paagsabangan.geojson': 'Pagsabangan',
            'Pandapan.geojson': 'Pandapan',
            'sanagustin.geojson': 'San Agustin',
            'SanIsidro.geojson': 'San Isidro',
            'SanMiguel.geojson': 'San Miguel',
            'VisayanVillage.geojson': 'Visayan Village',
        }
        
        combined_features = []
        processed_count = 0
        skipped_count = 0
        errors = []
        
        # Transformer for EPSG:3857 to WGS84 (if pyproj available)
        transformer_3857_to_wgs84 = None
        if HAS_PYPROJ:
            try:
                transformer_3857_to_wgs84 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Could not create coordinate transformer: {e}'))
                self.stdout.write(self.style.WARNING('Files with EPSG:3857 will be skipped'))
        
        # Process each GeoJSON file
        for filename in os.listdir(coord_dir):
            if not filename.endswith('.geojson'):
                continue
                
            filepath = os.path.join(coord_dir, filename)
            barangay_name = barangay_name_mapping.get(filename, filename.replace('.geojson', '').title())
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Get CRS information
                crs = data.get('crs', {})
                crs_name = None
                if crs:
                    crs_props = crs.get('properties', {})
                    crs_name = crs_props.get('name', '')
                
                # Process features
                features = data.get('features', [])
                if not features:
                    self.stdout.write(self.style.WARNING(f'No features found in {filename}'))
                    skipped_count += 1
                    continue
                
                for feature in features:
                    geometry = feature.get('geometry', {})
                    geometry_type = geometry.get('type', '')
                    coordinates = geometry.get('coordinates', [])
                    
                    # Skip LineString geometries (we need Polygon)
                    if geometry_type == 'LineString':
                        self.stdout.write(self.style.WARNING(f'Skipping LineString in {filename} - need Polygon'))
                        continue
                    
                    # Convert coordinates if needed (EPSG:3857 to WGS84)
                    if 'EPSG:3857' in str(crs_name):
                        if transformer_3857_to_wgs84:
                            self.stdout.write(f'Converting {filename} from EPSG:3857 to WGS84...')
                            converted_coords = self.convert_coordinates(coordinates, transformer_3857_to_wgs84, geometry_type)
                            coordinates = converted_coords
                        else:
                            self.stdout.write(self.style.WARNING(f'Skipping {filename} - EPSG:3857 conversion requires pyproj'))
                            skipped_count += 1
                            continue
                    
                    # Create new feature with normalized structure
                    new_feature = {
                        'type': 'Feature',
                        'properties': {
                            'id': processed_count + 1,
                            'name': barangay_name
                        },
                        'geometry': {
                            'type': geometry_type,
                            'coordinates': coordinates
                        }
                    }
                    
                    combined_features.append(new_feature)
                
                processed_count += 1
                self.stdout.write(self.style.SUCCESS(f'Processed: {filename} -> {barangay_name}'))
                
            except Exception as e:
                error_msg = f'Error processing {filename}: {str(e)}'
                self.stdout.write(self.style.ERROR(error_msg))
                errors.append(error_msg)
                skipped_count += 1
        
        # Create combined GeoJSON
        combined_geojson = {
            'type': 'FeatureCollection',
            'features': combined_features
        }
        
        # Write to output file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(combined_geojson, f, indent=2, ensure_ascii=False)
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(self.style.SUCCESS(f'Successfully combined GeoJSON files!'))
            self.stdout.write(self.style.SUCCESS(f'Output: {output_file}'))
            self.stdout.write(self.style.SUCCESS(f'Total features: {len(combined_features)}'))
            self.stdout.write(self.style.SUCCESS(f'Processed files: {processed_count}'))
            self.stdout.write(self.style.SUCCESS(f'Skipped files: {skipped_count}'))
            if errors:
                self.stdout.write(self.style.WARNING(f'Errors: {len(errors)}'))
            self.stdout.write(self.style.SUCCESS('=' * 60))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error writing output file: {str(e)}'))
            return
        
        # Validate the output
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                validation_data = json.load(f)
            if validation_data.get('type') == 'FeatureCollection' and len(validation_data.get('features', [])) > 0:
                self.stdout.write(self.style.SUCCESS('Output file is valid GeoJSON'))
            else:
                self.stdout.write(self.style.ERROR('Output file validation failed'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error validating output: {str(e)}'))
    
    def convert_coordinates(self, coordinates, transformer, geometry_type):
        """Convert coordinates from EPSG:3857 to WGS84"""
        if geometry_type == 'Polygon':
            # Polygon: [[[x1,y1], [x2,y2], ...]]
            converted = []
            for ring in coordinates:
                converted_ring = []
                for coord in ring:
                    if len(coord) >= 2:
                        x, y = coord[0], coord[1]
                        # Convert
                        lon, lat = transformer.transform(x, y)
                        converted_ring.append([lon, lat])
                converted.append(converted_ring)
            return converted
        elif geometry_type == 'LineString':
            # LineString: [[x1,y1], [x2,y2], ...]
            converted = []
            for coord in coordinates:
                if len(coord) >= 2:
                    x, y = coord[0], coord[1]
                    lon, lat = transformer.transform(x, y)
                    converted.append([lon, lat])
            return converted
        else:
            # For other types, return as-is (or implement conversion if needed)
            return coordinates

