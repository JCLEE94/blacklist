#!/usr/bin/env python3
"""
Unit tests for DatabaseSchema class
Tests schema management, table creation, and database operations.
"""

import os
import sqlite3
import tempfile
import unittest.mock as mock
from pathlib import Path

import pytest

from src.core.database.schema_manager import (
    DatabaseSchema,
    get_database_schema,
    initialize_database,
    migrate_database,
)


class TestDatabaseSchema:
    """Test cases for DatabaseSchema class"""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def schema_manager(self, temp_db_path):
        """Create DatabaseSchema instance with temporary database"""
        return DatabaseSchema(temp_db_path)

    def test_init_default_path(self):
        """Test DatabaseSchema initialization with default path"""
        schema = DatabaseSchema()
        assert schema.db_path == "instance/blacklist.db"
        assert schema.schema_version == "2.0.0"
        assert schema.connection_manager is not None
        assert schema.table_definitions is not None

    def test_init_custom_path(self, temp_db_path):
        """Test DatabaseSchema initialization with custom path"""
        schema = DatabaseSchema(temp_db_path)
        assert schema.db_path == temp_db_path
        assert schema.schema_version == "2.0.0"

    def test_get_connection(self, schema_manager):
        """Test get_connection method"""
        with mock.patch.object(
            schema_manager.connection_manager, "get_connection"
        ) as mock_conn:
            mock_conn.return_value = mock.Mock()
            conn = schema_manager.get_connection()
            mock_conn.assert_called_once()
            assert conn is not None

    def test_create_all_tables_success(self, schema_manager):
        """Test successful table creation"""
        with mock.patch.object(
            schema_manager.connection_manager, "get_connection"
        ) as mock_get_conn:
            mock_conn = mock.Mock()
            mock_get_conn.return_value.__enter__.return_value = mock_conn

            with mock.patch.object(
                schema_manager.table_definitions, "create_all_tables", return_value=True
            ):
                with mock.patch.object(schema_manager.index_manager, "create_indexes"):
                    result = schema_manager.create_all_tables()

                    assert result is True
                    mock_conn.commit.assert_called()
                    mock_conn.execute.assert_called()  # _record_schema_version

    def test_create_all_tables_failure(self, schema_manager):
        """Test table creation failure"""
        with mock.patch.object(
            schema_manager.connection_manager, "get_connection"
        ) as mock_get_conn:
            mock_conn = mock.Mock()
            mock_get_conn.return_value.__enter__.return_value = mock_conn

            with mock.patch.object(
                schema_manager.table_definitions,
                "create_all_tables",
                return_value=False,
            ):
                result = schema_manager.create_all_tables()
                assert result is False

    def test_create_all_tables_exception(self, schema_manager):
        """Test table creation with exception"""
        with mock.patch.object(
            schema_manager.connection_manager,
            "get_connection",
            side_effect=Exception("DB Error"),
        ):
            result = schema_manager.create_all_tables()
            assert result is False

    def test_record_schema_version(self, schema_manager):
        """Test _record_schema_version method"""
        mock_conn = mock.Mock()
        schema_manager._record_schema_version(mock_conn)

        # Verify INSERT query was called with correct parameters
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        assert "INSERT OR REPLACE INTO metadata" in call_args[0][0]
        assert call_args[0][1][0] == "schema_version"
        assert call_args[0][1][1] == "2.0.0"

    def test_get_current_schema_version(self, schema_manager):
        """Test get_current_schema_version method"""
        with mock.patch.object(
            schema_manager.migration_service,
            "get_current_schema_version",
            return_value="1.0.0",
        ):
            version = schema_manager.get_current_schema_version()
            assert version == "1.0.0"

    def test_migrate_schema(self, schema_manager):
        """Test migrate_schema method"""
        with mock.patch.object(
            schema_manager.migration_service, "migrate_schema", return_value=True
        ):
            result = schema_manager.migrate_schema("1.0.0")
            assert result is True
            schema_manager.migration_service.migrate_schema.assert_called_once_with(
                "1.0.0"
            )

    def test_cleanup_old_data(self, schema_manager):
        """Test cleanup_old_data method"""
        with mock.patch.object(
            schema_manager.migration_service, "cleanup_old_data", return_value=42
        ):
            result = schema_manager.cleanup_old_data(30)
            assert result == 42
            schema_manager.migration_service.cleanup_old_data.assert_called_once_with(
                30
            )

    def test_vacuum_database(self, schema_manager):
        """Test vacuum_database method"""
        with mock.patch.object(
            schema_manager.migration_service, "vacuum_database", return_value=True
        ):
            result = schema_manager.vacuum_database()
            assert result is True

    def test_get_table_stats_success(self, schema_manager):
        """Test successful get_table_stats"""
        mock_cursor = mock.Mock()
        mock_cursor.fetchone.side_effect = [
            {"count": 10},  # COUNT query
            {"min_id": 1, "max_id": 10},  # MIN/MAX query
        ]

        mock_conn = mock.Mock()
        mock_conn.execute.return_value = mock_cursor

        with mock.patch.object(
            schema_manager.connection_manager, "get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_conn

            stats = schema_manager.get_table_stats()

            assert "blacklist_entries" in stats
            assert stats["blacklist_entries"]["count"] == 10
            assert stats["blacklist_entries"]["min_id"] == 1
            assert stats["blacklist_entries"]["max_id"] == 10

    def test_get_table_stats_with_error(self, schema_manager):
        """Test get_table_stats with table error"""
        mock_conn = mock.Mock()
        mock_conn.execute.side_effect = Exception("Table not found")

        with mock.patch.object(
            schema_manager.connection_manager, "get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_conn

            stats = schema_manager.get_table_stats()

            # All tables should have error entries
            for table in ["blacklist_entries", "collection_logs", "auth_attempts"]:
                assert table in stats
                assert "error" in stats[table]

    def test_get_table_stats_connection_error(self, schema_manager):
        """Test get_table_stats with connection error"""
        with mock.patch.object(
            schema_manager.connection_manager,
            "get_connection",
            side_effect=Exception("Connection failed"),
        ):
            stats = schema_manager.get_table_stats()
            assert stats == {}

    def test_get_instance_singleton(self, temp_db_path):
        """Test singleton behavior of get_instance"""
        instance1 = DatabaseSchema.get_instance(temp_db_path)
        instance2 = DatabaseSchema.get_instance(temp_db_path)
        assert instance1 is instance2

    def test_get_instance_different_path(self, temp_db_path):
        """Test get_instance with different paths creates new instance"""
        instance1 = DatabaseSchema.get_instance(temp_db_path)

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db_path2 = f.name

        try:
            instance2 = DatabaseSchema.get_instance(temp_db_path2)
            assert instance1 is not instance2
            assert instance1.db_path != instance2.db_path
        finally:
            if os.path.exists(temp_db_path2):
                os.unlink(temp_db_path2)

    def test_initialize_without_force(self, temp_db_path):
        """Test initialize method without force flag"""
        with mock.patch.object(DatabaseSchema, "get_instance") as mock_get_instance:
            mock_schema = mock.Mock()
            mock_schema.create_all_tables.return_value = True
            mock_schema.migrate_schema.return_value = True
            mock_get_instance.return_value = mock_schema

            result = DatabaseSchema.initialize(temp_db_path, force=False)

            assert result is True
            mock_schema.create_all_tables.assert_called_once()
            mock_schema.migrate_schema.assert_called_once()

    def test_initialize_with_force(self, temp_db_path):
        """Test initialize method with force flag"""
        # Create a dummy file to be deleted
        Path(temp_db_path).touch()
        assert os.path.exists(temp_db_path)

        with mock.patch.object(DatabaseSchema, "get_instance") as mock_get_instance:
            mock_schema = mock.Mock()
            mock_schema.db_path = temp_db_path
            mock_schema.create_all_tables.return_value = True
            mock_schema.migrate_schema.return_value = True
            mock_get_instance.return_value = mock_schema

            result = DatabaseSchema.initialize(temp_db_path, force=True)

            assert result is True
            assert not os.path.exists(temp_db_path)  # File should be deleted
            mock_schema.create_all_tables.assert_called_once()
            mock_schema.migrate_schema.assert_called_once()

    def test_migrate_class_method(self, temp_db_path):
        """Test migrate class method"""
        with mock.patch.object(DatabaseSchema, "get_instance") as mock_get_instance:
            mock_schema = mock.Mock()
            mock_schema.migrate_schema.return_value = True
            mock_get_instance.return_value = mock_schema

            result = DatabaseSchema.migrate(temp_db_path)

            assert result is True
            mock_schema.migrate_schema.assert_called_once()


class TestModuleFunctions:
    """Test module-level functions"""

    def test_get_database_schema(self):
        """Test get_database_schema function"""
        with mock.patch.object(DatabaseSchema, "get_instance") as mock_get_instance:
            mock_schema = mock.Mock()
            mock_get_instance.return_value = mock_schema

            result = get_database_schema("test.db")

            assert result is mock_schema
            mock_get_instance.assert_called_once_with("test.db")

    def test_initialize_database(self):
        """Test initialize_database function"""
        with mock.patch.object(
            DatabaseSchema, "initialize", return_value=True
        ) as mock_initialize:
            result = initialize_database("test.db", force=True)

            assert result is True
            mock_initialize.assert_called_once_with("test.db", True)

    def test_migrate_database(self):
        """Test migrate_database function"""
        with mock.patch.object(
            DatabaseSchema, "migrate", return_value=True
        ) as mock_migrate:
            result = migrate_database("test.db")

            assert result is True
            mock_migrate.assert_called_once_with("test.db")


if __name__ == "__main__":
    pytest.main([__file__])
