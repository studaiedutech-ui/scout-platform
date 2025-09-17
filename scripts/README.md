# S.C.O.U.T. Platform Development Scripts

This directory contains helpful scripts for setting up and managing the S.C.O.U.T. platform development environment.

## Scripts Overview

### Setup Scripts
- **`setup.sh`** - Linux/Mac setup script
- **`setup.ps1`** - Windows PowerShell setup script

These scripts handle the initial development environment setup including:
- Prerequisites checking (Docker, Node.js, Python)
- Dependency installation (frontend and backend)
- Docker container building
- Database service startup
- Environment file creation

### Testing Scripts
- **`test.sh`** - Linux/Mac testing script
- **`test.ps1`** - Windows PowerShell testing script

These scripts run comprehensive tests including:
- Frontend unit tests
- Backend unit tests
- Integration tests
- Linting and code quality checks

### Migration Scripts
- **`migrate.sh`** - Database migration script

This script handles database operations:
- Database service startup
- Alembic migration creation and execution
- Sample data initialization

## Usage

### Windows (PowerShell)
```powershell
# Setup development environment
./scripts/setup.ps1

# Run tests
./scripts/test.ps1

# Run database migrations
./scripts/migrate.sh  # Use Git Bash or WSL for this script
```

### Linux/Mac
```bash
# Make scripts executable
chmod +x scripts/*.sh

# Setup development environment
./scripts/setup.sh

# Run tests
./scripts/test.sh

# Run database migrations
./scripts/migrate.sh
```

## Prerequisites

Before running any scripts, ensure you have:

1. **Docker Desktop** - For containerized services
2. **Node.js 18+** - For frontend development
3. **Python 3.11+** - For backend development (optional if using Docker)
4. **Git** - For version control

## Environment Configuration

The setup scripts will create a `.env` file with default values. You'll need to update it with your actual API keys:

```env
# API Keys (Replace with your actual keys)
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_ENVIRONMENT=your_pinecone_environment_here

# JWT Configuration
SECRET_KEY=your_jwt_secret_key_here
```

## Development Workflow

1. Run setup script once to initialize the environment
2. Use `npm run dev` to start development servers
3. Run test scripts during development
4. Use migration script when database schema changes

## Docker Services

The scripts manage these Docker services:
- **PostgreSQL** (localhost:5432) - Main database
- **Redis** (localhost:6379) - Caching and sessions

## Troubleshooting

If you encounter issues:
1. Ensure Docker Desktop is running
2. Check that all prerequisites are installed
3. Verify `.env` file has correct configuration
4. Try rebuilding Docker containers: `docker-compose build --no-cache`