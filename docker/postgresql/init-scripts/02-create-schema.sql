-- Blacklist Database Schema for PostgreSQL
-- Migrated from SQLite schema

\echo 'Creating Blacklist database schema...'

-- Main blacklist table
CREATE TABLE IF NOT EXISTS blacklist (
    id SERIAL PRIMARY KEY,
    ip_address INET NOT NULL,
    source VARCHAR(50) NOT NULL,
    threat_level VARCHAR(20) DEFAULT 'medium',
    description TEXT,
    country VARCHAR(100),
    detection_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Blacklist entries (compatibility)
CREATE TABLE IF NOT EXISTS blacklist_entries (
    id SERIAL PRIMARY KEY,
    ip_address INET NOT NULL,
    source VARCHAR(50) NOT NULL,
    threat_level VARCHAR(20) DEFAULT 'medium',
    description TEXT,
    country VARCHAR(100),
    detection_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- System metadata
CREATE TABLE IF NOT EXISTS metadata (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Collection logs
CREATE TABLE IF NOT EXISTS collection_logs (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    event VARCHAR(100) NOT NULL,
    details JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Auth attempts
CREATE TABLE IF NOT EXISTS auth_attempts (
    id SERIAL PRIMARY KEY,
    ip_address INET,
    username VARCHAR(100),
    success BOOLEAN,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_agent TEXT
);

-- System status
CREATE TABLE IF NOT EXISTS system_status (
    id SERIAL PRIMARY KEY,
    component VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    details JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cache entries
CREATE TABLE IF NOT EXISTS cache_entries (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT,
    expiry TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System logs
CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    details JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Collection sources
CREATE TABLE IF NOT EXISTS collection_sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    config JSONB,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Collection credentials
CREATE TABLE IF NOT EXISTS collection_credentials (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(100) NOT NULL,
    username VARCHAR(255),
    password_encrypted TEXT,
    api_key_encrypted TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Collection settings
CREATE TABLE IF NOT EXISTS collection_settings (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(100) NOT NULL,
    setting_key VARCHAR(100) NOT NULL,
    setting_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_name, setting_key)
);

-- Collection history
CREATE TABLE IF NOT EXISTS collection_history (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR(50) NOT NULL,
    items_collected INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    details JSONB
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_blacklist_ip ON blacklist USING btree (ip_address);
CREATE INDEX IF NOT EXISTS idx_blacklist_source ON blacklist (source);
CREATE INDEX IF NOT EXISTS idx_blacklist_date ON blacklist (detection_date);
CREATE INDEX IF NOT EXISTS idx_blacklist_active ON blacklist (is_active);
CREATE INDEX IF NOT EXISTS idx_blacklist_created ON blacklist (created_at);

CREATE INDEX IF NOT EXISTS idx_collection_logs_source ON collection_logs (source);
CREATE INDEX IF NOT EXISTS idx_collection_logs_timestamp ON collection_logs (timestamp);

CREATE INDEX IF NOT EXISTS idx_auth_attempts_ip ON auth_attempts USING btree (ip_address);
CREATE INDEX IF NOT EXISTS idx_auth_attempts_timestamp ON auth_attempts (timestamp);

CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs (level);
CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs (timestamp);

CREATE INDEX IF NOT EXISTS idx_collection_history_source ON collection_history (source);
CREATE INDEX IF NOT EXISTS idx_collection_history_started ON collection_history (started_at);

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers
CREATE TRIGGER update_blacklist_updated_at 
    BEFORE UPDATE ON blacklist 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_blacklist_entries_updated_at 
    BEFORE UPDATE ON blacklist_entries 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_metadata_updated_at 
    BEFORE UPDATE ON metadata 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_collection_sources_updated_at 
    BEFORE UPDATE ON collection_sources 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_collection_credentials_updated_at 
    BEFORE UPDATE ON collection_credentials 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_collection_settings_updated_at 
    BEFORE UPDATE ON collection_settings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

\echo 'Database schema created successfully!'