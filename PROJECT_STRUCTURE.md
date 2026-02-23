# OneTagumVision-DP — Project structure

This project uses a **backend / frontend** layout so you can work on server-side or UI code separately.

---

## Backend (Django)

**Location:** `backend/` and app folders at project root (see below)

- **`backend/gistagum/`** — Django project (settings, URLs, WSGI, middleware)
- **`backend/manage.py`** — Run this from project root: `python manage.py …` (or from `backend/`: `python manage.py …` if all apps are under backend)
- **App packages (at project root):** `projeng/`, `monitoring/`, `theme/`, `onetagumvision/`, `accounts/`
- **Config:** `requirements.txt`, `gunicorn_config.py` (in `backend/` when present)

**To work on backend only:** Open the repo and focus on `backend/`, `projeng/`, `monitoring/`, `theme/`, `onetagumvision/`, `accounts/`, and `manage.py`.

**Run server (from project root):**
```bash
python manage.py runserver
```

---

## Frontend (templates & static)

**Location:** `templates/` and `static/` at project root (or `frontend/templates/` and `frontend/static/` if you move them)

- **`templates/`** — Django HTML templates (base, registration, app-specific)
- **`static/`** — CSS, JS, images, and data (e.g. GeoJSON)

**To work on frontend only:** Open the repo and focus on `templates/` and `static/`.

If you move these under **`frontend/`** for a cleaner layout, the app will use `frontend/templates` and `frontend/static` automatically (see `backend/gistagum/settings.py`).

---

## Shared / root

- **`.env`** — Local env vars (not committed)
- **`media/`** — User uploads (local dev)
- **`docs/`** — Project documentation
- **`coord/`** — GeoJSON source files (e.g. for `combine_geojson`)

---

## Paths in code

In `backend/gistagum/settings.py`:

- **`BASE_DIR`** — Backend directory (`backend/`)
- **`PROJECT_ROOT`** — Repo root
- **`TEMPLATES_DIR`** — `frontend/templates` if it exists, else `templates/`
- **`STATIC_SOURCE_DIR`** — `frontend/static` if `frontend/` exists, else `static/`
- **`MEDIA_ROOT_DIR`** — `media/` at repo root

Other commands and views use these so paths stay correct whether you use root-level or `frontend/` layout.
