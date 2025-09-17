#!/bin/bash

# S.C.O.U.T. Platform Testing Script
# This script runs all tests for the platform

echo "🧪 Running S.C.O.U.T. Platform tests..."

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Run frontend tests
echo "🎨 Running frontend tests..."
cd frontend
if [ -f "package.json" ]; then
    if npm list --depth=0 | grep -q "jest\|vitest\|@testing-library"; then
        npm test -- --watchAll=false --coverage
    else
        echo "⚠️  No test framework found in frontend"
    fi
else
    echo "❌ Frontend package.json not found"
fi
cd ..

# Run backend tests
echo "🐍 Running backend tests..."
cd backend
if [ -f "requirements.txt" ]; then
    if command_exists python3; then
        # Check if pytest is installed
        if python3 -c "import pytest" 2>/dev/null; then
            python3 -m pytest tests/ -v --cov=app
        else
            echo "⚠️  pytest not installed. Installing..."
            python3 -m pip install pytest pytest-cov
            python3 -m pytest tests/ -v --cov=app
        fi
    else
        echo "⚠️  Python not found. Running tests in Docker..."
        docker-compose run --rm backend python -m pytest tests/ -v
    fi
else
    echo "❌ Backend requirements.txt not found"
fi
cd ..

# Run integration tests with Docker
echo "🐳 Running integration tests with Docker..."
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Lint checks
echo "🔍 Running lint checks..."

# Frontend linting
cd frontend
if [ -f "package.json" ]; then
    if npm list --depth=0 | grep -q "eslint"; then
        npm run lint
    else
        echo "⚠️  ESLint not configured"
    fi
fi
cd ..

# Backend linting
cd backend
if command_exists python3; then
    if python3 -c "import flake8" 2>/dev/null; then
        python3 -m flake8 app/
    else
        echo "⚠️  flake8 not installed"
    fi
    
    if python3 -c "import black" 2>/dev/null; then
        python3 -m black --check app/
    else
        echo "⚠️  black not installed"
    fi
fi
cd ..

echo "✅ All tests completed!"