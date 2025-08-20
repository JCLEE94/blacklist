#!/usr/bin/env python3
"""
Unit tests for StatisticsServiceMixin
Tests analytics, statistics, and reporting functionality.
"""

import os
import sqlite3
import tempfile
import unittest.mock as mock
from datetime import datetime
from datetime import timedelta

import pytest

from src.core.services.statistics_service import StatisticsServiceMixin


# Create a test service factory function
def create_test_statistics_service():
    """Factory function to create test service with proper initialization"""

    class TestStatisticsService(StatisticsServiceMixin):
        """Test implementation of StatisticsServiceMixin"""

        def get_collection_logs(self, limit=10):
            """Mock get_collection_logs method"""
            return [
                {
                    "timestamp": datetime.now().isoformat(),
                    "source": "regtech",
                    "action": "collection",
                    "success": True,
                }
            ]

    service = TestStatisticsService()
    service.logger = mock.Mock()
    service.blacklist_manager = mock.Mock()
    service.collection_enabled = True
    service._running = True
    service._components = {"regtech": mock.Mock(), "secudium": mock.Mock()}
    service.config = {
        "service_name": "blacklist",
        "version": "1.0.0",
        "auto_collection": True,
        "collection_interval": 3600,
    }

    return service


class TestStatisticsServiceMixin:
    """Test cases for StatisticsServiceMixin"""

    @pytest.fixture
    def service(self):
        """Create test service instance"""
        return create_test_statistics_service()

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def populated_db(self, temp_db_path):
        """Create and populate test database"""
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Create blacklist_entries table
        cursor.execute(
            """
            CREATE TABLE blacklist_entries (
                id INTEGER PRIMARY KEY,
                ip_address TEXT,
                source TEXT,
                is_active BOOLEAN,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                last_seen TEXT,
                reason TEXT,
                country TEXT
            )
        """
        )

        # Insert test data
        test_data = [
            (
                "192.168.1.1",
                "regtech",
                1,
                "2023-01-01 10:00:00",
                "2023-01-01 10:00:00",
                "2023-01-01",
                "malware",
                "US",
            ),
            (
                "192.168.1.2",
                "secudium",
                1,
                "2023-01-02 11:00:00",
                "2023-01-02 11:00:00",
                "2023-01-02",
                "phishing",
                "CN",
            ),
            (
                "192.168.1.3",
                "regtech",
                0,
                "2023-01-03 12:00:00",
                "2023-01-03 12:00:00",
                "2023-01-03",
                "botnet",
                "RU",
            ),
            (
                "192.168.1.4",
                "secudium",
                1,
                "2023-01-04 13:00:00",
                "2023-01-04 13:00:00",
                "2023-01-04",
                "spam",
                "KR",
            ),
        ]

        cursor.executemany(
            """
            INSERT INTO blacklist_entries 
            (ip_address, source, is_active, created_at, updated_at, last_seen, reason, country)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            test_data,
        )

        conn.commit()
        conn.close()
        return temp_db_path

    @pytest.mark.asyncio
    def test_get_blacklist_summary_success(self, service):
        """Test successful blacklist summary retrieval"""
        service.blacklist_manager.get_active_ips.return_value = [
            "192.168.1.1",
            "192.168.1.2",
            "192.168.1.3",
        ]

        with mock.patch.object(
            service,
            "_get_source_counts_from_db",
            return_value={"regtech": 2, "secudium": 1},
        ):
            result = service.get_blacklist_summary()

            assert result["success"] is True
            assert result["summary"]["total_active_ips"] == 3
            assert result["summary"]["sources"]["regtech"] == 2
            assert result["summary"]["sources"]["secudium"] == 1
            assert result["summary"]["collection_enabled"] is True

    def test_get_blacklist_summary_no_manager(self, service):
        """Test blacklist summary when manager is unavailable"""
        service.blacklist_manager = None

        result = service.get_blacklist_summary()

        assert result["success"] is False
        assert "Blacklist manager not available" in result["error"]

    def test_get_blacklist_summary_exception(self, service):
        """Test blacklist summary with exception"""
        service.blacklist_manager.get_active_ips.side_effect = Exception(
            "Database error"
        )

        result = service.get_blacklist_summary()

        assert result["success"] is False
        assert "Database error" in result["error"]

    def test_get_source_counts_from_db_success(self, service, populated_db):
        """Test successful source counts retrieval from database"""
        service.blacklist_manager.db_path = populated_db

        result = service._get_source_counts_from_db()

        assert "regtech" in result
        assert "secudium" in result
        assert result["regtech"] == 1  # Only active IPs
        assert result["secudium"] == 2  # Only active IPs

    def test_get_source_counts_from_db_no_db_path(self, service):
        """Test source counts when database path is unavailable"""
        service.blacklist_manager = None

        result = service._get_source_counts_from_db()

        assert result == {}

    def test_get_source_counts_from_db_exception(self, service):
        """Test source counts with database exception"""
        service.blacklist_manager.db_path = "/nonexistent/path.db"

        result = service._get_source_counts_from_db()

        assert result == {}

    def test_get_daily_stats_success(self, service, populated_db):
        """Test successful daily statistics retrieval"""
        service.blacklist_manager.db_path = populated_db

        result = service.get_daily_stats(7)

        assert isinstance(result, list)
        if result:  # If data exists
            assert "date" in result[0]
            assert "total" in result[0]
            assert "sources" in result[0]

    def test_get_daily_stats_no_db(self, service):
        """Test daily stats when database is unavailable"""
        service.blacklist_manager = None

        result = service.get_daily_stats()

        assert result == []

    def test_get_daily_stats_exception(self, service):
        """Test daily stats with database exception"""
        service.blacklist_manager.db_path = "/nonexistent/path.db"

        result = service.get_daily_stats()

        assert result == []

    def test_get_monthly_stats_success(self, service, populated_db):
        """Test successful monthly statistics retrieval"""
        service.blacklist_manager.db_path = populated_db

        result = service.get_monthly_stats("2023-01-01", "2023-01-31")

        assert result["success"] is True
        assert "monthly_stats" in result
        assert "period" in result

    def test_get_monthly_stats_no_db(self, service):
        """Test monthly stats when database is unavailable"""
        service.blacklist_manager = None

        result = service.get_monthly_stats("2023-01-01", "2023-01-31")

        assert result["success"] is False
        assert "Database not available" in result["error"]

    def test_get_monthly_stats_exception(self, service):
        """Test monthly stats with database exception"""
        service.blacklist_manager.db_path = "/nonexistent/path.db"

        result = service.get_monthly_stats("2023-01-01", "2023-01-31")

        assert result["success"] is False
        assert "error" in result


if __name__ == "__main__":
    pytest.main([__file__])
