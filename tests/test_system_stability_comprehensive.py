"""
Comprehensive tests for src/utils/system_stability.py
Tests system monitoring and database stability functionality
"""
import pytest
import sqlite3
import tempfile
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.system_stability import (
    SystemHealth,
    DatabaseStabilityManager
)


class TestSystemHealth:
    """Test the SystemHealth dataclass"""

    def test_system_health_initialization(self):
        """Test SystemHealth initialization with defaults"""
        health = SystemHealth()
        
        assert health.cpu_percent == 0.0
        assert health.memory_percent == 0.0
        assert health.disk_percent == 0.0
        assert health.database_status == "unknown"
        assert health.cache_status == "unknown"
        assert health.uptime_seconds == 0
        assert health.active_connections == 0
        assert health.error_count_last_hour == 0
        assert health.warnings == []
        assert isinstance(health.timestamp, datetime)

    def test_system_health_with_values(self):
        """Test SystemHealth initialization with specific values"""
        test_timestamp = datetime(2024, 1, 1, 12, 0, 0)
        test_warnings = ["Warning 1", "Warning 2"]
        
        health = SystemHealth(
            cpu_percent=75.5,
            memory_percent=60.2,
            disk_percent=45.8,
            database_status="healthy",
            cache_status="active",
            uptime_seconds=3600,
            active_connections=25,
            error_count_last_hour=5,
            warnings=test_warnings,
            timestamp=test_timestamp
        )
        
        assert health.cpu_percent == 75.5
        assert health.memory_percent == 60.2
        assert health.disk_percent == 45.8
        assert health.database_status == "healthy"
        assert health.cache_status == "active"
        assert health.uptime_seconds == 3600
        assert health.active_connections == 25
        assert health.error_count_last_hour == 5
        assert health.warnings == test_warnings
        assert health.timestamp == test_timestamp

    def test_overall_status_healthy(self):
        """Test overall_status when system is healthy"""
        health = SystemHealth(
            cpu_percent=50.0,
            memory_percent=40.0,
            database_status="healthy",
            error_count_last_hour=5
        )
        
        assert health.overall_status == "healthy"

    def test_overall_status_critical_high_errors(self):
        """Test overall_status when error count is too high"""
        health = SystemHealth(
            cpu_percent=30.0,
            memory_percent=40.0,
            database_status="healthy",
            error_count_last_hour=60  # > 50
        )
        
        assert health.overall_status == "critical"

    def test_overall_status_warning_high_cpu(self):
        """Test overall_status when CPU usage is too high"""
        health = SystemHealth(
            cpu_percent=95.0,  # > 90
            memory_percent=40.0,
            database_status="healthy",
            error_count_last_hour=5
        )
        
        assert health.overall_status == "warning"

    def test_overall_status_warning_high_memory(self):
        """Test overall_status when memory usage is too high"""
        health = SystemHealth(
            cpu_percent=50.0,
            memory_percent=95.0,  # > 90
            database_status="healthy",
            error_count_last_hour=5
        )
        
        assert health.overall_status == "warning"

    def test_overall_status_warning_unhealthy_database(self):
        """Test overall_status when database is unhealthy"""
        health = SystemHealth(
            cpu_percent=50.0,
            memory_percent=40.0,
            database_status="error",  # != "healthy"
            error_count_last_hour=5
        )
        
        assert health.overall_status == "warning"

    def test_overall_status_critical_takes_precedence(self):
        """Test that critical status takes precedence over warning"""
        health = SystemHealth(
            cpu_percent=95.0,  # Would be warning
            memory_percent=95.0,  # Would be warning
            database_status="error",  # Would be warning
            error_count_last_hour=60  # Critical
        )
        
        assert health.overall_status == "critical"

    def test_warnings_list_manipulation(self):
        """Test that warnings list can be manipulated"""
        health = SystemHealth()
        
        health.warnings.append("Test warning")
        assert len(health.warnings) == 1
        assert health.warnings[0] == "Test warning"
        
        health.warnings.extend(["Warning 2", "Warning 3"])
        assert len(health.warnings) == 3

    def test_timestamp_property(self):
        """Test timestamp property behavior"""
        before = datetime.now()
        health = SystemHealth()
        after = datetime.now()
        
        # Timestamp should be between before and after
        assert before <= health.timestamp <= after

    def test_field_defaults(self):
        """Test that field defaults work correctly"""
        health1 = SystemHealth()
        health2 = SystemHealth()
        
        # Each instance should have its own warnings list
        health1.warnings.append("Warning 1")
        health2.warnings.append("Warning 2")
        
        assert len(health1.warnings) == 1
        assert len(health2.warnings) == 1
        assert health1.warnings != health2.warnings


