# Blacklist Dockerfile - SafeWork 스타일 완전 적용
# SafeWork의 멀티스테이지 빌드와 보안 패턴을 blacklist에 최적화

# Pin specific Python version for reproducibility
FROM python:3.11.8-slim-bookworm AS base

# Build arguments for version tracking - SafeWork 동적 버전 패턴
ARG BUILD_VERSION
ARG BUILD_NUMBER=local
ARG COMMIT_SHA=unknown
ARG BUILD_TIMESTAMP
ARG IMAGE_TAG=latest

# Set Python environment variables for optimization (SafeWork 환경변수 패턴)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    # Pip configuration for security
    PIP_NO_COMPILE=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    # Python security
    PYTHONHASHSEED=random \
    # Build metadata (SafeWork 패턴)
    BUILD_VERSION=${BUILD_VERSION} \
    BUILD_NUMBER=${BUILD_NUMBER} \
    COMMIT_SHA=${COMMIT_SHA}

# Set working directory
WORKDIR /app

# ==============================================================================
# System dependencies stage (SafeWork 패턴)
# ==============================================================================
FROM base AS system-deps

# Install system dependencies and security updates in one layer
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    # Required for compilation
    gcc \
    g++ \
    # Database client
    postgresql-client \
    # Health checks and monitoring
    curl \
    wget \
    # Process management
    tini \
    # Timezone support
    tzdata \
    # Git for version info
    git && \
    # Set timezone (SafeWork 패턴)
    ln -snf /usr/share/zoneinfo/Asia/Seoul /etc/localtime && \
    echo "Asia/Seoul" > /etc/timezone && \
    # Clean apt cache
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# ==============================================================================
# Dependencies stage - Python packages (SafeWork 패턴)
# ==============================================================================
FROM system-deps AS dependencies

# Upgrade pip first
RUN pip install --upgrade pip setuptools wheel

# Copy dependency files
COPY requirements-docker.txt ./requirements.txt

# Install production dependencies with proper caching
RUN pip install -r requirements.txt && \
    # Remove pip cache
    rm -rf /root/.cache/pip

# ==============================================================================
# Build stage - Application build (SafeWork 패턴)
# ==============================================================================
FROM dependencies AS build

# Copy application source code
COPY app/ ./app/
COPY src/ ./src/
COPY templates/ ./templates/
COPY main.py ./
COPY config/ ./config/

# Copy additional files if they exist
RUN if [ -d "scripts" ]; then cp -r scripts/ ./scripts/; fi
RUN if [ -f "gunicorn.conf.py" ]; then cp gunicorn.conf.py ./; fi

# Compile Python files for faster startup
RUN python -m compileall -b app/ src/ 2>/dev/null || true

# Create version info file (SafeWork 패턴)
RUN echo "{\
  \"version\": \"${BUILD_VERSION:-unknown}\",\
  \"build_number\": \"${BUILD_NUMBER:-local}\",\
  \"commit_sha\": \"${COMMIT_SHA:-unknown}\",\
  \"build_timestamp\": \"${BUILD_TIMESTAMP:-$(date -Iseconds)}\",\
  \"python_version\": \"$(python --version)\"\
}" > /app/build_info.json

# ==============================================================================
# Production stage - Minimal runtime (SafeWork 패턴)
# ==============================================================================
FROM python:3.11.8-slim-bookworm AS production

# Install runtime dependencies and security updates (SafeWork 패턴)
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    wget \
    tini \
    tzdata \
    ca-certificates && \
    # Set timezone (SafeWork 패턴)
    ln -snf /usr/share/zoneinfo/Asia/Seoul /etc/localtime && \
    echo "Asia/Seoul" > /etc/timezone && \
    # Clean apt cache
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create non-root user with UID > 10000 (SafeWork 보안 패턴)
RUN groupadd -r appgroup -g 10001 && \
    useradd -r -u 10001 -g appgroup -m -d /home/appuser -s /sbin/nologin appuser

# Set working directory
WORKDIR /app

# Copy Python packages from dependencies stage (SafeWork 패턴)
COPY --from=dependencies --chown=appuser:appgroup /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies --chown=appuser:appgroup /usr/local/bin/gunicorn /usr/local/bin/gunicorn
COPY --from=dependencies --chown=appuser:appgroup /usr/local/bin/uvicorn /usr/local/bin/uvicorn

# Copy application files from build stage (SafeWork 패턴)
COPY --from=build --chown=appuser:appgroup /app/app ./app
COPY --from=build --chown=appuser:appgroup /app/src ./src
COPY --from=build --chown=appuser:appgroup /app/templates ./templates
COPY --from=build --chown=appuser:appgroup /app/main.py ./main.py
COPY --from=build --chown=appuser:appgroup /app/build_info.json ./build_info.json

# Create necessary directories with proper permissions (SafeWork 패턴)
RUN mkdir -p /app/instance /app/logs /app/data /app/temp && \
    chown -R appuser:appgroup /app && \
    # Set secure permissions
    chmod 750 /app && \
    chmod 770 /app/instance /app/logs /app/data /app/temp

# Set runtime environment variables - SafeWork 패턴으로 모든 필수 환경변수 직접 정의
ENV PYTHONPATH=/app \
    TZ=Asia/Seoul \
    # Application settings
    FLASK_ENV=production \
    FLASK_APP=main.py \
    PORT=2542 \
    # Database settings (컨테이너 이름 기반)
    DATABASE_URL=postgresql://postgres:postgres@blacklist-postgres:5432/blacklist \
    REDIS_URL=redis://blacklist-redis:6379/0 \
    # Security settings
    SECRET_KEY=change-in-production-please \
    JWT_SECRET_KEY=blacklist-jwt-secret-2024 \
    JWT_ALGORITHM=HS256 \
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15 \
    JWT_REFRESH_TOKEN_EXPIRE_DAYS=7 \
    # Collection settings
    COLLECTION_ENABLED=true \
    FORCE_DISABLE_COLLECTION=false \
    # Logging
    LOG_LEVEL=INFO \
    DEBUG=False

# Switch to non-root user (SafeWork 패턴)
USER appuser

# Add comprehensive labels (SafeWork 패턴 확장)
LABEL app="blacklist" \
      version="${BUILD_VERSION}" \
      build-number="${BUILD_NUMBER}" \
      commit-sha="${COMMIT_SHA}" \
      build-timestamp="${BUILD_TIMESTAMP}" \
      maintainer="Blacklist Management Team" \
      com.centurylinklabs.watchtower.enable="true" \
      org.opencontainers.image.title="Blacklist Management System" \
      org.opencontainers.image.description="Enterprise threat intelligence platform - SafeWork architecture" \
      org.opencontainers.image.version="${BUILD_VERSION}" \
      org.opencontainers.image.created="${BUILD_TIMESTAMP}" \
      org.opencontainers.image.revision="${COMMIT_SHA}" \
      org.opencontainers.image.source="https://github.com/JCLEE94/blacklist" \
      security.scan.enabled="true" \
      monitoring.health.endpoint="/health" \
      deployment.strategy="watchtower-auto"

# Expose port (documentation only)
EXPOSE 2542

# Health check with proper timing (SafeWork 패턴)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:2542/health || exit 1

# Use tini for proper signal handling (SafeWork 패턴)
ENTRYPOINT ["tini", "--"]

# Production command (SafeWork 패턴 - 서비스 대기 없이 바로 실행)
CMD ["python", "main.py"]