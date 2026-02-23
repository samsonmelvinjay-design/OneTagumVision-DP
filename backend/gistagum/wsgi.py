import os
from pathlib import Path

# Load .env file for local development (before Django settings)
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        pass

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gistagum.settings')

application = get_wsgi_application() 