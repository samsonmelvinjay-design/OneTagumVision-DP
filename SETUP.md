# OneTagumVision-DP — Setup & Deployment Guide

This guide explains what to download, install, and configure so you can run or deploy this project on a new machine or server.

---

## Table of Contents

1. [Prerequisites (What to Download & Install)](#1-prerequisites-what-to-download--install)
2. [Local Development Setup](#2-local-development-setup)
3. [Environment Variables (.env)](#3-environment-variables-env)
4. [Database Setup](#4-database-setup)
5. [Optional: Media Storage (DigitalOcean Spaces)](#5-optional-media-storage-digitalocean-spaces)
6. [Optional: PDF Export (wkhtmltopdf)](#6-optional-pdf-export-wkhtmltopdf)
7. [Running the Application](#7-running-the-application)
8. [Deployment (Production)](#8-deployment-production)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Prerequisites (What to Download & Install)

Install the following on the machine where you will run or deploy the app.

### Required

| Software | Version | Purpose | How to Install |
|----------|---------|---------|----------------|
| **Python** | 3.11 or 3.12 | Backend runtime | [python.org](https://www.python.org/downloads/) — check "Add Python to PATH". |
| **pip** | (comes with Python) | Install Python packages | Usually included; upgrade with `python -m pip install -U pip`. |
| **Git** | Latest | Clone the repo | [git-scm.com](https://git-scm.com/downloads). |

### Optional but recommended

| Software | Purpose | How to Install |
|----------|---------|----------------|
| **PostgreSQL** | Production/advanced dev database | [postgresql.org](https://www.postgresql.org/download/) or use a cloud DB (see [Database Setup](#4-database-setup)). |
| **Node.js & npm** | Tailwind CSS build (django-tailwind) | [nodejs.org](https://nodejs.org/) LTS. On Windows, default path is `C:\Program Files\nodejs\npm.cmd` (see [Troubleshooting](#9-troubleshooting) if different). |

### Optional (for specific features)

| Software | Purpose | How to Install |
|----------|---------|----------------|
| **wkhtmltopdf** | Better PDF export for reports | [wkhtmltopdf.org](https://wkhtmltopdf.org/downloads.html). Add its `bin` folder to PATH. Without it, the app falls back to xhtml2pdf. |
| **Redis** | Caching and Celery/Channels (background tasks, WebSockets) | [redis.io](https://redis.io/download) or use a cloud Redis. Not required for basic run. |
| **Microsoft C++ Build Tools** (Windows) | Build scikit-learn/numpy from source if no wheel | [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) — "Desktop development with C++". Only needed if `pip install -r requirements.txt` fails for `scikit-learn` or `numpy`. |

---

## 2. Local Development Setup

Run these steps from the **project root** (the folder that contains `manage.py`, `requirements.txt`, and `backend/`).

### 2.1 Clone the repository

```bash
git clone <your-repo-url>
cd OneTagumVision-DP
```

(Replace `<your-repo-url>` with the actual URL, e.g. `https://github.com/your-org/OneTagumVision-DP.git`.)

### 2.2 Create a virtual environment (recommended)

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**

```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2.3 Install Python dependencies

**Option A — Full install (includes ML: scikit-learn, numpy, pandas):**

```bash
pip install -r requirements.txt
```

If on Windows you get errors building `scikit-learn` or `numpy`, install **Option B** first, then optionally install the ML stack after installing [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/):

```bash
pip install -r requirements-base.txt
pip install -r requirements-ml.txt
```

**Option B — Base only (no ML; good for quick run or Windows without Build Tools):**

```bash
pip install -r requirements-base.txt
```

The app runs with Option B; clustering/ML features need the full `requirements.txt` or `requirements-ml.txt`.

### 2.4 Tailwind CSS (optional)

If you use django-tailwind and have Node.js installed:

```bash
python manage.py tailwind install
python manage.py tailwind build
```

If you skip this, the app still runs; you may need to run `tailwind build` if you change theme assets.

---

## 3. Environment Variables (.env)

The app reads configuration from environment variables. For local development, use a `.env` file in the **project root** (same folder as `manage.py`). Never commit `.env`; it can contain secrets.

### 3.1 Create `.env` from the example

```bash
copy .env.example .env
```

(On Linux/macOS: `cp .env.example .env`.)

### 3.2 Edit `.env` with your values

Open `.env` and set at least:

| Variable | Description | Example |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Secret key for Django (sessions, CSRF, etc.) | Generate with: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | `true` for development, `false` for production | `true` |
| `ALLOWED_HOSTS` | Comma-separated hosts that can serve the app | `localhost,127.0.0.1,0.0.0.0` |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated origins for CSRF | `http://localhost:8000,http://127.0.0.1:8000` |

For **local database** you can leave `DATABASE_URL` unset and either:

- Use **SQLite** (default): do nothing; no extra DB setup.
- Use **PostgreSQL**: set `DB_PASSWORD` (and optionally `DB_NAME`, `DB_USER`, `DB_HOST`, `DB_PORT`) in `.env` so the app connects to your local Postgres.

For **production**, set `DATABASE_URL` to your Postgres connection string (see [Database Setup](#4-database-setup)).

Remove or comment out any line in `.env` that runs a script (e.g. a line that runs `Activate.ps1`); those are for your local shell, not for the app.

---

## 4. Database Setup

### Using SQLite (default for local)

No setup. On first run, migrations will create `backend/db.sqlite3`. Ensure the app has write permission to the `backend/` directory.

### Using PostgreSQL locally

1. Install PostgreSQL and create a database and user.
2. In `.env` set for example:
   - `DB_PASSWORD=your_db_password`
   - `DB_NAME=gistagumnew` (or your DB name)
   - `DB_USER=postgres` (or your user)
   - `DB_HOST=localhost`
   - `DB_PORT=5432`
3. Run migrations (see [Running the Application](#7-running-the-application)).

### Using PostgreSQL in production

Set the single variable:

- `DATABASE_URL=postgresql://user:password@host:port/dbname`

The app uses `DATABASE_URL` when set and ignores `DB_*` variables. Create the database and user in your provider (e.g. DigitalOcean, Render, Neon), then run migrations after deployment.

---

## 5. Optional: Media Storage (DigitalOcean Spaces)

For production (or dev) you can store uploaded files (e.g. project images) in DigitalOcean Spaces (S3-compatible). See **docs/SPACES_SETUP.md** for full steps. In `.env`:

- `USE_SPACES=true`
- `AWS_ACCESS_KEY_ID=...`
- `AWS_SECRET_ACCESS_KEY=...`
- `AWS_STORAGE_BUCKET_NAME=...`
- `AWS_S3_ENDPOINT_URL=https://<region>.digitaloceanspaces.com`
- `AWS_S3_REGION_NAME=<region>`

If these are not set, the app uses local `media/` on disk.

---

## 6. Optional: PDF Export (wkhtmltopdf)

The monitoring reports can export PDFs. For best quality, install **wkhtmltopdf** and add its `bin` directory to your system PATH. The Python package `pdfkit` is already in `requirements.txt`. If wkhtmltopdf is not installed, the app falls back to xhtml2pdf.

- Download: [wkhtmltopdf.org](https://wkhtmltopdf.org/downloads.html)
- Windows: install and add e.g. `C:\Program Files\wkhtmltopdf\bin` to PATH.

---

## 7. Running the Application

All commands are run from the **project root** (where `manage.py` is).

### 7.1 Run migrations

```bash
python manage.py migrate
```

### 7.2 Create a superuser (optional)

```bash
python manage.py createsuperuser
```

Use this to log in to the admin at `/admin/`.

### 7.3 Run the development server

```bash
python manage.py runserver
```

- App: **http://127.0.0.1:8000/**
- Admin: **http://127.0.0.1:8000/admin/**

---

## 8. Deployment (Production)

### 8.1 What production needs

- **Python 3.11 or 3.12** on the server or in the container.
- **Environment variables** set in the platform (no `.env` file in production): at least `DJANGO_SECRET_KEY`, `DEBUG=false`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, and `DATABASE_URL`.
- **Static files**: run `python manage.py collectstatic --noinput` before or during startup (the provided `start.sh` does this).
- **Database**: PostgreSQL recommended; set `DATABASE_URL`.

### 8.2 Deploy with Docker

The project includes a **Dockerfile** and **start.sh**:

1. Build: `docker build -t onetagumvision .`
2. Run with env and database:
   - Set `DATABASE_URL` (and optionally `USE_SPACES`, etc.).
   - Example:  
     `docker run -p 8000:8000 -e DATABASE_URL=postgresql://... -e DJANGO_SECRET_KEY=... onetagumvision`

The image runs migrations and collectstatic then starts Gunicorn. For Celery workers, use the same image with a command like `celery -A gistagum worker --loglevel=info` and set `CELERY_WORKER` or pass the command (see `start.sh`).

### 8.3 Deploy to a platform (Render, DigitalOcean App Platform, etc.)

- Use the same environment variables as above.
- Set the **start command** to run your WSGI server (e.g. Gunicorn). If you use the repo’s `start.sh`, the default CMD already runs migrations, collectstatic, and Gunicorn.
- For **Render**, see **docs/QUICK_START_DEPLOYMENT.md** for a step-by-step and database migration tips.

---

## 9. Troubleshooting

### “No module named 'gistagum'” or “settings not found”

- Run all commands from the **project root** (directory that contains `manage.py` and `backend/`).
- Ensure `backend/` contains the `gistagum` package and that you activated the same virtual environment where you installed dependencies.

### Windows: “error: Microsoft Visual C++ 14.0 or greater is required” (scikit-learn/numpy)

- Install [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/), then run `pip install -r requirements.txt` again.
- Or install only base deps: `pip install -r requirements-base.txt` (no ML).

### Tailwind / npm not found (Windows)

- Install Node.js from [nodejs.org](https://nodejs.org/) and ensure `npm` is on PATH.
- If npm is installed elsewhere, set in `backend/gistagum/settings.py` the correct path, e.g.  
  `NPM_BIN_PATH = r"C:\Program Files\nodejs\npm.cmd"` (or your path).

### PDF export fails or is low quality

- Install **wkhtmltopdf** and add its `bin` to PATH; the app will use it via pdfkit when available.

### Database connection errors

- **SQLite**: ensure `backend/` is writable and no other process has the DB open.
- **PostgreSQL**: check `DATABASE_URL` or `DB_*` in `.env`; ensure the database and user exist and the server allows connections (host, port, firewall).

### Static files 404 in production

- Run `python manage.py collectstatic --noinput` before starting the app.
- Ensure the platform serves static files (e.g. WhiteNoise is in the stack) or that your reverse proxy/CDN serves the collected static directory.

---

## Quick reference

| Task | Command (from project root) |
|------|-----------------------------|
| Install deps (full) | `pip install -r requirements.txt` |
| Install deps (base only) | `pip install -r requirements-base.txt` |
| Migrate DB | `python manage.py migrate` |
| Create superuser | `python manage.py createsuperuser` |
| Run dev server | `python manage.py runserver` |
| Collect static (production) | `python manage.py collectstatic --noinput` |
| Generate secret key | `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |

For more on project layout, see **PROJECT_STRUCTURE.md**. For Spaces storage, see **docs/SPACES_SETUP.md**. For a fast deployment walkthrough, see **docs/QUICK_START_DEPLOYMENT.md**.
