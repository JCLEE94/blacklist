"""
데이터베이스 관리 및 핵심 기능 (< 500 lines)
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)


class DatabaseManager:
    """데이터베이스 관리자"""

    def __init__(self, database_url: str = None):
        # PostgreSQL 전용으로 변경
        self.database_url = database_url or os.environ.get(
            "DATABASE_URL",
            "postgresql://blacklist_user:blacklist_password_change_me@localhost:5432/blacklist",
        )

        # PostgreSQL 전용 최적화된 연결 풀 설정
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=20,  # 기본 연결 수
            max_overflow=40,  # 최대 오버플로우
            pool_timeout=30,  # 연결 대기 시간
            pool_recycle=3600,  # 1시간마다 연결 재활용
            pool_pre_ping=True,  # 연결 유효성 검사
            echo=False,  # 쿼리 로깅 비활성화 (성능)
            future=True,  # SQLAlchemy 2.0 스타일
            # PostgreSQL 특화 설정
            connect_args={
                "options": "-c timezone=Asia/Seoul",
                "connect_timeout": 10,
                "application_name": "blacklist_app",
            },
        )

        # 세션 팩토리
        self.Session = scoped_session(sessionmaker(bind=self.engine))

    def init_db(self):
        """데이터베이스 초기화"""
        from .database_indexes import create_all_indexes
        from .database_tables import create_all_tables

        # 테이블 생성 (필요한 경우)
        create_all_tables(self.engine)
        create_all_indexes(self.engine)
        logger.info("Database initialized")

    def get_session(self):
        """Get database session"""
        return self.Session()

    def optimize_database(self):
        """데이터베이스 최적화"""
        with self.engine.connect() as conn:
            if "sqlite" in self.database_url:
                # SQLite 최적화
                conn.execute(text("PRAGMA optimize"))
                conn.execute(text("VACUUM"))
                conn.execute(text("ANALYZE"))
            elif "postgresql" in self.database_url:
                # PostgreSQL 최적화
                conn.execute(text("VACUUM ANALYZE"))

            conn.commit()

        logger.info("Database optimized")

    def backup_database(self, backup_path: str = None) -> str:
        """데이터베이스 백업"""
        if not backup_path:
            backup_dir = os.path.join(
                os.path.dirname(self.database_url.replace("sqlite:///", "")), "backups"
            )
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(
                backup_dir, f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
            )

        if "sqlite" in self.database_url:
            import shutil

            db_path = self.database_url.replace("sqlite:///", "")
            shutil.copy2(db_path, backup_path)
            logger.info(f"Database backed up to: {backup_path}")
        else:
            # PostgreSQL pg_dump 사용
            logger.warning("PostgreSQL backup requires pg_dump")

        return backup_path

    def get_statistics(self) -> Dict:
        """데이터베이스 통계"""
        stats = {}

        with self.Session() as session:
            # 전체 IP 수
            stats["total_ips"] = session.execute(
                text(
                    "SELECT COUNT(DISTINCT ip_address) FROM blacklist_entries WHERE is_active = 1"
                )
            ).scalar()

            # 소스별 통계
            source_stats = session.execute(
                text(
                    """
                    SELECT source, COUNT(*) as count
                    FROM blacklist_entries
                    WHERE is_active = 1
                    GROUP BY source
                """
                )
            ).fetchall()
            stats["sources"] = {row[0]: row[1] for row in source_stats}

            # 월별 탐지 통계
            monthly_stats = session.execute(
                text(
                    """
                    SELECT strftime('%Y-%m', created_at) as month,
                           COUNT(DISTINCT ip_address) as unique_ips,
                           COUNT(*) as total_detections
                    FROM blacklist_entries
                    WHERE is_active = 1
                    GROUP BY month
                    ORDER BY month DESC
                    LIMIT 12
                """
                )
            ).fetchall()
            stats["monthly"] = [
                {"month": row[0], "unique_ips": row[1], "detections": row[2]}
                for row in monthly_stats
            ]

            # 데이터베이스 크기
            if "sqlite" in self.database_url:
                db_path = self.database_url.replace("sqlite:///", "")
                if os.path.exists(db_path):
                    stats["database_size"] = os.path.getsize(db_path)

        return stats

    def cleanup_old_data(self, days: int = 90) -> int:
        """오래된 데이터 정리"""
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0

        with self.Session() as session:
            # 오래된 탐지 기록 삭제
            result = session.execute(
                text("DELETE FROM ip_detection WHERE detection_date < :cutof"),
                {"cutof": cutoff_date},
            )
            deleted_count += result.rowcount

            # 비활성화된 오래된 블랙리스트 항목 삭제
            result = session.execute(
                text(
                    """
                    DELETE FROM blacklist_entries
                    WHERE is_active = 0 AND updated_at < :cutoff
                """
                ),
                {"cutoff": cutoff_date},
            )
            deleted_count += result.rowcount

            session.commit()

        logger.info(f"Cleaned up {deleted_count} old records")
        return deleted_count
