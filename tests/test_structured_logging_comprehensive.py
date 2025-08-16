#!/usr/bin/env python3
"""
Comprehensive Structured Logging Test Suite

Tests all structured logging features including:
- Structured logging with JSON format
- Log levels and context management
- Performance logging and metrics
- Error tracking and reporting
- Security audit logging
- Flask integration and request logging
- Log searching and statistics
"""

import json
import logging
import os
import sqlite3
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import pytest

# Test imports
from src.utils.structured_logging import (
    BufferHandler,
    LogManager,
    StructuredLogger,
    get_logger,
    log_manager,
    setup_request_logging,
)


class TestStructuredLogger:
    """Test StructuredLogger class functionality"""

    def setup_method(self):
        """Setup test environment"""
        self.test_log_dir = tempfile.mkdtemp()
        self.logger_name = "test_logger"
        self.structured_logger = StructuredLogger(self.logger_name, self.test_log_dir)

    def teardown_method(self):
        """Cleanup test environment"""
        # Clean up temp directory if it exists
        import shutil
        if os.path.exists(self.test_log_dir):
            try:
                shutil.rmtree(self.test_log_dir)
            except PermissionError:
                pass  # Handle permission errors in test cleanup

    def test_initialization(self):
        """Test StructuredLogger initialization"""
        assert self.structured_logger.name == self.logger_name
        assert self.structured_logger.log_dir == Path(self.test_log_dir)
        assert hasattr(self.structured_logger, 'log_buffer')
        assert hasattr(self.structured_logger, 'buffer_lock')
        assert hasattr(self.structured_logger, 'logger')
        assert hasattr(self.structured_logger, 'log_stats')

    def test_initialization_with_permission_error(self):
        """Test initialization with permission errors"""
        # Test with invalid directory path
        invalid_dir = "/root/invalid_log_dir"
        logger = StructuredLogger("test", invalid_dir)
        
        # Should handle permission error gracefully
        assert logger.name == "test"

    def test_log_stats_initialization(self):
        """Test log statistics initialization"""
        expected_levels = ["debug", "info", "warning", "error", "critical"]
        
        for level in expected_levels:
            assert level in self.structured_logger.log_stats
            assert self.structured_logger.log_stats[level] == 0

    def test_setup_logger_basic(self):
        """Test logger setup"""
        logger = self.structured_logger.logger
        
        assert isinstance(logger, logging.Logger)
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) > 0

    def test_create_log_record_basic(self):
        """Test basic log record creation"""
        level = "INFO"
        message = "Test message"
        context = {"key": "value"}
        
        record = self.structured_logger._create_log_record(level, message, context)
        
        assert record["level"] == level
        assert record["message"] == message
        assert record["logger_name"] == self.logger_name
        assert record["context"] == context
        assert "timestamp" in record

    def test_create_log_record_with_exception(self):
        """Test log record creation with exception"""
        level = "ERROR"
        message = "Error occurred"
        exception = ValueError("Test error")
        
        record = self.structured_logger._create_log_record(level, message, None, exception)
        
        assert record["level"] == level
        assert record["message"] == message
        assert "exception" in record
        assert record["exception"]["type"] == "ValueError"
        assert record["exception"]["message"] == "Test error"
        assert "traceback" in record["exception"]

    @patch('src.utils.structured_logging.request')
    @patch('src.utils.structured_logging.g')
    def test_create_log_record_with_flask_context(self, mock_g, mock_request):
        """Test log record creation with Flask request context"""
        # Setup mock Flask context
        mock_request.method = "GET"
        mock_request.path = "/api/test"
        mock_request.remote_addr = "192.168.1.1"
        mock_request.headers.get.return_value = "Mozilla/5.0"
        mock_g.request_id = "test-request-123"
        
        record = self.structured_logger._create_log_record("INFO", "Test with context")
        
        assert "request" in record["context"]
        request_context = record["context"]["request"]
        assert request_context["method"] == "GET"
        assert request_context["path"] == "/api/test"
        assert request_context["ip"] == "192.168.1.1"
        assert request_context["user_agent"] == "Mozilla/5.0"
        assert record["context"]["request_id"] == "test-request-123"

    def test_debug_logging(self):
        """Test debug level logging"""
        message = "Debug message"
        context = {"debug_key": "debug_value"}
        
        self.structured_logger.debug(message, **context)
        
        # Check buffer
        assert len(self.structured_logger.log_buffer) == 1
        record = self.structured_logger.log_buffer[0]
        assert record["level"] == "DEBUG"
        assert record["message"] == message
        
        # Check stats
        assert self.structured_logger.log_stats["debug"] == 1

    def test_info_logging(self):
        """Test info level logging"""
        message = "Info message"
        context = {"info_key": "info_value"}
        
        self.structured_logger.info(message, **context)
        
        # Check buffer
        assert len(self.structured_logger.log_buffer) == 1
        record = self.structured_logger.log_buffer[0]
        assert record["level"] == "INFO"
        assert record["message"] == message
        
        # Check stats
        assert self.structured_logger.log_stats["info"] == 1

    def test_warning_logging(self):
        """Test warning level logging"""
        message = "Warning message"
        context = {"warning_key": "warning_value"}
        
        self.structured_logger.warning(message, **context)
        
        # Check buffer
        assert len(self.structured_logger.log_buffer) == 1
        record = self.structured_logger.log_buffer[0]
        assert record["level"] == "WARNING"
        assert record["message"] == message
        
        # Check stats
        assert self.structured_logger.log_stats["warning"] == 1

    def test_error_logging(self):
        """Test error level logging"""
        message = "Error message"
        exception = RuntimeError("Test runtime error")
        context = {"error_key": "error_value"}
        
        self.structured_logger.error(message, exception=exception, **context)
        
        # Check buffer
        assert len(self.structured_logger.log_buffer) == 1
        record = self.structured_logger.log_buffer[0]
        assert record["level"] == "ERROR"
        assert record["message"] == message
        assert "exception" in record
        
        # Check stats
        assert self.structured_logger.log_stats["error"] == 1

    def test_critical_logging(self):
        """Test critical level logging"""
        message = "Critical message"
        exception = SystemError("Critical system error")
        context = {"critical_key": "critical_value"}
        
        self.structured_logger.critical(message, exception=exception, **context)
        
        # Check buffer
        assert len(self.structured_logger.log_buffer) == 1
        record = self.structured_logger.log_buffer[0]
        assert record["level"] == "CRITICAL"
        assert record["message"] == message
        assert "exception" in record
        
        # Check stats
        assert self.structured_logger.log_stats["critical"] == 1

    def test_get_recent_logs_all(self):
        """Test getting recent logs without filter"""
        # Add some logs
        self.structured_logger.info("Info 1")
        self.structured_logger.warning("Warning 1")
        self.structured_logger.error("Error 1")
        
        recent_logs = self.structured_logger.get_recent_logs(count=10)
        
        assert len(recent_logs) == 3
        assert recent_logs[0]["message"] == "Info 1"
        assert recent_logs[1]["message"] == "Warning 1"
        assert recent_logs[2]["message"] == "Error 1"

    def test_get_recent_logs_filtered_by_level(self):
        """Test getting recent logs filtered by level"""
        # Add logs of different levels
        self.structured_logger.info("Info 1")
        self.structured_logger.warning("Warning 1")
        self.structured_logger.error("Error 1")
        self.structured_logger.warning("Warning 2")
        
        warning_logs = self.structured_logger.get_recent_logs(count=10, level="WARNING")
        
        assert len(warning_logs) == 2
        assert all(log["level"] == "WARNING" for log in warning_logs)

    def test_get_recent_logs_count_limit(self):
        """Test getting recent logs with count limit"""
        # Add more logs than requested
        for i in range(10):
            self.structured_logger.info(f"Info {i}")
        
        recent_logs = self.structured_logger.get_recent_logs(count=5)
        
        assert len(recent_logs) == 5
        # Should get the last 5 logs
        assert recent_logs[0]["message"] == "Info 5"
        assert recent_logs[4]["message"] == "Info 9"

    def test_get_log_stats(self):
        """Test getting log statistics"""
        # Add various logs
        self.structured_logger.info("Info 1")
        self.structured_logger.info("Info 2")
        self.structured_logger.warning("Warning 1")
        self.structured_logger.error("Error 1")
        
        stats = self.structured_logger.get_log_stats()
        
        assert "stats" in stats
        assert "buffer_size" in stats
        assert "recent_errors" in stats
        assert "recent_warnings" in stats
        
        assert stats["stats"]["info"] == 2
        assert stats["stats"]["warning"] == 1
        assert stats["stats"]["error"] == 1
        assert stats["buffer_size"] == 4

    def test_search_logs_disabled(self):
        """Test that log search is disabled for performance"""
        # Add some logs
        self.structured_logger.info("Searchable info")
        self.structured_logger.error("Searchable error")
        
        # Search should return empty list (disabled for performance)
        results = self.structured_logger.search_logs("searchable")
        assert results == []

    def test_enable_db_logging(self):
        """Test enabling database logging"""
        self.structured_logger.enable_db_logging(True)
        assert hasattr(self.structured_logger, 'db_enabled')
        assert self.structured_logger.db_enabled is True
        
        self.structured_logger.enable_db_logging(False)
        assert self.structured_logger.db_enabled is False

    def test_save_to_db_disabled(self):
        """Test database saving when disabled"""
        # Ensure DB logging is disabled
        self.structured_logger.db_enabled = False
        
        record = {"level": "INFO", "message": "Test"}
        
        # Should not raise exception when DB logging is disabled
        self.structured_logger._save_to_db(record)

    def test_buffer_size_limit(self):
        """Test log buffer size limit"""
        # Add more logs than buffer can hold
        for i in range(1500):  # Buffer max is 1000
            self.structured_logger.info(f"Log {i}")
        
        # Buffer should be limited to maxlen
        assert len(self.structured_logger.log_buffer) == 1000
        
        # Should contain the most recent logs
        last_log = self.structured_logger.log_buffer[-1]
        assert "Log 1499" in last_log["message"]

    def test_thread_safety(self):
        """Test thread safety of structured logger"""
        def log_messages():
            for i in range(100):
                self.structured_logger.info(f"Thread message {i}")
        
        # Run concurrent threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=log_messages)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have logged all messages
        assert len(self.structured_logger.log_buffer) == 500
        assert self.structured_logger.log_stats["info"] == 500


