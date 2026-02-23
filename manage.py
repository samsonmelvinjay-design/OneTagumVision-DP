#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# Load .env file for local development (before Django settings)
from pathlib import Path
_root = Path(__file__).resolve().parent
env_path = _root / '.env'
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        pass

# Ensure backend (and thus gistagum) is on path when running from project root
_backend = _root / 'backend'
if _backend.exists():
    sys.path.insert(0, str(_root))
    sys.path.insert(0, str(_backend))


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gistagum.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main() 