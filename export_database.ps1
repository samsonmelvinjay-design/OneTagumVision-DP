# Export Database Using PostgreSQL 18 pg_dump
# This fixes the version mismatch issue

Write-Host "=== Exporting Local Database ===" -ForegroundColor Green
Write-Host ""

# Use PostgreSQL 18 pg_dump (matches your server version 18.0)
$PGDUMP = "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"

if (-not (Test-Path $PGDUMP)) {
    Write-Host "✗ PostgreSQL 18 pg_dump not found!" -ForegroundColor Red
    Write-Host "  Expected: $PGDUMP" -ForegroundColor Gray
    exit 1
}

Write-Host "Using: $PGDUMP" -ForegroundColor Cyan
Write-Host ""

# Database connection details
$DB_HOST = "localhost"
$DB_USER = "postgres"
$DB_NAME = "gistagumnew"
$BACKUP_FILE = "local_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"

Write-Host "Exporting database: $DB_NAME" -ForegroundColor Yellow
Write-Host "Output file: $BACKUP_FILE" -ForegroundColor Yellow
Write-Host ""

# Prompt for password
Write-Host "Enter your PostgreSQL password:" -ForegroundColor Yellow
$DB_PASSWORD = Read-Host -AsSecureString
$DB_PASSWORD_PLAIN = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($DB_PASSWORD)
)

Write-Host ""
Write-Host "Exporting..." -ForegroundColor Yellow

# Set password environment variable
$env:PGPASSWORD = $DB_PASSWORD_PLAIN

try {
    # Run pg_dump with full path
    & $PGDUMP -h $DB_HOST -U $DB_USER -d $DB_NAME -F p -f $BACKUP_FILE
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ Database exported successfully!" -ForegroundColor Green
        Write-Host "  File: $BACKUP_FILE" -ForegroundColor Gray
        
        # Get file size
        $fileSize = (Get-Item $BACKUP_FILE).Length / 1MB
        Write-Host "  Size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Next step: Import to DigitalOcean database" -ForegroundColor Cyan
        Write-Host "  Run: .\migrate_database_to_cloud.ps1" -ForegroundColor Gray
    } else {
        Write-Host ""
        Write-Host "✗ Export failed!" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host ""
    Write-Host "✗ Error during export: $_" -ForegroundColor Red
    exit 1
} finally {
    # Clear password
    $env:PGPASSWORD = ""
}

Write-Host ""

