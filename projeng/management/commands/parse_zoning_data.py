from django.core.management.base import BaseCommand
import re

class Command(BaseCommand):
    help = 'Parse PDF zoning data and prepare for database insertion'
    
    def handle(self, *args, **options):
        # PDF data provided by user
        zoning_data_text = """
Zone Classification,Specific Locations (Barangay/Subdivision/Site)

I. Residential Zones,
Low Density Residential Zone (R-1),"VISAYAN VILLAGE (Specific areas defined by roads/boundaries), LIBOGANON (Line abiding Liboganon road, Barangay Residential Site, Coastal Residential Area), MADAUM (Makabayan Village, specific areas defined by roads/boundaries), APOKON (Specific areas defined by roads/boundaries), PANDAPAN (Barangay Residential site), NEW BALAMBAN (Barangay Residential site, Sitio Mandapaan residential site, and areas abiding specific roads), SAN AGUSTIN (Barangay Residential Site, and area abiding San Agustin-New Balamban road), PAGSABANGAN (Barangay Residential Site, Purok Angkibit Site), LA FILIPINA (Specific area bounded by a proposed road and the Mankilam boundary), NUEVA FUERZA (Barangay Residential Site), MANKILAM (Specific area bounded by barangay boundaries and proposed/existing roads), SAN MIGUEL (Specific areas bounded by boundaries, creeks, and roads)."

Medium Density Residential Zone (R-2),"MAGUGPO WEST (Domingo Subdivision), MAGUGPO NORTH (Suaybaguio District, Mirafuentes, Kalambuan Christ the King Subdivisions), MAGUGPO EAST (Senangote Village 1 & 2, Zafra Compound, Mencidor, Briz District, Liwayway Village, Bag Village, Shrineville, DANECO Village, RJP Village II Subdivisions, and specific areas), MADAUM (Barrio Site, except institutional area), MAGDUM (Specific areas defined by subdivisions/boundaries and roads), LA FILIPINA (Bello, Kalamboan Christ the King Village, and specific areas), CUAMBOGAN (Purok San Antonio residential site, and specific areas), NUEVA FUERZA (Specific area bounded by a proposed circumferential road), MANKILAM (Margarita Village, Davao Sports Complex, Villa Margarita, Villa Patricia Subdivisions), SAN MIGUEL (Specific areas defined by roads/boundaries)."

High Density Residential Zone (R-3),"MAGUGPO WEST (Cristo Rey Village Subdivision 1 & 2, Padilla Subdivision, Gante Subdivision 1, 2 and 3, and specific areas), MAGUGPO EAST (Specific areas defined by roads and boundaries)."

Socialized Housing Zone (SHZ),"MAGUGPO SOUTH (City government area Proposed Resettlement Site @ Purok V), MADAUM (Area of the proposed resettlement site adjacent to Makabayan Village), LA FILIPINA (Proposed Inocencio Estabillo Subdivision), CUAMBOGAN (Sacred Heart Homeowners Subdivision, Proposed Tagum City resettlement site, Couples for Christ Resettlement Site)."

II. Commercial Zones,
Major Commercial Zone (C-1),"MAGUGPO WEST (Specific area defined by roads/boundaries, including the location of numerous banks), MAGUGPO EAST (Specific areas defined by roads and boundaries, except existing institutional establishments and subdivisions), MAGUGPO SOUTH (Specific area bounded by Pioneer Avenues, Sobrecary Street, except existing Subdivisions and Institutional establishments), VISAYAN VILLAGE (Specific area defined by roads/boundaries), MADAUM (Specific area bounded by Madaum road, Madaum-Baret road, and Katipunan Madaum barrio site boundary)."

Minor Commercial Zone (C-2),"MAGUGPO WEST (Specific area bounded by roads, except existing Institutional establishments), LA FILIPINA (Specific area bounded by boundaries and roads, except existing institutional establishments), MANKILAM (Specific area bounded by boundaries and roads), SAN MIGUEL (Specific area along Capitol-San Miguel road)."

III. Industrial Zones,
Light and Medium Industrial Zone (I-2),"MADAUM (Specific area near shoreline, Existing Packing Houses, Existing Plastic Factory), MAGDUM (Specific area near Hijo River, Twin Rivers Plantation, Inc Property, Tagum Wood Core Industry), CANOCOTAN (J & B Poultry and Industrial Compound), MAGUGPO EAST (Ian C. Neo Mini Saw Mill, Tagum Engineering Service Center Asphalt and Batching Plant, Proposed ""CLASS AA"" Slaughterhouse), MAGUGPO WEST (Heroben Saw Mill, Sato Pallet Maker), MANKILAM (Orient Wood Industries Co., F. Albatera, Robert Oliveros, Nomer V. Navarro Mini Sawmills), SAN MIGUEL (C. Z. Sarmento Pallet Maker), BINCUNGAN (Persan Construction Batching Plant Area)."

Heavy Industrial Zone (I-1),"MAGDUM (Specific area near Hijo River, Hexat Mining Corporation), PANDAPAN (Specific area bounded by roads/boundaries, Minex Mining Corporation), CANOCOTAN (Pryce Gases gas refilling station), CUAMBOGAN (Tagum PPMC Wood Veneer, Inc.)."

Agro-Industrial,"APOKON (Juania Iligan Rice and Corn Mill), CANOCOTAN (New Filipino Rice Mill), MAGDUM (Alben's Rice Mill, Royce Food Banana Chips Factory, Vina T. Li Dryer), MAGUGPO EAST (Tagum Commodities Corporation), MAGUGPO NORTH (A. Baga, E. Baga, AJ Bautista Rice Mills), MANKILAM (Pacatang, Calzada, Limbago Rice/Corn/Feed Mills, Bordago Corn Mill, AJ Rice Mill, Perfect Milling Corp.), PAGSABANGAN (Villarico Rice Mill), SAN MIGUEL (Solano Poultry Farm, Francis Apolinario Corn Mill and Dryier), VISAYAN VILLAGE (Calzada Poultry Farm, Masaganang Sakahan Inc., Venson Rice and Corn Mill), CUAMBOGAN (Edward Baga Rice Mill, and a specific area)."

IV. Other Major Zones,
Institutional Zone (Ins-1),"APOKON (USP-Regional-Trade School Compound), MANKILAM (Provincial Government Center - Capitol Site), LA FILIPINA/MAGDUM (Proposed University and Support Institutional Development Zone), MAGDUM (PCUP, Old NIA), CANOCOTAN (Tagum City Jail Site), VISAYAN VILLAGE (Philippine National Police Provincial Headquarter)."

Parks & Playgrounds/Open Spaces,"City-wide (All existing Public Parks and Playgrounds, including Tagum City Parks and Plaza, and Tagum Rotary Club house), MANKILAM (Provincial Sports Complex), APOKON (Proposed 5 hectares Nature's Park @ USP-Regional Compound)."

Agricultural,City-wide (All barangays covered by Strategic Agriculture and Fishery Development Zone (SAFDZ)).

Eco-tourism Zone,MADAUM (Specific area near Madaum shoreline).

Special Use Zones,"Cemeteries/Memorial Parks, Dumpsites/Sanitary Landfills, Buffer Zones, Reclamation, Coastal, Slaughterhouse, Cockpit (locations not specifically itemized by barangay in the provided section, but are classified as ""Special Use"")."
"""
        
        # Zone type mapping
        zone_mapping = {
            'Low Density Residential Zone (R-1)': 'R-1',
            'Medium Density Residential Zone (R-2)': 'R-2',
            'High Density Residential Zone (R-3)': 'R-3',
            'Socialized Housing Zone (SHZ)': 'SHZ',
            'Major Commercial Zone (C-1)': 'C-1',
            'Minor Commercial Zone (C-2)': 'C-2',
            'Light and Medium Industrial Zone (I-2)': 'I-2',
            'Heavy Industrial Zone (I-1)': 'I-1',
            'Agro-Industrial': 'AGRO',
            'Institutional Zone (Ins-1)': 'INS-1',
            'Parks & Playgrounds/Open Spaces': 'PARKS',
            'Agricultural': 'AGRICULTURAL',
            'Eco-tourism Zone': 'ECO-TOURISM',
            'Special Use Zones': 'SPECIAL',
        }
        
        # Barangay name normalization
        barangay_normalization = {
            'VISAYAN VILLAGE': 'Visayan Village',
            'LIBOGANON': 'Liboganon',
            'MADAUM': 'Madaum',
            'APOKON': 'Apokon',
            'PANDAPAN': 'Pandapan',
            'NEW BALAMBAN': 'New Balamban',
            'SAN AGUSTIN': 'San Agustin',
            'PAGSABANGAN': 'Pagsabangan',
            'LA FILIPINA': 'La Filipina',
            'NUEVA FUERZA': 'Nueva Fuerza',
            'MANKILAM': 'Mankilam',
            'SAN MIGUEL': 'San Miguel',
            'MAGUGPO WEST': 'Magugpo West',
            'MAGUGPO NORTH': 'Magugpo North',
            'MAGUGPO EAST': 'Magugpo East',
            'MAGUGPO SOUTH': 'Magugpo South',
            'MAGDUM': 'Magdum',
            'CUAMBOGAN': 'Cuambogan',
            'CANOCOTAN': 'Canocotan',
            'BINCUNGAN': 'Bincungan',
        }
        
        parsed_zones = []
        
        # Parse the text line by line
        lines = zoning_data_text.strip().split('\n')
        current_zone_type = None
        current_zone_code = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('Zone Classification') or line.startswith('I.') or line.startswith('II.') or line.startswith('III.') or line.startswith('IV.'):
                continue
            
            # Check if line contains zone type
            for zone_name, zone_code in zone_mapping.items():
                if zone_name in line:
                    current_zone_type = zone_name
                    current_zone_code = zone_code
                    break
            
            # Check if line contains locations (starts with quote or contains BARANGAY NAME)
            if line.startswith('"') or any(barangay.upper() in line for barangay in barangay_normalization.keys()):
                # Extract locations
                locations_text = line.strip('"').strip()
                
                # Skip if this is just a zone type line without locations
                if current_zone_code and current_zone_code in locations_text and len(locations_text) < 10:
                    continue
                
                # Split by barangay (look for BARANGAY NAME (pattern)
                # Pattern: BARANGAY_NAME (location description)
                # Improved pattern to avoid matching zone codes
                pattern = r'([A-Z][A-Z\s/]+?)\s*\(([^)]+)\)'
                matches = re.findall(pattern, locations_text)
                
                for match in matches:
                    barangay_raw = match[0].strip()
                    location_desc = match[1].strip()
                    
                    # Skip if barangay name is too short or looks like a zone code
                    if len(barangay_raw) < 3 or barangay_raw in ['R-1', 'R-2', 'R-3', 'C-1', 'C-2', 'I-1', 'I-2', 'SHZ', 'AGRO', 'INS-1']:
                        continue
                    
                    # Normalize barangay name
                    barangay = barangay_normalization.get(barangay_raw, barangay_raw.title())
                    
                    # Skip if still empty or invalid
                    if not barangay or len(barangay) < 3:
                        continue
                    
                    # Handle special cases (e.g., "LA FILIPINA/MAGDUM")
                    if '/' in barangay_raw:
                        # Split and create separate entries
                        barangays = [b.strip() for b in barangay_raw.split('/')]
                        for b in barangays:
                            if len(b) < 3:
                                continue
                            normalized_b = barangay_normalization.get(b, b.title())
                            if normalized_b:
                                parsed_zones.append({
                                    'zone_type': current_zone_code,
                                    'barangay': normalized_b,
                                    'location_description': location_desc,
                                    'keywords': self.extract_keywords(location_desc)
                                })
                    else:
                        parsed_zones.append({
                            'zone_type': current_zone_code,
                            'barangay': barangay,
                            'location_description': location_desc,
                            'keywords': self.extract_keywords(location_desc)
                        })
                
                # Also check for "City-wide" entries
                if 'City-wide' in locations_text:
                    # For city-wide zones, we'll create entries for all barangays
                    # But for now, skip or handle specially
                    self.stdout.write(self.style.WARNING(f'City-wide zone found: {current_zone_type} - will need special handling'))
        
        # Display parsed data
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Parsed Zoning Data'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        # Group by zone type
        zones_by_type = {}
        for zone in parsed_zones:
            zone_type = zone['zone_type']
            if zone_type not in zones_by_type:
                zones_by_type[zone_type] = []
            zones_by_type[zone_type].append(zone)
        
        for zone_type, zones in sorted(zones_by_type.items()):
            self.stdout.write(self.style.SUCCESS(f'\n{zone_type}: {len(zones)} entries'))
            for zone in zones[:3]:  # Show first 3 as examples
                self.stdout.write(f'  - {zone["barangay"]}: {zone["location_description"][:50]}...')
            if len(zones) > 3:
                self.stdout.write(f'  ... and {len(zones) - 3} more')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Total zones parsed: {len(parsed_zones)}'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        # Save to JSON file for review
        import json
        output_file = 'parsed_zoning_data.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(parsed_zones, f, indent=2, ensure_ascii=False)
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Data saved to: {output_file}'))
        self.stdout.write(self.style.SUCCESS('Review the file and then use populate_zoning_zones command to insert into database'))
    
    def extract_keywords(self, location_description):
        """Extract keywords from location description for matching"""
        keywords = []
        
        # Remove common words
        stop_words = {'specific', 'area', 'areas', 'defined', 'by', 'roads', 'road', 'boundaries', 
                     'boundary', 'and', 'the', 'a', 'an', 'or', 'except', 'existing', 'proposed'}
        
        # Split by common delimiters
        parts = re.split(r'[,;]|\sand\s', location_description)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Remove parentheses content for main keyword
            main_part = re.sub(r'\([^)]*\)', '', part).strip()
            
            # Extract meaningful words (capitalized words, subdivision names, etc.)
            words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', main_part)
            
            for word in words:
                word_lower = word.lower()
                if word_lower not in stop_words and len(word) > 2:
                    keywords.append(word)
            
            # Also add the full part if it's a specific name
            if any(char.isupper() for char in part) and len(part) > 5:
                keywords.append(part)
        
        # Remove duplicates and return
        return list(set(keywords))

