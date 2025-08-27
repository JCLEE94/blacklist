# Redis Standalone Container for Blacklist Service - SafeWork 패턴 적용
FROM redis:7-alpine

# Build arguments for version tracking - 동적 버전 패턴
ARG BUILD_VERSION=$(date +%Y%m%d%H%M)
ARG BUILD_NUMBER=${GITHUB_RUN_NUMBER:-local}
ARG COMMIT_SHA=${GITHUB_SHA:-unknown}
ARG BUILD_TIMESTAMP=$(date -Iseconds)

# Set timezone to Korea (KST)
RUN apk --no-cache add tzdata && \
    ln -snf /usr/share/zoneinfo/Asia/Seoul /etc/localtime && \
    echo "Asia/Seoul" > /etc/timezone

# Environment variables with build metadata
ENV TZ=Asia/Seoul \
    BUILD_VERSION=${BUILD_VERSION} \
    BUILD_NUMBER=${BUILD_NUMBER} \
    COMMIT_SHA=${COMMIT_SHA}

# Essential labels - Watchtower 활성화 및 모니터링
LABEL com.centurylinklabs.watchtower.enable="true" \
      monitoring.health.endpoint="/health"

# Environment variables from .env migration
ENV REDIS_URL=redis://redis:6379/0

# Create redis user and directories
RUN mkdir -p /data /usr/local/etc/redis && \
    chown redis:redis /data /usr/local/etc/redis

# Create version info file with dynamic values
RUN echo "{\
  \"version\": \"$(date +%Y%m%d%H%M)\",\
  \"build_number\": \"local\",\
  \"commit_sha\": \"unknown\",\
  \"build_timestamp\": \"$(date -Iseconds)\",\
  \"redis_version\": \"7-alpine\"\
}" > /data/version.json && chown redis:redis /data/version.json

# Create Redis configuration
RUN cat > /usr/local/etc/redis/redis.conf <<EOF
# Redis Configuration for Blacklist Service
bind 0.0.0.0
protected-mode no
port 6379
tcp-backlog 511
timeout 0
tcp-keepalive 300

# Persistence
dir /data
dbfilename dump.rdb
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Memory management
maxmemory 256mb
maxmemory-policy allkeys-lru

# Logging
loglevel notice
logfile ""

# Performance
databases 16
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes

# Client handling
maxclients 10000

# Lazy freeing
lazyfree-lazy-eviction no
lazyfree-lazy-expire no
lazyfree-lazy-server-del no
replica-lazy-flush no
EOF

# Health check script
RUN echo '#!/bin/sh' > /usr/local/bin/healthcheck.sh && \
    echo 'redis-cli ping | grep -q PONG' >> /usr/local/bin/healthcheck.sh && \
    chmod +x /usr/local/bin/healthcheck.sh

# Expose Redis port
EXPOSE 6379

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh || exit 1

# Volume for data persistence
VOLUME ["/data"]

# Switch to redis user
USER redis

# Run Redis with config
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]