#!/usr/bin/env python3
"""
Unit tests for collection trigger route endpoints
Tests collection triggering and progress monitoring endpoints.
"""

import json
import unittest.mock as mock
from datetime import datetime

import pytest

from .collection_routes_base import CollectionRoutesTestBase


class TestCollectionTriggerRoutes(CollectionRoutesTestBase):
    """Test cases for collection trigger route endpoints"""

    def test_trigger_regtech_collection_success(
        self, client, mock_service, mock_container
    ):
        """Test successful REGTECH collection trigger"""
        mock_service.trigger_regtech_collection.return_value = {
            "success": True,
            "message": "Collection started",
        }

        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post(
                    "/api/collection/regtech/trigger",
                    json={"start_date": "2023-01-01", "end_date": "2023-01-31"},
                )

                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["success"] is True
                assert data["source"] == "regtech"
                mock_service.add_collection_log.assert_called()

    def test_trigger_regtech_collection_failure(
        self, client, mock_service, mock_container
    ):
        """Test REGTECH collection trigger failure"""
        mock_service.trigger_regtech_collection.return_value = {
            "success": False,
            "message": "Collection failed",
            "error": "Network error",
        }

        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post("/api/collection/regtech/trigger")

                assert response.status_code == 500
                data = json.loads(response.data)
                assert data["success"] is False

    def test_trigger_regtech_collection_exception(
        self, client, mock_service, mock_container
    ):
        """Test REGTECH collection trigger with exception"""
        mock_service.trigger_regtech_collection.side_effect = Exception("Trigger error")

        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post("/api/collection/regtech/trigger")

                assert response.status_code == 500
                data = json.loads(response.data)
                assert data["success"] is False
                assert "error" in data

    def test_trigger_secudium_collection_disabled(
        self, client, mock_service, mock_container
    ):
        """Test SECUDIUM collection trigger (disabled)"""
        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post("/api/collection/secudium/trigger")

                assert response.status_code == 503
                data = json.loads(response.data)
                assert data["success"] is False
                assert data["disabled"] is True
                assert "SECUDIUM 수집은 현재 비활성화" in data["message"]

    def test_trigger_secudium_collection_exception(
        self, client, mock_service, mock_container
    ):
        """Test SECUDIUM collection trigger with exception"""
        mock_container.get.side_effect = Exception("Container error")

        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post("/api/collection/secudium/trigger")

                assert response.status_code == 500
                data = json.loads(response.data)
                assert data["success"] is False

    def test_get_collection_progress_success(
        self, client, mock_service, mock_container
    ):
        """Test successful collection progress retrieval"""
        progress_tracker = mock_container.get("progress_tracker")
        progress_tracker.get_progress.return_value = {
            "status": "running",
            "current_item": 25,
            "total_items": 100,
            "percentage": 25.0,
            "message": "Processing data",
            "started_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.get("/api/collection/progress/regtech")

                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["success"] is True
                assert data["source"] == "regtech"
                assert data["progress"]["status"] == "running"
                assert data["progress"]["percentage"] == 25.0

    def test_get_collection_progress_no_tracker(self, client, mock_service):
        """Test collection progress when tracker is unavailable"""
        mock_container = mock.Mock()
        mock_container.get.return_value = None

        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.get("/api/collection/progress/regtech")

                assert response.status_code == 503
                data = json.loads(response.data)
                assert data["success"] is False

    def test_get_collection_progress_no_progress(
        self, client, mock_service, mock_container
    ):
        """Test collection progress when no progress is available"""
        progress_tracker = mock_container.get("progress_tracker")
        progress_tracker.get_progress.return_value = None

        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.get("/api/collection/progress/regtech")

                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["success"] is True
                assert data["progress"] is None
