"""Database comprehensive test suite

This module serves as the main import hub for all database-related tests.
Actual test implementations have been split into specialized modules for better maintainability.
"""

# Import all test classes from specialized modules
from .test_database_connections import TestConnectionManager
from .test_database_migrations import TestMigrationManager  
from .test_database_queries import TestQueryBuilder
from .test_database_transactions import TestTransactionManager
from .test_database_integration import TestDatabaseIntegration

# Re-export test classes for backward compatibility
__all__ = [
    'TestConnectionManager',
    'TestMigrationManager', 
    'TestQueryBuilder',
    'TestTransactionManager',
    'TestDatabaseIntegration'
]
