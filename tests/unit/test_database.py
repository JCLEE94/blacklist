#!/usr/bin/env python3
"""
Unit tests for src/core/database.py
Testing DatabaseManager and MigrationManager classes
"""
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from src.core.database import DatabaseManager
from src.core.database import MigrationService as MigrationManager


class TestDatabaseManager:
    """Unit tests for DatabaseManager class"""

    def test_init_with_default_url(self):
        """Test DatabaseManager initialization with default URL"""
        with patch.dict(os.environ, {}, clear=True):
            db = DatabaseManager()
            assert "sqlite:///instance/blacklist.db" in db.database_url

    def test_init_with_custom_url(self):
        """Test DatabaseManager initialization with custom URL"""
        custom_url = "sqlite:///test.db"
        db = DatabaseManager(custom_url)
        assert db.database_url == custom_url

    def test_init_with_environment_url(self):
        """Test DatabaseManager initialization with environment variable"""
        env_url = "postgresql://user:pass@localhost/db"
        with patch.dict(os.environ, {"DATABASE_URL": env_url}):
            db = DatabaseManager()
            assert db.database_url == env_url

    @patch("src.core.database.create_engine")
    @patch("src.core.database.scoped_session")
    @patch("src.core.database.sessionmaker")
    def test_postgresql_engine_configuration(
        self, mock_sessionmaker, mock_scoped, mock_engine
    ):
        """Test PostgreSQL-specific engine configuration"""
        mock_engine_instance = Mock()
        mock_engine.return_value = mock_engine_instance

        db = DatabaseManager("postgresql://user:pass@localhost/db")

        # Verify create_engine was called with PostgreSQL settings
        mock_engine.assert_called_once()
        call_args = mock_engine.call_args

        assert call_args[0][0] == "postgresql://user:pass@localhost/db"
        assert call_args[1]["pool_size"] == 20
        assert call_args[1]["max_overflow"] == 40
        assert call_args[1]["pool_timeout"] == 30

    @patch("src.core.database.create_engine")
    @patch("src.core.database.scoped_session")
    @patch("src.core.database.sessionmaker")
    def test_sqlite_engine_configuration(
        self, mock_sessionmaker, mock_scoped, mock_engine
    ):
        """Test SQLite-specific engine configuration"""
        mock_engine_instance = Mock()
        mock_engine.return_value = mock_engine_instance

        db = DatabaseManager("sqlite:///test.db")

        # Verify create_engine was called with SQLite settings
        mock_engine.assert_called_once()
        call_args = mock_engine.call_args

        assert call_args[0][0] == "sqlite:///test.db"
        assert call_args[1]["pool_size"] == 5
        assert call_args[1]["max_overflow"] == 10
        assert "check_same_thread" in call_args[1]["connect_args"]

    @patch("src.core.database.create_engine")
    @patch("src.core.database.scoped_session")
    @patch("src.core.database.sessionmaker")
    def test_init_db(self, mock_sessionmaker, mock_scoped, mock_engine):
        """Test database initialization"""
        mock_engine_instance = Mock()
        mock_engine.return_value = mock_engine_instance

        db = DatabaseManager("sqlite:///test.db")

        # Mock the methods that init_db calls
        db._create_tables = Mock()
        db.create_indexes = Mock()

        db.init_db()

        db._create_tables.assert_called_once()
        db.create_indexes.assert_called_once()

    @patch("src.core.database.create_engine")
    @patch("src.core.database.scoped_session")
    @patch("src.core.database.sessionmaker")
    def test_create_tables(self, mock_sessionmaker, mock_scoped, mock_engine):
        """Test table creation"""
        mock_connection = Mock()
        mock_engine_instance = Mock()
        mock_engine_instance.connect.return_value.__enter__.return_value = (
            mock_connection
        )
        mock_engine.return_value = mock_engine_instance

        db = DatabaseManager("sqlite:///test.db")
        db._create_tables()

        # Verify connection was used and tables were created
        mock_engine_instance.connect.assert_called_once()
        assert (
            mock_connection.execute.call_count >= 3
        )  # blacklist_ip, ip_detection, daily_stats
        mock_connection.commit.assert_called_once()

    @patch("src.core.database.create_engine")
    @patch("src.core.database.scoped_session")
    @patch("src.core.database.sessionmaker")
    def test_create_indexes(self, mock_sessionmaker, mock_scoped, mock_engine):
        """Test index creation"""
        mock_connection = Mock()
        mock_engine_instance = Mock()
        mock_engine_instance.connect.return_value.__enter__.return_value = (
            mock_connection
        )
        mock_engine.return_value = mock_engine_instance

        db = DatabaseManager("sqlite:///test.db")
        db.create_indexes()

        # Verify connection was used and indexes were created
        mock_engine_instance.connect.assert_called_once()
        assert mock_connection.execute.call_count > 10  # Multiple indexes

    @patch("src.core.database.create_engine")
    @patch("src.core.database.scoped_session")
    @patch("src.core.database.sessionmaker")
    def test_create_indexes_with_failure(
        self, mock_sessionmaker, mock_scoped, mock_engine
    ):
        """Test index creation with some failures"""
        mock_connection = Mock()
        mock_connection.execute.side_effect = [None, Exception("Index exists"), None]
        mock_engine_instance = Mock()
        mock_engine_instance.connect.return_value.__enter__.return_value = (
            mock_connection
        )
        mock_engine.return_value = mock_engine_instance

        db = DatabaseManager("sqlite:///test.db")

        # Should not raise exception, should continue with other indexes
        db.create_indexes()

        # Should have attempted multiple executes despite failure
        assert mock_connection.execute.call_count >= 3

    @patch("src.core.database.create_engine")
    @patch("src.core.database.scoped_session")
    @patch("src.core.database.sessionmaker")
    def test_optimize_database_sqlite(
        self, mock_sessionmaker, mock_scoped, mock_engine
    ):
        """Test database optimization for SQLite"""
        mock_connection = Mock()
        mock_engine_instance = Mock()
        mock_engine_instance.connect.return_value.__enter__.return_value = (
            mock_connection
        )
        mock_engine.return_value = mock_engine_instance

        db = DatabaseManager("sqlite:///test.db")
        db.optimize_database()

        # Verify SQLite optimization commands
        mock_connection.execute.assert_any_call(Mock())  # PRAGMA optimize
        mock_connection.commit.assert_called()

    @patch("src.core.database.create_engine")
    @patch("src.core.database.scoped_session")
    @patch("src.core.database.sessionmaker")
    def test_optimize_database_postgresql(
        self, mock_sessionmaker, mock_scoped, mock_engine
    ):
        """Test database optimization for PostgreSQL"""
        mock_connection = Mock()
        mock_engine_instance = Mock()
        mock_engine_instance.connect.return_value.__enter__.return_value = (
            mock_connection
        )
        mock_engine.return_value = mock_engine_instance

        db = DatabaseManager("postgresql://user:pass@localhost/db")
        db.optimize_database()

        # Verify PostgreSQL optimization command
        mock_connection.execute.assert_called()
        mock_connection.commit.assert_called()

    @patch("src.core.database.create_engine")
    @patch("src.core.database.scoped_session")
    @patch("src.core.database.sessionmaker")
    @patch("os.path.exists")
    @patch("shutil.copy2")
    @patch("os.makedirs")
    def test_backup_database_sqlite(
        self,
        mock_makedirs,
        mock_copy,
        mock_exists,
        mock_sessionmaker,
        mock_scoped,
        mock_engine,
    ):
        """Test SQLite database backup"""
        mock_engine_instance = Mock()
        mock_engine.return_value = mock_engine_instance
        mock_exists.return_value = True

        db = DatabaseManager("sqlite:///test.db")

        backup_path = db.backup_database("/backup/test.db")

        mock_copy.assert_called_once_with("test.db", "/backup/test.db")
        assert backup_path == "/backup/test.db"

    @patch("src.core.database.create_engine")
    @patch("src.core.database.scoped_session")
    @patch("src.core.database.sessionmaker")
    def test_backup_database_postgresql(
        self, mock_sessionmaker, mock_scoped, mock_engine
    ):
        """Test PostgreSQL database backup (warning case)"""
        mock_engine_instance = Mock()
        mock_engine.return_value = mock_engine_instance

        db = DatabaseManager("postgresql://user:pass@localhost/db")

        # Should return backup path but log warning about pg_dump
        backup_path = db.backup_database("/backup/test.sql")
        assert backup_path == "/backup/test.sql"

    @patch("src.core.database.create_engine")
    @patch("src.core.database.scoped_session")
    @patch("src.core.database.sessionmaker")
    def test_get_session(self, mock_sessionmaker, mock_scoped, mock_engine):
        """Test getting database session"""
        mock_session_instance = Mock()
        mock_scoped_instance = Mock()
        mock_scoped_instance.return_value = mock_session_instance
        mock_scoped.return_value = mock_scoped_instance

        mock_engine_instance = Mock()
        mock_engine.return_value = mock_engine_instance

        db = DatabaseManager("sqlite:///test.db")
        session = db.get_session()

        assert session == mock_session_instance

    @patch("src.core.database.create_engine")
    @patch("src.core.database.scoped_session")
    @patch("src.core.database.sessionmaker")
    def test_get_statistics(self, mock_sessionmaker, mock_scoped, mock_engine):
        """Test database statistics retrieval"""
        # Mock session and query results
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock query results
        mock_session.execute.side_effect = [
            Mock(scalar=Mock(return_value=100)),  # total_ips
            Mock(
                fetchall=Mock(return_value=[("malware", 50), ("phishing", 30)])
            ),  # categories
            Mock(
                fetchall=Mock(return_value=[("2024-01", 20, 25), ("2024-02", 30, 35)])
            ),  # monthly
        ]

        mock_scoped_instance = Mock()
        mock_scoped_instance.return_value = mock_session
        mock_scoped.return_value = mock_scoped_instance

        mock_engine_instance = Mock()
        mock_engine.return_value = mock_engine_instance

        with patch("os.path.exists", return_value=True), patch(
            "os.path.getsize", return_value=1024
        ):

            db = DatabaseManager("sqlite:///test.db")
            stats = db.get_statistics()

            assert stats["total_ips"] == 100
            assert stats["categories"] == {"malware": 50, "phishing": 30}
            assert len(stats["monthly"]) == 2
            assert stats["database_size"] == 1024

    @patch("src.core.database.create_engine")
    @patch("src.core.database.scoped_session")
    @patch("src.core.database.sessionmaker")
    def test_cleanup_old_data(self, mock_sessionmaker, mock_scoped, mock_engine):
        """Test cleanup of old data"""
        # Mock session and execute results
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock delete operations returning rowcount
        mock_result1 = Mock(rowcount=10)
        mock_result2 = Mock(rowcount=5)
        mock_session.execute.side_effect = [mock_result1, mock_result2]

        mock_scoped_instance = Mock()
        mock_scoped_instance.return_value = mock_session
        mock_scoped.return_value = mock_scoped_instance

        mock_engine_instance = Mock()
        mock_engine.return_value = mock_engine_instance

        db = DatabaseManager("sqlite:///test.db")
        deleted_count = db.cleanup_old_data(30)

        assert deleted_count == 15  # 10 + 5
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_called_once()


