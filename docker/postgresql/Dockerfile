# PostgreSQL Standalone Container for Blacklist Service
FROM postgres:15-alpine

# Metadata
LABEL org.opencontainers.image.title="Blacklist PostgreSQL" \
      org.opencontainers.image.description="PostgreSQL database for Blacklist service" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.vendor="JCLee"

# Environment variables for database setup from .env migration
ENV POSTGRES_DB=blacklist \
    POSTGRES_USER=postgres \
    POSTGRES_PASSWORD=password \
    PGDATA=/var/lib/postgresql/data/pgdata \
    DATABASE_URL=postgresql://postgres:password@postgres:5432/blacklist

# Create initialization directory
RUN mkdir -p /docker-entrypoint-initdb.d

# Add initialization script
COPY --chown=postgres:postgres <<'EOF' /docker-entrypoint-initdb.d/01-init.sql
-- Create blacklist database and tables
CREATE TABLE IF NOT EXISTS blacklist_ips (
    id SERIAL PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL UNIQUE,
    source VARCHAR(50) NOT NULL,
    detection_date DATE NOT NULL,
    threat_level VARCHAR(20) DEFAULT 'MEDIUM',
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hits INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_ip_address ON blacklist_ips(ip_address);
CREATE INDEX idx_source ON blacklist_ips(source);
CREATE INDEX idx_detection_date ON blacklist_ips(detection_date);
CREATE INDEX idx_is_active ON blacklist_ips(is_active);

-- Create collections table
CREATE TABLE IF NOT EXISTS collections (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    total_ips INTEGER DEFAULT 0,
    new_ips INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create api_keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(100),
    name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP
);

-- Create user_sessions table
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    session_token VARCHAR(255) NOT NULL UNIQUE,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT true
);

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE blacklist TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Add sample data for testing
INSERT INTO blacklist_ips (ip_address, source, detection_date, threat_level) 
VALUES 
    ('192.168.1.100', 'MANUAL', CURRENT_DATE, 'HIGH'),
    ('10.0.0.1', 'MANUAL', CURRENT_DATE, 'MEDIUM')
ON CONFLICT (ip_address) DO NOTHING;
EOF

# Health check script
RUN echo '#!/bin/sh' > /usr/local/bin/healthcheck.sh && \
    echo 'pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}' >> /usr/local/bin/healthcheck.sh && \
    chmod +x /usr/local/bin/healthcheck.sh

# Expose PostgreSQL port
EXPOSE 5432

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh || exit 1

# Volume for data persistence
VOLUME ["/var/lib/postgresql/data"]

# Default command
CMD ["postgres"]