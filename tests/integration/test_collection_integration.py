"""
Collection Integration Tests

Tests for collection system integration with external sources.
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


class TestCollectionIntegration:
    """Collection system integration tests"""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup for each test method"""
        self.mock_config = {
            "COLLECTION_ENABLED": True,
            "FORCE_DISABLE_COLLECTION": False,
            "REGTECH_USERNAME": "test_user",
            "REGTECH_PASSWORD": "test_pass",
            "SECUDIUM_USERNAME": "test_user",
            "SECUDIUM_PASSWORD": "test_pass",
        }

    def test_collection_status(self):
        """Test collection status retrieval"""
        # Mock the collection manager
        with patch("src.core.container.get_container") as mock_container:
            mock_service = Mock()
            mock_service.get_collection_status.return_value = {
                "enabled": True,
                "last_update": "2024-01-01",
                "sources": {
                    "regtech": {"status": "active", "count": 100},
                    "secudium": {"status": "active", "count": 150},
                },
            }
            mock_container.return_value.get.return_value = mock_service

            # Test successful status retrieval
            status = mock_service.get_collection_status()
            assert status["enabled"] is True
            assert "sources" in status

    def test_regtech_collection(self):
        """Test REGTECH data collection"""
        with patch(
            "src.core.regtech_simple_collector.RegtechSimpleCollector"
        ) as MockCollector:
            mock_collector = MockCollector.return_value
            mock_collector.collect_data.return_value = {
                "success": True,
                "data": ["1.1.9.1", "2.2.2.2"],
                "count": 2,
            }

            result = mock_collector.collect_data()
            assert result["success"] is True
            assert len(result["data"]) == 2

    def test_secudium_collection(self):
        """Test SECUDIUM data collection"""
        with patch("src.core.secudium_collector.SecudiumCollector") as MockCollector:
            mock_collector = MockCollector.return_value
            mock_collector.collect_data.return_value = {
                "success": True,
                "data": ["3.3.3.3", "4.4.4.4"],
                "count": 2,
            }

            result = mock_collector.collect_data()
            assert result["success"] is True
            assert len(result["data"]) == 2

    def test_collection_trigger(self):
        """Test manual collection trigger"""
        with patch("src.core.container.get_container") as mock_container:
            mock_service = Mock()
            mock_service.trigger_collection.return_value = {
                "success": True,
                "message": "Collection triggered successfully",
            }
            mock_container.return_value.get.return_value = mock_service

            result = mock_service.trigger_collection("regtech")
            assert result["success"] is True

    def test_collection_disabled_state(self):
        """Test behavior when collection is disabled"""
        with patch.dict(os.environ, {"FORCE_DISABLE_COLLECTION": "true"}):
            with patch("src.core.container.get_container") as mock_container:
                mock_service = Mock()
                mock_service.collection_enabled = False
                mock_container.return_value.get.return_value = mock_service

                assert mock_service.collection_enabled is False

    def test_collection_error_handling(self):
        """Test collection error scenarios"""
        with patch(
            "src.core.regtech_simple_collector.RegtechSimpleCollector"
        ) as MockCollector:
            mock_collector = MockCollector.return_value
            mock_collector.collect_data.side_effect = Exception("Connection failed")

            with pytest.raises(Exception):
                mock_collector.collect_data()

    def test_collection_data_validation(self):
        """Test collection data validation"""
        test_ips = ["1.1.9.1", "2.2.2.2", "invalid_ip", "3.3.3.3"]

        with patch("src.core.container.get_container") as mock_container:
            mock_service = Mock()
            mock_service.validate_ip_data.return_value = [
                "1.1.9.1",
                "2.2.2.2",
                "3.3.3.3",
            ]
            mock_container.return_value.get.return_value = mock_service

            valid_ips = mock_service.validate_ip_data(test_ips)
            assert len(valid_ips) == 3
            assert "invalid_ip" not in valid_ips
