#!/usr/bin/env python
"""Test API endpoint directly"""
import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gistagum.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from projeng.views import zone_recommendation_api

print("=" * 60)
print("Testing Zone Recommendation API Endpoint")
print("=" * 60)

factory = RequestFactory()

# Create a mock request
request = factory.get('/projeng/api/zone-recommendation/', {
    'project_type_code': 'road',
    'limit': '5'
})
request.user = AnonymousUser()  # This might cause login_required to fail

try:
    response = zone_recommendation_api(request)
    print(f"\nResponse status code: {response.status_code}")
    print(f"Response content type: {response.get('Content-Type', 'N/A')}")
    
    # Get response data
    if hasattr(response, 'content'):
        try:
            data = json.loads(response.content.decode('utf-8'))
            print(f"\nResponse data keys: {list(data.keys())}")
            print(f"Allowed zones count: {len(data.get('allowed_zones', []))}")
            print(f"Recommendations count: {len(data.get('recommendations', []))}")
            
            if data.get('allowed_zones'):
                print(f"\nFirst 3 allowed zones:")
                for zone in data['allowed_zones'][:3]:
                    print(f"  - {zone.get('zone_type')}: {zone.get('zone_name')}")
            
            if data.get('recommendations'):
                print(f"\nTop 3 recommendations:")
                for rec in data['recommendations'][:3]:
                    print(f"  - {rec.get('zone_type')}: Score {rec.get('overall_score', 0):.1f}")
            
            if data.get('error'):
                print(f"\n⚠️  Error in response: {data['error']}")
                
        except json.JSONDecodeError as e:
            print(f"\n❌ Failed to parse JSON: {e}")
            print(f"Response content: {response.content.decode('utf-8')[:200]}")
    else:
        print("\n❌ Response has no content attribute")
        
except Exception as e:
    print(f"\n❌ Error calling API: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)

