#!/usr/bin/env python3
"""
Unit tests for collection logs route endpoints
Tests collection logs retrieval and request data handling.
"""

import json
import unittest.mock as mock

import pytest

from .collection_routes_base import CollectionRoutesTestBase


class TestCollectionLogsRoutes(CollectionRoutesTestBase):
    """Test cases for collection logs route endpoints"""

    def test_api_collection_logs_success(self, client, mock_service):
        """Test successful collection logs retrieval"""
        with mock.patch("os.path.exists", return_value=False):  # No log files
            with mock.patch(
                "src.core.routes.collection_logs_routes.service", mock_service
            ):
                response = client.get("/api/collection/logs")

                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["success"] is True
                assert "logs" in data
                assert "count" in data

    def test_api_collection_logs_with_file(self, client, mock_service):
        """Test collection logs retrieval with log files"""
        log_content = [
            "2023-01-01 10:00:00 - REGTECH collection started\n",
            "2023-01-01 10:05:00 - Collection completed\n",
        ]

        with mock.patch("os.path.exists", return_value=True):
            with mock.patch(
                "builtins.open", mock.mock_open(read_data="".join(log_content))
            ):
                with mock.patch(
                    "src.core.routes.collection_logs_routes.service", mock_service
                ):
                    response = client.get("/api/collection/logs")

                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data["success"] is True
                    assert len(data["logs"]) > 0

    def test_api_collection_logs_exception(self, client, mock_service):
        """Test collection logs retrieval with exception"""
        mock_service.get_collection_logs.side_effect = Exception("Log error")

        with mock.patch("os.path.exists", return_value=False):
            with mock.patch(
                "src.core.routes.collection_logs_routes.service", mock_service
            ):
                response = client.get("/api/collection/logs")

                assert response.status_code == 500
                data = json.loads(response.data)
                assert data["success"] is False

    def test_get_realtime_logs_success(self, client, mock_service):
        """Test successful realtime logs retrieval"""
        with mock.patch("src.core.routes.collection_logs_routes.service", mock_service):
            response = client.get("/api/collection/logs/realtime")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "logs" in data
            assert "count" in data

    def test_get_realtime_logs_exception(self, client, mock_service):
        """Test realtime logs retrieval with exception"""
        mock_service.get_collection_logs.side_effect = Exception("Realtime error")

        with mock.patch("src.core.routes.collection_logs_routes.service", mock_service):
            response = client.get("/api/collection/logs/realtime")

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data["success"] is False

    def test_get_collection_logs_with_limit(self, client, mock_service):
        """Test collection logs retrieval with limit parameter"""
        with mock.patch("src.core.routes.collection_logs_routes.service", mock_service):
            response = client.get("/api/collection/logs?limit=10")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            # Verify that the service was called with the correct limit
            mock_service.get_collection_logs.assert_called()

    def test_request_data_handling_json(self, client, mock_service, mock_container):
        """Test request data handling for JSON content"""
        mock_service.trigger_regtech_collection.return_value = {"success": True}

        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post(
                    "/api/collection/regtech/trigger",
                    json={"start_date": "2023-01-01"},
                    content_type="application/json",
                )

                assert response.status_code == 200
                # Verify the service was called with the extracted date
                mock_service.trigger_regtech_collection.assert_called_with(
                    start_date="2023-01-01", end_date=None
                )

    def test_request_data_handling_form(self, client, mock_service, mock_container):
        """Test request data handling for form content"""
        mock_service.trigger_regtech_collection.return_value = {"success": True}

        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post(
                    "/api/collection/regtech/trigger",
                    data={"start_date": "2023-01-01"},
                    content_type="application/x-www-form-urlencoded",
                )

                assert response.status_code == 200
                # Verify the service was called with the extracted date
                mock_service.trigger_regtech_collection.assert_called_with(
                    start_date="2023-01-01", end_date=None
                )

    def test_progress_tracker_integration(self, client, mock_service, mock_container):
        """Test progress tracker integration in collection trigger"""
        progress_tracker = mock_container.get("progress_tracker")
        mock_service.trigger_regtech_collection.return_value = {"success": True}

        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post("/api/collection/regtech/trigger")

                assert response.status_code == 200
                # Verify progress tracker methods were called
                progress_tracker.start_collection.assert_called_with("regtech")
                progress_tracker.get_progress.assert_called_with("regtech")
