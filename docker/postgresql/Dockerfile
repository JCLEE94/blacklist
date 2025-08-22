# Watchtower-optimized PostgreSQL for Blacklist System
FROM postgres:15-alpine

# Watchtower labels
LABEL org.opencontainers.image.title="Blacklist PostgreSQL Database" \
      org.opencontainers.image.description="PostgreSQL database optimized for Watchtower auto-deployment" \
      org.opencontainers.image.vendor="JCLee" \
      org.opencontainers.image.version="15-alpine" \
      com.watchtower.enable="true" \
      com.watchtower.monitor-only="false" \
      com.watchtower.lifecycle.pre-update="/docker-entrypoint-initdb.d/pre-update.sh" \
      com.watchtower.lifecycle.post-update="/docker-entrypoint-initdb.d/post-update.sh" \
      com.watchtower.stop-signal="SIGTERM"

# Environment variables for PostgreSQL
ENV POSTGRES_DB=blacklist \
    POSTGRES_USER=blacklist_user \
    POSTGRES_PASSWORD=blacklist_password_change_me \
    PGDATA=/var/lib/postgresql/data/pgdata

# Copy initialization scripts
COPY init.sql /docker-entrypoint-initdb.d/01-init.sql
COPY schema.sql /docker-entrypoint-initdb.d/02-schema.sql

# Create Watchtower lifecycle scripts
RUN mkdir -p /docker-entrypoint-initdb.d && \
    cat > /docker-entrypoint-initdb.d/pre-update.sh << 'EOF'
#!/bin/bash
echo "[$(date)] Watchtower pre-update: Creating database backup..."
pg_dump -U $POSTGRES_USER $POSTGRES_DB > /tmp/backup_$(date +%Y%m%d_%H%M%S).sql
echo "[$(date)] Database backup complete"
EOF

RUN cat > /docker-entrypoint-initdb.d/post-update.sh << 'EOF'
#!/bin/bash
echo "[$(date)] Watchtower post-update: Verifying database..."
pg_isready -U $POSTGRES_USER -d $POSTGRES_DB
if [ $? -eq 0 ]; then
    echo "[$(date)] Database is ready after update"
else
    echo "[$(date)] Database verification failed"
    exit 1
fi
EOF

RUN chmod +x /docker-entrypoint-initdb.d/*.sh

# Health check for Watchtower
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD pg_isready -U $POSTGRES_USER -d $POSTGRES_DB || exit 1

# Expose PostgreSQL port
EXPOSE 5432

# Volume for data persistence
VOLUME ["/var/lib/postgresql/data"]

# Run PostgreSQL
CMD ["postgres"]