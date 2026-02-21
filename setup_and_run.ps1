# Qur'an Backend - Complete Setup and Run Script
# This script will set up the environment and run the tokenization pipeline

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  QURÁN ANALYSIS BACKEND - AUTOMATED SETUP" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "Python 3\.1[0-9]") {
    Write-Host "✓ Python version OK: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "✗ Python 3.10+ required. Found: $pythonVersion" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Check if virtual environment exists
if (Test-Path ".venv") {
    Write-Host "✓ Virtual environment already exists" -ForegroundColor Green
} else {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
}
Write-Host ""

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1
Write-Host "✓ Virtual environment activated" -ForegroundColor Green
Write-Host ""

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -q -r requirements.txt
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to install dependencies" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Check if database exists
if (Test-Path "quran.db") {
    Write-Host "⚠ Database already exists" -ForegroundColor Yellow
    $response = Read-Host "Do you want to re-tokenize and overwrite? (y/n)"
    if ($response -eq "y") {
        Write-Host "Running tokenization..." -ForegroundColor Yellow
        python scripts/tokenize_quran.py --save-to-db
    } else {
        Write-Host "Skipping tokenization" -ForegroundColor Yellow
    }
} else {
    Write-Host "Running tokenization..." -ForegroundColor Yellow
    python scripts/tokenize_quran.py --save-to-db
}
Write-Host ""

# Ask if user wants to start the API server
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  SETUP COMPLETE!" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "The backend is ready to use." -ForegroundColor Green
Write-Host ""
Write-Host "Start the API server? (y/n): " -ForegroundColor Yellow -NoNewline
$response = Read-Host

if ($response -eq "y") {
    Write-Host ""
    Write-Host "Starting API server..." -ForegroundColor Yellow
    Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "API will be available at:" -ForegroundColor Cyan
    Write-Host "  - API Base: http://localhost:8000" -ForegroundColor White
    Write-Host "  - Interactive Docs: http://localhost:8000/docs" -ForegroundColor White
    Write-Host "  - ReDoc: http://localhost:8000/redoc" -ForegroundColor White
    Write-Host ""
    
    python backend/main.py
} else {
    Write-Host ""
    Write-Host "To start the server later, run:" -ForegroundColor Cyan
    Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host "  python backend/main.py" -ForegroundColor White
    Write-Host ""
    Write-Host "Or simply run:" -ForegroundColor Cyan
    Write-Host "  .\setup_and_run.ps1" -ForegroundColor White
    Write-Host ""
}
