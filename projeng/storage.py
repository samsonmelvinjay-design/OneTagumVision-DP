"""
Custom storage backends for DigitalOcean Spaces
"""
from django.conf import settings
try:
    from storages.backends.s3boto3 import S3Boto3Storage
except ImportError:
    # Fallback if django-storages is not installed
    S3Boto3Storage = None


if S3Boto3Storage:
    class PublicMediaStorage(S3Boto3Storage):
        """
        Storage backend for public media files (images, documents, etc.)
        Uses DigitalOcean Spaces when configured
        """
        location = ''
        default_acl = 'public-read'
        file_overwrite = False
        querystring_auth = False
else:
    # Fallback if django-storages is not available
    PublicMediaStorage = None