class TestBufferHandler:
    """Test BufferHandler class"""

    def setup_method(self):
        """Setup test environment"""
        self.structured_logger = Mock()
        self.structured_logger._add_to_buffer = Mock()
        self.handler = BufferHandler(self.structured_logger)

    def test_initialization(self):
        """Test BufferHandler initialization"""
        assert self.handler.structured_logger is self.structured_logger

    def test_emit_basic_record(self):
        """Test emitting basic log record"""
        # Create a mock log record
        record = Mock()
        record.created = time.time()
        record.levelname = "INFO"
        record.name = "test_logger"
        record.getMessage.return_value = "Test message"
        record.exc_info = None
        
        self.handler.emit(record)
        
        # Should call _add_to_buffer with formatted entry
        self.structured_logger._add_to_buffer.assert_called_once()
        call_args = self.structured_logger._add_to_buffer.call_args[0][0]
        
        assert call_args["level"] == "INFO"
        assert call_args["logger_name"] == "test_logger"
        assert call_args["message"] == "Test message"
        assert "timestamp" in call_args

    def test_emit_record_with_exception(self):
        """Test emitting log record with exception"""
        record = Mock()
        record.created = time.time()
        record.levelname = "ERROR"
        record.name = "test_logger"
        record.getMessage.return_value = "Error message"
        record.exc_info = ("Exception", "Error details", "traceback")
        
        # Mock the format method to return traceback
        self.handler.format = Mock(return_value="Formatted traceback")
        
        self.handler.emit(record)
        
        self.structured_logger._add_to_buffer.assert_called_once()
        call_args = self.structured_logger._add_to_buffer.call_args[0][0]
        
        assert call_args["level"] == "ERROR"
        assert "traceback" in call_args
        assert call_args["traceback"] == "Formatted traceback"

    def test_emit_with_context(self):
        """Test emitting record with context"""
        record = Mock()
        record.created = time.time()
        record.levelname = "INFO"
        record.name = "test_logger"
        record.getMessage.return_value = "Test message"
        record.exc_info = None
        record.context = {"key": "value"}
        
        self.handler.emit(record)
        
        self.structured_logger._add_to_buffer.assert_called_once()
        call_args = self.structured_logger._add_to_buffer.call_args[0][0]
        
        assert call_args["context"] == {"key": "value"}

    def test_emit_with_exception_handling(self):
        """Test emit method exception handling"""
        record = Mock()
        record.created = time.time()
        record.levelname = "INFO"
        record.name = "test_logger"
        record.getMessage.side_effect = Exception("getMessage failed")
        
        # Mock handleError to verify it's called
        self.handler.handleError = Mock()
        
        self.handler.emit(record)
        
        # Should call handleError when exception occurs
        self.handler.handleError.assert_called_once_with(record)


