# Start All Services for Qur'an Backend
# This script starts Redis, Celery Worker, and FastAPI in separate terminals

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Starting All Services - Qur'an Backend" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$venvPath = "C:\quran-backend\.venv\Scripts\Activate.ps1"
$backendPath = "C:\quran-backend"

# Check if Docker is available for Redis
Write-Host "Checking Docker availability..." -ForegroundColor Yellow
$dockerAvailable = $false
try {
    $dockerVersion = docker --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        $dockerAvailable = $true
        Write-Host "✓ Docker is available" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Docker is not available" -ForegroundColor Yellow
}

# Start Redis
Write-Host ""
Write-Host "Starting Redis..." -ForegroundColor Yellow
if ($dockerAvailable) {
    Write-Host "Using Docker to start Redis..." -ForegroundColor Cyan
    
    # Check if Redis container already exists
    $existingContainer = docker ps -a --filter "name=quran-redis" --format "{{.Names}}" 2>$null
    
    if ($existingContainer -eq "quran-redis") {
        Write-Host "Redis container already exists. Starting it..." -ForegroundColor Cyan
        docker start quran-redis
    } else {
        Write-Host "Creating new Redis container..." -ForegroundColor Cyan
        docker run -d --name quran-redis -p 6379:6379 redis:7-alpine
    }
    
    # Wait for Redis to be ready
    Start-Sleep -Seconds 2
    Write-Host "✓ Redis started on localhost:6379" -ForegroundColor Green
} else {
    Write-Host "Please start Redis manually:" -ForegroundColor Yellow
    Write-Host "  Option 1: docker run -d -p 6379:6379 redis:7-alpine" -ForegroundColor Cyan
    Write-Host "  Option 2: redis-server (if installed locally)" -ForegroundColor Cyan
    Write-Host ""
    $continue = Read-Host "Press Enter once Redis is running, or Ctrl+C to cancel"
}

# Start Celery Worker in new terminal
Write-Host ""
Write-Host "Starting Celery Worker in new terminal..." -ForegroundColor Yellow
$celeryCommand = "& '$venvPath'; `$env:PYTHONPATH='$backendPath'; Write-Host 'Celery Worker Started' -ForegroundColor Green; celery -A backend.worker worker --loglevel=info --concurrency=4 --pool=solo --queues=tokenization,root_extraction,maintenance"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $celeryCommand

Start-Sleep -Seconds 2
Write-Host "✓ Celery Worker terminal opened" -ForegroundColor Green

# Start FastAPI in new terminal
Write-Host ""
Write-Host "Starting FastAPI Server in new terminal..." -ForegroundColor Yellow
$fastApiCommand = "& '$venvPath'; `$env:PYTHONPATH='$backendPath'; Write-Host 'FastAPI Server Started' -ForegroundColor Green; python backend/main.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $fastApiCommand

Start-Sleep -Seconds 2
Write-Host "✓ FastAPI Server terminal opened" -ForegroundColor Green

# Summary
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   All Services Started!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services running:" -ForegroundColor Yellow
Write-Host "  ✓ Redis: localhost:6379" -ForegroundColor Green
Write-Host "  ✓ Celery Worker: 4 workers, 3 queues" -ForegroundColor Green
Write-Host "  ✓ FastAPI: http://localhost:8000" -ForegroundColor Green
Write-Host ""
Write-Host "Access points:" -ForegroundColor Yellow
Write-Host "  - API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  - Demo: http://localhost:8000/demo" -ForegroundColor Cyan
Write-Host "  - Enhanced Demo: http://localhost:8000/demo-enhanced" -ForegroundColor Cyan
Write-Host "  - Metrics: http://localhost:8000/metrics" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test pipeline:" -ForegroundColor Yellow
Write-Host "  curl -X POST 'http://localhost:8000/pipeline/tokenize?sura=1'" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
