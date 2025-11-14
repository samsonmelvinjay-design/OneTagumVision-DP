"""
Management command to populate project types
Usage: python manage.py populate_project_types
"""

from django.core.management.base import BaseCommand
from projeng.models import ProjectType


class Command(BaseCommand):
    help = 'Populate project types in the database'
    
    def handle(self, *args, **options):
        project_types_data = [
            # Residential
            {
                'code': 'single_family_house',
                'name': 'Single Family House',
                'description': 'Single-family detached or semi-detached residential unit',
                'density_level': 'low',
                'height_category': 'low',
                'requires_residential': True,
                'requires_commercial': False,
                'requires_industrial': False
            },
            {
                'code': 'multi_family_house',
                'name': 'Multi-Family House',
                'description': 'Multi-family residential building (2-4 units)',
                'density_level': 'medium',
                'height_category': 'low',
                'requires_residential': True,
                'requires_commercial': False,
                'requires_industrial': False
            },
            {
                'code': 'apartment_building',
                'name': 'Apartment Building (3-5 stories)',
                'description': 'Multi-story apartment building with 3-5 floors',
                'density_level': 'high',
                'height_category': 'medium',
                'requires_residential': True,
                'requires_commercial': False,
                'requires_industrial': False
            },
            {
                'code': 'high_rise_residential',
                'name': 'High-Rise Residential (6+ stories)',
                'description': 'High-rise residential building with 6 or more floors',
                'density_level': 'high',
                'height_category': 'high',
                'requires_residential': True,
                'requires_commercial': False,
                'requires_industrial': False
            },
            {
                'code': 'socialized_housing',
                'name': 'Socialized Housing',
                'description': 'Affordable housing for low-income families',
                'density_level': 'medium',
                'height_category': 'medium',
                'requires_residential': True,
                'requires_commercial': False,
                'requires_industrial': False
            },
            # Commercial
            {
                'code': 'retail_store',
                'name': 'Retail Store',
                'description': 'Small to medium retail store',
                'density_level': 'medium',
                'height_category': 'low',
                'requires_residential': False,
                'requires_commercial': True,
                'requires_industrial': False
            },
            {
                'code': 'shopping_mall',
                'name': 'Shopping Mall',
                'description': 'Large shopping mall or commercial complex',
                'density_level': 'high',
                'height_category': 'medium',
                'requires_residential': False,
                'requires_commercial': True,
                'requires_industrial': False
            },
            {
                'code': 'office_building',
                'name': 'Office Building',
                'description': 'Commercial office building',
                'density_level': 'high',
                'height_category': 'high',
                'requires_residential': False,
                'requires_commercial': True,
                'requires_industrial': False
            },
            {
                'code': 'hotel',
                'name': 'Hotel',
                'description': 'Hotel or lodging facility',
                'density_level': 'high',
                'height_category': 'high',
                'requires_residential': False,
                'requires_commercial': True,
                'requires_industrial': False
            },
            {
                'code': 'restaurant',
                'name': 'Restaurant',
                'description': 'Restaurant or food service establishment',
                'density_level': 'medium',
                'height_category': 'low',
                'requires_residential': False,
                'requires_commercial': True,
                'requires_industrial': False
            },
            # Industrial
            {
                'code': 'light_industrial',
                'name': 'Light Industrial Facility',
                'description': 'Light industrial manufacturing facility',
                'density_level': 'medium',
                'height_category': 'medium',
                'requires_residential': False,
                'requires_commercial': False,
                'requires_industrial': True
            },
            {
                'code': 'heavy_industrial',
                'name': 'Heavy Industrial Facility',
                'description': 'Heavy industrial manufacturing facility',
                'density_level': 'medium',
                'height_category': 'medium',
                'requires_residential': False,
                'requires_commercial': False,
                'requires_industrial': True
            },
            {
                'code': 'warehouse',
                'name': 'Warehouse',
                'description': 'Storage warehouse facility',
                'density_level': 'low',
                'height_category': 'medium',
                'requires_residential': False,
                'requires_commercial': False,
                'requires_industrial': True
            },
            {
                'code': 'factory',
                'name': 'Factory',
                'description': 'Manufacturing factory',
                'density_level': 'medium',
                'height_category': 'medium',
                'requires_residential': False,
                'requires_commercial': False,
                'requires_industrial': True
            },
            # Infrastructure
            {
                'code': 'road',
                'name': 'Road/Highway',
                'description': 'Road or highway infrastructure',
                'density_level': 'low',
                'height_category': None,
                'requires_residential': False,
                'requires_commercial': False,
                'requires_industrial': False
            },
            {
                'code': 'bridge',
                'name': 'Bridge',
                'description': 'Bridge infrastructure',
                'density_level': 'low',
                'height_category': None,
                'requires_residential': False,
                'requires_commercial': False,
                'requires_industrial': False
            },
            {
                'code': 'water_system',
                'name': 'Water System',
                'description': 'Water supply and distribution system',
                'density_level': 'low',
                'height_category': None,
                'requires_residential': False,
                'requires_commercial': False,
                'requires_industrial': False
            },
            {
                'code': 'sewer_system',
                'name': 'Sewer System',
                'description': 'Sewer and wastewater system',
                'density_level': 'low',
                'height_category': None,
                'requires_residential': False,
                'requires_commercial': False,
                'requires_industrial': False
            },
            # Institutional
            {
                'code': 'school',
                'name': 'School',
                'description': 'Educational institution (elementary, high school, college)',
                'density_level': 'medium',
                'height_category': 'medium',
                'requires_residential': False,
                'requires_commercial': False,
                'requires_industrial': False
            },
            {
                'code': 'hospital',
                'name': 'Hospital',
                'description': 'Medical hospital or healthcare facility',
                'density_level': 'high',
                'height_category': 'high',
                'requires_residential': False,
                'requires_commercial': False,
                'requires_industrial': False
            },
            {
                'code': 'government_building',
                'name': 'Government Building',
                'description': 'Government office or administrative building',
                'density_level': 'medium',
                'height_category': 'medium',
                'requires_residential': False,
                'requires_commercial': False,
                'requires_industrial': False
            },
            {
                'code': 'church',
                'name': 'Church/Religious Building',
                'description': 'Religious place of worship',
                'density_level': 'low',
                'height_category': 'medium',
                'requires_residential': False,
                'requires_commercial': False,
                'requires_industrial': False
            },
            # Other
            {
                'code': 'park',
                'name': 'Park/Recreation',
                'description': 'Public park or recreation facility',
                'density_level': 'low',
                'height_category': None,
                'requires_residential': False,
                'requires_commercial': False,
                'requires_industrial': False
            },
            {
                'code': 'cemetery',
                'name': 'Cemetery',
                'description': 'Cemetery or memorial park',
                'density_level': 'low',
                'height_category': None,
                'requires_residential': False,
                'requires_commercial': False,
                'requires_industrial': False
            },
        ]
        
        created = 0
        updated = 0
        
        for data in project_types_data:
            obj, created_flag = ProjectType.objects.update_or_create(
                code=data['code'],
                defaults={
                    'name': data['name'],
                    'description': data['description'],
                    'density_level': data['density_level'],
                    'height_category': data['height_category'],
                    'requires_residential': data['requires_residential'],
                    'requires_commercial': data['requires_commercial'],
                    'requires_industrial': data['requires_industrial']
                }
            )
            if created_flag:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'Created: {obj.name}'))
            else:
                updated += 1
                self.stdout.write(self.style.WARNING(f'Updated: {obj.name}'))
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully populated project types: '
                f'{created} created, {updated} updated'
            )
        )