class TestDatabaseStabilityManager:
    """Test the DatabaseStabilityManager class"""

    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name

    def tearDown(self):
        """Clean up test database"""
        try:
            import os
            os.unlink(self.db_path)
        except Exception:
            pass

    def test_database_manager_initialization(self):
        """Test DatabaseStabilityManager initialization"""
        self.setUp()
        try:
            manager = DatabaseStabilityManager(self.db_path)
            
            assert manager.db_path == self.db_path
            assert manager.connection_pool == []
            assert manager.max_connections == 10
            assert isinstance(manager.lock, threading.Lock)
        finally:
            self.tearDown()

    def test_get_connection_context_manager(self):
        """Test get_connection context manager basic functionality"""
        self.setUp()
        try:
            manager = DatabaseStabilityManager(self.db_path)
            
            with manager.get_connection() as conn:
                assert conn is not None
                assert isinstance(conn, sqlite3.Connection)
                
                # Test that we can execute a query
                cursor = conn.execute("SELECT 1")
                result = cursor.fetchone()
                assert result[0] == 1
        finally:
            self.tearDown()

    def test_connection_pool_reuse(self):
        """Test that connections are reused from the pool"""
        self.setUp()
        try:
            manager = DatabaseStabilityManager(self.db_path)
            
            # First connection should create new connection
            with manager.get_connection() as conn1:
                conn1_id = id(conn1)
            
            # Connection should be returned to pool
            assert len(manager.connection_pool) == 1
            
            # Second connection should reuse from pool
            with manager.get_connection() as conn2:
                conn2_id = id(conn2)
            
            # Should be the same connection object
            assert conn1_id == conn2_id
        finally:
            self.tearDown()

    def test_connection_pool_max_size(self):
        """Test that connection pool respects max size"""
        self.setUp()
        try:
            manager = DatabaseStabilityManager(self.db_path)
            manager.max_connections = 2  # Set small limit for testing
            
            connections = []
            
            # Create more connections than max pool size
            for i in range(5):
                with manager.get_connection() as conn:
                    connections.append(id(conn))
            
            # Pool should not exceed max size
            assert len(manager.connection_pool) <= manager.max_connections
        finally:
            self.tearDown()

    def test_connection_pragma_settings(self):
        """Test that connections have correct PRAGMA settings"""
        self.setUp()
        try:
            manager = DatabaseStabilityManager(self.db_path)
            
            with manager.get_connection() as conn:
                # Check WAL mode
                cursor = conn.execute("PRAGMA journal_mode")
                journal_mode = cursor.fetchone()[0]
                assert journal_mode.upper() == "WAL"
                
                # Check synchronous mode
                cursor = conn.execute("PRAGMA synchronous")
                synchronous = cursor.fetchone()[0]
                assert synchronous == 1  # NORMAL
                
                # Check cache size
                cursor = conn.execute("PRAGMA cache_size")
                cache_size = cursor.fetchone()[0]
                assert cache_size == 10000
                
                # Check temp store
                cursor = conn.execute("PRAGMA temp_store")
                temp_store = cursor.fetchone()[0]
                assert temp_store == 2  # MEMORY
        finally:
            self.tearDown()

    @patch('src.utils.system_stability.sqlite3.connect')
    def test_connection_error_handling(self, mock_connect):
        """Test connection error handling"""
        mock_connect.side_effect = sqlite3.Error("Connection failed")
        
        manager = DatabaseStabilityManager("/fake/path")
        
        with pytest.raises(sqlite3.Error):
            with manager.get_connection():
                pass

    @patch('src.utils.system_stability.logger')
    def test_connection_error_logging(self, mock_logger):
        """Test that connection errors are logged"""
        # Use invalid database path to trigger error
        manager = DatabaseStabilityManager("/invalid/path/db.sqlite")
        
        with pytest.raises(Exception):
            with manager.get_connection():
                pass
        
        # Should log the error
        mock_logger.error.assert_called()

    def test_connection_rollback_on_error(self):
        """Test that connections are rolled back on error"""
        self.setUp()
        try:
            manager = DatabaseStabilityManager(self.db_path)
            
            with manager.get_connection() as conn:
                # Create a table for testing
                conn.execute("CREATE TABLE test_table (id INTEGER, value TEXT)")
                conn.commit()
            
            # Now test rollback behavior
            try:
                with manager.get_connection() as conn:
                    conn.execute("INSERT INTO test_table VALUES (1, 'test')")
                    # Raise an exception to trigger rollback
                    raise Exception("Test exception")
            except Exception:
                pass
            
            # Check that the insert was rolled back
            with manager.get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM test_table")
                count = cursor.fetchone()[0]
                assert count == 0
        finally:
            self.tearDown()

    def test_connection_thread_safety(self):
        """Test that connection manager is thread-safe"""
        self.setUp()
        try:
            manager = DatabaseStabilityManager(self.db_path)
            results = []
            errors = []
            
            def worker(worker_id):
                try:
                    with manager.get_connection() as conn:
                        cursor = conn.execute("SELECT ?", (worker_id,))
                        result = cursor.fetchone()[0]
                        results.append(result)
                        time.sleep(0.01)  # Small delay to test concurrency
                except Exception as e:
                    errors.append(e)
            
            # Start multiple threads
            threads = []
            for i in range(10):
                thread = threading.Thread(target=worker, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Check that all workers completed successfully
            assert len(errors) == 0
            assert len(results) == 10
            assert sorted(results) == list(range(10))
        finally:
            self.tearDown()

    def test_connection_timeout_setting(self):
        """Test that connections use timeout setting"""
        self.setUp()
        try:
            manager = DatabaseStabilityManager(self.db_path)
            
            # We can't easily test timeout behavior without complex setup,
            # but we can verify the connection is created with timeout parameter
            with patch('src.utils.system_stability.sqlite3.connect') as mock_connect:
                mock_conn = Mock()
                mock_connect.return_value = mock_conn
                
                with manager.get_connection():
                    pass
                
                # Verify connect was called with timeout
                mock_connect.assert_called_once()
                args, kwargs = mock_connect.call_args
                assert args[0] == self.db_path
                assert kwargs.get('timeout') == 30.0
                assert kwargs.get('check_same_thread') == False
        finally:
            self.tearDown()

    def test_connection_commit_on_successful_exit(self):
        """Test that connections are committed on successful context exit"""
        self.setUp()
        try:
            manager = DatabaseStabilityManager(self.db_path)
            
            # Create table and insert data
            with manager.get_connection() as conn:
                conn.execute("CREATE TABLE test_commit (id INTEGER, value TEXT)")
                conn.execute("INSERT INTO test_commit VALUES (1, 'committed')")
                # No explicit commit - should be handled by context manager
            
            # Verify data was committed
            with manager.get_connection() as conn:
                cursor = conn.execute("SELECT value FROM test_commit WHERE id = 1")
                result = cursor.fetchone()
                assert result is not None
                assert result[0] == 'committed'
        finally:
            self.tearDown()

    def test_empty_connection_pool_creates_new_connection(self):
        """Test that empty pool creates new connections"""
        self.setUp()
        try:
            manager = DatabaseStabilityManager(self.db_path)
            
            # Initially pool should be empty
            assert len(manager.connection_pool) == 0
            
            with manager.get_connection() as conn:
                assert conn is not None
            
            # After use, connection should be in pool
            assert len(manager.connection_pool) == 1
        finally:
            self.tearDown()

    @patch('src.utils.system_stability.logger')
    def test_connection_return_error_handling(self, mock_logger):
        """Test error handling when returning connection to pool"""
        self.setUp()
        try:
            manager = DatabaseStabilityManager(self.db_path)
            
            with patch.object(manager, 'connection_pool') as mock_pool:
                # Make append raise an exception
                mock_pool.append.side_effect = Exception("Pool error")
                
                with manager.get_connection() as conn:
                    pass
                
                # Should log error when returning connection fails
                mock_logger.error.assert_called()
        finally:
            self.tearDown()


class TestSystemStabilityIntegration:
    """Integration tests for system stability components"""

    def test_system_health_with_database_manager(self):
        """Test integration between SystemHealth and DatabaseStabilityManager"""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        try:
            manager = DatabaseStabilityManager(temp_db.name)
            
            # Test that we can create system health and use database
            health = SystemHealth(
                database_status="healthy",
                active_connections=5
            )
            
            with manager.get_connection() as conn:
                conn.execute("CREATE TABLE health_test (status TEXT)")
                conn.execute("INSERT INTO health_test VALUES (?)", (health.database_status,))
            
            # Verify the integration worked
            with manager.get_connection() as conn:
                cursor = conn.execute("SELECT status FROM health_test")
                result = cursor.fetchone()
                assert result[0] == "healthy"
        
        finally:
            import os
            try:
                os.unlink(temp_db.name)
            except Exception:
                pass

    def test_concurrent_system_health_updates(self):
        """Test concurrent system health updates"""
        health = SystemHealth()
        results = []
        
        def update_health(worker_id):
            health.error_count_last_hour += worker_id
            health.warnings.append(f"Warning from worker {worker_id}")
            results.append(worker_id)
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=update_health, args=(i + 1,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Note: This test shows potential race conditions in SystemHealth
        # In real use, you'd want proper synchronization
        assert len(results) == 5


if __name__ == '__main__':
    pytest.main([__file__])