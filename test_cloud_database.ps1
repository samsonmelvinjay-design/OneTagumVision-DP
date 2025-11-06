# Test Cloud Database Connection Script
# Use this to verify your cloud database connection works

Write-Host "=== Test Cloud Database Connection ===" -ForegroundColor Green
Write-Host ""

Write-Host "Enter your cloud database connection string:" -ForegroundColor Yellow
Write-Host "(Format: postgresql://user:pass@host/dbname?sslmode=require)" -ForegroundColor Gray
$CONNECTION_STRING = Read-Host

Write-Host ""
Write-Host "Testing connection..." -ForegroundColor Yellow
Write-Host ""

# Test 1: Check PostgreSQL version
Write-Host "Test 1: PostgreSQL Version" -ForegroundColor Cyan
try {
    $version = psql $CONNECTION_STRING -t -c "SELECT version();" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Connected!" -ForegroundColor Green
        Write-Host "  $version" -ForegroundColor Gray
    } else {
        Write-Host "✗ Connection failed!" -ForegroundColor Red
        Write-Host "  $version" -ForegroundColor Gray
        exit 1
    }
} catch {
    Write-Host "✗ Error: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Test 2: List databases
Write-Host "Test 2: Current Database" -ForegroundColor Cyan
try {
    $dbname = psql $CONNECTION_STRING -t -c "SELECT current_database();" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Database: $dbname" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Error: $_" -ForegroundColor Red
}

Write-Host ""

# Test 3: List tables (Django tables)
Write-Host "Test 3: Django Tables" -ForegroundColor Cyan
try {
    $tables = psql $CONNECTION_STRING -t -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;" 2>&1
    if ($LASTEXITCODE -eq 0) {
        $tableCount = ($tables | Where-Object { $_.Trim() -ne "" }).Count
        Write-Host "✓ Found $tableCount tables" -ForegroundColor Green
        if ($tableCount -gt 0) {
            Write-Host "  Sample tables:" -ForegroundColor Gray
            $tables | Select-Object -First 5 | ForEach-Object { Write-Host "    - $($_.Trim())" -ForegroundColor Gray }
        } else {
            Write-Host "  ⚠ Database is empty (no tables yet)" -ForegroundColor Yellow
            Write-Host "  Run migrations: python manage.py migrate" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "✗ Error: $_" -ForegroundColor Red
}

Write-Host ""

# Test 4: Check if Django migrations table exists
Write-Host "Test 4: Django Migrations" -ForegroundColor Cyan
try {
    $migrations = psql $CONNECTION_STRING -t -c "SELECT COUNT(*) FROM django_migrations;" 2>&1
    if ($LASTEXITCODE -eq 0) {
        $migrationCount = $migrations.Trim()
        if ($migrationCount -gt 0) {
            Write-Host "✓ Django migrations found: $migrationCount" -ForegroundColor Green
        } else {
            Write-Host "⚠ No migrations yet" -ForegroundColor Yellow
            Write-Host "  Run: python manage.py migrate" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "⚠ django_migrations table doesn't exist yet" -ForegroundColor Yellow
    Write-Host "  This is normal for a new database" -ForegroundColor Gray
    Write-Host "  Run: python manage.py migrate" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== Connection Test Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "If all tests passed, your database is ready!" -ForegroundColor White
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Add DATABASE_URL to your deployment platform" -ForegroundColor Gray
Write-Host "  2. Run migrations: python manage.py migrate" -ForegroundColor Gray
Write-Host "  3. Create superuser: python manage.py createsuperuser" -ForegroundColor Gray
Write-Host ""

