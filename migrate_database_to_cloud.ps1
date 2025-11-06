# Database Migration Script
# This script helps you migrate your local PostgreSQL database to a cloud database

Write-Host "=== Database Migration to Cloud ===" -ForegroundColor Green
Write-Host ""

# Step 1: Export local database
Write-Host "Step 1: Export Local Database" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

$LOCAL_DB_NAME = "gistagumnew"
$LOCAL_DB_USER = "postgres"
$LOCAL_DB_HOST = "localhost"
$LOCAL_DB_PORT = "5432"

Write-Host "Enter your local PostgreSQL password:" -ForegroundColor Yellow
$LOCAL_PASSWORD = Read-Host -AsSecureString
$LOCAL_PASSWORD_PLAIN = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($LOCAL_PASSWORD)
)

$BACKUP_FILE = "gistagum_cloud_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"

Write-Host ""
Write-Host "Exporting database to: $BACKUP_FILE" -ForegroundColor Yellow
$env:PGPASSWORD = $LOCAL_PASSWORD_PLAIN

try {
    pg_dump -h $LOCAL_DB_HOST -p $LOCAL_DB_PORT -U $LOCAL_DB_USER -d $LOCAL_DB_NAME -F p -f $BACKUP_FILE
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Database exported successfully!" -ForegroundColor Green
        Write-Host "  File: $BACKUP_FILE" -ForegroundColor Gray
    } else {
        Write-Host "✗ Export failed!" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "✗ Error during export: $_" -ForegroundColor Red
    exit 1
} finally {
    $env:PGPASSWORD = ""
}

Write-Host ""
Write-Host "Step 2: Import to Cloud Database" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Choose your cloud database provider:" -ForegroundColor Yellow
Write-Host "1. Neon (neon.tech)" -ForegroundColor White
Write-Host "2. Render (render.com)" -ForegroundColor White
Write-Host "3. DigitalOcean" -ForegroundColor White
Write-Host "4. Railway" -ForegroundColor White
Write-Host "5. Custom (paste connection string)" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Enter choice (1-5)"

$CLOUD_CONNECTION_STRING = ""

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "Get your connection string from Neon dashboard:" -ForegroundColor Yellow
        Write-Host "  Format: postgresql://user:pass@host/dbname?sslmode=require" -ForegroundColor Gray
        $CLOUD_CONNECTION_STRING = Read-Host "Paste your Neon connection string"
    }
    "2" {
        Write-Host ""
        Write-Host "Get your connection string from Render dashboard:" -ForegroundColor Yellow
        Write-Host "  Go to your database service → Connections tab" -ForegroundColor Gray
        $CLOUD_CONNECTION_STRING = Read-Host "Paste your Render connection string"
    }
    "3" {
        Write-Host ""
        Write-Host "Get your connection string from DigitalOcean dashboard:" -ForegroundColor Yellow
        Write-Host "  Go to your database → Connection Details" -ForegroundColor Gray
        $CLOUD_CONNECTION_STRING = Read-Host "Paste your DigitalOcean connection string"
    }
    "4" {
        Write-Host ""
        Write-Host "Get your connection string from Railway dashboard:" -ForegroundColor Yellow
        Write-Host "  Go to your database → Connect tab" -ForegroundColor Gray
        $CLOUD_CONNECTION_STRING = Read-Host "Paste your Railway connection string"
    }
    "5" {
        Write-Host ""
        $CLOUD_CONNECTION_STRING = Read-Host "Paste your database connection string"
    }
    default {
        Write-Host "✗ Invalid choice!" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Testing connection to cloud database..." -ForegroundColor Yellow

try {
    # Test connection
    $testResult = psql $CLOUD_CONNECTION_STRING -c "SELECT version();" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Connection successful!" -ForegroundColor Green
    } else {
        Write-Host "✗ Connection failed! Check your connection string." -ForegroundColor Red
        Write-Host "  Error: $testResult" -ForegroundColor Gray
        exit 1
    }
} catch {
    Write-Host "✗ Error testing connection: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Importing database..." -ForegroundColor Yellow
Write-Host "  This may take a few minutes depending on database size..." -ForegroundColor Gray
Write-Host ""

try {
    # Import the backup
    Get-Content $BACKUP_FILE | psql $CLOUD_CONNECTION_STRING
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ Database imported successfully!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "✗ Import failed! Check the error messages above." -ForegroundColor Red
        Write-Host ""
        Write-Host "Common issues:" -ForegroundColor Yellow
        Write-Host "  - Database already has data (may need to drop tables first)" -ForegroundColor Gray
        Write-Host "  - Version mismatch" -ForegroundColor Gray
        Write-Host "  - Permission issues" -ForegroundColor Gray
        exit 1
    }
} catch {
    Write-Host "✗ Error during import: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Next Steps ===" -ForegroundColor Green
Write-Host ""
Write-Host "1. Add DATABASE_URL to your deployment platform:" -ForegroundColor White
Write-Host "   $CLOUD_CONNECTION_STRING" -ForegroundColor Yellow
Write-Host ""
Write-Host "2. Run Django migrations on cloud database:" -ForegroundColor White
Write-Host "   \$env:DATABASE_URL = '$CLOUD_CONNECTION_STRING'" -ForegroundColor Gray
Write-Host "   python manage.py migrate" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Create superuser:" -ForegroundColor White
Write-Host "   python manage.py createsuperuser" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Deploy your app!" -ForegroundColor White
Write-Host ""

# Copy connection string to clipboard
$CLOUD_CONNECTION_STRING | Set-Clipboard
Write-Host "✓ Connection string copied to clipboard!" -ForegroundColor Green
Write-Host ""

