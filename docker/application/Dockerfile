# Blacklist Application Standalone Container
FROM python:3.11-slim

# Metadata
LABEL org.opencontainers.image.title="Blacklist Application" \
      org.opencontainers.image.description="Blacklist threat intelligence application" \
      org.opencontainers.image.version="1.0.42" \
      org.opencontainers.image.vendor="JCLee"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    netcat-traditional \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash app && \
    mkdir -p /app/data /app/logs /app/instance /app/config /app/temp && \
    chown -R app:app /app

WORKDIR /app

# Copy requirements and install Python dependencies
COPY --chown=app:app config/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=app:app . /app/

# Create startup script with wait logic
RUN cat > /app/entrypoint.sh <<'EOF'
#!/bin/bash
set -e

echo "[$(date)] Starting Blacklist Application..."

# Environment variables from .env migration
export DATABASE_URL="${DATABASE_URL:-postgresql://postgres:password@postgres:5432/blacklist}"
export REDIS_URL="${REDIS_URL:-redis://redis:6379/0}"
export PORT="${PORT:-2542}"
export FLASK_ENV="${FLASK_ENV:-production}"
export SECRET_KEY="${SECRET_KEY:-jztm3kGAUsxMZRBuU0uVlA0B4BXvIE6xe2KeHfDYsPs}"
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-crmTBlEZ4ozEl6oRbrMuR-o_dDxxW8QcHLOZ1rGM_eU}"
export DEFAULT_API_KEY="${DEFAULT_API_KEY:-blk_3BRg24QnUVaWw8sovs3CGdB6PH27LMEo}"
export ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
export ADMIN_PASSWORD="${ADMIN_PASSWORD:-nOwyNq5cqq_M7cLaIZEm3A}"
export COLLECTION_ENABLED="${COLLECTION_ENABLED:-true}"
export FORCE_DISABLE_COLLECTION="${FORCE_DISABLE_COLLECTION:-false}"
export API_KEY_ENABLED="${API_KEY_ENABLED:-true}"
export JWT_ENABLED="${JWT_ENABLED:-true}"
export MAX_AUTH_ATTEMPTS="${MAX_AUTH_ATTEMPTS:-5}"
export BLOCK_DURATION_HOURS="${BLOCK_DURATION_HOURS:-1}"

# Function to wait for service
wait_for_service() {
    local host=$1
    local port=$2
    local service=$3
    local max_retries=30
    local retry=0
    
    echo "Waiting for $service at $host:$port..."
    while [ $retry -lt $max_retries ]; do
        if nc -z $host $port 2>/dev/null; then
            echo "$service is ready!"
            return 0
        fi
        retry=$((retry + 1))
        echo "Waiting for $service... ($retry/$max_retries)"
        sleep 2
    done
    echo "ERROR: $service not available after 60 seconds"
    return 1
}

# Parse database URL for host and port
DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

# Parse Redis URL for host and port
REDIS_HOST=$(echo $REDIS_URL | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
REDIS_PORT=$(echo $REDIS_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

# Default values if parsing fails
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"

# Wait for PostgreSQL
if ! wait_for_service "$DB_HOST" "$DB_PORT" "PostgreSQL"; then
    echo "WARNING: PostgreSQL not available, continuing anyway..."
fi

# Wait for Redis
if ! wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis"; then
    echo "WARNING: Redis not available, will use memory cache..."
    export REDIS_URL="memory://"
fi

# Initialize database if needed
echo "Initializing database schema..."
python3 scripts/init_postgres_standalone.py || echo "Database initialization failed, continuing..."

# Create required directories
mkdir -p /app/data /app/logs /app/instance /app/temp

echo "Starting application on port ${PORT}..."
echo "Database: ${DATABASE_URL}"
echo "Redis: ${REDIS_URL}"
echo "Environment: ${FLASK_ENV}"

# Start application
if [ "${FLASK_ENV}" = "development" ]; then
    exec python3 main.py
else
    exec gunicorn --bind 0.0.0.0:${PORT} \
        --workers ${GUNICORN_WORKERS:-2} \
        --threads ${GUNICORN_THREADS:-2} \
        --timeout 60 \
        --keep-alive 5 \
        --max-requests 1000 \
        --max-requests-jitter 50 \
        --access-logfile - \
        --error-logfile - \
        --log-level ${LOG_LEVEL:-info} \
        "src.core.main:create_app()"
fi
EOF

RUN chmod +x /app/entrypoint.sh

# Switch to non-root user
USER app

# Environment variables from .env migration
ENV DATABASE_URL="postgresql://postgres:password@postgres:5432/blacklist" \
    REDIS_URL="redis://redis:6379/0" \
    FLASK_ENV="production" \
    PORT="2542" \
    PYTHONUNBUFFERED="1" \
    SECRET_KEY="jztm3kGAUsxMZRBuU0uVlA0B4BXvIE6xe2KeHfDYsPs" \
    JWT_SECRET_KEY="crmTBlEZ4ozEl6oRbrMuR-o_dDxxW8QcHLOZ1rGM_eU" \
    DEFAULT_API_KEY="blk_3BRg24QnUVaWw8sovs3CGdB6PH27LMEo" \
    ADMIN_USERNAME="admin" \
    ADMIN_PASSWORD="nOwyNq5cqq_M7cLaIZEm3A" \
    COLLECTION_ENABLED="true" \
    FORCE_DISABLE_COLLECTION="false" \
    API_KEY_ENABLED="true" \
    JWT_ENABLED="true" \
    MAX_AUTH_ATTEMPTS="5" \
    BLOCK_DURATION_HOURS="1"

# Expose port
EXPOSE 2542

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:2542/health || exit 1

# Volume for persistent data
VOLUME ["/app/data", "/app/logs"]

# Run application
CMD ["/app/entrypoint.sh"]