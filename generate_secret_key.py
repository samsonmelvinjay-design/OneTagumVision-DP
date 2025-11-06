#!/usr/bin/env python
"""
Quick script to generate a Django secret key for production.
Run: python generate_secret_key.py
"""
from django.core.management.utils import get_random_secret_key

if __name__ == "__main__":
    secret_key = get_random_secret_key()
    print("\n" + "="*60)
    print("Your Django Secret Key (copy this for production):")
    print("="*60)
    print(secret_key)
    print("="*60)
    print("\n⚠️  IMPORTANT: Keep this key secret and never commit it to Git!")
    print("   Add it as an environment variable: DJANGO_SECRET_KEY\n")

