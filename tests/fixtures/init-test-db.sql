-- Test database initialization
CREATE DATABASE IF NOT EXISTS blacklist_test;

\c blacklist_test;

-- Create main blacklist table
CREATE TABLE IF NOT EXISTS blacklist (
    id SERIAL PRIMARY KEY,
    ip INET UNIQUE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    source TEXT,
    metadata JSONB,
    detection_date DATE,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create auth attempts table
CREATE TABLE IF NOT EXISTS auth_attempts (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    username TEXT,
    success BOOLEAN NOT NULL DEFAULT FALSE,
    attempt_time TIMESTAMP NOT NULL DEFAULT NOW(),
    error_message TEXT,
    ip_address INET
);

-- Create collection config table
CREATE TABLE IF NOT EXISTS collection_config (
    id SERIAL PRIMARY KEY,
    config_data JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create collection logs table
CREATE TABLE IF NOT EXISTS collection_logs (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    data_count INTEGER DEFAULT 0,
    collection_time TIMESTAMP NOT NULL DEFAULT NOW(),
    duration_seconds INTEGER DEFAULT 0
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_blacklist_ip ON blacklist(ip);
CREATE INDEX IF NOT EXISTS idx_blacklist_source ON blacklist(source);
CREATE INDEX IF NOT EXISTS idx_blacklist_created_at ON blacklist(created_at);
CREATE INDEX IF NOT EXISTS idx_blacklist_is_active ON blacklist(is_active);
CREATE INDEX IF NOT EXISTS idx_auth_attempts_source ON auth_attempts(source);
CREATE INDEX IF NOT EXISTS idx_auth_attempts_time ON auth_attempts(attempt_time);
CREATE INDEX IF NOT EXISTS idx_collection_logs_source ON collection_logs(source);
CREATE INDEX IF NOT EXISTS idx_collection_logs_time ON collection_logs(collection_time);

-- Insert test data for testing
INSERT INTO blacklist (ip, source, metadata, detection_date) VALUES
    ('192.168.1.1', 'REGTECH', '{"severity": "high", "category": "malware"}', '2024-01-01'),
    ('10.0.0.1', 'SECUDIUM', '{"severity": "medium", "category": "spam"}', '2024-01-02'),
    ('172.16.0.1', 'MANUAL', '{"severity": "low", "category": "suspicious"}', '2024-01-03'),
    ('203.0.113.1', 'REGTECH', '{"severity": "high", "category": "botnet"}', '2024-01-04'),
    ('198.51.100.1', 'SECUDIUM', '{"severity": "critical", "category": "exploit"}', '2024-01-05')
ON CONFLICT (ip) DO NOTHING;

-- Insert test collection logs
INSERT INTO collection_logs (source, status, message, data_count, duration_seconds) VALUES
    ('REGTECH', 'success', 'Test collection successful', 100, 30),
    ('SECUDIUM', 'success', 'Test collection successful', 150, 45),
    ('REGTECH', 'error', 'Test authentication failed', 0, 10),
    ('SECUDIUM', 'success', 'Test collection partial', 75, 25);

-- Create test user and grant permissions
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'test_user') THEN
        CREATE USER test_user WITH PASSWORD 'test_pass_123';
    END IF;
END
$$;

GRANT ALL PRIVILEGES ON DATABASE blacklist_test TO test_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO test_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO test_user;