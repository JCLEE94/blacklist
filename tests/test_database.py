"""데이터베이스 테스트 설정 모듈"""

import os
import tempfile

import pytest

# Set test environment
os.environ["FLASK_ENV"] = "testing"
os.environ["TESTING"] = "1"

# Disable Redis in tests (use memory cache)
os.environ["CACHE_TYPE"] = "simple"

test_db = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_URL"] = "sqlite:///{test_db}"
os.environ["FORCE_DISABLE_COLLECTION"] = "false"  # Allow collection in tests
os.environ["COLLECTION_ENABLED"] = "true"  # Enable collection for tests
os.environ["RESTART_PROTECTION"] = "false"  # Disable restart protection for tests
os.environ["SAFETY_PROTECTION"] = "false"  # Disable safety protection for tests


def _create_additional_test_tables(conn):
    """Create additional test tables with unified schema"""
    # Auth attempts table (aligned with actual schema)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT NOT NULL,
            user_agent TEXT,
            endpoint TEXT,
            method TEXT DEFAULT 'POST',
            success BOOLEAN NOT NULL,
            username TEXT,
            service TEXT,
            failure_reason TEXT,
            session_id TEXT,
            geographic_location TEXT,
            risk_score REAL DEFAULT 0.0,
            is_suspicious BOOLEAN DEFAULT 0,
            blocked_until TIMESTAMP,
            attempt_count INTEGER DEFAULT 1,
            fingerprint TEXT
        )
    """
    )

    # Collection config table (keeping for backward compatibility)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS collection_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_data TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
    """
    )

    # Blacklist table (aligned with actual schema)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT UNIQUE NOT NULL,
            created_at DATETIME NOT NULL,
            source TEXT DEFAULT 'unknown',
            metadata TEXT
        )
    """
    )

    # Blacklist entries table (main schema)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS blacklist_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT NOT NULL UNIQUE,
            first_seen TEXT,
            last_seen TEXT,
            detection_months TEXT,
            is_active BOOLEAN DEFAULT 1,
            days_until_expiry INTEGER DEFAULT 90,
            threat_level TEXT DEFAULT 'medium',
            source TEXT NOT NULL DEFAULT 'unknown',
            source_details TEXT,
            country TEXT,
            reason TEXT,
            reg_date TEXT,
            exp_date TEXT,
            view_count INTEGER DEFAULT 0,
            uuid TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            severity_score REAL DEFAULT 0.0,
            confidence_level REAL DEFAULT 1.0,
            tags TEXT,
            last_verified TIMESTAMP,
            verification_status TEXT DEFAULT 'unverified'
        )
    """
    )

    # Collection logs table (aligned with actual schema)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS collection_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source TEXT NOT NULL,
            status TEXT NOT NULL,
            items_collected INTEGER DEFAULT 0,
            items_new INTEGER DEFAULT 0,
            items_updated INTEGER DEFAULT 0,
            items_failed INTEGER DEFAULT 0,
            execution_time_ms REAL DEFAULT 0.0,
            error_message TEXT,
            details TEXT,
            collection_type TEXT DEFAULT 'scheduled',
            user_id TEXT,
            session_id TEXT,
            data_size_bytes INTEGER DEFAULT 0,
            memory_usage_mb REAL DEFAULT 0.0
        )
    """
    )


@pytest.fixture(autouse=True)
def init_test_database():
    """Initialize database for tests"""
    try:
        # Initialize database for each test
        import sys
        from pathlib import Path
        
        # Add app directory to path for import
        project_root = Path(__file__).parent.parent
        app_path = project_root / 'app'
        sys.path.insert(0, str(app_path))
        
        from init_database import init_database_enhanced
        
        # Use enhanced initialization with fallback
        init_database_enhanced(force_recreate=True, migrate=False)

        # Additional collection manager table creation
        import os
        import sqlite3

        db_path = os.environ.get("DATABASE_URL", "").replace("sqlite:///", "")
        if db_path and os.path.exists(db_path):
            try:
                with sqlite3.connect(db_path) as conn:
                    # Create additional tables using shared schema
                    _create_additional_test_tables(conn)
                    conn.commit()
            except Exception as e:
                pass  # Ignore errors in test table creation

    except ImportError:
        # Fallback: create database tables manually if needed
        import os
        import sqlite3

        db_path = os.environ.get("DATABASE_URL", "").replace("sqlite:///", "")
        if db_path and not os.path.exists(db_path):
            # Create the database file if it doesn't exist
            os.makedirs(os.path.dirname(db_path), exist_ok=True)

        if db_path:
            try:
                with sqlite3.connect(db_path) as conn:
                    # Create all necessary tables using shared schema
                    _create_additional_test_tables(conn)
                    conn.commit()
            except Exception as e:
                pass  # Ignore errors in fallback table creation
    yield
