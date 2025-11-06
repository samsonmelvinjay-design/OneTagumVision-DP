# Import Database to DigitalOcean
# This script helps you import your local backup to DigitalOcean database

Write-Host "=== Import Database to DigitalOcean ===" -ForegroundColor Green
Write-Host ""

# Find the latest backup file
$backupFiles = Get-ChildItem -Path . -Filter "local_backup_*.sql" | Sort-Object LastWriteTime -Descending
if ($backupFiles.Count -eq 0) {
    Write-Host "✗ No backup files found!" -ForegroundColor Red
    Write-Host "  Run: .\export_database.ps1 first" -ForegroundColor Gray
    exit 1
}

$latestBackup = $backupFiles[0]
Write-Host "Found backup file: $($latestBackup.Name)" -ForegroundColor Cyan
Write-Host "  Size: $([math]::Round($latestBackup.Length / 1MB, 2)) MB" -ForegroundColor Gray
Write-Host ""

Write-Host "Enter your DigitalOcean database connection string:" -ForegroundColor Yellow
Write-Host "(Format: postgresql://doadmin:password@host:port/dbname?sslmode=require)" -ForegroundColor Gray
Write-Host ""
$CONNECTION_STRING = Read-Host "Connection String"

if ([string]::IsNullOrWhiteSpace($CONNECTION_STRING)) {
    Write-Host "✗ Connection string cannot be empty!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Testing connection..." -ForegroundColor Yellow

# Test connection
try {
    $testResult = psql $CONNECTION_STRING -c "SELECT version();" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Connection successful!" -ForegroundColor Green
    } else {
        Write-Host "✗ Connection failed!" -ForegroundColor Red
        Write-Host "  Error: $testResult" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Please check:" -ForegroundColor Yellow
        Write-Host "  - Connection string is correct" -ForegroundColor Gray
        Write-Host "  - Database is accessible" -ForegroundColor Gray
        Write-Host "  - Firewall allows your IP" -ForegroundColor Gray
        exit 1
    }
} catch {
    Write-Host "✗ Error testing connection: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Importing database..." -ForegroundColor Yellow
Write-Host "  This may take a few minutes..." -ForegroundColor Gray
Write-Host ""

try {
    # Import the backup
    Get-Content $latestBackup.FullName | psql $CONNECTION_STRING
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ Database imported successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "  1. Verify data: .\test_cloud_database.ps1" -ForegroundColor Gray
        Write-Host "  2. Run Django migrations: python manage.py migrate" -ForegroundColor Gray
        Write-Host "  3. Create superuser: python manage.py createsuperuser" -ForegroundColor Gray
    } else {
        Write-Host ""
        Write-Host "✗ Import failed!" -ForegroundColor Red
        Write-Host ""
        Write-Host "Common issues:" -ForegroundColor Yellow
        Write-Host "  - Database already has data (may need to drop tables first)" -ForegroundColor Gray
        Write-Host "  - Version mismatch" -ForegroundColor Gray
        Write-Host "  - Permission issues" -ForegroundColor Gray
        Write-Host "  - Connection timeout" -ForegroundColor Gray
        exit 1
    }
} catch {
    Write-Host ""
    Write-Host "✗ Error during import: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

