#!/usr/bin/env python3
"""
Flask integration tests for structured logging

Tests Flask-specific logging features including request logging,
Flask integration setup, and API endpoints.
"""

import json
import logging
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

# Test imports
from src.utils.structured_logging import get_logger, log_manager, setup_request_logging


class TestFlaskIntegration:
    """Test Flask integration functionality"""

    def setup_method(self):
        """Setup test environment"""
        self.mock_app = Mock()
        self.mock_app.before_request = Mock()
        self.mock_app.after_request = Mock()
        self.mock_app.route = Mock()

    @patch("src.utils.structured_logging.get_logger")
    def test_setup_request_logging(self, mock_get_logger):
        """Test setup_request_logging function"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        setup_request_logging(self.mock_app)

        # Should register before_request and after_request handlers
        self.mock_app.before_request.assert_called()
        self.mock_app.after_request.assert_called()

        # Should register API routes
        assert self.mock_app.route.call_count >= 2

    @patch("src.utils.structured_logging.g")
    @patch("src.utils.structured_logging.request")
    @patch("src.utils.structured_logging.get_logger")
    def test_before_request_handler(self, mock_get_logger, mock_request, mock_g):
        """Test before_request handler functionality"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Setup mock request
        mock_request.method = "POST"
        mock_request.path = "/api/test"
        mock_request.remote_addr = "192.168.1.100"

        # Setup mock g without existing attributes
        type(mock_g).request_id = PropertyDescriptor()
        type(mock_g).start_time = PropertyDescriptor()
        type(mock_g).log_start_time = PropertyDescriptor()

        # Call setup to get the handler
        setup_request_logging(self.mock_app)

        # Get the before_request handler
        before_handler = self.mock_app.before_request.call_args[0][0]

        # Call the handler
        before_handler()

        # Should log request start
        mock_logger.info.assert_called()

    @patch("src.utils.structured_logging.g")
    @patch("src.utils.structured_logging.get_logger")
    def test_after_request_handler(self, mock_get_logger, mock_g):
        """Test after_request handler functionality"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Setup mock g with log_start_time
        mock_g.log_start_time = datetime.utcnow() - timedelta(seconds=0.5)
        mock_g.request_id = "test-request-123"

        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200

        # Call setup to get the handler
        setup_request_logging(self.mock_app)

        # Get the after_request handler
        after_handler = self.mock_app.after_request.call_args[0][0]

        # Call the handler
        result = after_handler(mock_response)

        # Should return the same response
        assert result is mock_response

        # Should log request completion
        mock_logger.info.assert_called()

    @patch("src.utils.structured_logging.request")
    @patch("src.utils.structured_logging.log_manager")
    def test_log_stats_api_endpoint(self, mock_log_manager, mock_request):
        """Test log stats API endpoint"""
        # Setup mock stats
        mock_stats = {"logger1": {"stats": {"info": 5}}}
        mock_log_manager.get_all_stats.return_value = mock_stats

        # Call setup to register routes
        setup_request_logging(self.mock_app)

        # Find the stats endpoint handler
        route_calls = self.mock_app.route.call_args_list
        stats_handler = None
        for call in route_calls:
            if "/api/logs/stats" in str(call):
                stats_handler = call[0][0]  # The decorator returns the function
                break

        # The route decorator should have been called
        assert any("/api/logs/stats" in str(call) for call in route_calls)

    @patch("src.utils.structured_logging.request")
    @patch("src.utils.structured_logging.log_manager")
    def test_search_logs_api_endpoint(self, mock_log_manager, mock_request):
        """Test search logs API endpoint"""
        # Setup mock request args
        mock_request.args.get.side_effect = lambda key, default=None: {
            "q": "test_query",
            "limit": "50",
        }.get(key, default)

        # Setup mock search results
        mock_results = {"logger1": [{"message": "test log"}]}
        mock_log_manager.search_all_logs.return_value = mock_results

        # Call setup to register routes
        setup_request_logging(self.mock_app)

        # Find the search endpoint handler
        route_calls = self.mock_app.route.call_args_list
        search_handler = None
        for call in route_calls:
            if "/api/logs/search" in str(call):
                search_handler = call[0][0]
                break

        # The route decorator should have been called
        assert any("/api/logs/search" in str(call) for call in route_calls)


class PropertyDescriptor:
    """Helper class for mocking property assignment"""

    def __init__(self):
        self.value = None

    def __get__(self, obj, objtype=None):
        return self.value

    def __set__(self, obj, value):
        self.value = value


if __name__ == "__main__":
    pytest.main([__file__])
