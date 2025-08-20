-- Create missing tables for Blacklist Management System
-- PostgreSQL Schema v2.0

-- Create blacklist_entries table
CREATE TABLE IF NOT EXISTS blacklist_entries (
    id SERIAL PRIMARY KEY,
    ip_address INET NOT NULL,
    source VARCHAR(50) NOT NULL,
    threat_type VARCHAR(100),
    description TEXT,
    detection_date DATE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    confidence_score INTEGER DEFAULT 100,
    country_code VARCHAR(2),
    isp VARCHAR(255),
    UNIQUE(ip_address, source)
);

-- Create metadata table
CREATE TABLE IF NOT EXISTS metadata (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create collection_logs table
CREATE TABLE IF NOT EXISTS collection_logs (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    message TEXT,
    ip_count INTEGER DEFAULT 0,
    duration_seconds FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create api_keys table for security
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    permissions JSONB DEFAULT '{}',
    expires_at TIMESTAMP
);

-- Create user_sessions table
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    ip_address INET,
    user_agent TEXT
);

-- Create indices for performance
CREATE INDEX IF NOT EXISTS idx_blacklist_ip ON blacklist_entries(ip_address);
CREATE INDEX IF NOT EXISTS idx_blacklist_source ON blacklist_entries(source);
CREATE INDEX IF NOT EXISTS idx_blacklist_active ON blacklist_entries(is_active);
CREATE INDEX IF NOT EXISTS idx_blacklist_date ON blacklist_entries(detection_date);
CREATE INDEX IF NOT EXISTS idx_collection_logs_source ON collection_logs(source);
CREATE INDEX IF NOT EXISTS idx_collection_logs_created ON collection_logs(created_at);

-- Insert initial metadata
INSERT INTO metadata (key, value) VALUES 
    ('db_version', '2.0'),
    ('db_type', 'postgresql'),
    ('schema_migrated', 'true')
ON CONFLICT (key) DO UPDATE SET 
    value = EXCLUDED.value,
    updated_at = CURRENT_TIMESTAMP;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO blacklist_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO blacklist_user;