"""
Management command to populate zone allowed uses
Usage: python manage.py populate_zone_allowed_uses

This command defines which project types are allowed in each zone based on
Tagum City Zoning Ordinance and standard zoning practices.
"""

from django.core.management.base import BaseCommand
from projeng.models import ProjectType, ZoneAllowedUse


class Command(BaseCommand):
    help = 'Populate zone allowed uses (which project types are allowed in each zone)'
    
    def handle(self, *args, **options):
        # Get all project types
        project_types = {pt.code: pt for pt in ProjectType.objects.all()}
        
        if not project_types:
            self.stdout.write(
                self.style.ERROR(
                    'No project types found. Please run populate_project_types first.'
                )
            )
            return
        
        # Define allowed uses for each zone
        # Format: (zone_type, project_type_code, is_primary, is_conditional, conditions, max_density, max_height)
        allowed_uses = [
            # Infrastructure - Allowed in all zones (infrastructure projects)
            # Roads/Highways - Allowed in all zones
            ('R1', 'road', True, False, '', '', ''),
            ('R2', 'road', True, False, '', '', ''),
            ('R3', 'road', True, False, '', '', ''),
            ('SHZ', 'road', True, False, '', '', ''),
            ('C1', 'road', True, False, '', '', ''),
            ('C2', 'road', True, False, '', '', ''),
            ('I1', 'road', True, False, '', '', ''),
            ('I2', 'road', True, False, '', '', ''),
            ('Al', 'road', True, False, '', '', ''),
            ('In', 'road', True, False, '', '', ''),
            ('Ag', 'road', True, False, '', '', ''),
            ('Cu', 'road', True, False, '', '', ''),
            
            # Bridges - Allowed in all zones (infrastructure)
            ('R1', 'bridge', True, False, '', '', ''),
            ('R2', 'bridge', True, False, '', '', ''),
            ('R3', 'bridge', True, False, '', '', ''),
            ('SHZ', 'bridge', True, False, '', '', ''),
            ('C1', 'bridge', True, False, '', '', ''),
            ('C2', 'bridge', True, False, '', '', ''),
            ('I1', 'bridge', True, False, '', '', ''),
            ('I2', 'bridge', True, False, '', '', ''),
            ('Al', 'bridge', True, False, '', '', ''),
            ('In', 'bridge', True, False, '', '', ''),
            ('Ag', 'bridge', True, False, '', '', ''),
            ('Cu', 'bridge', True, False, '', '', ''),
            
            # Water Systems - Allowed in all zones (infrastructure)
            ('R1', 'water_system', True, False, '', '', ''),
            ('R2', 'water_system', True, False, '', '', ''),
            ('R3', 'water_system', True, False, '', '', ''),
            ('SHZ', 'water_system', True, False, '', '', ''),
            ('C1', 'water_system', True, False, '', '', ''),
            ('C2', 'water_system', True, False, '', '', ''),
            ('I1', 'water_system', True, False, '', '', ''),
            ('I2', 'water_system', True, False, '', '', ''),
            ('Al', 'water_system', True, False, '', '', ''),
            ('In', 'water_system', True, False, '', '', ''),
            ('Ag', 'water_system', True, False, '', '', ''),
            ('Cu', 'water_system', True, False, '', '', ''),
            
            # Sewer Systems - Allowed in all zones (infrastructure)
            ('R1', 'sewer_system', True, False, '', '', ''),
            ('R2', 'sewer_system', True, False, '', '', ''),
            ('R3', 'sewer_system', True, False, '', '', ''),
            ('SHZ', 'sewer_system', True, False, '', '', ''),
            ('C1', 'sewer_system', True, False, '', '', ''),
            ('C2', 'sewer_system', True, False, '', '', ''),
            ('I1', 'sewer_system', True, False, '', '', ''),
            ('I2', 'sewer_system', True, False, '', '', ''),
            ('Al', 'sewer_system', True, False, '', '', ''),
            ('In', 'sewer_system', True, False, '', '', ''),
            ('Ag', 'sewer_system', True, False, '', '', ''),
            ('Cu', 'sewer_system', True, False, '', '', ''),
            
            # R1 - Low Density Residential
            ('R1', 'single_family_house', True, False, '', '', '2 stories'),
            ('R1', 'multi_family_house', True, False, '', '20 units/hectare', '2 stories'),
            ('R1', 'church', True, False, '', '', '2 stories'),
            ('R1', 'school', True, False, '', '', '2 stories'),
            ('R1', 'park', True, False, '', '', ''),
            
            # R2 - Medium Density Residential
            ('R2', 'single_family_house', True, False, '', '', '3 stories'),
            ('R2', 'multi_family_house', True, False, '', '50 units/hectare', '3 stories'),
            ('R2', 'apartment_building', True, False, '', '100 units/hectare', '5 stories'),
            ('R2', 'retail_store', True, False, 'Ground floor only', '', '3 stories'),
            ('R2', 'restaurant', True, False, 'Ground floor only', '', '3 stories'),
            ('R2', 'church', True, False, '', '', '3 stories'),
            ('R2', 'school', True, False, '', '', '3 stories'),
            ('R2', 'park', True, False, '', '', ''),
            
            # R3 - High Density Residential
            ('R3', 'multi_family_house', True, False, '', '150 units/hectare', '5 stories'),
            ('R3', 'apartment_building', True, True, '', '200 units/hectare', '5 stories'),
            ('R3', 'high_rise_residential', True, False, '', '300 units/hectare', '10+ stories'),
            ('R3', 'retail_store', True, False, 'Ground floor only', '', '5 stories'),
            ('R3', 'restaurant', True, False, 'Ground floor only', '', '5 stories'),
            ('R3', 'office_building', True, False, '', '', '5 stories'),
            ('R3', 'church', True, False, '', '', '5 stories'),
            ('R3', 'school', True, False, '', '', '5 stories'),
            ('R3', 'park', True, False, '', '', ''),
            
            # SHZ - Socialized Housing Zone
            ('SHZ', 'socialized_housing', True, False, '', '150 units/hectare', '5 stories'),
            ('SHZ', 'single_family_house', True, False, '', '50 units/hectare', '2 stories'),
            ('SHZ', 'multi_family_house', True, False, '', '100 units/hectare', '3 stories'),
            ('SHZ', 'apartment_building', True, False, '', '150 units/hectare', '5 stories'),
            ('SHZ', 'church', True, False, '', '', '3 stories'),
            ('SHZ', 'school', True, False, '', '', '3 stories'),
            ('SHZ', 'park', True, False, '', '', ''),
            
            # C1 - Major Commercial Zone
            ('C1', 'retail_store', True, False, '', '', '5 stories'),
            ('C1', 'shopping_mall', True, False, '', '', '10+ stories'),
            ('C1', 'office_building', True, False, '', '', '10+ stories'),
            ('C1', 'hotel', True, False, '', '', '10+ stories'),
            ('C1', 'restaurant', True, False, '', '', '5 stories'),
            ('C1', 'apartment_building', True, False, 'Upper floors only', '', '10+ stories'),
            ('C1', 'high_rise_residential', True, False, 'Upper floors only', '', '10+ stories'),
            ('C1', 'church', True, False, '', '', '5 stories'),
            ('C1', 'school', True, False, '', '', '5 stories'),
            ('C1', 'hospital', True, False, '', '', '10+ stories'),
            ('C1', 'government_building', True, False, '', '', '10+ stories'),
            
            # C2 - Minor Commercial Zone
            ('C2', 'retail_store', True, False, '', '', '3 stories'),
            ('C2', 'restaurant', True, False, '', '', '3 stories'),
            ('C2', 'office_building', True, False, '', '', '5 stories'),
            ('C2', 'apartment_building', True, False, 'Upper floors only', '', '5 stories'),
            ('C2', 'church', True, False, '', '', '3 stories'),
            ('C2', 'school', True, False, '', '', '3 stories'),
            
            # I1 - Heavy Industrial Zone
            ('I1', 'heavy_industrial', True, False, '', '', ''),
            ('I1', 'factory', True, False, '', '', ''),
            ('I1', 'warehouse', True, False, '', '', ''),
            ('I1', 'light_industrial', True, False, '', '', ''),
            
            # I2 - Light and Medium Industrial Zone
            ('I2', 'light_industrial', True, False, '', '', ''),
            ('I2', 'warehouse', True, False, '', '', ''),
            ('I2', 'factory', True, False, 'Light manufacturing only', '', ''),
            ('I2', 'office_building', True, False, 'Industrial offices', '', '5 stories'),
            
            # Al - Agro-Industrial
            ('Al', 'warehouse', True, False, 'Agricultural storage', '', ''),
            ('Al', 'light_industrial', True, False, 'Agro-processing', '', ''),
            ('Al', 'factory', True, False, 'Agro-processing', '', ''),
            
            # In - Institutional
            ('In', 'school', True, False, '', '', '10+ stories'),
            ('In', 'hospital', True, False, '', '', '10+ stories'),
            ('In', 'government_building', True, False, '', '', '10+ stories'),
            ('In', 'church', True, False, '', '', '5 stories'),
            ('In', 'park', True, False, '', '', ''),
            ('In', 'cemetery', True, False, '', '', ''),
            
            # Ag - Agricultural
            ('Ag', 'park', True, False, '', '', ''),
            ('Ag', 'cemetery', True, False, '', '', ''),
            
            # Cu - Cultural
            ('Cu', 'church', True, False, '', '', '5 stories'),
            ('Cu', 'park', True, False, '', '', ''),
            ('Cu', 'government_building', True, False, 'Cultural centers only', '', '5 stories'),
        ]
        
        created = 0
        updated = 0
        errors = 0
        
        for zone_type, project_type_code, is_primary, is_conditional, conditions, max_density, max_height in allowed_uses:
            if project_type_code not in project_types:
                self.stdout.write(
                    self.style.ERROR(
                        f'Project type "{project_type_code}" not found. Skipping.'
                    )
                )
                errors += 1
                continue
            
            project_type = project_types[project_type_code]
            
            try:
                obj, created_flag = ZoneAllowedUse.objects.update_or_create(
                    zone_type=zone_type,
                    project_type=project_type,
                    defaults={
                        'is_primary_use': is_primary,
                        'is_conditional': is_conditional,
                        'conditions': conditions,
                        'max_density': max_density,
                        'max_height': max_height
                    }
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error creating {zone_type} - {project_type.name}: {e}'
                    )
                )
                errors += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully populated zone allowed uses: '
                f'{created} created, {updated} updated, {errors} errors'
            )
        )

