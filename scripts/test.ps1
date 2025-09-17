# S.C.O.U.T. Platform Testing Script (PowerShell)
# This script runs all tests for the platform

Write-Host "🧪 Running S.C.O.U.T. Platform tests..." -ForegroundColor Green

# Run frontend tests
Write-Host "🎨 Running frontend tests..." -ForegroundColor Cyan
Set-Location frontend
if (Test-Path "package.json") {
    $packageJson = Get-Content "package.json" | ConvertFrom-Json
    if ($packageJson.dependencies -or $packageJson.devDependencies) {
        $hasTestFramework = $false
        @("jest", "vitest", "@testing-library/react") | ForEach-Object {
            if ($packageJson.dependencies.$_ -or $packageJson.devDependencies.$_) {
                $hasTestFramework = $true
            }
        }
        
        if ($hasTestFramework) {
            npm test -- --watchAll=false --coverage
        } else {
            Write-Host "⚠️  No test framework found in frontend" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "❌ Frontend package.json not found" -ForegroundColor Red
}
Set-Location ..

# Run backend tests
Write-Host "🐍 Running backend tests..." -ForegroundColor Cyan
Set-Location backend
if (Test-Path "requirements.txt") {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        # Check if pytest is installed
        try {
            python -c "import pytest" 2>$null
            python -m pytest tests/ -v --cov=app
        } catch {
            Write-Host "⚠️  pytest not installed. Installing..." -ForegroundColor Yellow
            python -m pip install pytest pytest-cov
            python -m pytest tests/ -v --cov=app
        }
    } else {
        Write-Host "⚠️  Python not found. Running tests in Docker..." -ForegroundColor Yellow
        docker-compose run --rm backend python -m pytest tests/ -v
    }
} else {
    Write-Host "❌ Backend requirements.txt not found" -ForegroundColor Red
}
Set-Location ..

# Run integration tests with Docker
Write-Host "🐳 Running integration tests with Docker..." -ForegroundColor Cyan
if (Test-Path "docker-compose.test.yml") {
    docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
} else {
    Write-Host "⚠️  docker-compose.test.yml not found. Skipping integration tests." -ForegroundColor Yellow
}

# Lint checks
Write-Host "🔍 Running lint checks..." -ForegroundColor Cyan

# Frontend linting
Set-Location frontend
if (Test-Path "package.json") {
    $packageJson = Get-Content "package.json" | ConvertFrom-Json
    if ($packageJson.dependencies.eslint -or $packageJson.devDependencies.eslint) {
        npm run lint
    } else {
        Write-Host "⚠️  ESLint not configured" -ForegroundColor Yellow
    }
}
Set-Location ..

# Backend linting
Set-Location backend
if (Get-Command python -ErrorAction SilentlyContinue) {
    try {
        python -c "import flake8" 2>$null
        python -m flake8 app/
    } catch {
        Write-Host "⚠️  flake8 not installed" -ForegroundColor Yellow
    }
    
    try {
        python -c "import black" 2>$null
        python -m black --check app/
    } catch {
        Write-Host "⚠️  black not installed" -ForegroundColor Yellow
    }
}
Set-Location ..

Write-Host "✅ All tests completed!" -ForegroundColor Green