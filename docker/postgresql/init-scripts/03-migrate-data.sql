-- Data Migration Script for PostgreSQL
-- Migrates existing data and sets up initial configuration

\echo 'Inserting initial metadata and configuration...'

-- Initial system metadata
INSERT INTO metadata (key, value) VALUES 
    ('db_version', '2.0'),
    ('migration_date', CURRENT_TIMESTAMP::text),
    ('schema_type', 'postgresql'),
    ('system_initialized', 'true')
ON CONFLICT (key) DO UPDATE SET 
    value = EXCLUDED.value,
    updated_at = CURRENT_TIMESTAMP;

-- Initial collection sources
INSERT INTO collection_sources (name, config, enabled) VALUES 
    ('REGTECH', '{"url": "https://regtech.fsec.or.kr", "type": "web_scraping", "auth_mode": "cookie"}', true),
    ('SECUDIUM', '{"url": "https://secudium.com", "type": "api", "auth_mode": "login"}', true)
ON CONFLICT (name) DO UPDATE SET 
    config = EXCLUDED.config,
    enabled = EXCLUDED.enabled,
    updated_at = CURRENT_TIMESTAMP;

-- Initial system status
INSERT INTO system_status (component, status, details) VALUES 
    ('database', 'ready', '{"type": "postgresql", "version": "15"}'),
    ('collection', 'ready', '{"sources": ["REGTECH", "SECUDIUM"]}'),
    ('api', 'ready', '{"endpoints": ["blacklist", "fortigate", "analytics"]}')
ON CONFLICT DO NOTHING;

-- Create view for compatibility with existing queries
CREATE OR REPLACE VIEW blacklist_view AS 
SELECT 
    id,
    ip_address::text as ip_address,
    source,
    threat_level,
    description,
    country,
    detection_date,
    created_at,
    updated_at,
    is_active
FROM blacklist;

-- Function for IP address validation
CREATE OR REPLACE FUNCTION validate_ip_address(ip_text TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    -- Try to cast to INET type
    PERFORM ip_text::INET;
    RETURN TRUE;
EXCEPTION WHEN OTHERS THEN
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Function to get active blacklist count
CREATE OR REPLACE FUNCTION get_active_blacklist_count()
RETURNS INTEGER AS $$
BEGIN
    RETURN (SELECT COUNT(*) FROM blacklist WHERE is_active = true);
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old logs
CREATE OR REPLACE FUNCTION cleanup_old_logs(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM collection_logs 
    WHERE timestamp < (CURRENT_TIMESTAMP - INTERVAL '1 day' * days_to_keep);
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    DELETE FROM system_logs 
    WHERE timestamp < (CURRENT_TIMESTAMP - INTERVAL '1 day' * days_to_keep);
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create sequence for compatibility (if needed)
CREATE SEQUENCE IF NOT EXISTS blacklist_id_seq OWNED BY blacklist.id;
CREATE SEQUENCE IF NOT EXISTS collection_logs_id_seq OWNED BY collection_logs.id;

\echo 'Data migration and initial setup completed successfully!'