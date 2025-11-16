#!/usr/bin/env python
"""Test road recommendations API response"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gistagum.settings')
django.setup()

from projeng.zone_recommendation import ZoneCompatibilityEngine

print("=" * 60)
print("Testing Road/Highway Recommendations")
print("=" * 60)

engine = ZoneCompatibilityEngine()
result = engine.recommend_zones('road', None, None, 5)

print(f"\nAllowed zones count: {len(result['allowed_zones'])}")
print(f"Recommendations count: {len(result['recommendations'])}")
print(f"\nFirst 5 allowed zones:")
for zone in result['allowed_zones'][:5]:
    print(f"  - {zone['zone_type']}: {zone['zone_name']}")

if result['recommendations']:
    print(f"\nTop 3 recommendations:")
    for rec in result['recommendations'][:3]:
        print(f"  - {rec['zone_type']}: Score {rec['overall_score']:.1f}")
else:
    print("\n⚠️  No recommendations generated!")

print("\n" + "=" * 60)

