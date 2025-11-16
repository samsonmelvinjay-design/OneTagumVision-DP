"""
Management command to check and display zone recommendation data
Usage: python manage.py check_zone_data [--project-type CODE]

Shows detailed information about zone allowed uses and helps identify missing data.
"""

from django.core.management.base import BaseCommand
from projeng.models import ZoneAllowedUse, ProjectType


class Command(BaseCommand):
    help = 'Check zone recommendation data completeness and details'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--project-type',
            type=str,
            help='Filter by project type code (e.g., "road", "apartment_building")',
        )
        parser.add_argument(
            '--zone',
            type=str,
            help='Filter by zone type (e.g., "R1", "C1")',
        )
    
    def handle(self, *args, **options):
        project_type_code = options.get('project_type')
        zone_type = options.get('zone')
        
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("Zone Recommendation Data Check"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write("")
        
        if project_type_code:
            self._show_project_type_details(project_type_code)
        elif zone_type:
            self._show_zone_details(zone_type)
        else:
            self._show_summary()
    
    def _show_summary(self):
        """Show overall summary of zone data"""
        total_project_types = ProjectType.objects.count()
        total_allowed_uses = ZoneAllowedUse.objects.count()
        
        self.stdout.write(f"Total Project Types: {total_project_types}")
        self.stdout.write(f"Total Zone Allowed Uses: {total_allowed_uses}")
        
        if total_project_types > 0:
            avg_zones = total_allowed_uses / total_project_types
            self.stdout.write(f"Average zones per project type: {avg_zones:.1f}")
        
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Project Types with Zone Mappings:"))
        self.stdout.write("-" * 70)
        
        for pt in ProjectType.objects.all().order_by('name'):
            zone_count = ZoneAllowedUse.objects.filter(project_type=pt).count()
            status = "✅" if zone_count > 0 else "❌"
            self.stdout.write(f"{status} {pt.name} ({pt.code}): {zone_count} zones")
        
        self.stdout.write("")
        self.stdout.write("Use --project-type CODE to see details for a specific project type")
        self.stdout.write("Use --zone ZONE to see details for a specific zone")
    
    def _show_project_type_details(self, project_type_code):
        """Show detailed zone mappings for a project type"""
        try:
            project_type = ProjectType.objects.get(code=project_type_code)
        except ProjectType.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ Project type '{project_type_code}' not found"))
            return
        
        self.stdout.write(self.style.SUCCESS(f"\nProject Type: {project_type.name} ({project_type.code})"))
        self.stdout.write(f"Description: {project_type.description or 'N/A'}")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Allowed Zones:"))
        self.stdout.write("-" * 70)
        
        allowed_uses = ZoneAllowedUse.objects.filter(project_type=project_type).order_by('zone_type')
        
        if not allowed_uses:
            self.stdout.write(self.style.ERROR("❌ No zones mapped for this project type"))
            self.stdout.write("   Run: python manage.py populate_zone_allowed_uses")
            return
        
        for use in allowed_uses:
            primary_badge = "PRIMARY" if use.is_primary_use else ""
            conditional_badge = "CONDITIONAL" if use.is_conditional else ""
            badges = " ".join(filter(None, [primary_badge, conditional_badge]))
            
            self.stdout.write(f"✅ Zone {use.zone_type}: {badges}")
            
            if use.conditions:
                self.stdout.write(f"   Conditions: {use.conditions}")
            if use.max_density:
                self.stdout.write(f"   Max Density: {use.max_density}")
            if use.max_height:
                self.stdout.write(f"   Max Height: {use.max_height}")
            
            # Zone name lookup
            zone_names = {
                'R1': 'Low Density Residential',
                'R2': 'Medium Density Residential',
                'R3': 'High Density Residential',
                'SHZ': 'Socialized Housing Zone',
                'C1': 'Major Commercial Zone',
                'C2': 'Minor Commercial Zone',
                'I1': 'Heavy Industrial Zone',
                'I2': 'Light and Medium Industrial Zone',
                'Al': 'Agro-Industrial',
                'In': 'Institutional',
                'Ag': 'Agricultural',
                'Cu': 'Cultural',
            }
            zone_name = zone_names.get(use.zone_type, 'Unknown')
            self.stdout.write(f"   Full Name: {zone_name}")
            self.stdout.write("")
        
        # Check for missing zones
        all_zones = ['R1', 'R2', 'R3', 'SHZ', 'C1', 'C2', 'I1', 'I2', 'Al', 'In', 'Ag', 'Cu']
        mapped_zones = {use.zone_type for use in allowed_uses}
        missing_zones = set(all_zones) - mapped_zones
        
        if missing_zones:
            self.stdout.write(self.style.WARNING(f"⚠️  Missing zones: {', '.join(sorted(missing_zones))}"))
    
    def _show_zone_details(self, zone_type):
        """Show all project types allowed in a zone"""
        zone_names = {
            'R1': 'Low Density Residential',
            'R2': 'Medium Density Residential',
            'R3': 'High Density Residential',
            'SHZ': 'Socialized Housing Zone',
            'C1': 'Major Commercial Zone',
            'C2': 'Minor Commercial Zone',
            'I1': 'Heavy Industrial Zone',
            'I2': 'Light and Medium Industrial Zone',
            'Al': 'Agro-Industrial',
            'In': 'Institutional',
            'Ag': 'Agricultural',
            'Cu': 'Cultural',
        }
        
        zone_name = zone_names.get(zone_type, 'Unknown')
        self.stdout.write(self.style.SUCCESS(f"\nZone: {zone_type} - {zone_name}"))
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Allowed Project Types:"))
        self.stdout.write("-" * 70)
        
        allowed_uses = ZoneAllowedUse.objects.filter(zone_type=zone_type).order_by('project_type__name')
        
        if not allowed_uses:
            self.stdout.write(self.style.ERROR(f"❌ No project types mapped for zone {zone_type}"))
            return
        
        for use in allowed_uses:
            primary_badge = "[PRIMARY]" if use.is_primary_use else ""
            conditional_badge = "[CONDITIONAL]" if use.is_conditional else ""
            badges = " ".join(filter(None, [primary_badge, conditional_badge]))
            
            self.stdout.write(f"✅ {use.project_type.name} ({use.project_type.code}) {badges}")
            
            if use.conditions:
                self.stdout.write(f"   Conditions: {use.conditions}")
            if use.max_density or use.max_height:
                restrictions = []
                if use.max_density:
                    restrictions.append(f"Density: {use.max_density}")
                if use.max_height:
                    restrictions.append(f"Height: {use.max_height}")
                self.stdout.write(f"   Restrictions: {', '.join(restrictions)}")
        
        self.stdout.write("")
        self.stdout.write(f"Total: {allowed_uses.count()} project types allowed")

