from django.core.management.base import BaseCommand
from projeng.models import ZoningZone
import json
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Populate ZoningZone database from parsed zoning data JSON file'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='parsed_zoning_data.json',
            help='Path to the parsed zoning data JSON file'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing zones before populating'
        )
    
    def handle(self, *args, **options):
        file_path = options['file']
        
        # If relative path, look in project root
        if not os.path.isabs(file_path):
            project_root = getattr(settings, 'PROJECT_ROOT', settings.BASE_DIR)
            file_path = os.path.join(str(project_root), file_path)
        
        # Check if file exists
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            self.stdout.write(self.style.WARNING('Run "python manage.py parse_zoning_data" first to create the JSON file'))
            return
        
        # Clear existing zones if requested
        if options['clear']:
            count = ZoningZone.objects.count()
            ZoningZone.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count} existing zones'))
        
        # Load JSON data
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                zones_data = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error reading file: {str(e)}'))
            return
        
        if not isinstance(zones_data, list):
            self.stdout.write(self.style.ERROR('Invalid JSON format: expected a list'))
            return
        
        # Process each zone entry
        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        
        for zone_data in zones_data:
            try:
                # Validate required fields
                if not zone_data.get('zone_type') or not zone_data.get('barangay'):
                    skipped_count += 1
                    continue
                
                zone_type = zone_data['zone_type']
                barangay = zone_data['barangay']
                location_description = zone_data.get('location_description', '')
                keywords = zone_data.get('keywords', [])
                
                # Ensure keywords is a list
                if not isinstance(keywords, list):
                    keywords = []
                
                # Create or update zone
                zone, created = ZoningZone.objects.update_or_create(
                    zone_type=zone_type,
                    barangay=barangay,
                    location_description=location_description,
                    defaults={
                        'keywords': keywords,
                        'is_active': True
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'Created: {zone_type} - {barangay}'))
                else:
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f'Updated: {zone_type} - {barangay}'))
                    
            except Exception as e:
                error_msg = f"Error processing {zone_data.get('barangay', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                self.stdout.write(self.style.ERROR(error_msg))
                skipped_count += 1
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Zoning Zone Population Complete'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Created: {created_count}')
        self.stdout.write(f'Updated: {updated_count}')
        self.stdout.write(f'Skipped: {skipped_count}')
        if errors:
            self.stdout.write(self.style.WARNING(f'Errors: {len(errors)}'))
        
        total = ZoningZone.objects.count()
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Total zones in database: {total}'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        # Show zone distribution
        self.stdout.write('')
        self.stdout.write('Zone Distribution:')
        from django.db.models import Count
        distribution = ZoningZone.objects.values('zone_type').annotate(
            count=Count('id')
        ).order_by('zone_type')
        
        for item in distribution:
            self.stdout.write(f'  {item["zone_type"]}: {item["count"]} zones')

