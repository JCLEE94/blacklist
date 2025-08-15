#!/usr/bin/env python3
"""
Unit tests for src/core/database.py
Testing DatabaseManager and MigrationManager classes
"""
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock, call
import pytest
from datetime import datetime, timedelta

from src.core.database import DatabaseManager, MigrationService as MigrationManager


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
        with patch.dict(os.environ, {'DATABASE_URL': env_url}):
            db = DatabaseManager()
            assert db.database_url == env_url

    @patch('src.core.database.create_engine')
    @patch('src.core.database.scoped_session')
    @patch('src.core.database.sessionmaker')
    def test_postgresql_engine_configuration(self, mock_sessionmaker, mock_scoped, mock_engine):
        """Test PostgreSQL-specific engine configuration"""
        mock_engine_instance = Mock()
        mock_engine.return_value = mock_engine_instance
        
        db = DatabaseManager("postgresql://user:pass@localhost/db")
        
        # Verify create_engine was called with PostgreSQL settings
        mock_engine.assert_called_once()
        call_args = mock_engine.call_args
        
        assert call_args[0][0] == "postgresql://user:pass@localhost/db"
        assert call_args[1]['pool_size'] == 20
        assert call_args[1]['max_overflow'] == 40
        assert call_args[1]['pool_timeout'] == 30

    @patch('src.core.database.create_engine')
    @patch('src.core.database.scoped_session')
    @patch('src.core.database.sessionmaker')
    def test_sqlite_engine_configuration(self, mock_sessionmaker, mock_scoped, mock_engine):
        """Test SQLite-specific engine configuration"""
        mock_engine_instance = Mock()
        mock_engine.return_value = mock_engine_instance
        
        db = DatabaseManager("sqlite:///test.db")
        
        # Verify create_engine was called with SQLite settings
        mock_engine.assert_called_once()
        call_args = mock_engine.call_args
        
        assert call_args[0][0] == "sqlite:///test.db"
        assert call_args[1]['pool_size'] == 5
        assert call_args[1]['max_overflow'] == 10
        assert 'check_same_thread' in call_args[1]['connect_args']

    @patch('src.core.database.create_engine')
    @patch('src.core.database.scoped_session')
    @patch('src.core.database.sessionmaker')
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

    @patch('src.core.database.create_engine')
    @patch('src.core.database.scoped_session')
    @patch('src.core.database.sessionmaker')
    def test_create_tables(self, mock_sessionmaker, mock_scoped, mock_engine):
        """Test table creation"""
        mock_connection = Mock()
        mock_engine_instance = Mock()
        mock_engine_instance.connect.return_value.__enter__.return_value = mock_connection
        mock_engine.return_value = mock_engine_instance
        
        db = DatabaseManager("sqlite:///test.db")
        db._create_tables()
        
        # Verify connection was used and tables were created
        mock_engine_instance.connect.assert_called_once()
        assert mock_connection.execute.call_count >= 3  # blacklist_ip, ip_detection, daily_stats
        mock_connection.commit.assert_called_once()

    @patch('src.core.database.create_engine')
    @patch('src.core.database.scoped_session')
    @patch('src.core.database.sessionmaker')
    def test_create_indexes(self, mock_sessionmaker, mock_scoped, mock_engine):
        """Test index creation"""
        mock_connection = Mock()
        mock_engine_instance = Mock()
        mock_engine_instance.connect.return_value.__enter__.return_value = mock_connection
        mock_engine.return_value = mock_engine_instance
        
        db = DatabaseManager("sqlite:///test.db")
        db.create_indexes()
        
        # Verify connection was used and indexes were created
        mock_engine_instance.connect.assert_called_once()
        assert mock_connection.execute.call_count > 10  # Multiple indexes

    @patch('src.core.database.create_engine')
    @patch('src.core.database.scoped_session')
    @patch('src.core.database.sessionmaker')
    def test_create_indexes_with_failure(self, mock_sessionmaker, mock_scoped, mock_engine):
        """Test index creation with some failures"""
        mock_connection = Mock()
        mock_connection.execute.side_effect = [None, Exception("Index exists"), None]
        mock_engine_instance = Mock()
        mock_engine_instance.connect.return_value.__enter__.return_value = mock_connection
        mock_engine.return_value = mock_engine_instance
        
        db = DatabaseManager("sqlite:///test.db")
        
        # Should not raise exception, should continue with other indexes
        db.create_indexes()
        
        # Should have attempted multiple executes despite failure
        assert mock_connection.execute.call_count >= 3

    @patch('src.core.database.create_engine')
    @patch('src.core.database.scoped_session')
    @patch('src.core.database.sessionmaker')
    def test_optimize_database_sqlite(self, mock_sessionmaker, mock_scoped, mock_engine):
        """Test database optimization for SQLite"""
        mock_connection = Mock()
        mock_engine_instance = Mock()
        mock_engine_instance.connect.return_value.__enter__.return_value = mock_connection
        mock_engine.return_value = mock_engine_instance
        
        db = DatabaseManager("sqlite:///test.db")
        db.optimize_database()
        
        # Verify SQLite optimization commands
        mock_connection.execute.assert_any_call(Mock())  # PRAGMA optimize
        mock_connection.commit.assert_called()

    @patch('src.core.database.create_engine')
    @patch('src.core.database.scoped_session')
    @patch('src.core.database.sessionmaker')
    def test_optimize_database_postgresql(self, mock_sessionmaker, mock_scoped, mock_engine):
        """Test database optimization for PostgreSQL"""
        mock_connection = Mock()
        mock_engine_instance = Mock()
        mock_engine_instance.connect.return_value.__enter__.return_value = mock_connection
        mock_engine.return_value = mock_engine_instance
        
        db = DatabaseManager("postgresql://user:pass@localhost/db")
        db.optimize_database()
        
        # Verify PostgreSQL optimization command
        mock_connection.execute.assert_called()
        mock_connection.commit.assert_called()

    @patch('src.core.database.create_engine')
    @patch('src.core.database.scoped_session')
    @patch('src.core.database.sessionmaker')
    @patch('os.path.exists')
    @patch('shutil.copy2')
    @patch('os.makedirs')
    def test_backup_database_sqlite(self, mock_makedirs, mock_copy, mock_exists, 
                                   mock_sessionmaker, mock_scoped, mock_engine):
        """Test SQLite database backup"""
        mock_engine_instance = Mock()
        mock_engine.return_value = mock_engine_instance
        mock_exists.return_value = True
        
        db = DatabaseManager("sqlite:///test.db")
        
        backup_path = db.backup_database("/backup/test.db")
        
        mock_copy.assert_called_once_with("test.db", "/backup/test.db")
        assert backup_path == "/backup/test.db"

    @patch('src.core.database.create_engine')
    @patch('src.core.database.scoped_session')
    @patch('src.core.database.sessionmaker')
    def test_backup_database_postgresql(self, mock_sessionmaker, mock_scoped, mock_engine):
        """Test PostgreSQL database backup (warning case)"""
        mock_engine_instance = Mock()
        mock_engine.return_value = mock_engine_instance
        
        db = DatabaseManager("postgresql://user:pass@localhost/db")
        
        # Should return backup path but log warning about pg_dump
        backup_path = db.backup_database("/backup/test.sql")
        assert backup_path == "/backup/test.sql"

    @patch('src.core.database.create_engine')
    @patch('src.core.database.scoped_session')
    @patch('src.core.database.sessionmaker')
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

    @patch('src.core.database.create_engine')
    @patch('src.core.database.scoped_session')
    @patch('src.core.database.sessionmaker')
    def test_get_statistics(self, mock_sessionmaker, mock_scoped, mock_engine):
        """Test database statistics retrieval"""
        # Mock session and query results
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        
        # Mock query results
        mock_session.execute.side_effect = [
            Mock(scalar=Mock(return_value=100)),  # total_ips
            Mock(fetchall=Mock(return_value=[('malware', 50), ('phishing', 30)])),  # categories
            Mock(fetchall=Mock(return_value=[('2024-01', 20, 25), ('2024-02', 30, 35)])),  # monthly
        ]
        
        mock_scoped_instance = Mock()
        mock_scoped_instance.return_value = mock_session
        mock_scoped.return_value = mock_scoped_instance
        
        mock_engine_instance = Mock()
        mock_engine.return_value = mock_engine_instance
        
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024):
            
            db = DatabaseManager("sqlite:///test.db")
            stats = db.get_statistics()
            
            assert stats['total_ips'] == 100
            assert stats['categories'] == {'malware': 50, 'phishing': 30}
            assert len(stats['monthly']) == 2
            assert stats['database_size'] == 1024

    @patch('src.core.database.create_engine')
    @patch('src.core.database.scoped_session')
    @patch('src.core.database.sessionmaker')
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