class TestLogManager:
    """Test LogManager class"""

    def setup_method(self):
        """Setup test environment"""
        # Create a new instance for testing
        self.log_manager = LogManager()

    def test_singleton_pattern(self):
        """Test LogManager singleton pattern"""
        manager1 = LogManager()
        manager2 = LogManager()
        
        assert manager1 is manager2

    def test_get_logger_new_logger(self):
        """Test getting new logger instance"""
        logger_name = "test_new_logger"
        logger = self.log_manager.get_logger(logger_name)
        
        assert isinstance(logger, StructuredLogger)
        assert logger.name == logger_name
        assert logger_name in self.log_manager._loggers

    def test_get_logger_existing_logger(self):
        """Test getting existing logger instance"""
        logger_name = "test_existing_logger"
        
        # Get logger first time
        logger1 = self.log_manager.get_logger(logger_name)
        
        # Get logger second time - should be same instance
        logger2 = self.log_manager.get_logger(logger_name)
        
        assert logger1 is logger2

    def test_get_all_stats(self):
        """Test getting statistics from all loggers"""
        # Create some loggers and add logs
        logger1 = self.log_manager.get_logger("logger1")
        logger2 = self.log_manager.get_logger("logger2")
        
        logger1.info("Info message")
        logger1.error("Error message")
        logger2.warning("Warning message")
        
        all_stats = self.log_manager.get_all_stats()
        
        assert "logger1" in all_stats
        assert "logger2" in all_stats
        assert all_stats["logger1"]["stats"]["info"] == 1
        assert all_stats["logger1"]["stats"]["error"] == 1
        assert all_stats["logger2"]["stats"]["warning"] == 1

    def test_search_all_logs_disabled(self):
        """Test searching all logs (disabled for performance)"""
        # Create loggers with some logs
        logger1 = self.log_manager.get_logger("logger1")
        logger2 = self.log_manager.get_logger("logger2")
        
        logger1.info("Searchable info")
        logger2.error("Searchable error")
        
        # Search should return empty results (disabled)
        results = self.log_manager.search_all_logs("searchable")
        assert results == {}


