#!/usr/bin/env python3
"""
Unit tests for ConnectionManager class
Tests database connection management and configuration.
"""

import os
import sqlite3
import tempfile
import unittest.mock as mock
from pathlib import Path

import pytest

from src.core.database.connection_manager import ConnectionManager


class TestConnectionManager:
    """Test cases for ConnectionManager class"""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file path"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def connection_manager(self, temp_db_path):
        """Create ConnectionManager instance with temporary database"""
        return ConnectionManager(temp_db_path)

    def test_init_default_path(self):
        """Test ConnectionManager initialization with default path"""
        manager = ConnectionManager()
        assert manager.db_path == "instance/blacklist.db"
        assert manager._memory_connection is None

    def test_init_custom_path(self, temp_db_path):
        """Test ConnectionManager initialization with custom path"""
        manager = ConnectionManager(temp_db_path)
        assert manager.db_path == temp_db_path
        assert manager._memory_connection is None

    @mock.patch.dict(os.environ, {"DATABASE_URL": "sqlite:///custom/path/db.sqlite"})
    def test_init_with_database_url_file(self):
        """Test initialization with DATABASE_URL environment variable (file)"""
        manager = ConnectionManager()
        assert manager.db_path == "custom/path/db.sqlite"

    @mock.patch.dict(os.environ, {"DATABASE_URL": "sqlite:///:memory:"})
    def test_init_with_database_url_memory(self):
        """Test initialization with DATABASE_URL environment variable (memory)"""
        manager = ConnectionManager()
        assert manager.db_path == ":memory:"

    @mock.patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@host/db"})
    def test_init_with_non_sqlite_database_url(self, temp_db_path):
        """Test initialization with non-SQLite DATABASE_URL"""
        manager = ConnectionManager(temp_db_path)
        assert manager.db_path == temp_db_path  # Should use provided path

    def test_get_connection_file_database(self, temp_db_path):
        """Test get_connection for file-based database"""
        manager = ConnectionManager(temp_db_path)

        with mock.patch("sqlite3.connect") as mock_connect:
            mock_conn = mock.Mock()
            mock_connect.return_value = mock_conn

            with mock.patch.object(
                manager, "_configure_file_connection"
            ) as mock_configure:
                conn = manager.get_connection()

                mock_connect.assert_called_once_with(temp_db_path)
                assert mock_conn.row_factory == sqlite3.Row
                mock_configure.assert_called_once_with(mock_conn)
                assert conn is mock_conn

    def test_get_connection_memory_database_first_time(self):
        """Test get_connection for in-memory database (first time)"""
        manager = ConnectionManager(":memory:")

        with mock.patch("sqlite3.connect") as mock_connect:
            mock_conn = mock.Mock()
            mock_connect.return_value = mock_conn

            with mock.patch.object(
                manager, "_configure_memory_connection"
            ) as mock_configure:
                conn = manager.get_connection()

                mock_connect.assert_called_once_with(":memory:")
                assert mock_conn.row_factory == sqlite3.Row
                mock_configure.assert_called_once_with(mock_conn)
                assert manager._memory_connection is mock_conn
                assert conn is mock_conn

    def test_get_connection_memory_database_subsequent(self):
        """Test get_connection for in-memory database (subsequent calls)"""
        manager = ConnectionManager(":memory:")
        mock_conn = mock.Mock()
        manager._memory_connection = mock_conn

        with mock.patch("sqlite3.connect") as mock_connect:
            conn = manager.get_connection()

            # Should not create new connection
            mock_connect.assert_not_called()
            assert conn is mock_conn

    def test_get_connection_creates_parent_directory(self, temp_db_path):
        """Test that get_connection creates parent directory for file database"""
        # Use a path in a non-existent directory
        nested_path = os.path.join(os.path.dirname(temp_db_path), "nested", "db.sqlite")
        manager = ConnectionManager(nested_path)

        with mock.patch("sqlite3.connect") as mock_connect:
            mock_conn = mock.Mock()
            mock_connect.return_value = mock_conn

            with mock.patch.object(manager, "_configure_file_connection"):
                manager.get_connection()

                # Parent directory should exist
                assert os.path.exists(os.path.dirname(nested_path))

                # Clean up
                os.rmdir(os.path.dirname(nested_path))

    def test_configure_memory_connection(self, connection_manager):
        """Test _configure_memory_connection method"""
        mock_conn = mock.Mock()

        connection_manager._configure_memory_connection(mock_conn)

        # Verify PRAGMA commands were executed
        expected_calls = [
            mock.call("PRAGMA synchronous=OFF"),
            mock.call("PRAGMA cache_size=10000"),
            mock.call("PRAGMA temp_store=MEMORY"),
        ]
        mock_conn.execute.assert_has_calls(expected_calls)

    def test_configure_file_connection(self, connection_manager):
        """Test _configure_file_connection method"""
        mock_conn = mock.Mock()

        connection_manager._configure_file_connection(mock_conn)

        # Verify PRAGMA commands were executed
        expected_calls = [
            mock.call("PRAGMA journal_mode=WAL"),
            mock.call("PRAGMA synchronous=NORMAL"),
            mock.call("PRAGMA cache_size=10000"),
            mock.call("PRAGMA temp_store=MEMORY"),
        ]
        mock_conn.execute.assert_has_calls(expected_calls)

    def test_close_memory_connection_with_connection(self):
        """Test close_memory_connection when connection exists"""
        manager = ConnectionManager(":memory:")
        mock_conn = mock.Mock()
        manager._memory_connection = mock_conn

        manager.close_memory_connection()

        mock_conn.close.assert_called_once()
        assert manager._memory_connection is None

    def test_close_memory_connection_without_connection(self):
        """Test close_memory_connection when no connection exists"""
        manager = ConnectionManager(":memory:")
        assert manager._memory_connection is None

        # Should not raise an exception
        manager.close_memory_connection()
        assert manager._memory_connection is None

    def test_memory_connection_persistence(self):
        """Test that memory connection persists across calls"""
        manager = ConnectionManager(":memory:")

        with mock.patch("sqlite3.connect") as mock_connect:
            mock_conn = mock.Mock()
            mock_connect.return_value = mock_conn

            with mock.patch.object(manager, "_configure_memory_connection"):
                # First call
                conn1 = manager.get_connection()
                # Second call
                conn2 = manager.get_connection()

                # Connect should only be called once
                mock_connect.assert_called_once()
                assert conn1 is conn2
                assert conn1 is mock_conn

    @pytest.mark.integration
    def test_real_database_connection(self, temp_db_path):
        """Integration test with real SQLite database"""
        manager = ConnectionManager(temp_db_path)

        # Get connection and verify it works
        conn = manager.get_connection()
        assert isinstance(conn, sqlite3.Connection)
        assert conn.row_factory == sqlite3.Row

        # Test basic operation
        cursor = conn.execute("SELECT 1 as test")
        row = cursor.fetchone()
        assert row["test"] == 1

        conn.close()

    @pytest.mark.integration
    def test_real_memory_database_connection(self):
        """Integration test with real in-memory database"""
        manager = ConnectionManager(":memory:")

        # Get connection and verify it works
        conn = manager.get_connection()
        assert isinstance(conn, sqlite3.Connection)
        assert conn.row_factory == sqlite3.Row

        # Test basic operation
        cursor = conn.execute("SELECT 1 as test")
        row = cursor.fetchone()
        assert row["test"] == 1

        # Test persistence
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.execute("INSERT INTO test (id) VALUES (1)")

        # Get connection again and verify data persists
        conn2 = manager.get_connection()
        cursor = conn2.execute("SELECT id FROM test")
        row = cursor.fetchone()
        assert row["id"] == 1

        # Cleanup
        manager.close_memory_connection()

    def test_error_handling_in_get_connection(self, temp_db_path):
        """Test error handling in get_connection"""
        manager = ConnectionManager(temp_db_path)

        with mock.patch(
            "sqlite3.connect", side_effect=sqlite3.Error("Connection failed")
        ):
            with pytest.raises(sqlite3.Error):
                manager.get_connection()

    def test_path_normalization(self):
        """Test that paths are handled correctly"""
        # Test with relative path
        manager = ConnectionManager("./test.db")
        assert manager.db_path == "./test.db"

        # Test with absolute path
        abs_path = "/tmp/test.db"
        manager = ConnectionManager(abs_path)
        assert manager.db_path == abs_path

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_no_database_url_env_var(self, temp_db_path):
        """Test behavior when DATABASE_URL is not set"""
        manager = ConnectionManager(temp_db_path)
        assert manager.db_path == temp_db_path


if __name__ == "__main__":
    pytest.main([__file__])
