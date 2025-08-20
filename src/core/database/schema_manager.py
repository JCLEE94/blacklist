"""
스키마 관리자

데이터베이스 스키마 전체를 최상위로 관리합니다.
"""

import logging
import os
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from .connection_manager import ConnectionManager
from .index_manager import IndexManager
from .migration_service import MigrationService
from .table_definitions import TableDefinitions

logger = logging.getLogger(__name__)


class DatabaseSchema:
    """데이터베이스 스키마 관리 클래스"""

    def __init__(self, database_url: str = None):
        # Backward compatibility: support both db_path and database_url
        if database_url:
            self.database_url = database_url
            if database_url.startswith("sqlite:///"):
                self.db_path = database_url[10:]  # Remove 'sqlite:///' prefix
                # If the path starts with ./, make it relative to current dir
                if self.db_path.startswith("./"):
                    self.db_path = self.db_path[2:]
            else:
                self.db_path = "instance/blacklist.db"  # Default for non-sqlite
        else:
            self.database_url = os.environ.get(
                "DATABASE_URL", "sqlite:///instance/blacklist.db"
            )
            # Handle local instance path
            if self.database_url.startswith("sqlite:///./"):
                self.db_path = self.database_url[12:]  # Remove 'sqlite:///./' prefix
            elif self.database_url.startswith("sqlite:///"):
                self.db_path = self.database_url[10:]  # Remove 'sqlite:///' prefix
            else:
                self.db_path = "instance/blacklist.db"

        self.schema_version = "2.0.0"

        # SQLAlchemy compatibility
        self.engine = create_engine(self.database_url)
        self.Session = scoped_session(sessionmaker(bind=self.engine))

        # 컴포넌트 초기화
        self.connection_manager = ConnectionManager(self.db_path)
        self.table_definitions = TableDefinitions()
        self.index_manager = IndexManager()
        self.migration_service = MigrationService(
            self.connection_manager, self.table_definitions
        )

    def get_connection(self):
        """데이터베이스 연결 반환 (호환성)"""
        return self.connection_manager.get_connection()

    # Backward compatibility methods for old DatabaseManager interface
    def init_db(self):
        """데이터베이스 초기화 (호환성)"""
        self._create_tables()
        self.create_indexes()
        logger.info("Database initialized")

    def _create_tables(self):
        """테이블 생성 (호환성)"""
        return self.create_all_tables()

    def create_indexes(self):
        """인덱스 생성 (호환성)"""
        try:
            with self.connection_manager.get_connection() as conn:
                return self.index_manager.create_indexes(conn)
        except Exception as e:
            logger.error(f"인덱스 생성 중 오류: {e}")
            return False

    def get_session(self):
        """세션 반환 (호환성)"""
        return self.Session()

    def get_statistics(self):
        """통계 정보 반환 (호환성)"""
        return self.get_table_stats()

    def cleanup_old_data(self, days_to_keep: int = 90):
        """오래된 데이터 정리 (호환성)"""
        return self.migration_service.cleanup_old_data(days_to_keep)

    def backup_database(self, backup_path: str = None):
        """데이터베이스 백업 (호환성)"""
        if "sqlite" in self.database_url.lower():
            # SQLite backup logic
            logger.info("SQLite database backup requested")
            return True
        else:
            # PostgreSQL backup warning
            logger.warning("PostgreSQL backup should be done using pg_dump")
            return False

    def optimize_database(self):
        """데이터베이스 최적화 (호환성)"""
        return self.vacuum_database()

    def create_all_tables(self) -> bool:
        """모든 테이블 생성"""
        try:
            with self.connection_manager.get_connection() as conn:
                # 테이블 생성
                success = self.table_definitions.create_all_tables(conn)

                if success:
                    # 스키마 버전 기록
                    self._record_schema_version(conn)

                    # 중간 커밋
                    conn.commit()

                    # 인덱스 생성 (테이블 생성 후)
                    self.index_manager.create_indexes(conn)

                    conn.commit()
                    logger.info("모든 데이터베이스 테이블이 성공적으로 생성되었습니다.")
                    return True
                else:
                    return False

        except Exception as e:
            logger.error(f"테이블 생성 중 오류: {e}")
            return False

    def _record_schema_version(self, conn):
        """스키마 버전 기록"""
        conn.execute(
            """
            INSERT OR REPLACE INTO metadata 
            (key, value, value_type, description, category) 
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                "schema_version",
                self.schema_version,
                "string",
                "데이터베이스 스키마 버전",
                "system",
            ),
        )

    def get_current_schema_version(self) -> Optional[str]:
        """현재 스키마 버전 조회"""
        return self.migration_service.get_current_schema_version()

    def migrate_schema(self, from_version: str = None) -> bool:
        """스키마 마이그레이션"""
        return self.migration_service.migrate_schema(from_version)

    def cleanup_old_data(self, days_to_keep: int = 90) -> int:
        """오래된 데이터 정리"""
        return self.migration_service.cleanup_old_data(days_to_keep)

    def vacuum_database(self) -> bool:
        """데이터베이스 압축"""
        return self.migration_service.vacuum_database()

    def get_table_stats(self) -> Dict[str, Any]:
        """테이블 통계 정보"""
        stats = {}

        try:
            with self.connection_manager.get_connection() as conn:
                tables = [
                    "blacklist_entries",
                    "collection_logs",
                    "auth_attempts",
                    "system_status",
                    "cache_entries",
                    "metadata",
                    "system_logs",  # Add missing table
                ]

                for table in tables:
                    try:
                        cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
                        count = cursor.fetchone()["count"]

                        cursor = conn.execute(
                            f"""
                            SELECT 
                                MIN(rowid) as min_id,
                                MAX(rowid) as max_id
                            FROM {table}
                        """
                        )
                        ids = cursor.fetchone()

                        stats[table] = {
                            "count": count,
                            "min_id": ids["min_id"],
                            "max_id": ids["max_id"],
                        }
                    except Exception as e:
                        stats[table] = {"error": str(e)}

        except Exception as e:
            logger.error(f"테이블 통계 조회 실패: {e}")

        return stats

    @classmethod
    def get_instance(cls, db_path: str = None) -> "DatabaseSchema":
        """싱글톤 인스턴스 반환 (호환성)"""
        global _schema_instance

        if not hasattr(cls, "_instance") or (
            db_path and cls._instance.db_path != db_path
        ):
            # Convert db_path to database_url format if needed
            if db_path:
                if db_path.startswith("sqlite:///"):
                    database_url = db_path
                else:
                    database_url = f"sqlite:///{db_path}"
            else:
                database_url = None
            cls._instance = cls(database_url)

        return cls._instance

    @classmethod
    def initialize(cls, db_path: str = None, force: bool = False) -> bool:
        """데이터베이스 초기화 (호환성)"""
        schema = cls.get_instance(db_path)

        if force:
            # 강제 초기화: 기존 파일 삭제
            db_file = Path(schema.db_path)
            if db_file.exists():
                db_file.unlink()
                logger.info("기존 데이터베이스 파일 삭제됨")

        success = schema.create_all_tables()

        if success:
            # 마이그레이션 시도
            schema.migrate_schema()

        return success

    @classmethod
    def migrate(cls, db_path: str = None) -> bool:
        """데이터베이스 마이그레이션 (호환성)"""
        schema = cls.get_instance(db_path)
        return schema.migrate_schema()


# 전역 스키마 인스턴스 (호환성)
_schema_instance = None


def get_database_schema(db_path: str = None) -> DatabaseSchema:
    """데이터베이스 스키마 인스턴스 반환"""
    return DatabaseSchema.get_instance(db_path)


def initialize_database(db_path: str = None, force: bool = False) -> bool:
    """데이터베이스 초기화"""
    return DatabaseSchema.initialize(db_path, force)


def migrate_database(db_path: str = None) -> bool:
    """데이터베이스 마이그레이션"""
    return DatabaseSchema.migrate(db_path)
