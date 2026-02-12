#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run pytest-postgresql tests in Docker container with PostgreSQL binaries.

.DESCRIPTION
    This script builds and runs the Docker test environment that includes
    PostgreSQL 17 binaries (pg_ctl, initdb, postgres) to run all tests
    including those that require pg_ctl, regardless of the host OS.

.PARAMETER Coverage
    Generate coverage reports (default: true)

.PARAMETER Verbose
    Run tests with verbose output (default: true)

.PARAMETER TestPath
    Specific test file or directory to run (default: tests/)

.PARAMETER BuildOnly
    Only build the Docker image without running tests

.PARAMETER NoBuild
    Skip building and use existing Docker image

.EXAMPLE
    .\run-docker-tests.ps1
    Run all tests with coverage

.EXAMPLE
    .\run-docker-tests.ps1 -TestPath tests/test_executor.py
    Run specific test file

.EXAMPLE
    .\run-docker-tests.ps1 -BuildOnly
    Only build the Docker image
#>

param(
    [switch]$Coverage = $true,
    [switch]$Verbose = $true,
    [string]$TestPath = "tests/",
    [switch]$BuildOnly,
    [switch]$NoBuild
)

$ErrorActionPreference = "Stop"

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "pytest-postgresql Docker Test Runner" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is installed
try {
    $dockerVersion = docker --version
    Write-Host "Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Docker Desktop from https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# Check if Docker is running
try {
    docker ps | Out-Null
    Write-Host "Docker daemon is running" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker daemon is not running" -ForegroundColor Red
    Write-Host "Please start Docker Desktop" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Build Docker image if needed
if (-not $NoBuild) {
    Write-Host "Building Docker test image..." -ForegroundColor Cyan
    docker-compose -f docker-compose.tests.yml build test-runner
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Docker build failed" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Docker image built successfully" -ForegroundColor Green
    Write-Host ""
}

if ($BuildOnly) {
    Write-Host "Build complete. Use -NoBuild flag to skip building next time." -ForegroundColor Green
    exit 0
}

# Prepare pytest command
$pytestCmd = "pytest $TestPath"

if ($Verbose) {
    $pytestCmd += " -v"
}

if ($Coverage) {
    $pytestCmd += " --cov=pytest_postgresql --cov-report=term --cov-report=html --cov-report=json --cov-branch"
}

$pytestCmd += " --tb=short"

Write-Host "Running tests in Docker container..." -ForegroundColor Cyan
Write-Host "Command: $pytestCmd" -ForegroundColor Gray
Write-Host ""

# Run tests
docker-compose -f docker-compose.tests.yml run --rm test-runner bash -c $pytestCmd

$exitCode = $LASTEXITCODE

Write-Host ""

if ($exitCode -eq 0) {
    Write-Host "=====================================" -ForegroundColor Green
    Write-Host "All tests passed!" -ForegroundColor Green
    Write-Host "=====================================" -ForegroundColor Green
    
    if ($Coverage) {
        Write-Host ""
        Write-Host "Coverage reports generated:" -ForegroundColor Cyan
        Write-Host "  - Terminal output (see above)" -ForegroundColor Gray
        Write-Host "  - HTML: htmlcov/index.html" -ForegroundColor Gray
        Write-Host "  - JSON: coverage.json" -ForegroundColor Gray
        
        if (Test-Path "check_coverage.py") {
            Write-Host ""
            Write-Host "Running coverage analysis..." -ForegroundColor Cyan
            python check_coverage.py
        }
    }
} else {
    Write-Host "=====================================" -ForegroundColor Red
    Write-Host "Tests failed with exit code: $exitCode" -ForegroundColor Red
    Write-Host "=====================================" -ForegroundColor Red
}

Write-Host ""
Write-Host "Cleaning up..." -ForegroundColor Cyan
docker-compose -f docker-compose.tests.yml down

exit $exitCode
