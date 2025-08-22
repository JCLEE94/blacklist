# Watchtower-optimized Docker image with automatic deployment support
# Version: 1.3.4
# Registry: registry.jclee.me/blacklist

FROM python:3.11-slim as builder

# Build metadata for Watchtower
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Set environment to minimize external calls
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Copy and prepare all dependencies locally
COPY config/requirements.txt .

# Download all dependencies as wheels for offline installation
RUN pip wheel --wheel-dir=/wheels -r requirements.txt

# Production stage - minimal base image
FROM python:3.11-slim

# Container labels for metadata
LABEL org.opencontainers.image.created="2025-08-22" \
      org.opencontainers.image.authors="jclee94@gmail.com" \
      org.opencontainers.image.url="https://blacklist.jclee.me" \
      org.opencontainers.image.documentation="https://github.com/JCLEE94/blacklist" \
      org.opencontainers.image.source="https://github.com/JCLEE94/blacklist" \
      org.opencontainers.image.version="v1.0.37" \
      org.opencontainers.image.vendor="JCLee" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.title="Blacklist Management System" \
      org.opencontainers.image.description="Enterprise threat intelligence platform"

# Set environment to prevent external access
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    FLASK_ENV=production

# Install only essential system packages
RUN apt-get update && apt-get install -y \
    curl \
    libpq5 \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get purge -y --auto-remove

# Create non-root user with specific UID/GID for consistency
RUN groupadd -g 1000 app \
    && useradd -u 1000 -g app -m -s /bin/bash app \
    && mkdir -p /app/instance /app/data /app/logs /app/backups /app/scripts \
    && chown -R app:app /app

WORKDIR /app

# Copy wheels from builder (optimized layer caching)
COPY --from=builder /wheels /wheels

# Install Python packages from local wheels only (from requirements.txt)
RUN pip install --no-index --find-links=/wheels --no-cache-dir \
    flask gunicorn sqlalchemy psycopg2-binary redis python-dotenv \
    pandas openpyxl orjson requests cryptography alembic \
    flask-caching prometheus-client flask-compress beautifulsoup4 \
    lxml PyJWT psutil python-dateutil PyYAML APScheduler \
    defusedxml httpx aiohttp fastapi uvicorn numpy \
    && rm -rf /wheels

# Copy application code with proper ownership
COPY --chown=app:app . .

# Create all required directories with proper permissions
RUN mkdir -p \
    /app/data/by_detection_month \
    /app/data/by_source \
    /app/data/blacklist_ips \
    /app/data/exports \
    /app/data/logs \
    /app/data/regtech \
    /app/data/secudium \
    /app/temp \
    && chown -R app:app /app \
    && chmod -R 755 /app/data /app/logs /app/instance \
    && chmod +x /app/scripts/*.sh 2>/dev/null || true

# Copy version file and create version endpoint
COPY --chown=app:app version.txt /app/version.txt
RUN echo "${VERSION:-latest}" > /app/version.txt

# Create Watchtower lifecycle scripts
RUN echo '#!/bin/bash' > /app/scripts/pre-update.sh && \
    echo 'echo "[$(date)] Watchtower pre-update: Gracefully stopping application..."' >> /app/scripts/pre-update.sh && \
    echo '# Send SIGTERM to gunicorn for graceful shutdown' >> /app/scripts/pre-update.sh && \
    echo 'pkill -TERM -f gunicorn || true' >> /app/scripts/pre-update.sh && \
    echo 'sleep 5' >> /app/scripts/pre-update.sh && \
    echo 'echo "[$(date)] Pre-update complete"' >> /app/scripts/pre-update.sh

RUN echo '#!/bin/bash' > /app/scripts/post-update.sh && \
    echo 'echo "[$(date)] Watchtower post-update: Verifying new container..."' >> /app/scripts/post-update.sh && \
    echo '# Wait for application to be ready' >> /app/scripts/post-update.sh && \
    echo 'for i in {1..30}; do' >> /app/scripts/post-update.sh && \
    echo '    if curl -sf http://localhost:2542/health >/dev/null 2>&1; then' >> /app/scripts/post-update.sh && \
    echo '        echo "[$(date)] Health check passed after update"' >> /app/scripts/post-update.sh && \
    echo '        exit 0' >> /app/scripts/post-update.sh && \
    echo '    fi' >> /app/scripts/post-update.sh && \
    echo '    sleep 2' >> /app/scripts/post-update.sh && \
    echo 'done' >> /app/scripts/post-update.sh && \
    echo 'echo "[$(date)] Health check failed after update"' >> /app/scripts/post-update.sh && \
    echo 'exit 1' >> /app/scripts/post-update.sh

RUN chmod +x /app/scripts/*.sh && chown app:app /app/scripts/*.sh

# Switch to non-root user
USER app

# Advanced health check for Watchtower monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD PYTHONPATH=/app python3 -c "import urllib.request, json; \
    response = urllib.request.urlopen('http://localhost:2542/health'); \
    data = json.loads(response.read()); \
    assert data.get('status') == 'healthy', 'Unhealthy status'; \
    print('Health check passed')" || exit 1

# Expose port
EXPOSE 2542

# Signal handling for graceful shutdown
STOPSIGNAL SIGTERM

# Run application with proper signal handling
CMD ["python3", "-u", "-m", "src.core.main"]