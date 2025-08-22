# Single unified Dockerfile for Blacklist Management System
# Supports multi-service builds with build args
FROM python:3.11-slim

# Build arguments for service selection
ARG SERVICE=main
ARG VERSION=1.3.4
ARG BUILD_DATE
ARG VCS_REF

# Base environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    libpq5 \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create app user
RUN groupadd -g 1000 app \
    && useradd -u 1000 -g app -m -s /bin/bash app

WORKDIR /app

# Copy requirements and install Python dependencies
COPY config/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Service-specific configuration
COPY . .

# Main application service
RUN if [ "$SERVICE" = "main" ]; then \
    mkdir -p /app/data /app/logs /app/instance /app/scripts && \
    chown -R app:app /app && \
    chmod -R 755 /app/data /app/logs /app/instance; \
fi

# PostgreSQL service setup
RUN if [ "$SERVICE" = "postgresql" ]; then \
    apt-get update && apt-get install -y postgresql-15 postgresql-contrib-15 \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/lib/postgresql/data \
    && chown -R postgres:postgres /var/lib/postgresql; \
fi

# Redis service setup  
RUN if [ "$SERVICE" = "redis" ]; then \
    apt-get update && apt-get install -y redis-server \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/lib/redis \
    && chown -R redis:redis /var/lib/redis; \
fi

# Watchtower labels
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.title="Blacklist-${SERVICE}" \
      com.watchtower.enable="true"

# Service-specific exposure and commands
EXPOSE 2542
EXPOSE 5432
EXPOSE 6379

# Health checks
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD if [ "$SERVICE" = "main" ]; then \
        python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:2542/health')" || exit 1; \
    elif [ "$SERVICE" = "postgresql" ]; then \
        pg_isready -U postgres || exit 1; \
    elif [ "$SERVICE" = "redis" ]; then \
        redis-cli ping || exit 1; \
    fi

# Switch to appropriate user
USER app

# Service-specific startup commands
CMD if [ "$SERVICE" = "main" ]; then \
        python3 -u -m src.core.main; \
    elif [ "$SERVICE" = "postgresql" ]; then \
        exec gosu postgres postgres; \
    elif [ "$SERVICE" = "redis" ]; then \
        exec redis-server /etc/redis/redis.conf; \
    fi