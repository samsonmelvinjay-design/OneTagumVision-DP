# Fix pg_dump version mismatch
# Your PostgreSQL server is 18.0, but pg_dump is 17.3

Write-Host "=== Fixing pg_dump Version Mismatch ===" -ForegroundColor Green
Write-Host ""
Write-Host "Your PostgreSQL server: 18.0" -ForegroundColor Yellow
Write-Host "Your pg_dump client: 17.3" -ForegroundColor Yellow
Write-Host ""

Write-Host "Solutions:" -ForegroundColor Cyan
Write-Host ""
Write-Host "Option 1: Use Django dumpdata (Recommended - No version issues)" -ForegroundColor White
Write-Host "  python manage.py dumpdata --exclude auth.permission --exclude contenttypes > data_backup.json" -ForegroundColor Gray
Write-Host ""

Write-Host "Option 2: Find PostgreSQL 18 pg_dump" -ForegroundColor White
Write-Host "  Check: C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -ForegroundColor Gray
Write-Host ""

Write-Host "Option 3: Use full path to PostgreSQL 18 pg_dump" -ForegroundColor White
Write-Host "  & 'C:\Program Files\PostgreSQL\18\bin\pg_dump.exe' -h localhost -U postgres -d gistagumnew -F p -f local_backup.sql" -ForegroundColor Gray
Write-Host ""

# Check if PostgreSQL 18 exists
$pg18Path = "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"
if (Test-Path $pg18Path) {
    Write-Host "✓ Found PostgreSQL 18 pg_dump!" -ForegroundColor Green
    Write-Host "  Location: $pg18Path" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Use this command:" -ForegroundColor Yellow
    Write-Host "  & '$pg18Path' -h localhost -U postgres -d gistagumnew -F p -f local_backup.sql" -ForegroundColor Cyan
} else {
    Write-Host "⚠ PostgreSQL 18 pg_dump not found at standard location" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Try finding it:" -ForegroundColor White
    Write-Host "  Get-ChildItem 'C:\Program Files\PostgreSQL' -Recurse -Filter pg_dump.exe" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== Recommended: Use Django dumpdata ===" -ForegroundColor Green
Write-Host "This avoids version mismatch issues completely!" -ForegroundColor Gray
Write-Host ""

