-- Sample data for blacklist_entries
-- This script adds sample data for testing

\echo 'Inserting sample blacklist data...'

-- Insert sample blacklist entries
INSERT INTO blacklist_entries (ip_address, source, threat_level, description, country, detection_date, created_at)
VALUES 
    ('192.168.1.100', 'REGTECH', 'HIGH', 'Malicious activity detected', 'KR', CURRENT_DATE, NOW()),
    ('10.0.0.50', 'SECUDIUM', 'MEDIUM', 'Suspicious behavior', 'US', CURRENT_DATE - INTERVAL '1 day', NOW() - INTERVAL '1 day'),
    ('172.16.0.25', 'REGTECH', 'HIGH', 'Brute force attempt', 'CN', CURRENT_DATE - INTERVAL '2 days', NOW() - INTERVAL '2 days'),
    ('203.0.113.42', 'REGTECH', 'CRITICAL', 'Known botnet member', 'RU', CURRENT_DATE - INTERVAL '3 days', NOW() - INTERVAL '3 days'),
    ('198.51.100.89', 'SECUDIUM', 'HIGH', 'Port scanning detected', 'JP', CURRENT_DATE - INTERVAL '4 days', NOW() - INTERVAL '4 days'),
    ('192.0.2.123', 'SYSTEM', 'MEDIUM', 'Automated threat detection', 'KR', CURRENT_DATE, NOW() - INTERVAL '6 hours'),
    ('10.10.10.10', 'REGTECH', 'HIGH', 'DDoS participant', 'US', CURRENT_DATE, NOW() - INTERVAL '12 hours'),
    ('172.31.255.255', 'SECUDIUM', 'LOW', 'Potential threat', 'GB', CURRENT_DATE - INTERVAL '5 days', NOW() - INTERVAL '5 days')
ON CONFLICT DO NOTHING;

-- Also insert into main blacklist table for compatibility
INSERT INTO blacklist (ip_address, source, threat_level, description, country, detection_date, created_at)
SELECT ip_address, source, threat_level, description, country, detection_date, created_at
FROM blacklist_entries
ON CONFLICT DO NOTHING;

\echo 'Sample data inserted successfully!'