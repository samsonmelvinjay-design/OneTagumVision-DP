FROM python:3.12-slim

# Install system dependencies (build tools, Postgres client libs, GDAL, FreeType for reportlab)
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       build-essential \
       libpq-dev \
       gdal-bin \
       libgdal-dev \
       libfreetype6-dev \
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

# Copy and make startup script executable
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=gistagum.settings

# Cloud platforms (DigitalOcean, Railway, Render, etc.) will provide PORT environment variable
# The startup script will detect if we should run as web service or worker
# For web service: runs migrations, collects static files, starts Gunicorn
# For worker: runs the command from run_command (Celery)
CMD ["/app/start.sh"]


