#!/usr/bin/env python3
"""
Unit tests for TableDefinitions class
Tests table creation and schema definitions.
"""

import pytest
import unittest.mock as mock
import sqlite3
import tempfile
import os

from src.core.database.table_definitions import TableDefinitions


class TestTableDefinitions:
    """Test cases for TableDefinitions class"""

    @pytest.fixture
    def mock_connection(self):
        """Create mock database connection"""
        return mock.Mock(spec=sqlite3.Connection)

    @pytest.fixture
    def table_definitions(self):
        """Create TableDefinitions instance"""
        return TableDefinitions()

    def test_create_blacklist_entries_table(self, mock_connection, table_definitions):
        """Test blacklist_entries table creation"""
        table_definitions.create_blacklist_entries_table(mock_connection)
        
        mock_connection.execute.assert_called_once()
        sql = mock_connection.execute.call_args[0][0]
        
        # Verify table structure
        assert "CREATE TABLE IF NOT EXISTS blacklist_entries" in sql
        assert "id INTEGER PRIMARY KEY AUTOINCREMENT" in sql
        assert "ip_address TEXT NOT NULL UNIQUE" in sql
        assert "source TEXT NOT NULL DEFAULT 'unknown'" in sql
        assert "threat_level TEXT DEFAULT 'medium'" in sql
        assert "severity_score REAL DEFAULT 0.0" in sql
        assert "confidence_level REAL DEFAULT 1.0" in sql

    def test_create_collection_logs_table(self, mock_connection, table_definitions):
        """Test collection_logs table creation"""
        table_definitions.create_collection_logs_table(mock_connection)
        
        mock_connection.execute.assert_called_once()
        sql = mock_connection.execute.call_args[0][0]
        
        # Verify table structure
        assert "CREATE TABLE IF NOT EXISTS collection_logs" in sql
        assert "id INTEGER PRIMARY KEY AUTOINCREMENT" in sql
        assert "timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP" in sql
        assert "source TEXT NOT NULL" in sql
        assert "status TEXT NOT NULL" in sql
        assert "items_collected INTEGER DEFAULT 0" in sql
        assert "execution_time_ms REAL DEFAULT 0.0" in sql
        assert "collection_type TEXT DEFAULT 'scheduled'" in sql

    def test_create_auth_attempts_table(self, mock_connection, table_definitions):
        """Test auth_attempts table creation"""
        table_definitions.create_auth_attempts_table(mock_connection)
        
        mock_connection.execute.assert_called_once()
        sql = mock_connection.execute.call_args[0][0]
        
        # Verify table structure
        assert "CREATE TABLE IF NOT EXISTS auth_attempts" in sql
        assert "id INTEGER PRIMARY KEY AUTOINCREMENT" in sql
        assert "ip_address TEXT NOT NULL" in sql
        assert "success BOOLEAN NOT NULL" in sql
        assert "service TEXT" in sql
        assert "risk_score REAL DEFAULT 0.0" in sql
        assert "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP" in sql

    def test_create_system_status_table(self, mock_connection, table_definitions):
        """Test system_status table creation"""
        table_definitions.create_system_status_table(mock_connection)
        
        mock_connection.execute.assert_called_once()
        sql = mock_connection.execute.call_args[0][0]
        
        # Verify table structure
        assert "CREATE TABLE IF NOT EXISTS system_status" in sql
        assert "component TEXT NOT NULL" in sql
        assert "status TEXT NOT NULL" in sql
        assert "response_time_ms REAL DEFAULT 0.0" in sql
        assert "cpu_usage REAL DEFAULT 0.0" in sql
        assert "memory_usage REAL DEFAULT 0.0" in sql
        assert "alert_level TEXT DEFAULT 'info'" in sql

    def test_create_cache_table(self, mock_connection, table_definitions):
        """Test cache_entries table creation"""
        table_definitions.create_cache_table(mock_connection)
        
        mock_connection.execute.assert_called_once()
        sql = mock_connection.execute.call_args[0][0]
        
        # Verify table structure
        assert "CREATE TABLE IF NOT EXISTS cache_entries" in sql
        assert "key TEXT PRIMARY KEY" in sql
        assert "value TEXT NOT NULL" in sql
        assert "ttl INTEGER NOT NULL" in sql
        assert "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP" in sql
        assert "priority INTEGER DEFAULT 1" in sql
        assert "cache_type TEXT DEFAULT 'general'" in sql

    def test_create_metadata_table(self, mock_connection, table_definitions):
        """Test metadata table creation"""
        table_definitions.create_metadata_table(mock_connection)
        
        mock_connection.execute.assert_called_once()
        sql = mock_connection.execute.call_args[0][0]
        
        # Verify table structure
        assert "CREATE TABLE IF NOT EXISTS metadata" in sql
        assert "key TEXT PRIMARY KEY" in sql
        assert "value TEXT NOT NULL" in sql
        assert "value_type TEXT DEFAULT 'string'" in sql
        assert "description TEXT" in sql
        assert "category TEXT DEFAULT 'general'" in sql
        assert "is_sensitive BOOLEAN DEFAULT 0" in sql

    def test_create_system_logs_table(self, mock_connection, table_definitions):
        """Test system_logs table creation"""
        table_definitions.create_system_logs_table(mock_connection)
        
        mock_connection.execute.assert_called_once()
        sql = mock_connection.execute.call_args[0][0]
        
        # Verify table structure
        assert "CREATE TABLE IF NOT EXISTS system_logs" in sql
        assert "id INTEGER PRIMARY KEY AUTOINCREMENT" in sql
        assert "level TEXT NOT NULL" in sql
        assert "message TEXT NOT NULL" in sql
        assert "component TEXT" in sql
        assert "details TEXT" in sql

    def test_create_all_tables_success(self, mock_connection, table_definitions):
        """Test successful creation of all tables"""
        result = table_definitions.create_all_tables(mock_connection)
        
        assert result is True
        # Should call execute for each table (7 tables)
        assert mock_connection.execute.call_count == 7
        mock_connection.commit.assert_called_once()

    def test_create_all_tables_exception(self, mock_connection, table_definitions):
        """Test create_all_tables with exception"""
        mock_connection.execute.side_effect = Exception("Database error")
        
        result = table_definitions.create_all_tables(mock_connection)
        
        assert result is False
        mock_connection.execute.assert_called()

    def test_create_all_tables_order(self, mock_connection, table_definitions):
        """Test that tables are created in correct order"""
        result = table_definitions.create_all_tables(mock_connection)
        
        assert result is True
        
        # Get all executed SQL statements
        executed_sqls = [call[0][0] for call in mock_connection.execute.call_args_list]
        
        # Verify metadata table is created first
        assert "CREATE TABLE IF NOT EXISTS metadata" in executed_sqls[0]
        
        # Verify all expected tables are created
        table_names = [
            "metadata",
            "blacklist_entries", 
            "collection_logs",
            "auth_attempts",
            "system_status",
            "cache_entries",
            "system_logs"
        ]
        
        for i, table_name in enumerate(table_names):
            assert f"CREATE TABLE IF NOT EXISTS {table_name}" in executed_sqls[i]

    @pytest.mark.integration
    def test_real_table_creation(self):
        """Integration test with real SQLite database"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            conn = sqlite3.connect(db_path)
            table_definitions = TableDefinitions()
            
            # Create all tables
            result = table_definitions.create_all_tables(conn)
            assert result is True
            
            # Verify tables exist
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            table_names = [row[0] for row in cursor.fetchall()]
            
            expected_tables = [
                "blacklist_entries",
                "collection_logs", 
                "auth_attempts",
                "system_status",
                "cache_entries",
                "metadata",
                "system_logs"
            ]
            
            for table in expected_tables:
                assert table in table_names
            
            conn.close()
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    @pytest.mark.integration
    def test_table_structure_validation(self):
        """Integration test to validate actual table structures"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            conn = sqlite3.connect(db_path)
            table_definitions = TableDefinitions()
            
            # Create all tables
            table_definitions.create_all_tables(conn)
            
            # Test blacklist_entries structure
            cursor = conn.execute("PRAGMA table_info(blacklist_entries)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}  # name: type
            
            assert "id" in columns
            assert "ip_address" in columns
            assert "source" in columns
            assert "threat_level" in columns
            assert "severity_score" in columns
            
            # Test collection_logs structure
            cursor = conn.execute("PRAGMA table_info(collection_logs)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            assert "id" in columns
            assert "timestamp" in columns
            assert "source" in columns
            assert "status" in columns
            assert "execution_time_ms" in columns
            
            conn.close()
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_static_method_access(self):
        """Test that all table creation methods are static"""
        # Should be able to call without instance
        mock_conn = mock.Mock()
        
        TableDefinitions.create_blacklist_entries_table(mock_conn)
        TableDefinitions.create_collection_logs_table(mock_conn)
        TableDefinitions.create_auth_attempts_table(mock_conn)
        TableDefinitions.create_system_status_table(mock_conn)
        TableDefinitions.create_cache_table(mock_conn)
        TableDefinitions.create_metadata_table(mock_conn)
        TableDefinitions.create_system_logs_table(mock_conn)
        
        # Each method should have been called once
        assert mock_conn.execute.call_count == 7

    def test_sql_injection_protection(self, mock_connection, table_definitions):
        """Test that table creation SQL is safe from injection"""
        # All table creation methods use static SQL without parameters
        # This test ensures no user input is directly concatenated
        
        table_definitions.create_blacklist_entries_table(mock_connection)
        sql = mock_connection.execute.call_args[0][0]
        
        # Verify it's a static CREATE TABLE statement
        assert sql.strip().startswith("CREATE TABLE IF NOT EXISTS")
        assert ";" not in sql or sql.count(";") <= 1  # Only trailing semicolon allowed
        assert "--" not in sql  # No SQL comments
        assert "'" not in sql or sql.count("'") % 2 == 0  # Balanced quotes

    def test_table_names_consistency(self, mock_connection):
        """Test that table names are consistent across methods"""
        table_definitions = TableDefinitions()
        
        # Create all tables and collect the table names
        table_definitions.create_all_tables(mock_connection)
        
        executed_sqls = [call[0][0] for call in mock_connection.execute.call_args_list]
        
        # Extract table names from SQL
        created_tables = []
        for sql in executed_sqls:
            if "CREATE TABLE IF NOT EXISTS" in sql:
                table_name = sql.split("CREATE TABLE IF NOT EXISTS")[1].split("(")[0].strip()
                created_tables.append(table_name)
        
        # Verify expected table names
        expected_tables = [
            "metadata",
            "blacklist_entries",
            "collection_logs", 
            "auth_attempts",
            "system_status",
            "cache_entries",
            "system_logs"
        ]
        
        assert len(created_tables) == len(expected_tables)
        for table in expected_tables:
            assert table in created_tables


if __name__ == "__main__":
    pytest.main([__file__])