class TestGlobalFunctions:
    """Test global functions"""

    def test_get_logger_function(self):
        """Test get_logger global function"""
        logger_name = "global_test_logger"
        logger = get_logger(logger_name)
        
        assert isinstance(logger, StructuredLogger)
        assert logger.name == logger_name

    def test_get_logger_function_uses_global_manager(self):
        """Test that get_logger uses global log manager"""
        logger_name = "global_manager_test"
        
        # Get logger using global function
        logger1 = get_logger(logger_name)
        
        # Get logger directly from global manager
        logger2 = log_manager.get_logger(logger_name)
        
        assert logger1 is logger2


class TestFlaskIntegration:
    """Test Flask integration functionality"""

    def setup_method(self):
        """Setup test environment"""
        self.mock_app = Mock()
        self.mock_app.before_request = Mock()
        self.mock_app.after_request = Mock()
        self.mock_app.route = Mock()

    @patch('src.utils.structured_logging.get_logger')
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

    @patch('src.utils.structured_logging.g')
    @patch('src.utils.structured_logging.request')
    @patch('src.utils.structured_logging.get_logger')
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

    @patch('src.utils.structured_logging.g')
    @patch('src.utils.structured_logging.get_logger')
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

    @patch('src.utils.structured_logging.request')
    @patch('src.utils.structured_logging.log_manager')
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

    @patch('src.utils.structured_logging.request')
    @patch('src.utils.structured_logging.log_manager')
    def test_search_logs_api_endpoint(self, mock_log_manager, mock_request):
        """Test search logs API endpoint"""
        # Setup mock request args
        mock_request.args.get.side_effect = lambda key, default=None: {
            "q": "test_query",
            "limit": "50"
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


class TestPerformanceOptimizations:
    """Test performance optimization features"""

    def test_log_buffer_deque_maxlen(self):
        """Test that log buffer uses deque with maxlen for performance"""
        logger = StructuredLogger("perf_test")
        
        # Buffer should be a deque with maxlen
        from collections import deque
        assert isinstance(logger.log_buffer, deque)
        assert logger.log_buffer.maxlen == 1000

    def test_thread_lock_usage(self):
        """Test that thread locks are used for thread safety"""
        logger = StructuredLogger("thread_test")
        
        assert isinstance(logger.buffer_lock, threading.Lock)

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