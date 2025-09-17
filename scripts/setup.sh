#!/bin/bash

# S.C.O.U.T. Platform Development Setup Script
# This script sets up the development environment

echo "🚀 Setting up S.C.O.U.T. Platform development environment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11+ first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Copy environment file
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration before continuing"
fi

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd frontend
npm install
cd ..

# Install backend dependencies (if Python is available)
echo "📦 Installing backend dependencies..."
cd backend
if command -v python3 &> /dev/null; then
    python3 -m pip install -r requirements.txt
else
    echo "⚠️  Python not found. Backend dependencies will be installed in Docker."
fi
cd ..

# Build Docker containers
echo "🐳 Building Docker containers..."
docker-compose build

# Start database services
echo "🗄️  Starting database services..."
docker-compose up -d postgres redis

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Run database migrations (if backend dependencies are installed)
if command -v python3 &> /dev/null; then
    echo "🔄 Running database migrations..."
    cd backend
    # python3 -m alembic upgrade head
    cd ..
fi

echo "✅ Development environment setup complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Edit .env file with your API keys and configuration"
echo "2. Run 'npm run dev' to start the development servers"
echo "3. Open http://localhost:3000 for the frontend"
echo "4. Open http://localhost:8000/docs for the API documentation"
echo ""
echo "🐳 Docker services:"
echo "- PostgreSQL: localhost:5432"
echo "- Redis: localhost:6379"
echo ""
echo "Happy coding! 🚀"