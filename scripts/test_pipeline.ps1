# Test Pipeline API Endpoints
# This script tests the pipeline functionality

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "   Pipeline API Test Suite" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://localhost:8000"

# Check if server is running
Write-Host "Checking server status..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/meta/health" -Method Get
    Write-Host "✓ Server is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Server is not running" -ForegroundColor Red
    Write-Host "Please start the server with: python backend/main.py" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Test 1: Queue Tokenization Job for Sura 1" -ForegroundColor Yellow
Write-Host "=========================================" -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/pipeline/tokenize?sura=1" -Method Post
    Write-Host "✓ Job queued successfully" -ForegroundColor Green
    Write-Host "Job ID: $($response.job_id)" -ForegroundColor Cyan
    Write-Host "Correlation ID: $($response.correlation_id)" -ForegroundColor Cyan
    Write-Host "Status: $($response.status)" -ForegroundColor Cyan
    $jobId1 = $response.job_id
} catch {
    Write-Host "✗ Failed to queue job" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Waiting 2 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Test 2: Check Job Status" -ForegroundColor Yellow
Write-Host "=========================" -ForegroundColor Cyan
try {
    $status = Invoke-RestMethod -Uri "$baseUrl/pipeline/job/$jobId1" -Method Get
    Write-Host "✓ Job status retrieved" -ForegroundColor Green
    Write-Host "Status: $($status.status)" -ForegroundColor Cyan
    Write-Host "Sura: $($status.sura)" -ForegroundColor Cyan
    if ($status.progress) {
        Write-Host "Progress: $($status.progress)%" -ForegroundColor Cyan
    }
} catch {
    Write-Host "✗ Failed to get job status" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Write-Host ""
Write-Host "Test 3: Get Pipeline Status for Sura 1" -ForegroundColor Yellow
Write-Host "======================================" -ForegroundColor Cyan
try {
    $pipelineStatus = Invoke-RestMethod -Uri "$baseUrl/pipeline/status?sura=1" -Method Get
    Write-Host "✓ Pipeline status retrieved" -ForegroundColor Green
    Write-Host "Sura: $($pipelineStatus.sura)" -ForegroundColor Cyan
    Write-Host "Has tokenization job: $($pipelineStatus.has_tokenization_job)" -ForegroundColor Cyan
    Write-Host "Has root extraction job: $($pipelineStatus.has_root_extraction_job)" -ForegroundColor Cyan
} catch {
    Write-Host "✗ Failed to get pipeline status" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Write-Host ""
Write-Host "Test 4: Queue Complete Pipeline for Sura 1" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan
try {
    $fullPipeline = Invoke-RestMethod -Uri "$baseUrl/pipeline/process-sura?sura=1" -Method Post
    Write-Host "✓ Full pipeline queued" -ForegroundColor Green
    Write-Host "Tokenization Job ID: $($fullPipeline.tokenization_job_id)" -ForegroundColor Cyan
    Write-Host "Root Extraction Job ID: $($fullPipeline.root_extraction_job_id)" -ForegroundColor Cyan
    Write-Host "Correlation ID: $($fullPipeline.correlation_id)" -ForegroundColor Cyan
} catch {
    Write-Host "✗ Failed to queue full pipeline" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Write-Host ""
Write-Host "Test 5: Get Tokens with Pagination" -ForegroundColor Yellow
Write-Host "===================================" -ForegroundColor Cyan
try {
    $tokens = Invoke-RestMethod -Uri "$baseUrl/quran/tokens?sura=1&page=1&page_size=10" -Method Get
    Write-Host "✓ Tokens retrieved" -ForegroundColor Green
    Write-Host "Total tokens: $($tokens.total)" -ForegroundColor Cyan
    Write-Host "Page: $($tokens.page)" -ForegroundColor Cyan
    Write-Host "Page size: $($tokens.page_size)" -ForegroundColor Cyan
    Write-Host "Tokens returned: $($tokens.tokens.Count)" -ForegroundColor Cyan
} catch {
    Write-Host "✗ Failed to get tokens" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "   All Tests Completed!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Check Celery worker logs for task execution" -ForegroundColor Cyan
Write-Host "  2. Visit http://localhost:8000/demo-enhanced" -ForegroundColor Cyan
Write-Host "  3. Try processing Sura 2 with:" -ForegroundColor Cyan
Write-Host "     curl -X POST 'http://localhost:8000/pipeline/process-sura?sura=2'" -ForegroundColor Cyan
Write-Host ""
