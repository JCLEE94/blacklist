# Unified Blacklist Application Dockerfile
# Multi-stage build optimized for production deployment
FROM python:3.11-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    postgresql-dev \
    build-base

# Copy dependency files
COPY config/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-alpine AS runtime

WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache \
    postgresql-libs \
    curl \
    bash \
    && adduser -D appuser

# Copy dependencies from builder
COPY --from=builder /root/.local /usr/local
ENV PATH=/usr/local/bin:$PATH

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/instance /app/logs /app/temp /app/data \
    && chown -R appuser:appuser /app

# Core application environment variables
ENV FLASK_ENV=production \
    PYTHONPATH=/app:$PYTHONPATH \
    PYTHONUNBUFFERED=1 \
    PORT=2542

# Database and Cache Configuration
ENV DATABASE_URL=postgresql://postgres:password@postgres:5432/blacklist \
    DATABASE_URI=postgresql://postgres:password@postgres:5432/blacklist \
    REDIS_URL=redis://redis:6379/0 \
    REDIS_DB=0 \
    REDIS_PORT=6379

# Security Configuration  
ENV SECRET_KEY=jztm3kGAUsxMZRBuU0uVlA0B4BXvIE6xe2KeHfDYsPs \
    JWT_SECRET_KEY=crmTBlEZ4ozEl6oRbrMuR-o_dDxxW8QcHLOZ1rGM_eU \
    JWT_ALGORITHM=HS256 \
    JWT_ACCESS_TOKEN_EXPIRES=3600 \
    JWT_EXPIRY_HOURS=24 \
    DEFAULT_API_KEY=blk_3BRg24QnUVaWw8sovs3CGdB6PH27LMEo \
    API_KEY_ENABLED=true \
    JWT_ENABLED=true

# Admin Configuration
ENV ADMIN_USERNAME=admin \
    ADMIN_PASSWORD=nOwyNq5cqq_M7cLaIZEm3A \
    ADMIN_EMAIL=admin@blacklist.local

# Collection System Configuration
ENV COLLECTION_ENABLED=true \
    FORCE_DISABLE_COLLECTION=false \
    COLLECTION_INTERVAL=3600 \
    COLLECTION_INTERVAL_HOURS=1 \
    COLLECTION_MAX_RETRIES=3 \
    RESTART_PROTECTION=false

# Authentication and Security Limits
ENV MAX_AUTH_ATTEMPTS=5 \
    BLOCK_DURATION_HOURS=1 \
    FORCE_HTTPS=false

# REGTECH Collector Configuration
ENV REGTECH_ENABLED=true \
    REGTECH_USERNAME="" \
    REGTECH_PASSWORD="" \
    REGTECH_BASE_URL="https://regtech.go.kr" \
    REGTECH_TIMEOUT=30 \
    REGTECH_MAX_RETRIES=3 \
    REGTECH_COLLECTION_DAYS=30 \
    REGTECH_MAX_PAGES=10 \
    REGTECH_PAGE_SIZE=50 \
    REGTECH_INTERVAL=3600 \
    REGTECH_COOKIES=""

# SECUDIUM Collector Configuration  
ENV SECUDIUM_USERNAME="" \
    SECUDIUM_PASSWORD="" \
    SECUDIUM_BASE_URL="https://www.secudium.com" \
    SECUDIUM_TIMEOUT=30 \
    SECUDIUM_MAX_RETRIES=3 \
    SECUDIUM_COLLECTION_DAYS=30 \
    SECUDIUM_INTERVAL=3600

# System Resource Limits
ENV MAX_MEMORY_MB=1024 \
    MAX_CPU_PERCENT=80 \
    MAX_DISK_PERCENT=90

# Switch to non-root user
USER appuser

# Health check with proper container networking
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Run application
CMD ["python", "main.py"]