"""
데이터베이스 마이그레이션 관리자 (< 200 lines)
"""

import logging
from typing import Optional

from sqlalchemy import text

logger = logging.getLogger(__name__)


class MigrationManager:
    """데이터베이스 마이그레이션 관리"""

    def __init__(self, db_manager):
        self.db = db_manager
        self.migrations = []

    def add_migration(
        self, version: str, up_func: callable, down_func: callable = None
    ):
        """마이그레이션 추가"""
        self.migrations.append({"version": version, "up": up_func, "down": down_func})

    def get_current_version(self) -> Optional[str]:
        """현재 데이터베이스 버전"""
        try:
            with self.db.Session() as session:
                result = session.execute(
                    text(
                        "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1"
                    )
                ).scalar()
                return result
        except Exception as e:
            # 마이그레이션 테이블이 없는 경우
            logger.debug(f"Migration table not found: {e}")
            return None

    def init_migrations_table(self):
        """마이그레이션 테이블 초기화"""
        with self.db.engine.connect() as conn:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(20) PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                )
            )
            conn.commit()

    def run_migrations(self):
        """마이그레이션 실행"""
        self.init_migrations_table()
        current_version = self.get_current_version()

        for migration in sorted(self.migrations, key=lambda x: x["version"]):
            if not current_version or migration["version"] > current_version:
                logger.info(f"Running migration: {migration['version']}")

                try:
                    migration["up"](self.db)

                    # 버전 기록
                    with self.db.Session() as session:
                        session.execute(
                            text(
                                "INSERT INTO schema_migrations (version) VALUES (:version)"
                            ),
                            {"version": migration["version"]},
                        )
                        session.commit()

                    logger.info(f"Migration {migration['version']} completed")

                except Exception as e:
                    logger.error(f"Migration {migration['version']} failed: {e}")
                    raise
