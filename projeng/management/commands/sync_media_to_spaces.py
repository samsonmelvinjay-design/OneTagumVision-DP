"""
Upload local media files to DigitalOcean Spaces.
Run when you have project images in media/ folder but they're not yet in Spaces.
Usage: python manage.py sync_media_to_spaces [--media-dir PATH]
"""
import os
from pathlib import Path

# Load .env before checking Spaces config (handles venvs where dotenv may not run in manage.py)
def _load_env():
    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    env_path = base_dir / ".env"
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except ImportError:
            pass

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Upload local media files (project_images, progress_photos) to DigitalOcean Spaces"

    def add_arguments(self, parser):
        parser.add_argument(
            "--media-dir",
            type=str,
            default=None,
            help="Path to local media folder (default: settings.MEDIA_ROOT or ./media)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List files that would be uploaded without uploading",
        )

    def handle(self, *args, **options):
        _load_env()

        media_dir = options.get("media_dir")
        if not media_dir:
            # Use MEDIA_ROOT if it points to local; else default to project media/
            mr = getattr(settings, "MEDIA_ROOT", "")
            media_dir = mr if mr and os.path.isdir(mr) else str(Path(settings.BASE_DIR) / "media")
        dry_run = options.get("dry_run")

        if not os.path.isdir(media_dir):
            self.stdout.write(self.style.ERROR(f"Media directory not found: {media_dir}"))
            self.stdout.write(
                "Ensure you have a local media/ folder with project_images/ and progress_photos/"
            )
            return

        # Check Spaces config (read from os.environ since we just loaded .env)
        use_spaces = os.environ.get("USE_SPACES", "").lower() in ("true", "1", "yes")
        bucket = os.environ.get("AWS_STORAGE_BUCKET_NAME", "") or getattr(settings, "AWS_STORAGE_BUCKET_NAME", "")
        endpoint = os.environ.get("AWS_S3_ENDPOINT_URL", "") or getattr(settings, "AWS_S3_ENDPOINT_URL", "")
        if not use_spaces or not bucket or not endpoint:
            self.stdout.write(
                self.style.ERROR(
                    "Spaces not configured. Set in .env: USE_SPACES=true, AWS_ACCESS_KEY_ID, "
                    "AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME, AWS_S3_ENDPOINT_URL. "
                    "Install python-dotenv if .env is not loading: pip install python-dotenv"
                )
            )
            return

        try:
            import boto3
        except ImportError:
            self.stdout.write(self.style.ERROR("boto3 required: pip install boto3"))
            return

        access_key = os.environ.get("AWS_ACCESS_KEY_ID", "") or getattr(settings, "AWS_ACCESS_KEY_ID", "")
        secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "") or getattr(settings, "AWS_SECRET_ACCESS_KEY", "")
        region = os.environ.get("AWS_S3_REGION_NAME", "") or getattr(settings, "AWS_S3_REGION_NAME", "sgp1")

        session = boto3.session.Session()
        client = session.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

        uploaded = 0
        for root, _dirs, files in os.walk(media_dir):
            for f in files:
                local_path = os.path.join(root, f)
                rel = os.path.relpath(local_path, media_dir).replace("\\", "/")
                if rel.startswith("."):
                    continue
                key = rel

                if dry_run:
                    self.stdout.write(f"Would upload: {key}")
                    uploaded += 1
                    continue

                try:
                    client.upload_file(
                        local_path,
                        bucket,
                        key,
                        ExtraArgs={"ACL": "public-read", "ContentType": self._guess_content_type(f)},
                    )
                    self.stdout.write(self.style.SUCCESS(f"Uploaded: {key}"))
                    uploaded += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed {key}: {e}"))

        if dry_run:
            self.stdout.write(self.style.WARNING(f"Dry run: {uploaded} file(s) would be uploaded"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Done. Uploaded {uploaded} file(s)"))

    def _guess_content_type(self, filename):
        ext = os.path.splitext(filename)[1].lower()
        return {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".jfif": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }.get(ext, "application/octet-stream")
