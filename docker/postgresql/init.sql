-- PostgreSQL Initialization Script for Blacklist System
-- Version: 1.3.4

-- Create database if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'blacklist') THEN
        CREATE DATABASE blacklist;
    END IF;
END
$$;