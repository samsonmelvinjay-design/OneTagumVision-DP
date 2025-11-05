FROM python:3.12-slim

# Install system dependencies (build tools, Postgres client libs, GDAL)
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       build-essential \
       libpq-dev \
       gdal-bin \
       libgdal-dev \
       curl \
    && rm -rf /var/lib/apt/lists/*

# Ensure pip is up to date
RUN pip install --no-cache-dir --upgrade pip

WORKDIR /app

# Install Python dependencies first (cache-friendly)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=gistagum.settings

# Collect static files at build time via Render buildCommand (in render.yaml)

# Run Gunicorn by default (Render will override with $PORT)
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn gistagum.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]


