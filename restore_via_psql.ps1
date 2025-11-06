# Restore database using psql (alternative to pgAdmin)

Write-Host "=== Restore Database to DigitalOcean using psql ===" -ForegroundColor Green
Write-Host ""

# DigitalOcean connection details
$DO_HOST = "tagumdb-do-user-28669441-0.j.db.ondigitalocean.com"
$DO_PORT = "25060"
$DO_USER = "doadmin"
$DO_DB = "defaultdb"

Write-Host "Enter your DigitalOcean database password:" -ForegroundColor Yellow
$DO_PASSWORD = Read-Host -AsSecureString
$DO_PASSWORD_PLAIN = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($DO_PASSWORD)
)

Write-Host ""
Write-Host "Enter path to your backup file:" -ForegroundColor Yellow
Write-Host "(e.g., C:\Users\kenne\Desktop\GISTAGUM\gistagum_backup.sql)" -ForegroundColor Gray
$BACKUP_FILE = Read-Host

if (-not (Test-Path $BACKUP_FILE)) {
    Write-Host "✗ Error: Backup file not found: $BACKUP_FILE" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Restoring database..." -ForegroundColor Yellow
Write-Host "Host: $DO_HOST" -ForegroundColor Gray
Write-Host "Port: $DO_PORT" -ForegroundColor Gray
Write-Host "Database: $DO_DB" -ForegroundColor Gray

# Set password
$env:PGPASSWORD = $DO_PASSWORD_PLAIN

# For SQL files (Plain format)
if ($BACKUP_FILE -like "*.sql") {
    Write-Host "Importing SQL file..." -ForegroundColor Cyan
    psql -h $DO_HOST -p $DO_PORT -U $DO_USER -d $DO_DB -f $BACKUP_FILE -v ON_ERROR_STOP=1
}
# For Custom format (.backup files)
elseif ($BACKUP_FILE -like "*.backup") {
    Write-Host "Restoring Custom format backup..." -ForegroundColor Cyan
    pg_restore -h $DO_HOST -p $DO_PORT -U $DO_USER -d $DO_DB -v --no-owner --no-acl $BACKUP_FILE
}
else {
    Write-Host "✗ Unknown backup format. Use .sql or .backup files." -ForegroundColor Red
    $env:PGPASSWORD = ""
    exit 1
}

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ Database restored successfully!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "✗ Restore failed! Check the error messages above." -ForegroundColor Red
    Write-Host ""
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  - Version mismatch (try Plain SQL format)" -ForegroundColor Gray
    Write-Host "  - Database not empty (drop and recreate)" -ForegroundColor Gray
    Write-Host "  - Permission issues" -ForegroundColor Gray
}

# Clear password
$env:PGPASSWORD = ""

