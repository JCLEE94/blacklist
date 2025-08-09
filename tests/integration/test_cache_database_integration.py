"""
Cache and database integration tests

Tests cache behavior, database operations, and performance characteristics.
"""

import sqlite3
import threading
import time
from datetime import datetime
from unittest.mock import patch

import pytest

from src.core.unified_service import UnifiedBlacklistService

from .fixtures import IntegrationTestFixtures


class TestCacheDatabaseIntegration(IntegrationTestFixtures):
    """Test cache and database integration"""

    @pytest.fixture
    def service(self, mock_container):
        """Create service instance with mock container"""
        with patch(
            "src.core.services.unified_service_core.get_container",
            return_value=mock_container,
        ):
            service = UnifiedBlacklistService()
            service.container = mock_container
            service.blacklist_manager = mock_container.get("blacklist_manager")
            service.cache = mock_container.get("cache_manager")
            service.collection_manager = mock_container.get("collection_manager")
            service.regtech_collector = mock_container.get("regtech_collector")
            return service

    def test_cache_invalidation_on_collection(self, service):
        """Test cache is properly invalidated after collection"""
        # Set some cache values
        service.cache.get.return_value = {"cached": "data"}

        # Trigger collection
        service.trigger_regtech_collection()

        # Verify cache operations
        cache_calls = service.cache.delete.call_args_list
        assert len(cache_calls) > 0

        # Check specific cache keys were invalidated
        deleted_keys = [call[0][0] for call in cache_calls]
        assert any("active_ips" in key for key in deleted_keys)
        assert any("fortigate" in key for key in deleted_keys)

    def test_cache_fallback_behavior(self, service):
        """Test service behavior when cache is unavailable"""
        # Make cache raise errors
        service.cache.get.side_effect = Exception("Redis connection failed")
        service.cache.set.side_effect = Exception("Redis connection failed")

        # Service should still function
        status = service.get_system_health()
        assert "total_ips" in status
        assert "active_ips" in status

        # Data should come from blacklist manager
        service.blacklist_manager.get_all_ips.assert_called()

    def test_database_transaction_handling(self, service, temp_db):
        """Test database transaction handling during collection"""
        # Create real database connection
        conn = sqlite3.connect(temp_db)

        # Mock blacklist manager to use real DB operations
        def add_ip_to_db(ip_data):
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO blacklist_ip (ip_address, source, detection_date, reason)
                VALUES (?, ?, ?, ?)
            """,
                (
                    ip_data["ip"],
                    ip_data["source"],
                    ip_data["detection_date"],
                    ip_data.get("reason"),
                ),
            )
            conn.commit()
            return True

        service.blacklist_manager.add_ip.side_effect = add_ip_to_db

        # Trigger collection
        result = service.trigger_regtech_collection()

        # Verify data in database
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM blacklist_ip")
        count = cursor.fetchone()[0]

        assert count > 0
        assert result["success"] is True

        conn.close()

    def test_bulk_operation_performance(self, service):
        """Test performance of bulk IP operations"""
        # Generate large number of IPs
        large_ip_list = [
            {
                "ip": f"10.0.{i//256}.{i%256}",
                "source": "regtech",
                "detection_date": datetime.now(),
                "reason": "Bulk test",
            }
            for i in range(1000)
        ]

        service.regtech_collector.collect_from_web.return_value = large_ip_list

        start_time = time.time()

        result = service.trigger_regtech_collection()

        duration = time.time() - start_time

        # Should handle 1000 IPs reasonably fast
        assert duration < 5.0  # Less than 5 seconds
        assert result["success"] is True
        assert result["collected"] == 1000

    def test_concurrent_service_access(self, service):
        """Test service handles concurrent access correctly"""
        results = []
        errors = []

        def access_service():
            try:
                # Multiple operations
                health = service.get_system_health()
                status = service.get_collection_status()
                results.append({"health": health, "status": status})
            except Exception as e:
                errors.append(str(e))

        # Create threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=access_service)
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0
        assert len(results) == 10

        # All results should be consistent
        assert all(r["status"]["enabled"] for r in results)
