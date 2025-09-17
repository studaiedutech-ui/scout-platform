# Production-ready Dockerfile for S.C.O.U.T. Backend
# Multi-stage build for optimized production image

# Stage 1: Build stage
FROM python:3.11-slim as builder

# Set build environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Python dependencies in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

# Stage 2: Production stage
FROM python:3.11-slim as production

# Set production environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PATH="/opt/venv/bin:$PATH"
ENV APP_ENV=production

# Install runtime dependencies and security updates
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    netcat-openbsd \
    ca-certificates \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create application directory
WORKDIR /app

# Create non-root user with minimal privileges
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /bin/bash appuser \
    && mkdir -p /app/logs \
    && chown -R appuser:appgroup /app

# Copy application code with proper ownership
COPY --chown=appuser:appgroup . .

# Remove unnecessary files for security
RUN rm -rf tests/ \
    && rm -rf .git/ \
    && rm -rf .gitignore \
    && rm -rf README.md \
    && find . -name "*.pyc" -delete \
    && find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Create startup script with health check logic
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Wait for dependencies\n\
echo "Waiting for database..."\n\
while ! nc -z $DB_HOST $DB_PORT; do\n\
  sleep 1\n\
done\n\
echo "Database is ready!"\n\
\n\
# Run database migrations if needed\n\
if [ "$RUN_MIGRATIONS" = "true" ]; then\n\
  echo "Running database migrations..."\n\
  alembic upgrade head\n\
fi\n\
\n\
# Start the application\n\
exec uvicorn app.main:app \\\n\
  --host 0.0.0.0 \\\n\
  --port 8000 \\\n\
  --workers ${WORKERS:-4} \\\n\
  --worker-class uvicorn.workers.UvicornWorker \\\n\
  --access-log \\\n\
  --log-level ${LOG_LEVEL:-info}\n' > /app/start.sh \
    && chmod +x /app/start.sh \
    && chown appuser:appgroup /app/start.sh

# Switch to non-root user
USER appuser

# Expose application port
EXPOSE 8000

# Add metadata labels
LABEL maintainer="S.C.O.U.T. Platform Team"
LABEL version="1.0.0"
LABEL description="S.C.O.U.T. AI Talent Acquisition Platform Backend"
LABEL org.opencontainers.image.source="https://github.com/scout-platform/backend"

# Health check with comprehensive validation
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/ready || exit 1

# Security scanning metadata
LABEL security.scan.policy="strict"
LABEL security.vulnerability.threshold="medium"

# Use startup script as entrypoint
CMD ["/app/start.sh"]