# Test Database Connection
# This script tests if we can connect to DigitalOcean database

$DO_HOST = "tagumdb-do-user-28669441-0.j.db.ondigitalocean.com"
$DO_PORT = "25060"
$DO_USER = "doadmin"
$DO_PASSWORD = "AVNS_TQ6zrWJ4RA1ODtzCT9t"
$DO_DB = "defaultdb"

Write-Host "Testing connection to DigitalOcean database..." -ForegroundColor Yellow
Write-Host "Host: $DO_HOST" -ForegroundColor Cyan
Write-Host "Port: $DO_PORT" -ForegroundColor Cyan
Write-Host "Database: $DO_DB" -ForegroundColor Cyan
Write-Host ""

# Set environment variables for psql
$env:PGPASSWORD = $DO_PASSWORD
$env:PGSSLMODE = "require"

# Test connection
Write-Host "Attempting to connect..." -ForegroundColor Yellow
$result = psql -h $DO_HOST -p $DO_PORT -U $DO_USER -d $DO_DB -c "SELECT version();" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Connection successful!" -ForegroundColor Green
    Write-Host $result
} else {
    Write-Host "❌ Connection failed!" -ForegroundColor Red
    Write-Host $result
}

# Clean up
$env:PGPASSWORD = ""
$env:PGSSLMODE = ""

Write-Host ""
Write-Host "Connection string for DATABASE_URL:" -ForegroundColor Yellow
Write-Host "postgresql://${DO_USER}:${DO_PASSWORD}@${DO_HOST}:${DO_PORT}/${DO_DB}?sslmode=require" -ForegroundColor Cyan

