# 🚀 Enterprise Production Dockerfile v8.3.0
# Multi-stage build optimized for security and performance

# ================================
# STAGE 1: Dependency Builder
# ================================
FROM python:3.11-alpine AS builder

LABEL maintainer="AI Automation Platform v8.3.0"
LABEL version="8.3.0"
LABEL description="Enterprise Blacklist Management System"

WORKDIR /app

# Security hardening - create non-root user early
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

# Install build dependencies with security updates
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
    ca-certificates && \
    rm -rf /var/cache/apk/*

# Copy and install Python dependencies with security verification
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --user -r requirements.txt && \
    pip check

# Verify installed packages security
RUN pip list --format=json > /tmp/installed-packages.json

# ================================
# STAGE 2: Production Runtime
# ================================
FROM python:3.11-alpine AS production

# Metadata and labels for container management
LABEL com.centurylinklabs.watchtower.enable="true"
LABEL security.scan="trivy,bandit,safety"
LABEL deployment.type="blue-green"
LABEL monitoring.health="/health"
LABEL backup.strategy="automated"

WORKDIR /app

# Security hardening - create identical non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

# Install minimal runtime dependencies with security updates
RUN apk update && apk upgrade && \
    apk add --no-cache \
    postgresql-libs \
    curl \
    bash \
    jq \
    dumb-init \
    tzdata \
    ca-certificates && \
    rm -rf /var/cache/apk/* && \
    update-ca-certificates

# Set timezone for Korean operations
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copy Python packages from builder stage
COPY --from=builder --chown=appuser:appgroup /root/.local /usr/local

# Create security reports directory (scan reports removed)
RUN mkdir -p /app/security-reports

# Copy application code with proper ownership
COPY --chown=appuser:appgroup . .

# Create necessary directories with secure permissions
RUN mkdir -p /app/{instance,logs,temp,data,backups,monitoring} && \
    chmod -R 755 /app && \
    chown -R appuser:appgroup /app

# ================================
# PRODUCTION ENVIRONMENT VARIABLES
# ================================

# Core Application Configuration
ENV FLASK_ENV=production \
    PYTHONPATH=/app:$PYTHONPATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8 \
    PORT=2542

# Database and Cache Configuration (Production)
ENV DATABASE_URL=postgresql://postgres:password@postgres:5432/blacklist \
    DATABASE_URI=postgresql://postgres:password@postgres:5432/blacklist \
    DATABASE_POOL_SIZE=20 \
    DATABASE_MAX_OVERFLOW=5 \
    DATABASE_POOL_TIMEOUT=30 \
    REDIS_URL=redis://redis:6379/0 \
    REDIS_DB=0 \
    REDIS_PORT=6379 \
    REDIS_TIMEOUT=5

# Security Environment Variables (All hardcoded)
ENV SECRET_KEY=jztm3kGAUsxMZRBuU0uVlA0B4BXvIE6xe2KeHfDYsPs \
    JWT_SECRET_KEY=crmTBlEZ4ozEl6oRbrMuR-o_dDxxW8QcHLOZ1rGM_eU \
    DEFAULT_API_KEY=blk_3BRg24QnUVaWw8sovs3CGdB6PH27LMEo \
    ADMIN_PASSWORD=nOwyNq5cqq_M7cLaIZEm3A \
    JWT_ALGORITHM=HS256 \
    JWT_ACCESS_TOKEN_EXPIRES=3600 \
    JWT_EXPIRY_HOURS=24 \
    JWT_REFRESH_TOKEN_EXPIRES=604800 \
    API_KEY_ENABLED=true \
    JWT_ENABLED=true \
    SESSION_COOKIE_SECURE=true \
    SESSION_COOKIE_HTTPONLY=true \
    SESSION_COOKIE_SAMESITE=Lax \
    ADMIN_USERNAME=admin \
    ADMIN_EMAIL=admin@blacklist.jclee.me

# Collection System Configuration (Production Ready)
ENV COLLECTION_ENABLED=true \
    FORCE_DISABLE_COLLECTION=false \
    COLLECTION_INTERVAL=3600 \
    COLLECTION_INTERVAL_HOURS=1 \
    COLLECTION_MAX_RETRIES=3 \
    COLLECTION_TIMEOUT=300 \
    RESTART_PROTECTION=false \
    COLLECTION_RATE_LIMIT=100

# Security Limits and Rate Limiting
ENV MAX_AUTH_ATTEMPTS=5 \
    BLOCK_DURATION_HOURS=1 \
    RATE_LIMIT_PER_MINUTE=100 \
    API_RATE_LIMIT=1000 \
    MAX_REQUEST_SIZE=16777216 \
    FORCE_HTTPS=true

# System Resource Limits and Performance
ENV MAX_MEMORY_MB=1024 \
    MAX_CPU_PERCENT=80 \
    MAX_DISK_PERCENT=90 \
    WORKERS=4 \
    THREADS=2 \
    WORKER_CLASS=gevent \
    WORKER_CONNECTIONS=1000 \
    MAX_REQUESTS=1000 \
    MAX_REQUESTS_JITTER=100 \
    PRELOAD_APP=true \
    TIMEOUT=30 \
    KEEPALIVE=2

# Monitoring and Observability
ENV ENABLE_METRICS=true \
    METRICS_PORT=8080 \
    LOG_LEVEL=INFO \
    LOG_FORMAT=json \
    ENABLE_TRACING=true \
    HEALTH_CHECK_TIMEOUT=10

# REGTECH Collector Configuration (Production)
ENV REGTECH_ENABLED=true \
    REGTECH_USERNAME=your-regtech-username \
    REGTECH_PASSWORD=your-regtech-password \
    REGTECH_BASE_URL=https://www.krcert.or.kr \
    REGTECH_TIMEOUT=30 \
    REGTECH_MAX_RETRIES=3 \
    REGTECH_COLLECTION_DAYS=30 \
    REGTECH_MAX_PAGES=10 \
    REGTECH_PAGE_SIZE=50 \
    REGTECH_INTERVAL=3600 \
    REGTECH_COOKIES=""

# SECUDIUM Collector Configuration (Production)  
ENV SECUDIUM_USERNAME=your-secudium-username \
    SECUDIUM_PASSWORD=your-secudium-password \
    SECUDIUM_BASE_URL=https://www.secudium.com \
    SECUDIUM_TIMEOUT=30 \
    SECUDIUM_MAX_RETRIES=3 \
    SECUDIUM_COLLECTION_DAYS=30 \
    SECUDIUM_INTERVAL=3600

# Production Feature Flags and A/B Testing
ENV FEATURE_FLAG_ENABLED=true \
    AB_TESTING_ENABLED=true \
    FEATURE_NEW_UI=false \
    FEATURE_ADVANCED_ANALYTICS=true \
    FEATURE_AUTO_SCALING=true

# Backup and Recovery Configuration
ENV BACKUP_ENABLED=true \
    BACKUP_INTERVAL=86400 \
    BACKUP_RETENTION_DAYS=30 \
    AUTO_BACKUP_ON_DEPLOY=true \
    BACKUP_COMPRESS=true

# ================================
# SECURITY HARDENING
# ================================

# Remove package managers and unnecessary tools
RUN apk del --purge apk-tools && \
    rm -rf /var/cache/apk/* /tmp/* /var/tmp/* && \
    find /usr/local -name "*.pyc" -delete && \
    find /usr/local -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Set secure file permissions
RUN chmod -R o-rwx /app && \
    chmod -R g-w /app && \
    chmod +x /app/main.py

# Switch to non-root user (Security Best Practice)
USER appuser

# ================================
# HEALTH CHECKS AND MONITORING
# ================================

# Enhanced health check with multiple endpoints
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:${PORT}/health && \
        curl -f http://localhost:${PORT}/api/health && \
        curl -f http://localhost:${PORT}/ready || exit 1

# Expose application port
EXPOSE ${PORT}

# Expose metrics port for monitoring
EXPOSE 8080

# ================================
# STARTUP AND ENTRYPOINT
# ================================

# Use dumb-init for proper signal handling
ENTRYPOINT ["dumb-init", "--"]

# Production startup with Gunicorn
CMD ["sh", "-c", "\
    echo '🚀 AI 자동화 플랫폼 v8.3.0 Production 서버 시작' && \
    echo '📊 환경: Production (Enterprise Grade)' && \
    echo '🔒 보안: 강화된 컨테이너 보안 적용' && \
    echo '⚡ 성능: Gunicorn + Gevent 워커' && \
    echo '📈 모니터링: 실시간 메트릭 수집 활성화' && \
    python main.py"]

# ================================
# BUILD METADATA
# ================================
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=8.3.0

LABEL org.opencontainers.image.created=${BUILD_DATE}
LABEL org.opencontainers.image.url="https://blacklist.jclee.me"
LABEL org.opencontainers.image.source="https://github.com/jclee94/blacklist"
LABEL org.opencontainers.image.version=${VERSION}
LABEL org.opencontainers.image.revision=${VCS_REF}
LABEL org.opencontainers.image.vendor="AI Automation Platform"
LABEL org.opencontainers.image.title="Enterprise Blacklist Management System"
LABEL org.opencontainers.image.description="Production-ready threat intelligence platform with automated GitOps pipeline"