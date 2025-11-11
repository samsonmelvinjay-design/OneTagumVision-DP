from django.core.management.base import BaseCommand
from projeng.models import BarangayMetadata

class Command(BaseCommand):
    help = 'Populate barangay metadata from the infographic data (PSA-2020 CPH)'
    
    def handle(self, *args, **options):
        # Data extracted from the infographic
        # Note: Some data may need to be verified or updated from official sources
        barangay_data = [
            {
                'name': 'Apokon',
                'population': 37984,
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
                'barangay_class': 'rural',
                'economic_class': 'satellite',
                'elevation_type': 'coastal',
                'industrial_zones': ['agro_industrial'],
                'primary_industries': ['fishery', 'eco_tourism', 'coconut'],
                'special_features': ['mangrove_forest', 'marine_protected_area', 'cemetery']
            },
            {
                'name': 'Busaon',
                'barangay_class': 'rural',
                'economic_class': 'emerging',
                'elevation_type': 'coastal',
                'industrial_zones': ['agro_industrial'],
                'primary_industries': ['fishery', 'coconut', 'agriculture'],
                'special_features': ['public_cemeteries', 'piggery', 'pomelo', 'mandarin', 'banana']
            },
            {
                'name': 'Canocotan',
                'barangay_class': 'urban',
                'economic_class': 'satellite',
                'elevation_type': 'plains',
                'industrial_zones': ['institutional_recreational'],
                'primary_industries': ['coconut', 'residential', 'industrial'],
                'special_features': ['city_jail', 'dpwh', 'pallet_maker']
            },
            {
                'name': 'Cuambogan',
                'barangay_class': 'rural',
                'economic_class': 'satellite',
                'elevation_type': 'plains',
                'industrial_zones': ['agro_industrial'],
                'primary_industries': ['industrial', 'banana', 'agriculture'],
                'special_features': ['plywood', 'banana_chips', 'cardava', 'rice']
            },
            {
                'name': 'La Filipina',
                'population': 21262,
                'growth_rate': 7.0,
                'barangay_class': 'urban',
                'economic_class': 'emerging',
                'elevation_type': 'plains',
                'industrial_zones': ['institutional_recreational', 'commercial_expansion'],
                'primary_industries': ['tourism', 'banana', 'residential', 'agriculture'],
                'special_features': ['cemeteries', 'funeral_parlors', 'inland_resorts', 'parks', 'hotels', 'inns', 'night_clubs']
            },
            {
                'name': 'Liboganon',
                'barangay_class': 'rural',
                'economic_class': 'satellite',
                'elevation_type': 'coastal',
                'industrial_zones': ['agro_industrial'],
                'primary_industries': ['tourism', 'fishery', 'coconut'],
                'special_features': ['beach_resorts', 'marine_protected_area', 'mangrove_forest']
            },
            {
                'name': 'Madaum',
                'growth_rate': 6.4,
                'barangay_class': 'rural',
                'economic_class': 'emerging',
                'elevation_type': 'coastal',
                'industrial_zones': ['agro_industrial', 'commercial_expansion'],
                'primary_industries': ['banana', 'corn', 'tourism', 'agriculture'],
                'special_features': ['banana_beach_resort', 'wharf', 'cattle_ranch', 'public_cemetery', 'satellite_market']
            },
            {
                'name': 'Magdum',
                'growth_rate': 6.10,
                'barangay_class': 'urban',
                'economic_class': 'satellite',
                'elevation_type': 'plains',
                'industrial_zones': ['agro_industrial'],
                'primary_industries': ['industrial', 'residential'],
                'special_features': ['nestle', 'demo_farm', 'ngas', 'slaughter_house']
            },
            {
                'name': 'Magugpo East',
                'barangay_class': 'urban',
                'economic_class': 'growth_center',
                'elevation_type': 'plains',
                'industrial_zones': ['cbd', 'institutional_recreational'],
                'primary_industries': ['shopping', 'institutional', 'residential', 'agro_industrial'],
                'special_features': ['motorpool', 'colleges', 'churches']
            },
            {
                'name': 'Magugpo North',
                'density': 7224,
                'barangay_class': 'urban',
                'economic_class': 'growth_center',
                'elevation_type': 'plains',
                'industrial_zones': ['cbd', 'commercial_expansion'],
                'primary_industries': ['residential', 'agro_industrial', 'tourism'],
                'special_features': ['inns', 'hotels', 'warehouses']
            },
            {
                'name': 'Magugpo Poblacion',
                'barangay_class': 'urban',
                'economic_class': 'growth_center',
                'elevation_type': 'plains',
                'industrial_zones': ['cbd', 'institutional_recreational'],
                'primary_industries': ['shopping', 'institutional', 'tourism', 'financial'],
                'special_features': ['historical_cultural_center', 'trade_center', 'ngas', 'churches', 'schools', 'inns', 'hotels', 'financial_institutions']
            },
            {
                'name': 'Magugpo South',
                'density': 8349,
                'barangay_class': 'urban',
                'economic_class': 'growth_center',
                'elevation_type': 'plains',
                'industrial_zones': ['cbd', 'commercial_expansion'],
                'primary_industries': ['residential', 'institutional', 'tourism'],
                'special_features': ['churches', 'city_health_center', 'schools', 'colleges', 'ngas', 'inns']
            },
            {
                'name': 'Magugpo West',
                'density': 7339,
                'barangay_class': 'urban',
                'economic_class': 'growth_center',
                'elevation_type': 'plains',
                'industrial_zones': ['cbd', 'commercial_expansion'],
                'primary_industries': ['commercial', 'institutional', 'financial'],
                'special_features': ['public_market', 'transport_terminal', 'quacs', 'lay_formation_training_center', 'orphanage', 'lending_institutions']
            },
            {
                'name': 'Mankilam',
                'population': 41345,
                'land_area': 15.12,
                'barangay_class': 'urban',
                'economic_class': 'growth_center',
                'elevation_type': 'plains',
                'industrial_zones': ['institutional_recreational', 'agro_industrial'],
                'primary_industries': ['institutional', 'recreation', 'residential', 'agriculture'],
                'special_features': ['provincial_government', 'ngas', 'sports_complex', 'inland_resorts', 'comprehensive_high_school', 'churches', 'banana', 'vegetables']
            },
            {
                'name': 'New Balamban',
                'population': 1596,
                'land_area': 8.415,
                'barangay_class': 'rural',
                'economic_class': 'emerging',
                'elevation_type': 'plains',
                'industrial_zones': ['agro_industrial'],
                'primary_industries': ['agriculture'],
                'special_features': ['rice', 'coconut', 'durian', 'corn', 'vegetables', 'mango', 'banana']
            },
            {
                'name': 'Nueva Fuerza',
                'population': 2496,
                'land_area': 4.518,
                'barangay_class': 'rural',
                'economic_class': 'emerging',
                'elevation_type': 'plains',
                'industrial_zones': ['agro_industrial'],
                'primary_industries': ['agriculture'],
                'special_features': ['rice', 'coconut', 'durian', 'corn', 'vegetables', 'mango', 'bamboo', 'cemetery']
            },
            {
                'name': 'Pagsabangan',
                'population': 5556,
                'land_area': 9.826,
                'barangay_class': 'rural',
                'economic_class': 'satellite',
                'elevation_type': 'plains',
                'industrial_zones': ['agro_industrial'],
                'primary_industries': ['agriculture', 'industrial'],
                'special_features': ['rice', 'public_cemetery', 'banana', 'vegetables', 'coco_twine', 'water_system']
            },
            {
                'name': 'Pandapan',
                'population': 2504,
                'land_area': 5.382,
                'barangay_class': 'rural',
                'economic_class': 'satellite',
                'elevation_type': 'highland',
                'industrial_zones': ['agro_industrial'],
                'primary_industries': ['industrial', 'agriculture'],
                'special_features': ['quarrying', 'gold_processing', 'bamboo', 'calamansi', 'coconut', 'watershed']
            },
            {
                'name': 'San Agustin',
                'population': 1567,
                'land_area': 4.169,
                'growth_rate': 7.40,
                'barangay_class': 'rural',
                'economic_class': 'emerging',
                'elevation_type': 'highland',
                'industrial_zones': ['agro_industrial', 'institutional_recreational'],
                'primary_industries': ['agriculture', 'tourism'],
                'special_features': ['controlled_dumpsite', 'bamboo', 'coconut', 'corn', 'rice', 'vegetables', 'agro_forest', 'botanical_park']
            },
            {
                'name': 'San Isidro',
                'population': 4795,
                'land_area': 7.984,
                'barangay_class': 'urban',
                'economic_class': 'satellite',
                'elevation_type': 'plains',
                'industrial_zones': ['agro_industrial'],
                'primary_industries': ['residential', 'agriculture', 'industrial'],
                'special_features': ['resettlement_area', 'coconut', 'coffin_maker', 'pallet_maker']
            },
            {
                'name': 'San Miguel',
                'population': 21735,
                'land_area': 10.25,
                'barangay_class': 'urban',
                'economic_class': 'growth_center',
                'elevation_type': 'plains',
                'industrial_zones': ['commercial_expansion', 'institutional_recreational', 'agro_industrial'],
                'primary_industries': ['residential', 'tourism', 'agriculture', 'agro_industrial'],
                'special_features': ['resettlement_areas', 'center_for_elderly', 'inland_resorts', 'inns', 'coconut', 'calamansi', 'poultry', 'piggery', 'game_fowl', 'warehouses']
            },
            {
                'name': 'Visayan Village',
                'population': 42648,
                'density': 5237,
                'barangay_class': 'urban',
                'economic_class': 'growth_center',
                'elevation_type': 'plains',
                'industrial_zones': ['cbd', 'institutional_recreational', 'commercial_expansion'],
                'primary_industries': ['residential', 'institutional', 'shopping', 'tourism'],
                'special_features': ['private_hospitals', 'city_high_school', 'colleges', 'home_for_aged']
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for data in barangay_data:
            barangay, created = BarangayMetadata.objects.update_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created: {barangay.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated: {barangay.name}')
                )
        
        total = BarangayMetadata.objects.count()
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {len(barangay_data)} barangays\n'
                f'   Created: {created_count}\n'
                f'   Updated: {updated_count}\n'
                f'   Total in database: {total}'
            )
        )

