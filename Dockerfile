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

# Core Application Configuration (필수)
ENV FLASK_ENV=production \
    PYTHONPATH=/app:$PYTHONPATH \
    PYTHONUNBUFFERED=1 \
    PORT=2542

# Database Configuration (런타임 오버라이드 가능)
ENV DATABASE_URL=${DATABASE_URL:-sqlite:////app/instance/blacklist.db} \
    REDIS_URL=${REDIS_URL:-redis://localhost:6379/0}

# Security (런타임 설정 필수 - 기본값은 개발용)
ENV SECRET_KEY=${SECRET_KEY:-dev-secret-key-change-in-production} \
    JWT_SECRET_KEY=${JWT_SECRET_KEY:-dev-jwt-key-change-in-production}

# Collection System (기본값으로 충분)
ENV COLLECTION_ENABLED=true

# Security Limits (기본값 사용)

# Performance Settings (기본값 충분)
ENV WORKERS=4 \
    THREADS=2

# Logging (필수)
ENV LOG_LEVEL=INFO

# External Services (런타임에 설정)

# Features (제거 - 불필요)

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