# Nuclear Restart Script for LNC Dashboard
Write-Host "--- STARTING NUCLEAR CLEANUP ---" -ForegroundColor Cyan

# 1. Kill all Python processes
Write-Host "Stopping all Python processes..." -ForegroundColor Yellow
Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force

# 2. Clear Python Cache
Write-Host "Cleaning __pycache__ directories..." -ForegroundColor Yellow
Get-ChildItem -Path . -Filter "__pycache__" -Recurse | Remove-Item -Force -Recurse

# 3. Final instructions for the user
Write-Host ""
Write-Host "Cleanup Complete!" -ForegroundColor Green
Write-Host "IMPORTANT: To see the new interface in your browser:" -ForegroundColor White
Write-Host "1. Press CTRL + F5 (Hard Refresh) on PC." -ForegroundColor Cyan
Write-Host "2. On Phone: Close the PWA/Tab and reopen it." -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting App..." -ForegroundColor Yellow
python modbus_web/app.py
