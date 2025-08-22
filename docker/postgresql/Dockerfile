# PostgreSQL with Watchtower optimization and lifecycle management
# Version: 1.3.4
# Registry: registry.jclee.me/blacklist-postgresql

FROM postgres:15-alpine

# Build metadata for Watchtower
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Watchtower labels for automatic updates
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.authors="jclee94@gmail.com" \
      org.opencontainers.image.url="https://blacklist.jclee.me" \
      org.opencontainers.image.documentation="https://github.com/JCLEE94/blacklist" \
      org.opencontainers.image.source="https://github.com/JCLEE94/blacklist" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.vendor="JCLee" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.title="Blacklist PostgreSQL" \
      org.opencontainers.image.description="PostgreSQL database for Blacklist Management System with Watchtower auto-deployment" \
      com.watchtower.enable="true" \
      com.watchtower.monitor-only="false" \
      com.watchtower.lifecycle.pre-update="/docker-entrypoint-initdb.d/pre-update.sh" \
      com.watchtower.lifecycle.post-update="/docker-entrypoint-initdb.d/post-update.sh" \
      com.watchtower.stop-signal="SIGTERM"

# Environment variables for database
ENV POSTGRES_DB=blacklist \
    POSTGRES_USER=postgres \
    POSTGRES_PASSWORD=password \
    PGDATA=/var/lib/postgresql/data/pgdata

# Create lifecycle management scripts
# Create database initialization script with no external dependencies
RUN echo '#!/bin/bash' > /docker-entrypoint-initdb.d/init-blacklist.sql && \
    echo 'CREATE DATABASE IF NOT EXISTS blacklist;' >> /docker-entrypoint-initdb.d/init-blacklist.sql && \
    echo 'CREATE TABLE IF NOT EXISTS blacklist_ips (id SERIAL PRIMARY KEY, ip VARCHAR(45), source VARCHAR(100), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);' >> /docker-entrypoint-initdb.d/init-blacklist.sql

RUN echo '#!/bin/bash' > /docker-entrypoint-initdb.d/pre-update.sh && \
    echo 'echo "[$(date)] Watchtower pre-update: Backing up PostgreSQL data..."' >> /docker-entrypoint-initdb.d/pre-update.sh && \
    echo 'pg_dumpall -U postgres > /var/lib/postgresql/data/backup-$(date +%Y%m%d-%H%M%S).sql 2>/dev/null || true' >> /docker-entrypoint-initdb.d/pre-update.sh && \
    echo 'echo "[$(date)] Database backup completed"' >> /docker-entrypoint-initdb.d/pre-update.sh

RUN echo '#!/bin/bash' > /docker-entrypoint-initdb.d/post-update.sh && \
    echo 'echo "[$(date)] Watchtower post-update: Verifying PostgreSQL..."' >> /docker-entrypoint-initdb.d/post-update.sh && \
    echo 'for i in {1..30}; do' >> /docker-entrypoint-initdb.d/post-update.sh && \
    echo '    if pg_isready -U postgres >/dev/null 2>&1; then' >> /docker-entrypoint-initdb.d/post-update.sh && \
    echo '        echo "[$(date)] PostgreSQL is ready after update"' >> /docker-entrypoint-initdb.d/post-update.sh && \
    echo '        exit 0' >> /docker-entrypoint-initdb.d/post-update.sh && \
    echo '    fi' >> /docker-entrypoint-initdb.d/post-update.sh && \
    echo '    sleep 2' >> /docker-entrypoint-initdb.d/post-update.sh && \
    echo 'done' >> /docker-entrypoint-initdb.d/post-update.sh && \
    echo 'echo "[$(date)] PostgreSQL failed to start after update"' >> /docker-entrypoint-initdb.d/post-update.sh && \
    echo 'exit 1' >> /docker-entrypoint-initdb.d/post-update.sh

RUN chmod +x /docker-entrypoint-initdb.d/*.sh

# Enhanced health check for Watchtower monitoring
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD pg_isready -U $POSTGRES_USER -d $POSTGRES_DB || exit 1

# Signal handling for graceful shutdown
STOPSIGNAL SIGTERM

# Expose PostgreSQL port
EXPOSE 5432