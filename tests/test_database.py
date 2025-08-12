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
    # Auth attempts table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            username TEXT,
            success BOOLEAN NOT NULL DEFAULT 0,
            attempt_time DATETIME NOT NULL,
            error_message TEXT,
            ip_address TEXT
        )
    """
    )

    # Collection config table
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

    # Blacklist table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT UNIQUE NOT NULL,
            created_at DATETIME NOT NULL,
            source TEXT,
            metadata TEXT
        )
    """
    )

    # Blacklist IP table (alternative schema)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS blacklist_ip (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address VARCHAR(45) NOT NULL,
            source VARCHAR(50) NOT NULL,
            detection_date TIMESTAMP,
            reason TEXT,
            threat_level VARCHAR(20),
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    """
    )


@pytest.fixture(autouse=True)
def init_test_database():
    """Initialize database for tests"""
    try:
        # Initialize database for each test
        from src.init_database import initialize_database

        initialize_database(force=True, quiet=True)

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
