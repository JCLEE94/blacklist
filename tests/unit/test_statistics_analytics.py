#!/usr/bin/env python3
"""
Unit tests for Statistics Analytics functionality
Tests analytics, summary, and trends functionality.
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
def create_test_analytics_service():
    """Factory function to create test service with proper initialization"""

    class TestAnalyticsService(StatisticsServiceMixin):
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

    service = TestAnalyticsService()
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


class TestStatisticsAnalytics:
    """Test class for statistics analytics functionality"""

    @pytest.fixture
    def service(self):
        """Create service instance for testing"""
        return create_test_analytics_service()

    @pytest.fixture
    def populated_db(self):
        """Create a populated test database"""
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        db_path = db_file.name
        db_file.close()

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create blacklist_ips table
        cursor.execute(
            """
            CREATE TABLE blacklist_ips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                source TEXT NOT NULL,
                threat_level TEXT DEFAULT 'medium',
                first_seen TEXT,
                last_seen TEXT,
                is_active BOOLEAN DEFAULT 1,
                detection_count INTEGER DEFAULT 1
            )
            """
        )

        # Insert test data
        test_data = [
            ("192.168.1.1", "regtech", "high", "2023-01-01", "2023-01-01", 1, 5),
            ("192.168.1.2", "secudium", "medium", "2023-01-02", "2023-01-02", 1, 3),
            ("192.168.1.3", "secudium", "low", "2023-01-03", "2023-01-03", 1, 2),
            ("192.168.1.4", "regtech", "high", "2023-01-04", "2023-01-04", 0, 1),
        ]

        cursor.executemany(
            """
            INSERT INTO blacklist_ips 
            (ip_address, source, threat_level, first_seen, last_seen, is_active, detection_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            test_data,
        )

        conn.commit()
        conn.close()

        yield db_path

        # Cleanup
        os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_get_statistics_success(self, service):
        """Test successful statistics retrieval"""
        service.blacklist_manager.get_system_health.return_value = {
            "status": "healthy",
            "sources": {"regtech": 100, "secudium": 50},
            "last_update": "2023-01-01T10:00:00",
        }
        service.blacklist_manager.get_active_ips.return_value = [
            "192.168.1.1",
            "192.168.1.2",
        ]

        result = await service.get_statistics()

        assert result["success"] is True
        assert "statistics" in result
        assert result["statistics"]["total_ips"] == 2
        assert result["statistics"]["status"] == "healthy"
        assert result["statistics"]["service"]["name"] == "blacklist"
        assert result["statistics"]["service"]["running"] is True

    @pytest.mark.asyncio
    async def test_get_statistics_no_manager(self, service):
        """Test statistics retrieval when blacklist manager is unavailable"""
        service.blacklist_manager = None

        result = await service.get_statistics()

        assert result["success"] is False
        assert "Blacklist manager not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_get_statistics_exception(self, service):
        """Test statistics retrieval with exception"""
        service.blacklist_manager.get_system_health.side_effect = Exception(
            "Health check failed"
        )

        result = await service.get_statistics()

        assert result["success"] is False
        assert "Health check failed" in result["error"]

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

    def test_get_analytics_summary(self, service):
        """Test analytics summary functionality"""
        mock_data = {
            "total_entries": 1000,
            "active_entries": 950,
            "inactive_entries": 50,
            "threat_levels": {"high": 100, "medium": 500, "low": 350},
            "sources": {"regtech": 600, "secudium": 400},
        }

        with mock.patch.object(
            service,
            "_get_detailed_analytics",
            return_value=mock_data,
        ):
            result = service.get_analytics_summary(period="7d")

            assert result["success"] is True
            assert result["analytics"]["total_entries"] == 1000
            assert result["analytics"]["active_entries"] == 950
            assert result["analytics"]["threat_levels"]["high"] == 100
            assert result["analytics"]["sources"]["regtech"] == 600

    def test_get_analytics_summary_exception(self, service):
        """Test analytics summary with exception"""
        with mock.patch.object(
            service,
            "_get_detailed_analytics",
            side_effect=Exception("Analytics error"),
        ):
            result = service.get_analytics_summary()

            assert result["success"] is False
            assert "Analytics error" in result["error"]

    def test_get_source_statistics_success(self, service, populated_db):
        """Test successful source statistics retrieval"""
        service.blacklist_manager.db_path = populated_db

        result = service.get_source_statistics("regtech")

        assert result["success"] is True
        assert result["statistics"]["source"] == "regtech"
        assert result["statistics"]["total_entries"] == 2
        assert result["statistics"]["active_entries"] == 1

    def test_get_source_statistics_no_db(self, service):
        """Test source statistics when database is unavailable"""
        service.blacklist_manager = None

        result = service.get_source_statistics("regtech")

        assert result["success"] is False
        assert "Database not available" in result["error"]

    def test_get_source_statistics_exception(self, service):
        """Test source statistics with exception"""
        service.blacklist_manager.db_path = "/invalid/path"

        result = service.get_source_statistics("regtech")

        assert result["success"] is False
        assert "error" in result

    def test_get_trends_analysis(self, service, populated_db):
        """Test trends analysis functionality"""
        service.blacklist_manager.db_path = populated_db

        result = service.get_trends_analysis(days=7)

        assert result["success"] is True
        assert "trends" in result
        assert "daily_counts" in result["trends"]
        assert "trend_direction" in result["trends"]
        assert result["trends"]["period_days"] == 7

    def test_get_trends_analysis_exception(self, service):
        """Test trends analysis with exception"""
        service.blacklist_manager = None

        result = service.get_trends_analysis()

        assert result["success"] is False
        assert "error" in result