class TestMigrationManager:
    """Unit tests for MigrationManager class"""

    def test_init(self):
        """Test MigrationManager initialization"""
        mock_db = Mock(spec=DatabaseManager)
        migration_mgr = MigrationManager(mock_db)
        
        assert migration_mgr.db == mock_db
        assert migration_mgr.migrations == []

    def test_add_migration(self):
        """Test adding a migration"""
        mock_db = Mock(spec=DatabaseManager)
        migration_mgr = MigrationManager(mock_db)
        
        up_func = Mock()
        down_func = Mock()
        
        migration_mgr.add_migration("1.0.0", up_func, down_func)
        
        assert len(migration_mgr.migrations) == 1
        assert migration_mgr.migrations[0]['version'] == "1.0.0"
        assert migration_mgr.migrations[0]['up'] == up_func
        assert migration_mgr.migrations[0]['down'] == down_func

    def test_add_migration_without_down(self):
        """Test adding a migration without down function"""
        mock_db = Mock(spec=DatabaseManager)
        migration_mgr = MigrationManager(mock_db)
        
        up_func = Mock()
        migration_mgr.add_migration("1.0.0", up_func)
        
        assert len(migration_mgr.migrations) == 1
        assert migration_mgr.migrations[0]['down'] is None

    def test_get_current_version_success(self):
        """Test getting current version successfully"""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_session.execute.return_value.scalar.return_value = "1.2.0"
        
        mock_db = Mock(spec=DatabaseManager)
        mock_db.Session.return_value = mock_session
        
        migration_mgr = MigrationManager(mock_db)
        version = migration_mgr.get_current_version()
        
        assert version == "1.2.0"

    def test_get_current_version_no_table(self):
        """Test getting current version when table doesn't exist"""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_session.execute.side_effect = Exception("no such table")
        
        mock_db = Mock(spec=DatabaseManager)
        mock_db.Session.return_value = mock_session
        
        migration_mgr = MigrationManager(mock_db)
        version = migration_mgr.get_current_version()
        
        assert version is None

    def test_init_migrations_table(self):
        """Test migration table initialization"""
        mock_connection = Mock()
        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=None)
        
        mock_engine = Mock()
        mock_engine.connect.return_value = mock_connection
        
        mock_db = Mock(spec=DatabaseManager)
        mock_db.engine = mock_engine
        
        migration_mgr = MigrationManager(mock_db)
        migration_mgr.init_migrations_table()
        
        mock_connection.execute.assert_called_once()
        mock_connection.commit.assert_called_once()

    def test_run_migrations_no_previous_version(self):
        """Test running migrations when no previous version exists"""
        # Mock database components
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        
        mock_db = Mock(spec=DatabaseManager)
        mock_db.Session.return_value = mock_session
        
        migration_mgr = MigrationManager(mock_db)
        
        # Mock methods
        migration_mgr.init_migrations_table = Mock()
        migration_mgr.get_current_version = Mock(return_value=None)
        
        # Add test migrations
        up_func1 = Mock()
        up_func2 = Mock()
        migration_mgr.add_migration("1.0.0", up_func1)
        migration_mgr.add_migration("1.1.0", up_func2)
        
        migration_mgr.run_migrations()
        
        # Verify both migrations ran
        up_func1.assert_called_once_with(mock_db)
        up_func2.assert_called_once_with(mock_db)
        
        # Verify versions were recorded
        assert mock_session.execute.call_count == 2
        mock_session.commit.call_count == 2

    def test_run_migrations_with_previous_version(self):
        """Test running migrations when previous version exists"""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        
        mock_db = Mock(spec=DatabaseManager)
        mock_db.Session.return_value = mock_session
        
        migration_mgr = MigrationManager(mock_db)
        
        # Mock methods
        migration_mgr.init_migrations_table = Mock()
        migration_mgr.get_current_version = Mock(return_value="1.0.0")
        
        # Add test migrations
        up_func1 = Mock()
        up_func2 = Mock()
        migration_mgr.add_migration("1.0.0", up_func1)  # Should not run
        migration_mgr.add_migration("1.1.0", up_func2)  # Should run
        
        migration_mgr.run_migrations()
        
        # Only newer migration should run
        up_func1.assert_not_called()
        up_func2.assert_called_once_with(mock_db)

    def test_run_migrations_with_failure(self):
        """Test migration failure handling"""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        
        mock_db = Mock(spec=DatabaseManager)
        mock_db.Session.return_value = mock_session
        
        migration_mgr = MigrationManager(mock_db)
        
        # Mock methods
        migration_mgr.init_migrations_table = Mock()
        migration_mgr.get_current_version = Mock(return_value=None)
        
        # Add migration that will fail
        up_func = Mock(side_effect=Exception("Migration failed"))
        migration_mgr.add_migration("1.0.0", up_func)
        
        # Should raise the exception
        with pytest.raises(Exception, match="Migration failed"):
            migration_mgr.run_migrations()
        
        up_func.assert_called_once_with(mock_db)