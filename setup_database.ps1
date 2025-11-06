# Quick Database Setup Script
# This helps you set up your DigitalOcean database connection

Write-Host "=== DigitalOcean Database Setup ===" -ForegroundColor Green
Write-Host ""

# Your connection string (from DigitalOcean dashboard)
$CONNECTION_STRING = "postgresql://doadmin:AVNS_TQ6zrWJ4RA10DtzCT9t@tagumdb-do-user-28669441-0.j.db.ondigitalocean.com:25060/defaultdb?sslmode=require"

Write-Host "Your DATABASE_URL connection string:" -ForegroundColor Cyan
Write-Host $CONNECTION_STRING -ForegroundColor Yellow
Write-Host ""

Write-Host "=== Next Steps ===" -ForegroundColor Green
Write-Host ""
Write-Host "1. Go to DigitalOcean App Platform" -ForegroundColor White
Write-Host "   → Your app: one-tagumvision" -ForegroundColor Gray
Write-Host "   → Settings → Components → gisonetagumvision" -ForegroundColor Gray
Write-Host "   → Environment Variables" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Add/Edit DATABASE_URL:" -ForegroundColor White
Write-Host "   - Key: DATABASE_URL" -ForegroundColor Gray
Write-Host "   - Value: (copy the string above)" -ForegroundColor Gray
Write-Host "   - Type: SECRET" -ForegroundColor Gray
Write-Host "   - Save" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Wait for app to redeploy" -ForegroundColor White
Write-Host ""
Write-Host "4. Import your data:" -ForegroundColor White
Write-Host "   → Go to Console tab in your app" -ForegroundColor Gray
Write-Host "   → Run: python manage.py loaddata gistagum_data.json" -ForegroundColor Gray
Write-Host "   → Run: python manage.py createsuperuser" -ForegroundColor Gray
Write-Host ""

# Copy to clipboard
$CONNECTION_STRING | Set-Clipboard
Write-Host "✓ Connection string copied to clipboard!" -ForegroundColor Green
Write-Host "  You can paste it directly into DigitalOcean" -ForegroundColor Gray
Write-Host ""

