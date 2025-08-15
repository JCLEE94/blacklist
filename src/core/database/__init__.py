"""데이터베이스 모듈 - 스키마, 연결, 마이그레이션 관리"""

# SQLAlchemy imports for test compatibility
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker

from .connection_manager import ConnectionManager
from .migration_service import MigrationService
from .schema_manager import DatabaseSchema
from .table_definitions import TableDefinitions

# Backward compatibility
DatabaseManager = DatabaseSchema  # Alias for backward compatibility
get_database_schema = DatabaseSchema.get_instance
initialize_database = DatabaseSchema.initialize
migrate_database = DatabaseSchema.migrate

__all__ = [
    "DatabaseSchema",
    "DatabaseManager",  # Backward compatibility alias
    "MigrationService",
    "TableDefinitions",
    "ConnectionManager",
    "get_database_schema",
    "initialize_database",
    "migrate_database",
    # SQLAlchemy components for test patching
    "create_engine",
    "text",
    "scoped_session",
    "sessionmaker",
]
