# OneTagumVision-DP

A GIS-driven platform for project monitoring and visualization for Tagum City. Django-based, with Leaflet and OpenStreetMap for maps and dashboards.

## Features

- Project listing and details
- Interactive map visualization
- Monitoring dashboard and reports (including PDF export)
- Admin interface for project management
- Optional: DigitalOcean Spaces for media storage, Celery/Channels for background tasks and WebSockets

## Quick start (local)

From the **project root** (folder containing `manage.py`):

```bash
# Clone and enter project
git clone <repository-url>
cd OneTagumVision-DP

# Virtual environment (recommended)
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
# source .venv/bin/activate     # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Copy and edit environment variables
copy .env.example .env
# Set DJANGO_SECRET_KEY (see SETUP.md for how to generate)

# Database and run
python manage.py migrate
python manage.py runserver
```

Visit **http://127.0.0.1:8000/** for the app and **http://127.0.0.1:8000/admin/** for the admin.

**Full instructions** — including what to download/install, database options, deployment, and troubleshooting — are in **[SETUP.md](SETUP.md)**.

## Data migration (restore database and media on a new machine)

1. Clone the repo and install dependencies (see [SETUP.md](SETUP.md)).
2. **Restore the database:**
   - **SQLite:** copy the existing `backend/db.sqlite3` (or your `.sqlite3` file) into place.
   - **PostgreSQL:** import your dump, e.g. `psql "DATABASE_URL" < backup.sql`.
3. **Restore media:** copy `media/` (and any `project_images/` folders) into the project root if needed.
4. Run `python manage.py migrate` (for Postgres or if schema changed).
5. Run `python manage.py runserver` and open http://127.0.0.1:8000/.

## Usage

| Page | URL |
|------|-----|
| App / project list | http://127.0.0.1:8000/ |
| Map view | http://127.0.0.1:8000/map/ |
| Admin | http://127.0.0.1:8000/admin/ |

For deployment, environment variables, and troubleshooting, see **[SETUP.md](SETUP.md)**. 