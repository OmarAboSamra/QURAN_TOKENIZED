# Comprehensive API Test Suite
# Tests all endpoints to ensure nothing is broken

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   API Comprehensive Test Suite" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://localhost:8000"
$testsPassed = 0
$testsFailed = 0
$errors = @()

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Url,
        [int]$ExpectedStatus = 200
    )
    
    try {
        Write-Host "Testing: $Name..." -NoNewline
        $response = Invoke-WebRequest -Uri $Url -Method $Method -ErrorAction Stop
        
        if ($response.StatusCode -eq $ExpectedStatus) {
            Write-Host " PASS" -ForegroundColor Green
            $script:testsPassed++
            return $true
        } else {
            Write-Host " FAIL (Status: $($response.StatusCode))" -ForegroundColor Red
            $script:testsFailed++
            $script:errors += "$Name - Expected $ExpectedStatus, got $($response.StatusCode)"
            return $false
        }
    } catch {
        Write-Host " FAIL" -ForegroundColor Red
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Yellow
        $script:testsFailed++
        $script:errors += "$Name - $($_.Exception.Message)"
        return $false
    }
}

Write-Host "Phase 1: Core Endpoints" -ForegroundColor Yellow
Write-Host "------------------------" -ForegroundColor Yellow
Test-Endpoint "Root Endpoint" "GET" "$baseUrl/"
Test-Endpoint "Health Check" "GET" "$baseUrl/meta/health"
Test-Endpoint "API Documentation" "GET" "$baseUrl/docs"
Test-Endpoint "OpenAPI Schema" "GET" "$baseUrl/openapi.json"

Write-Host ""
Write-Host "Phase 2: Statistics and Metadata" -ForegroundColor Yellow
Write-Host "---------------------------------" -ForegroundColor Yellow
Test-Endpoint "Statistics (Enhanced)" "GET" "$baseUrl/quran/stats"

Write-Host ""
Write-Host "Phase 3: Token Endpoints" -ForegroundColor Yellow
Write-Host "------------------------" -ForegroundColor Yellow
$url1 = $baseUrl + '/quran/tokens?page=1&page_size=10'
Test-Endpoint "List Tokens (Paginated)" "GET" $url1
$url2 = $baseUrl + '/quran/tokens?sura=1&page_size=10'
Test-Endpoint "List Tokens (Filtered by Sura)" "GET" $url2
$url3 = $baseUrl + '/quran/search?q=test&page_size=5'
Test-Endpoint "Search Tokens" "GET" $url3

Write-Host ""
Write-Host "Phase 4: Root Endpoints" -ForegroundColor Yellow
Write-Host "-----------------------" -ForegroundColor Yellow
# Note: Root endpoint may return 404 if root doesn't exist, which is expected
Write-Host "Testing: Get Root Details (may be 404)..." -NoNewline
try {
    $response = Invoke-WebRequest -Uri ($baseUrl + '/quran/root/test') -Method GET -ErrorAction Stop
    Write-Host " PASS (Status: $($response.StatusCode))" -ForegroundColor Green
    $script:testsPassed++
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 404) {
        Write-Host " PASS (404 - No data for this root)" -ForegroundColor Green
        $script:testsPassed++
    } else {
        Write-Host " FAIL" -ForegroundColor Red
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Yellow
        $script:testsFailed++
        $script:errors += "Get Root Details - $($_.Exception.Message)"
    }
}

Write-Host ""
Write-Host "Phase 5: Pipeline Endpoints" -ForegroundColor Yellow
Write-Host "---------------------------" -ForegroundColor Yellow
Test-Endpoint "Pipeline Status (Sura 1)" "GET" "$baseUrl/pipeline/status?sura=1"

Write-Host ""
Write-Host "Phase 6: Frontend Pages" -ForegroundColor Yellow
Write-Host "-----------------------" -ForegroundColor Yellow
Test-Endpoint "Original Demo" "GET" "$baseUrl/demo"
Test-Endpoint "Enhanced Demo" "GET" "$baseUrl/demo-enhanced"

Write-Host ""
Write-Host "Phase 7: Data Validation" -ForegroundColor Yellow
Write-Host "------------------------" -ForegroundColor Yellow

try {
    Write-Host "Checking database has data..." -NoNewline
    $stats = Invoke-RestMethod -Uri "$baseUrl/quran/stats" -Method Get
    
    if ($stats.total_tokens -gt 0) {
        Write-Host " PASS ($($stats.total_tokens) tokens)" -ForegroundColor Green
        $script:testsPassed++
    } else {
        Write-Host " WARNING (No data in database)" -ForegroundColor Yellow
        Write-Host "  Run: Invoke-RestMethod -Uri '$baseUrl/pipeline/process-sura?sura=1' -Method Post" -ForegroundColor Cyan
    }
} catch {
    Write-Host " FAIL" -ForegroundColor Red
    $script:testsFailed++
    $script:errors += "Data validation - $($_.Exception.Message)"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Test Results Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Tests Passed: $testsPassed" -ForegroundColor Green
Write-Host "Tests Failed: $testsFailed" -ForegroundColor $(if ($testsFailed -eq 0) { "Green" } else { "Red" })
Write-Host ""

if ($errors.Count -gt 0) {
    Write-Host "Failed Tests:" -ForegroundColor Red
    foreach ($err in $errors) {
        Write-Host "  - $err" -ForegroundColor Yellow
    }
    Write-Host ""
}

if ($testsFailed -eq 0) {
    Write-Host "All tests passed! API is healthy." -ForegroundColor Green
    exit 0
} else {
    Write-Host "Some tests failed. Check errors above." -ForegroundColor Red
    exit 1
}
