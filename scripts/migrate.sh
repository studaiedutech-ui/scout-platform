#!/bin/bash

# S.C.O.U.T. Platform Migration Script
# This script handles database migrations

echo "🗄️  S.C.O.U.T. Platform Database Migration Script"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Ensure database is running
echo "🐳 Starting database services..."
docker-compose up -d postgres redis

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Check database connection
echo "🔗 Testing database connection..."
docker-compose exec postgres pg_isready -U scout_user -d scout_db

if [ $? -ne 0 ]; then
    echo "❌ Database is not ready. Please check your Docker setup."
    exit 1
fi

cd backend

# Initialize Alembic if not already initialized
if [ ! -d "alembic/versions" ]; then
    echo "🆕 Initializing Alembic migrations..."
    mkdir -p alembic/versions
fi

# Check if Python is available locally
if command_exists python3; then
    echo "🐍 Running migrations with local Python..."
    
    # Create initial migration if none exist
    if [ -z "$(ls -A alembic/versions)" ]; then
        echo "📝 Creating initial migration..."
        python3 -m alembic revision --autogenerate -m "Initial migration"
    fi
    
    # Run migrations
    echo "🔄 Running database migrations..."
    python3 -m alembic upgrade head
    
    # Initialize database with sample data
    echo "🌱 Initializing database with sample data..."
    python3 -c "
from app.core.database import init_db
import asyncio

async def main():
    await init_db()
    print('Database initialized successfully!')

asyncio.run(main())
"
    
else
    echo "🐳 Running migrations with Docker..."
    
    # Create initial migration if none exist
    if [ -z "$(ls -A alembic/versions)" ]; then
        echo "📝 Creating initial migration..."
        docker-compose run --rm backend alembic revision --autogenerate -m "Initial migration"
    fi
    
    # Run migrations
    echo "🔄 Running database migrations..."
    docker-compose run --rm backend alembic upgrade head
    
    # Initialize database
    echo "🌱 Initializing database with sample data..."
    docker-compose run --rm backend python -c "
from app.core.database import init_db
import asyncio

async def main():
    await init_db()
    print('Database initialized successfully!')

asyncio.run(main())
"
fi

cd ..

echo "✅ Database migrations completed successfully!"
echo ""
echo "📊 You can now:"
echo "- Connect to PostgreSQL: localhost:5432"
echo "- Username: scout_user"
echo "- Database: scout_db"
echo "- Check tables with: docker-compose exec postgres psql -U scout_user -d scout_db -c '\\dt'"