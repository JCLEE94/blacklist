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

# Environment variables from .env - managed by Docker Compose
ENV FLASK_ENV=production \
    PYTHONPATH=/app:$PYTHONPATH \
    PYTHONUNBUFFERED=1 \
    PORT=2542

# Default environment variables with security keys
ENV DATABASE_URL=postgresql://postgres:password@postgres:5432/blacklist \
    REDIS_URL=redis://redis:6379/0 \
    FORCE_DISABLE_COLLECTION=false \
    COLLECTION_ENABLED=true \
    API_KEY_ENABLED=true \
    JWT_ENABLED=true \
    MAX_AUTH_ATTEMPTS=5 \
    BLOCK_DURATION_HOURS=1 \
    SECRET_KEY=jztm3kGAUsxMZRBuU0uVlA0B4BXvIE6xe2KeHfDYsPs \
    JWT_SECRET_KEY=crmTBlEZ4ozEl6oRbrMuR-o_dDxxW8QcHLOZ1rGM_eU \
    DEFAULT_API_KEY=blk_3BRg24QnUVaWw8sovs3CGdB6PH27LMEo \
    ADMIN_USERNAME=admin \
    ADMIN_PASSWORD=nOwyNq5cqq_M7cLaIZEm3A

# Switch to non-root user
USER appuser

# Health check with proper container networking
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Run application
CMD ["python", "main.py"]