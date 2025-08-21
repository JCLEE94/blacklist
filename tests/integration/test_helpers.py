"""Common test helpers for integration tests

Shared utilities to reduce duplication across test files.
"""

import json
import sqlite3
import tempfile
from datetime import datetime
from unittest.mock import Mock

import pytest
from flask import Flask


def create_test_app():
    """Create standardized test Flask app"""
    from src.core.unified_routes import unified_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    app.register_blueprint(unified_bp)
    return app


def create_mock_service(failing=False):
    """Create standardized mock service"""
    service = Mock()

    if failing:
        # Configure failure modes
        service.network_error = Exception("Network connection timeout")
        service.auth_error = Exception("Authentication failed: Invalid credentials")
        service.db_error = sqlite3.DatabaseError("Database is locked")
        service.parse_error = json.JSONDecodeError("Invalid JSON", "", 0)
    else:
        # Configure success responses
        service.get_active_ips.return_value = (["1.1.4.1", "2.2.2.2"], 2)
        service.add_ip.return_value = True
        service.get_all_ips.return_value = [
            {
                "ip": "1.1.4.1",
                "source": "regtech",
                "detection_date": datetime.now().isoformat(),
                "is_active": True,
            }
        ]
        service.get_status.return_value = {
            "enabled": True,
            "sources": {"regtech": {"enabled": True}},
        }

    return service


def create_temp_db():
    """Create temporary test database"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_path = temp_file.name
    temp_file.close()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
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
    conn.commit()
    conn.close()

    return db_path


class BaseIntegrationTest:
    """Base class for integration tests with common fixtures"""

    @pytest.fixture
    def app(self):
        """Create test Flask app"""
        return create_test_app()

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    @pytest.fixture
    def temp_db(self):
        """Create temporary database"""
        import os

        db_path = create_temp_db()
        yield db_path
        try:
            os.unlink(db_path)
        except:
            pass
