#!/usr/bin/env python3
"""
Unit tests for Database Migration functionality
Testing MigrationManager class
"""
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from src.core.database import MigrationService as MigrationManager
from src.core.database.schema_manager import DatabaseSchema as DatabaseManager


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
        assert migration_mgr.migrations[0]["version"] == "1.0.0"
        assert migration_mgr.migrations[0]["up"] == up_func
        assert migration_mgr.migrations[0]["down"] == down_func

    def test_add_migration_without_down(self):
        """Test adding a migration without down function"""
        mock_db = Mock(spec=DatabaseManager)
        migration_mgr = MigrationManager(mock_db)

        up_func = Mock()
        migration_mgr.add_migration("1.0.0", up_func)

        assert len(migration_mgr.migrations) == 1
        assert migration_mgr.migrations[0]["down"] is None

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
