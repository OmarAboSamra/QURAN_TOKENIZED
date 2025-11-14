# Start FastAPI Server for Qur'an Backend
# Simple script to start just the FastAPI server

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "   FastAPI Server - Qur'an Backend" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & "C:\quran-backend\.venv\Scripts\Activate.ps1"
}

# Set PYTHONPATH
$env:PYTHONPATH = "C:\quran-backend"
Write-Host "PYTHONPATH set to: $env:PYTHONPATH" -ForegroundColor Green

# Start server
Write-Host ""
Write-Host "Starting FastAPI server..." -ForegroundColor Yellow
Write-Host "Server will be available at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Enhanced Demo: http://localhost:8000/demo-enhanced" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

python backend/main.py
