# Redis with Watchtower optimization and enhanced health monitoring
# Version: 1.3.4
# Registry: registry.jclee.me/blacklist-redis

FROM redis:7-alpine

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
      org.opencontainers.image.title="Blacklist Redis" \
      org.opencontainers.image.description="Redis cache for Blacklist Management System with Watchtower auto-deployment" \
      com.watchtower.enable="true" \
      com.watchtower.monitor-only="false" \
      com.watchtower.lifecycle.pre-update="/usr/local/bin/pre-update.sh" \
      com.watchtower.lifecycle.post-update="/usr/local/bin/post-update.sh" \
      com.watchtower.stop-signal="SIGTERM"

# Create Redis configuration for production - completely self-contained
RUN mkdir -p /usr/local/etc/redis /data && \
    echo 'bind 0.0.0.0' > /usr/local/etc/redis/redis.conf && \
    echo 'port 6379' >> /usr/local/etc/redis/redis.conf && \
    echo 'tcp-keepalive 60' >> /usr/local/etc/redis/redis.conf && \
    echo 'timeout 0' >> /usr/local/etc/redis/redis.conf && \
    echo 'databases 16' >> /usr/local/etc/redis/redis.conf && \
    echo 'save 900 1' >> /usr/local/etc/redis/redis.conf && \
    echo 'save 300 10' >> /usr/local/etc/redis/redis.conf && \
    echo 'save 60 10000' >> /usr/local/etc/redis/redis.conf && \
    echo 'dir /data' >> /usr/local/etc/redis/redis.conf && \
    echo 'maxmemory 256mb' >> /usr/local/etc/redis/redis.conf && \
    echo 'maxmemory-policy allkeys-lru' >> /usr/local/etc/redis/redis.conf && \
    echo 'appendonly yes' >> /usr/local/etc/redis/redis.conf && \
    echo 'appendfsync everysec' >> /usr/local/etc/redis/redis.conf && \
    echo 'protected-mode no' >> /usr/local/etc/redis/redis.conf && \
    echo 'loglevel notice' >> /usr/local/etc/redis/redis.conf && \
    echo 'logfile ""' >> /usr/local/etc/redis/redis.conf

# Create Watchtower lifecycle scripts
RUN echo '#!/bin/sh' > /usr/local/bin/pre-update.sh && \
    echo 'echo "[$(date)] Watchtower pre-update: Saving Redis data..."' >> /usr/local/bin/pre-update.sh && \
    echo 'redis-cli BGSAVE || true' >> /usr/local/bin/pre-update.sh && \
    echo 'sleep 2' >> /usr/local/bin/pre-update.sh && \
    echo 'echo "[$(date)] Redis data save completed"' >> /usr/local/bin/pre-update.sh

RUN echo '#!/bin/sh' > /usr/local/bin/post-update.sh && \
    echo 'echo "[$(date)] Watchtower post-update: Verifying Redis..."' >> /usr/local/bin/post-update.sh && \
    echo 'for i in $(seq 1 30); do' >> /usr/local/bin/post-update.sh && \
    echo '    if redis-cli ping >/dev/null 2>&1; then' >> /usr/local/bin/post-update.sh && \
    echo '        echo "[$(date)] Redis is ready after update"' >> /usr/local/bin/post-update.sh && \
    echo '        exit 0' >> /usr/local/bin/post-update.sh && \
    echo '    fi' >> /usr/local/bin/post-update.sh && \
    echo '    sleep 2' >> /usr/local/bin/post-update.sh && \
    echo 'done' >> /usr/local/bin/post-update.sh && \
    echo 'echo "[$(date)] Redis failed to start after update"' >> /usr/local/bin/post-update.sh && \
    echo 'exit 1' >> /usr/local/bin/post-update.sh

RUN chmod +x /usr/local/bin/*.sh

# Enhanced health check for Watchtower monitoring
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD redis-cli ping || exit 1

# Signal handling for graceful shutdown
STOPSIGNAL SIGTERM

# Expose Redis port
EXPOSE 6379

# Start Redis with custom configuration
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]