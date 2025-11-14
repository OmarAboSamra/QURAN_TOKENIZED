# Start Celery Beat Scheduler for Qur'an Backend
# This script starts the Celery beat scheduler for periodic tasks

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "   Celery Beat - Qur'an Backend" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "Virtual environment not activated. Activating..." -ForegroundColor Yellow
    & "C:\quran-backend\.venv\Scripts\Activate.ps1"
}

# Set PYTHONPATH
$env:PYTHONPATH = "C:\quran-backend"
Write-Host "PYTHONPATH set to: $env:PYTHONPATH" -ForegroundColor Green

# Check if Redis is running
Write-Host ""
Write-Host "Checking Redis connection..." -ForegroundColor Yellow
try {
    $redisTest = Test-NetConnection -ComputerName localhost -Port 6379 -WarningAction SilentlyContinue
    if ($redisTest.TcpTestSucceeded) {
        Write-Host "✓ Redis is running on localhost:6379" -ForegroundColor Green
    } else {
        Write-Host "✗ Redis is NOT running on localhost:6379" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please start Redis first:" -ForegroundColor Yellow
        Write-Host "  Option 1: docker run -d -p 6379:6379 redis:7-alpine" -ForegroundColor Cyan
        Write-Host "  Option 2: redis-server (if installed locally)" -ForegroundColor Cyan
        Write-Host ""
        exit 1
    }
} catch {
    Write-Host "✗ Could not check Redis connection" -ForegroundColor Red
    Write-Host "Please ensure Redis is running on localhost:6379" -ForegroundColor Yellow
    exit 1
}

# Start Celery beat
Write-Host ""
Write-Host "Starting Celery beat scheduler..." -ForegroundColor Yellow
Write-Host "Scheduled tasks:" -ForegroundColor Cyan
Write-Host "  - Database backup (daily at 2:00 AM)" -ForegroundColor Cyan
Write-Host "  - Cache cleanup (daily at 3:00 AM)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

celery -A backend.worker beat --loglevel=info
