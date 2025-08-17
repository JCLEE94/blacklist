"""
마이그레이션 서비스

데이터베이스 스키마 마이그레이션을 처리합니다.
"""

import logging
import sqlite3
from typing import Optional

logger = logging.getLogger(__name__)


class MigrationService:
    """마이그레이션 서비스 클래스"""

    def __init__(self, connection_manager, table_definitions):
        self.connection_manager = connection_manager
        self.table_definitions = table_definitions
        self.schema_version = "2.0.0"

    def get_current_schema_version(self) -> Optional[str]:
        """현재 스키마 버전 조회"""
        try:
            with self.connection_manager.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT value FROM metadata WHERE key = ?", ("schema_version",)
                )
                row = cursor.fetchone()
                return row["value"] if row else None
        except Exception:
            return None

    def migrate_schema(self, from_version: str = None) -> bool:
        """스키마 마이그레이션"""
        current_version = self.get_current_schema_version()

        if current_version == self.schema_version:
            logger.info("스키마가 이미 최신 버전입니다.")
            return True

        try:
            with self.connection_manager.get_connection() as conn:
                # 메타데이터 테이블이 없으면 새로 생성
                if not current_version:
                    logger.info("메타데이터 테이블이 없습니다. 새로 생성합니다.")
                    self.table_definitions.create_metadata_table(conn)

                # 1.x에서 2.0으로 마이그레이션
                if not current_version or current_version.startswith("1."):
                    self._migrate_to_v2(conn)

                # 추가 마이그레이션이 필요한 경우 여기에 추가

                # 스키마 버전 업데이트
                self._record_schema_version(conn)
                conn.commit()

                logger.info(
                    f"스키마 마이그레이션 완료: {current_version} -> {self.schema_version}"
                )
                return True

        except Exception as e:
            logger.error(f"스키마 마이그레이션 실패: {e}")
            return False

    def _migrate_to_v2(self, conn: sqlite3.Connection):
        """버전 2.0으로 마이그레이션"""
        logger.info("스키마를 버전 2.0으로 마이그레이션합니다...")

        # 기존 테이블에 새 컨럼 추가
        new_columns = [
            # blacklist_entries 테이블
            ("blacklist_entries", "source", "TEXT DEFAULT 'unknown'"),
            ("blacklist_entries", "severity_score", "REAL DEFAULT 0.0"),
            ("blacklist_entries", "confidence_level", "REAL DEFAULT 1.0"),
            ("blacklist_entries", "tags", "TEXT"),
            ("blacklist_entries", "last_verified", "TIMESTAMP"),
            ("blacklist_entries", "verification_status", "TEXT DEFAULT 'unverified'"),
            # collection_logs 테이블
            ("collection_logs", "collection_type", "TEXT DEFAULT 'scheduled'"),
            ("collection_logs", "user_id", "TEXT"),
            ("collection_logs", "session_id", "TEXT"),
            ("collection_logs", "data_size_bytes", "INTEGER DEFAULT 0"),
            ("collection_logs", "memory_usage_mb", "REAL DEFAULT 0.0"),
            # system_logs 테이블
            ("system_logs", "additional_data", "TEXT"),
        ]

        for table, column, definition in new_columns:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                logger.info(f"컨럼 추가: {table}.{column}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    logger.debug(f"컨럼이 이미 존재함: {table}.{column}")
                else:
                    logger.warning(f"컨럼 추가 실패: {table}.{column} - {e}")

        # 새 테이블 생성
        self.table_definitions.create_auth_attempts_table(conn)
        self.table_definitions.create_system_status_table(conn)
        self.table_definitions.create_cache_table(conn)
        self.table_definitions.create_metadata_table(conn)
        self.table_definitions.create_system_logs_table(conn)  # Add missing table

    def _record_schema_version(self, conn: sqlite3.Connection):
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

    def cleanup_old_data(self, days_to_keep: int = 90) -> int:
        """오래된 데이터 정리"""
        deleted_count = 0

        try:
            with self.connection_manager.get_connection() as conn:
                # 오래된 수집 로그 삭제
                cursor = conn.execute(
                    """
                    DELETE FROM collection_logs 
                    WHERE timestamp < datetime('now', '-{} days')
                """.format(
                        days_to_keep
                    )
                )
                deleted_count += cursor.rowcount

                # 오래된 인증 시도 기록 삭제 (성공한 것만, 실패한 것은 보안상 더 오래 보관)
                cursor = conn.execute(
                    """
                    DELETE FROM auth_attempts 
                    WHERE timestamp < datetime('now', '-{} days') AND success = 1
                """.format(
                        days_to_keep
                    )
                )
                deleted_count += cursor.rowcount

                # 오래된 시스템 상태 기록 삭제
                cursor = conn.execute(
                    """
                    DELETE FROM system_status 
                    WHERE timestamp < datetime('now', '-{} days')
                """.format(
                        days_to_keep
                    )
                )
                deleted_count += cursor.rowcount

                # 만료된 캐시 항목 삭제
                cursor = conn.execute(
                    """
                    DELETE FROM cache_entries 
                    WHERE datetime(created_at, '+' || ttl || ' seconds') < datetime('now')
                """
                )
                deleted_count += cursor.rowcount

                # 오래된 시스템 로그 삭제
                try:
                    cursor = conn.execute(
                        """
                        DELETE FROM system_logs 
                        WHERE timestamp < datetime('now', '-{} days')
                    """.format(
                            days_to_keep
                        )
                    )
                    deleted_count += cursor.rowcount
                except sqlite3.OperationalError:
                    # system_logs 테이블이 아직 없을 수 있음
                    pass

                conn.commit()
                logger.info(f"데이터 정리 완료: {deleted_count}개 레코드 삭제")

        except Exception as e:
            logger.error(f"데이터 정리 중 오류: {e}")

        return deleted_count

    def vacuum_database(self) -> bool:
        """데이터베이스 압축"""
        try:
            with self.connection_manager.get_connection() as conn:
                conn.execute("VACUUM")
                logger.info("데이터베이스 압축 완료")
                return True
        except Exception as e:
            logger.error(f"데이터베이스 압축 실패: {e}")
            return False
