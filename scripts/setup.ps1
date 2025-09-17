# S.C.O.U.T. Platform Development Setup Script (PowerShell)
# This script sets up the development environment on Windows

Write-Host "🚀 Setting up S.C.O.U.T. Platform development environment..." -ForegroundColor Green

# Check if Docker is installed
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker Compose is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Check if Node.js is installed
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Node.js is not installed. Please install Node.js 18+ first." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Prerequisites check passed" -ForegroundColor Green

# Copy environment file
if (-not (Test-Path ".env")) {
    Write-Host "📝 Creating .env file from template..." -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
    } else {
        Write-Host "⚠️  .env.example not found. Creating basic .env file..." -ForegroundColor Yellow
        @"
# Database Configuration
DATABASE_URL=postgresql://scout_user:scout_password@localhost:5432/scout_db
REDIS_URL=redis://localhost:6379

# API Keys (Replace with your actual keys)
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_ENVIRONMENT=your_pinecone_environment_here

# JWT Configuration
SECRET_KEY=your_jwt_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Frontend Configuration
REACT_APP_API_URL=http://localhost:8000

# Development
DEBUG=true
"@ | Out-File -FilePath ".env" -Encoding utf8
    }
    Write-Host "⚠️  Please edit .env file with your configuration before continuing" -ForegroundColor Yellow
}

# Install frontend dependencies
Write-Host "📦 Installing frontend dependencies..." -ForegroundColor Cyan
Set-Location frontend
npm install
Set-Location ..

# Install backend dependencies (if Python is available)
Write-Host "📦 Installing backend dependencies..." -ForegroundColor Cyan
Set-Location backend
if (Get-Command python -ErrorAction SilentlyContinue) {
    python -m pip install -r requirements.txt
} else {
    Write-Host "⚠️  Python not found. Backend dependencies will be installed in Docker." -ForegroundColor Yellow
}
Set-Location ..

# Build Docker containers
Write-Host "🐳 Building Docker containers..." -ForegroundColor Cyan
docker-compose build

# Start database services
Write-Host "🗄️  Starting database services..." -ForegroundColor Cyan
docker-compose up -d postgres redis

# Wait for database to be ready
Write-Host "⏳ Waiting for database to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "✅ Development environment setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "🎯 Next steps:" -ForegroundColor Cyan
Write-Host "1. Edit .env file with your API keys and configuration"
Write-Host "2. Run 'npm run dev' to start the development servers"
Write-Host "3. Open http://localhost:3000 for the frontend"
Write-Host "4. Open http://localhost:8000/docs for the API documentation"
Write-Host ""
Write-Host "🐳 Docker services:" -ForegroundColor Cyan
Write-Host "- PostgreSQL: localhost:5432"
Write-Host "- Redis: localhost:6379"
Write-Host ""
Write-Host "Happy coding! 🚀" -ForegroundColor Green