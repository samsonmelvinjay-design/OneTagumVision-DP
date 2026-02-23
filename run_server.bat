@echo off
REM Run Django dev server from project root (finds backend/gistagum and root apps)
cd /d "%~dp0"
python manage.py runserver
pause
