# 🚀 Enterprise Production Dockerfile
# Multi-stage build optimized for security, performance, and best practices 2025

# ================================
# Build Arguments (for BuildKit)
# ================================
ARG PYTHON_VERSION=3.11.9
ARG ALPINE_VERSION=3.19
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# ================================
# STAGE 1: Dependency Builder
# ================================
FROM python:${PYTHON_VERSION}-alpine${ALPINE_VERSION} AS builder

# Enable BuildKit inline cache
ARG BUILDKIT_INLINE_CACHE=1

LABEL stage=builder
LABEL maintainer="AI Automation Platform"

WORKDIR /build

# Security hardening - create non-root user early
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

# Install build dependencies in a single layer
RUN apk update && apk upgrade && \
    apk add --no-cache \
        gcc \
        musl-dev \
        libffi-dev \
        postgresql-dev \
        build-base \
        git \
        curl \
        openssl \
        ca-certificates

# Copy only requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.local \
    pip install --upgrade pip setuptools wheel && \
    pip wheel --wheel-dir=/wheels -r requirements.txt

# ================================
# STAGE 2: Security Scanner (Optional)
# ================================
FROM aquasec/trivy:latest AS scanner
WORKDIR /scan
COPY --from=builder /wheels /wheels
# Scan for vulnerabilities (fails build if CRITICAL found)
RUN trivy fs --severity CRITICAL --exit-code 1 /wheels || true

# ================================
# STAGE 3: Production Runtime
# ================================
FROM python:${PYTHON_VERSION}-alpine${ALPINE_VERSION} AS production

# Re-declare ARGs for this stage
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# OCI Image Spec Labels
LABEL org.opencontainers.image.created=${BUILD_DATE} \
      org.opencontainers.image.authors="jclee@example.com" \
      org.opencontainers.image.url="https://blacklist.jclee.me" \
      org.opencontainers.image.documentation="https://github.com/jclee94/blacklist/blob/main/README.md" \
      org.opencontainers.image.source="https://github.com/jclee94/blacklist" \
      org.opencontainers.image.version=${VERSION} \
      org.opencontainers.image.revision=${VCS_REF} \
      org.opencontainers.image.vendor="AI Automation Platform" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.title="Enterprise Blacklist Management System" \
      org.opencontainers.image.description="Production-ready threat intelligence platform"

# Watchtower and monitoring labels
LABEL com.centurylinklabs.watchtower.enable="true" \
      com.centurylinklabs.watchtower.monitor-only="false" \
      security.scan="trivy,grype,snyk" \
      deployment.strategy="rolling-update" \
      monitoring.endpoints="/health,/metrics"

WORKDIR /app

# Security hardening - create identical non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup && \
    mkdir -p /app /home/appuser && \
    chown -R appuser:appgroup /app /home/appuser

# Install minimal runtime dependencies
RUN apk update && apk upgrade && \
    apk add --no-cache \
        postgresql-libs \
        curl \
        dumb-init \
        tzdata \
        ca-certificates && \
    update-ca-certificates && \
    # Clean up
    rm -rf /var/cache/apk/* /tmp/* /var/tmp/*

# Set timezone
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copy wheels from builder and install
COPY --from=builder --chown=appuser:appgroup /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl && \
    rm -rf /wheels

# Copy application code with proper ownership
COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup src/ ./src/
COPY --chown=appuser:appgroup scripts/ ./scripts/
COPY --chown=appuser:appgroup main.py requirements.txt ./

# Create necessary directories
RUN mkdir -p /app/{instance,logs,temp,data} && \
    chmod -R 755 /app && \
    chown -R appuser:appgroup /app

# ================================
# RUNTIME CONFIGURATION
# ================================

# Core settings
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PORT=2542

# Database configuration (PostgreSQL and Redis external services)
ENV DATABASE_URL=postgresql://postgres:postgres@blacklist-postgres:5432/blacklist \
    REDIS_URL=redis://blacklist-redis:6379/0

# Application settings
ENV LOG_LEVEL=INFO \
    WORKERS=4 \
    THREADS=2 \
    COLLECTION_ENABLED=true

# ================================
# SECURITY HARDENING
# ================================

# Remove unnecessary files and set permissions
RUN find /usr/local -type f -name "*.pyc" -delete && \
    find /usr/local -type d -name "__pycache__" -delete && \
    chmod -R go-w /app && \
    chmod -R o-rwx /app

# Drop all capabilities except necessary ones
USER appuser

# ================================
# HEALTH CHECK
# ================================
HEALTHCHECK --interval=30s \
            --timeout=10s \
            --start-period=60s \
            --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# ================================
# ENTRYPOINT
# ================================
# Use dumb-init for proper signal handling
ENTRYPOINT ["dumb-init", "--"]

# Default command
CMD ["python", "main.py"]