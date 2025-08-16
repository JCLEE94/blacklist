#!/usr/bin/env python3
"""
Unit tests for collection status route endpoints
Tests collection status retrieval, enablement/disablement, and configuration.
"""

import json
import unittest.mock as mock

import pytest

from .collection_routes_base import CollectionRoutesTestBase


class TestCollectionStatusRoutes(CollectionRoutesTestBase):
    """Test cases for collection status route endpoints"""

    def test_get_collection_status_success(self, client, mock_service):
        """Test successful collection status retrieval"""
        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            response = client.get("/api/collection/status")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["enabled"] is True
            assert data["collection_enabled"] is True
            assert data["status"] == "active"
            assert "stats" in data
            assert "daily_collection" in data

    def test_get_collection_status_disabled(self, client, mock_service):
        """Test collection status when collection is disabled"""
        mock_service.collection_enabled = False
        mock_service.get_collection_status.return_value["collection_enabled"] = False

        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            response = client.get("/api/collection/status")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["enabled"] is False
            assert data["status"] == "inactive"

    def test_get_collection_status_exception(self, client, mock_service):
        """Test collection status with exception"""
        mock_service.get_collection_status.side_effect = Exception("Service error")

        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            response = client.get("/api/collection/status")

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data["enabled"] is False
            assert data["status"] == "error"
            assert "error" in data

    def test_enable_collection_success(self, client, mock_service, mock_container):
        """Test successful collection enablement"""
        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_status_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post(
                    "/api/collection/enable", json={"clear_data": True}
                )

                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["success"] is True
                assert data["collection_enabled"] is True
                mock_service.add_collection_log.assert_called()

    def test_enable_collection_no_manager(self, client, mock_service):
        """Test collection enablement when manager is unavailable"""
        mock_container = mock.Mock()
        mock_container.get.return_value = None

        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_status_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post("/api/collection/enable")

                assert response.status_code == 500
                data = json.loads(response.data)
                assert data["success"] is False
                assert "Collection manager not available" in data["error"]

    def test_enable_collection_exception(self, client, mock_service, mock_container):
        """Test collection enablement with exception"""
        collection_manager = mock_container.get("collection_manager")
        collection_manager.enable_collection.side_effect = Exception("Enable failed")

        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_status_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post("/api/collection/enable")

                assert response.status_code == 500
                data = json.loads(response.data)
                assert data["success"] is False

    def test_disable_collection_success(self, client, mock_service, mock_container):
        """Test successful collection disablement"""
        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_status_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post("/api/collection/disable")

                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["success"] is True
                mock_service.add_collection_log.assert_called()

    def test_disable_collection_no_manager(self, client, mock_service):
        """Test collection disablement when manager is unavailable"""
        mock_container = mock.Mock()
        mock_container.get.return_value = None

        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_status_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post("/api/collection/disable")

                assert response.status_code == 500
                data = json.loads(response.data)
                assert data["success"] is False

    def test_collection_statistics_success(self, client, mock_service):
        """Test successful collection statistics retrieval"""
        mock_service.get_source_statistics.return_value = {
            "regtech": {"total": 50, "active": 45},
            "secudium": {"total": 30, "active": 25},
        }

        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            response = client.get("/api/collection/statistics")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "daily_stats" in data
            assert "source_stats" in data
            assert "summary" in data

    def test_collection_statistics_exception(self, client, mock_service):
        """Test collection statistics with exception"""
        mock_service.get_daily_collection_stats.side_effect = Exception("Stats error")

        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_status_routes.create_error_response",
                return_value={"error": "Stats error"},
            ):
                response = client.get("/api/collection/statistics")

                assert response.status_code == 500

    def test_get_collection_intervals_success(self, client, mock_service):
        """Test successful collection intervals retrieval"""
        mock_service.get_collection_intervals.return_value = {
            "regtech_days": 90,
            "secudium_days": 3,
        }

        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            response = client.get("/api/collection/intervals")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert data["regtech_days"] == 90
            assert data["secudium_days"] == 3

    def test_update_collection_intervals_success(self, client, mock_service):
        """Test successful collection intervals update"""
        mock_service.update_collection_intervals = mock.Mock()

        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            response = client.post(
                "/api/collection/intervals",
                json={"regtech_days": 120, "secudium_days": 5},
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            mock_service.update_collection_intervals.assert_called_with(120, 5)

    def test_update_collection_intervals_invalid_regtech(self, client, mock_service):
        """Test collection intervals update with invalid REGTECH days"""
        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            response = client.post(
                "/api/collection/intervals",
                json={"regtech_days": 400, "secudium_days": 5},
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "REGTECH 수집 간격" in data["error"]

    def test_update_collection_intervals_invalid_secudium(self, client, mock_service):
        """Test collection intervals update with invalid SECUDIUM days"""
        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            response = client.post(
                "/api/collection/intervals",
                json={"regtech_days": 90, "secudium_days": 50},
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "SECUDIUM 수집 간격" in data["error"]