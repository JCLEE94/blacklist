#!/usr/bin/env python3
"""
Unit tests for StatisticsServiceMixin
Tests analytics, statistics, and reporting functionality.
"""

import os
import sqlite3
import tempfile
import unittest.mock as mock
from datetime import datetime, timedelta

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

    def test_get_analytics_summary(self, service):
        """Test analytics summary retrieval"""
        with mock.patch.object(
            service, "get_blacklist_summary", return_value={"success": True}
        ):
            with mock.patch.object(service, "get_daily_stats", return_value=[]):
                with mock.patch.object(
                    service, "get_source_statistics", return_value={}
                ):
                    result = service.get_analytics_summary(7)

                    assert "period_days" in result
                    assert result["period_days"] == 7
                    assert "current_stats" in result
                    assert "daily_trends" in result
                    assert "source_breakdown" in result

    def test_get_analytics_summary_exception(self, service):
        """Test analytics summary with exception"""
        with mock.patch.object(
            service, "get_blacklist_summary", side_effect=Exception("Summary failed")
        ):
            result = service.get_analytics_summary()

            assert result["success"] is False
            assert "Summary failed" in result["error"]

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

    def test_get_source_statistics_success(self, service, populated_db):
        """Test successful source statistics retrieval"""
        service.blacklist_manager.db_path = populated_db

        result = service.get_source_statistics()

        assert isinstance(result, dict)
        if result:  # If data exists
            for source, stats in result.items():
                assert "total_ips" in stats
                assert "active_ips" in stats
                assert "active_percentage" in stats

    def test_get_source_statistics_no_db(self, service):
        """Test source statistics when database is unavailable"""
        service.blacklist_manager = None

        result = service.get_source_statistics()

        assert result == {}

    def test_get_source_statistics_exception(self, service):
        """Test source statistics with database exception"""
        service.blacklist_manager.db_path = "/nonexistent/path.db"

        result = service.get_source_statistics()

        assert result == {}

    def test_get_daily_collection_stats_success(self, service):
        """Test successful daily collection statistics"""
        # Mock collection logs with various dates and sources
        mock_logs = [
            {
                "timestamp": datetime.now().isoformat(),
                "source": "regtech",
                "action": "collection",
            },
            {
                "timestamp": (datetime.now() - timedelta(days=1)).isoformat(),
                "source": "secudium",
                "action": "collection",
            },
            {
                "timestamp": datetime.now().isoformat(),
                "source": "regtech",
                "action": "collection",
                "error": "Failed",
            },
        ]

        with mock.patch.object(service, "get_collection_logs", return_value=mock_logs):
            result = service.get_daily_collection_stats()

            assert isinstance(result, list)
            assert len(result) <= 30  # Maximum 30 days
            if result:
                assert "date" in result[0]
                assert "collections" in result[0]
                assert "successful" in result[0]
                assert "failed" in result[0]

    def test_get_daily_collection_stats_exception(self, service):
        """Test daily collection stats with exception"""
        with mock.patch.object(
            service, "get_collection_logs", side_effect=Exception("Log error")
        ):
            result = service.get_daily_collection_stats()

            assert result == []

    def test_get_blacklist_with_metadata_success(self, service, populated_db):
        """Test successful blacklist retrieval with metadata"""
        service.blacklist_manager.db_path = populated_db

        result = service.get_blacklist_with_metadata(limit=10, offset=0)

        assert result["success"] is True
        assert "ips" in result
        assert "pagination" in result
        assert result["pagination"]["limit"] == 10
        assert result["pagination"]["offset"] == 0

    def test_get_blacklist_with_metadata_source_filter(self, service, populated_db):
        """Test blacklist retrieval with source filter"""
        service.blacklist_manager.db_path = populated_db

        result = service.get_blacklist_with_metadata(source_filter="regtech")

        assert result["success"] is True
        assert result["filter"]["source"] == "regtech"

    def test_get_blacklist_with_metadata_no_db(self, service):
        """Test blacklist with metadata when database is unavailable"""
        service.blacklist_manager = None

        result = service.get_blacklist_with_metadata()

        assert result["success"] is False
        assert "Database not available" in result["error"]

    def test_search_ip_success(self, service):
        """Test successful IP search"""
        service.blacklist_manager.search_ip.return_value = {
            "found": True,
            "ip": "192.168.1.1",
            "threat_level": "high",
        }

        result = service.search_ip("192.168.1.1")

        assert result["success"] is True
        assert result["ip"] == "192.168.1.1"
        assert result["result"]["found"] is True

    def test_search_ip_no_manager(self, service):
        """Test IP search when manager is unavailable"""
        service.blacklist_manager = None

        result = service.search_ip("192.168.1.1")

        assert result["success"] is False
        assert "Blacklist manager not available" in result["error"]

    def test_search_ip_exception(self, service):
        """Test IP search with exception"""
        service.blacklist_manager.search_ip.side_effect = Exception("Search failed")

        result = service.search_ip("192.168.1.1")

        assert result["success"] is False
        assert "Search failed" in result["error"]

    def test_search_batch_ips(self, service):
        """Test batch IP search"""
        ips = ["192.168.1.1", "192.168.1.2", "192.168.1.3"]

        with mock.patch.object(service, "search_ip") as mock_search:
            mock_search.return_value = {"success": True, "found": False}

            result = service.search_batch_ips(ips)

            assert len(result) == 3
            assert mock_search.call_count == 3
            for ip in ips:
                assert ip in result

    def test_format_for_fortigate_success(self, service):
        """Test successful FortiGate format conversion"""
        ips = ["192.168.1.1", "192.168.1.2"]

        result = service.format_for_fortigate(ips)

        assert "version" in result
        assert "timestamp" in result
        assert "total_entries" in result
        assert "entries" in result
        assert result["total_entries"] == 2
        assert len(result["entries"]) == 2

        for entry in result["entries"]:
            assert "ip" in entry
            assert entry["type"] == "blacklist"
            assert entry["action"] == "deny"

    def test_format_for_fortigate_exception(self, service):
        """Test FortiGate format conversion with exception"""
        # Create a problematic input that causes an exception
        with mock.patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.side_effect = Exception("DateTime error")

            result = service.format_for_fortigate(["192.168.1.1"])

            assert result["success"] is False
            assert "DateTime error" in result["error"]

    def test_get_blacklist_paginated_success(self, service):
        """Test successful paginated blacklist retrieval"""
        with mock.patch.object(service, "get_blacklist_with_metadata") as mock_get:
            mock_get.return_value = {"success": True, "ips": []}

            result = service.get_blacklist_paginated(page=2, per_page=50)

            assert result["success"] is True
            mock_get.assert_called_once_with(limit=50, offset=50, source_filter=None)

    def test_get_blacklist_paginated_with_source_filter(self, service):
        """Test paginated blacklist retrieval with source filter"""
        with mock.patch.object(service, "get_blacklist_with_metadata") as mock_get:
            mock_get.return_value = {"success": True, "ips": []}

            result = service.get_blacklist_paginated(
                page=1, per_page=25, source_filter="regtech"
            )

            mock_get.assert_called_once_with(
                limit=25, offset=0, source_filter="regtech"
            )

    def test_get_blacklist_paginated_exception(self, service):
        """Test paginated blacklist retrieval with exception"""
        with mock.patch.object(
            service,
            "get_blacklist_with_metadata",
            side_effect=Exception("Pagination error"),
        ):
            result = service.get_blacklist_paginated()

            assert result["success"] is False
            assert "Pagination error" in result["error"]

    def test_pagination_calculation(self, service):
        """Test pagination offset calculation"""
        with mock.patch.object(service, "get_blacklist_with_metadata") as mock_get:
            mock_get.return_value = {"success": True}

            # Test different page and per_page combinations
            test_cases = [
                (1, 10, 0),  # Page 1, offset 0
                (2, 10, 10),  # Page 2, offset 10
                (3, 25, 50),  # Page 3, offset 50
                (5, 100, 400),  # Page 5, offset 400
            ]

            for page, per_page, expected_offset in test_cases:
                service.get_blacklist_paginated(page=page, per_page=per_page)
                mock_get.assert_called_with(
                    limit=per_page, offset=expected_offset, source_filter=None
                )


if __name__ == "__main__":
    pytest.main([__file__])
