#!/usr/bin/env python
"""
Check Zone Mappings for All Project Types
Verifies that all project types have zone mappings configured
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gistagum.settings')
django.setup()

from projeng.models import ProjectType, ZoneAllowedUse

print("=" * 80)
print("CHECKING ZONE MAPPINGS FOR ALL PROJECT TYPES")
print("=" * 80)
print()

project_types = ProjectType.objects.all().order_by('name')
total_types = project_types.count()
types_with_zones = 0
types_without_zones = []

print(f"{'Status':<10} {'Project Type':<45} {'Code':<30} {'Zones':<10}")
print("-" * 80)

for pt in project_types:
    zone_count = ZoneAllowedUse.objects.filter(project_type=pt).count()
    status = "✅" if zone_count > 0 else "❌"
    
    if zone_count > 0:
        types_with_zones += 1
        print(f"{status:<10} {pt.name:<45} {pt.code:<30} {zone_count:>3}")
    else:
        types_without_zones.append(pt.code)
        print(f"{status:<10} {pt.name:<45} {pt.code:<30} {zone_count:>3} ⚠️  NO ZONES!")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total Project Types: {total_types}")
print(f"Types with zones: {types_with_zones}/{total_types} ({types_with_zones/total_types*100:.1f}%)")
print(f"Types without zones: {len(types_without_zones)}/{total_types} ({len(types_without_zones)/total_types*100:.1f}%)")

if types_without_zones:
    print()
    print("⚠️  PROJECT TYPES WITHOUT ZONE MAPPINGS:")
    for code in types_without_zones:
        pt = ProjectType.objects.get(code=code)
        print(f"   - {pt.name} ({code})")
    print()
    print("💡 SOLUTION:")
    print("   Run: python manage.py populate_zone_allowed_uses")
    print("   Then run: python manage.py check_zone_data --project-type <code>")
    print("   to verify each project type has proper zone mappings.")
else:
    print()
    print("✅ All project types have zone mappings configured!")

print()
print("=" * 80)

