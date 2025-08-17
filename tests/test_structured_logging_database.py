#!/usr/bin/env python3
"""
Database integration tests for structured logging

Tests database logging features and performance optimizations.
"""

import os
import sqlite3
import tempfile
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Test imports
from src.utils.structured_logging import (
    StructuredLogger,
)


class TestDatabaseIntegration:
    """Test database integration features"""

    def setup_method(self):
        """Setup test environment"""
        self.test_db_path = tempfile.mktemp(suffix=".db")
        self.structured_logger = StructuredLogger("db_test_logger")

    def teardown_method(self):
        """Cleanup test environment"""
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except PermissionError:
                pass

    @patch('src.utils.structured_logging.sqlite3.connect')
    def test_save_to_db_success(self, mock_connect):
        """Test successful database saving"""
        # Setup mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_connect.return_value.__exit__ = Mock(return_value=None)
        
        # Enable DB logging
        self.structured_logger.enable_db_logging(True)
        
        # Create test record
        record = {
            "timestamp": "2023-01-01T12:00:00",
            "level": "INFO",
            "name": "test_logger",
            "message": "Test message",
            "context": {"key": "value"}
        }
        
        # Call _save_to_db
        self.structured_logger._save_to_db(record)
        
        # Should execute table creation and insert
        assert mock_cursor.execute.call_count >= 2
        mock_conn.commit.assert_called_once()

    def test_save_to_db_disabled(self):
        """Test database saving when disabled"""
        # DB logging is disabled by default
        record = {"level": "INFO", "message": "Test"}
        
        # Should not raise exception when disabled
        self.structured_logger._save_to_db(record)

    @patch('src.utils.structured_logging.sqlite3.connect')
    def test_save_to_db_exception_handling(self, mock_connect):
        """Test database saving exception handling"""
        # Setup mock to raise exception
        mock_connect.side_effect = sqlite3.OperationalError("Database error")
        
        # Enable DB logging
        self.structured_logger.enable_db_logging(True)
        
        record = {"level": "INFO", "message": "Test"}
        
        # Should handle exception gracefully
        self.structured_logger._save_to_db(record)

    def test_enable_db_logging(self):
        """Test enabling database logging"""
        self.structured_logger.enable_db_logging(True)
        assert hasattr(self.structured_logger, 'db_enabled')
        assert self.structured_logger.db_enabled is True
        
        self.structured_logger.enable_db_logging(False)
        assert self.structured_logger.db_enabled is False

    def test_search_logs_disabled(self):
        """Test that log search is disabled for performance"""
        # Add some logs
        self.structured_logger.info("Searchable info")
        self.structured_logger.error("Searchable error")
        
        # Search should return empty list (disabled for performance)
        results = self.structured_logger.search_logs("searchable")
        assert results == []


class TestPerformanceOptimizations:
    """Test performance optimization features"""

    def test_log_buffer_deque_maxlen(self):
        """Test that log buffer uses deque with maxlen for performance"""
        logger = StructuredLogger("perf_test")
        
        # Buffer should be a deque with maxlen
        assert isinstance(logger.log_buffer, deque)
        assert logger.log_buffer.maxlen == 1000

    def test_disabled_search_for_performance(self):
        """Test that search is disabled for performance"""
        logger = StructuredLogger("search_test")
        
        # Add some logs
        logger.info("Searchable message")
        
        # Search should return empty list (disabled for performance)
        results = logger.search_logs("searchable")
        assert results == []

    def test_minimal_db_operations(self):
        """Test that DB operations are minimized"""
        logger = StructuredLogger("db_perf_test")
        
        # DB logging should be disabled by default
        assert not hasattr(logger, 'db_enabled') or not logger.db_enabled

    def test_efficient_stats_tracking(self):
        """Test efficient statistics tracking"""
        logger = StructuredLogger("stats_test")
        
        # Add logs of different levels
        logger.info("Info")
        logger.warning("Warning")
        logger.error("Error")
        
        # Stats should be efficiently tracked
        stats = logger.log_stats
        assert stats["info"] == 1
        assert stats["warning"] == 1
        assert stats["error"] == 1
        assert stats["debug"] == 0
        assert stats["critical"] == 0


if __name__ == "__main__":
    pytest.main([__file__])
