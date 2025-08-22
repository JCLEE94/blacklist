#!/usr/bin/env python3
"""Initialize PostgreSQL database for standalone operation"""
import os
import sys
import time
import psycopg2
from psycopg2 import sql


def wait_for_postgres(db_url, max_retries=30):
    """Wait for PostgreSQL to be ready"""
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(db_url)
            conn.close()
            print(f"PostgreSQL is ready after {i+1} attempts")
            return True
        except Exception as e:
            print(f"Waiting for PostgreSQL... ({i+1}/{max_retries})")
            time.sleep(2)
    return False


def init_postgres_database():
    """Initialize PostgreSQL database with complete schema"""
    db_url = os.environ.get(
        "DATABASE_URL", "postgresql://blacklist_user:password@postgres:5432/blacklist"
    )

    if not wait_for_postgres(db_url):
        print("ERROR: PostgreSQL not available after 60 seconds")
        sys.exit(1)

    print(f"Initializing PostgreSQL database")

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    # Create blacklist_ips table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS blacklist_ips (
            id SERIAL PRIMARY KEY,
            ip_address VARCHAR(45) NOT NULL UNIQUE,
            source VARCHAR(50) NOT NULL,
            detection_date DATE NOT NULL,
            threat_level VARCHAR(20) DEFAULT 'MEDIUM',
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            hits INTEGER DEFAULT 1,
            status VARCHAR(20) DEFAULT 'ACTIVE',
            country VARCHAR(100),
            region VARCHAR(100),
            city VARCHAR(100),
            asn INTEGER,
            organization VARCHAR(255),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Create indexes
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_blacklist_ips_ip_address ON blacklist_ips(ip_address)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_blacklist_ips_source ON blacklist_ips(source)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_blacklist_ips_detection_date ON blacklist_ips(detection_date)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_blacklist_ips_status ON blacklist_ips(status)"
    )

    # Create collection_logs table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS collection_logs (
            id SERIAL PRIMARY KEY,
            source VARCHAR(50) NOT NULL,
            collection_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ips_collected INTEGER DEFAULT 0,
            status VARCHAR(20) DEFAULT 'SUCCESS',
            error_message TEXT,
            execution_time REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Create collection_status table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS collection_status (
            id SERIAL PRIMARY KEY,
            source VARCHAR(50) NOT NULL UNIQUE,
            last_collection TIMESTAMP,
            next_scheduled TIMESTAMP,
            status VARCHAR(20) DEFAULT 'DISABLED',
            enabled BOOLEAN DEFAULT FALSE,
            error_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            total_ips_collected INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Create api_keys table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            id SERIAL PRIMARY KEY,
            key_hash VARCHAR(255) NOT NULL UNIQUE,
            key_prefix VARCHAR(20) NOT NULL,
            name VARCHAR(100),
            user_id VARCHAR(100),
            permissions TEXT DEFAULT '[]',
            rate_limit INTEGER DEFAULT 1000,
            is_active BOOLEAN DEFAULT TRUE,
            expires_at TIMESTAMP,
            last_used TIMESTAMP,
            usage_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Create user_sessions table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_sessions (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL UNIQUE,
            user_id VARCHAR(100) NOT NULL,
            access_token_hash VARCHAR(255),
            refresh_token_hash VARCHAR(255),
            expires_at TIMESTAMP NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            ip_address VARCHAR(45),
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Create token_blacklist table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS token_blacklist (
            id SERIAL PRIMARY KEY,
            token_hash VARCHAR(255) NOT NULL UNIQUE,
            token_type VARCHAR(20) NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Insert default collection status (disabled)
    cursor.execute(
        """
        INSERT INTO collection_status (source, status, enabled) 
        VALUES 
            ('REGTECH', 'DISABLED', FALSE),
            ('SECUDIUM', 'DISABLED', FALSE)
        ON CONFLICT (source) DO NOTHING
    """
    )

    # Insert sample data for testing
    cursor.execute(
        """
        INSERT INTO blacklist_ips 
        (ip_address, source, detection_date, threat_level, status, notes) 
        VALUES 
            ('192.168.1.100', 'SAMPLE', CURRENT_DATE, 'LOW', 'ACTIVE', 'Sample IP for standalone testing'),
            ('10.0.0.50', 'TEST', CURRENT_DATE, 'MEDIUM', 'ACTIVE', 'Test IP for functionality verification')
        ON CONFLICT (ip_address) DO NOTHING
    """
    )

    conn.commit()
    conn.close()

    print("PostgreSQL database initialized successfully!")


if __name__ == "__main__":
    init_postgres_database()
