# Watchtower-optimized Redis for Blacklist System
FROM redis:7-alpine

# Watchtower labels
LABEL org.opencontainers.image.title="Blacklist Redis Cache" \
      org.opencontainers.image.description="Redis cache optimized for Watchtower auto-deployment" \
      org.opencontainers.image.vendor="JCLee" \
      org.opencontainers.image.version="7-alpine" \
      com.watchtower.enable="true" \
      com.watchtower.monitor-only="false" \
      com.watchtower.stop-signal="SIGTERM"

# Copy custom Redis configuration
COPY redis.conf /usr/local/etc/redis/redis.conf

# Create data directory
RUN mkdir -p /data && chown redis:redis /data

# Health check for Watchtower
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD redis-cli ping | grep -q PONG || exit 1

# Expose Redis port
EXPOSE 6379

# Volume for data persistence
VOLUME ["/data"]

# Run Redis with custom config
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]