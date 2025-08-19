-- PostgreSQL Extensions for Blacklist System
-- This script runs during database initialization

\echo 'Creating PostgreSQL extensions for Blacklist System...'

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Network functions for IP handling
CREATE EXTENSION IF NOT EXISTS "cidr";

\echo 'Extensions created successfully!'