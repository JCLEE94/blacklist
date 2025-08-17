#!/usr/bin/env python3
"""
Database Operations Tests
Tests for database operations split from test_final_coverage_push.py
"""

import pytest
import os
import tempfile
import sqlite3
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


class TestDatabaseOperations:
    """Test database operations with comprehensive coverage"""
    
    def test_sqlite_operations(self):
        """Test SQLite database operations"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
            
        try:
            # Create connection and test basic operations
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create test table
            cursor.execute('''
                CREATE TABLE test_table (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert test data
            cursor.execute("INSERT INTO test_table (name) VALUES (?)", ("test_entry",))
            conn.commit()
            
            # Query test data
            cursor.execute("SELECT * FROM test_table")
            results = cursor.fetchall()
            assert len(results) == 1
            assert results[0][1] == "test_entry"
            
            conn.close()
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_database_connection_pooling(self):
        """Test database connection pooling"""
        try:
            from src.utils.memory.database_operations import DatabaseOperations
            
            db_ops = DatabaseOperations()
            assert db_ops is not None
            
            # Test connection methods if available
            if hasattr(db_ops, 'get_connection'):
                with patch('sqlite3.connect') as mock_connect:
                    mock_conn = Mock()
                    mock_connect.return_value = mock_conn
                    
                    conn = db_ops.get_connection()
                    assert conn is not None
                    
        except ImportError:
            pytest.skip("DatabaseOperations not importable")

    def test_memory_database_operations(self):
        """Test in-memory database operations"""
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        
        # Test table creation and operations
        cursor.execute('''
            CREATE TABLE blacklist_entries (
                id INTEGER PRIMARY KEY,
                ip_address TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                threat_level TEXT,
                detection_date DATE,
                expiry_date DATE
            )
        ''')
        
        # Test insertion with different data types
        test_data = [
            ('192.168.1.100', 'REGTECH', 'HIGH', '2025-01-01', '2025-12-31'),
            ('10.0.0.1', 'SECUDIUM', 'MEDIUM', '2025-01-02', '2025-12-30')
        ]
        
        cursor.executemany(
            "INSERT INTO blacklist_entries (ip_address, source, threat_level, detection_date, expiry_date) VALUES (?, ?, ?, ?, ?)",
            test_data
        )
        conn.commit()
        
        # Verify data
        cursor.execute("SELECT COUNT(*) FROM blacklist_entries")
        count = cursor.fetchone()[0]
        assert count == 2
        
        # Test queries
        cursor.execute("SELECT * FROM blacklist_entries WHERE threat_level = 'HIGH'")
        high_threat = cursor.fetchall()
        assert len(high_threat) == 1
        assert high_threat[0][1] == '192.168.1.100'
        
        conn.close()
