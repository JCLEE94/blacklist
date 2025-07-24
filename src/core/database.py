"""
데이터베이스 관리 및 마이그레이션
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
        self.database_url = database_url or os.environ.get(
            "DATABASE_URL", "sqlite:///instance/blacklist.db"
        )

        # 데이터베이스별 최적화된 연결 풀 설정
        if self.database_url.startswith("postgresql"):
            self.engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=20,  # 기본 연결 수 증가
                max_overflow=40,  # 최대 오버플로우 증가
                pool_timeout=30,  # 연결 대기 시간
                pool_recycle=3600,  # 1시간마다 연결 재활용
                pool_pre_ping=True,  # 연결 유효성 검사
                echo=False,  # 쿼리 로깅 비활성화 (성능)
                future=True,  # SQLAlchemy 2.0 스타일
            )
        else:
            # SQLite 최적화 설정
            self.engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=5,  # SQLite는 적은 연결 수
                max_overflow=10,
                pool_timeout=20,
                pool_recycle=7200,  # 2시간
                connect_args={
                    "check_same_thread": False,
                    "timeout": 30,  # 잠금 대기 시간
                    "isolation_level": None,  # 자동 커밋 모드
                }
                if "sqlite" in self.database_url
                else {},
                echo=False,
                future=True,
            )

        # 세션 팩토리
        self.Session = scoped_session(sessionmaker(bind=self.engine))

    def init_db(self):
        """데이터베이스 초기화"""
        # 테이블 생성 (필요한 경우)
        self._create_tables()
        self.create_indexes()
        logger.info("Database initialized")

    def _create_tables(self):
        """필요한 테이블 생성"""
        with self.engine.connect() as conn:
            # blacklist_ip 테이블 (실제 DB 스키마와 일치)
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS blacklist_ip (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip VARCHAR(45) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    attack_type VARCHAR(50),
                    country VARCHAR(100),
                    source VARCHAR(100),
                    extra_data TEXT
                )
            """
                )
            )

            # ip_detection 테이블 (실제 DB 스키마와 일치)
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS ip_detection (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip VARCHAR(45) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source VARCHAR(50),
                    attack_type VARCHAR(50),
                    confidence_score REAL DEFAULT 1.0,
                    blacklist_ip_id INTEGER,
                    FOREIGN KEY (blacklist_ip_id) REFERENCES blacklist_ip(id)
                )
            """
                )
            )

            # daily_stats 테이블
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS daily_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE NOT NULL,
                    total_ips INTEGER DEFAULT 0,
                    new_ips INTEGER DEFAULT 0,
                    removed_ips INTEGER DEFAULT 0,
                    active_ips INTEGER DEFAULT 0,
                    malware_count INTEGER DEFAULT 0,
                    phishing_count INTEGER DEFAULT 0,
                    botnet_count INTEGER DEFAULT 0,
                    spam_count INTEGER DEFAULT 0,
                    other_count INTEGER DEFAULT 0,
                    country_stats TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                )
            )

            conn.commit()

    def create_indexes(self):
        """성능 최적화를 위한 인덱스 생성"""
        with self.engine.connect() as conn:
            # 기본 인덱스
            indexes = [
                # blacklist_ip 테이블 인덱스 (실제 DB 스키마와 일치)
                "CREATE INDEX IF NOT EXISTS idx_blacklist_ip ON blacklist_ip(ip)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_attack_type ON blacklist_ip(attack_type)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_country ON blacklist_ip(country)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_source ON blacklist_ip(source)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_created_at ON blacklist_ip(created_at)",
                # 복합 인덱스 (쿼리 패턴 기반)
                "CREATE INDEX IF NOT EXISTS idx_blacklist_ip_attack_type ON blacklist_ip(ip, attack_type)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_source_attack_type ON blacklist_ip(source, attack_type)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_country_attack_type ON blacklist_ip(country, attack_type)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_created_at_source ON blacklist_ip(created_at, source)",
                # ip_detection 테이블 인덱스 (실제 DB 스키마와 일치)
                "CREATE INDEX IF NOT EXISTS idx_detection_ip ON ip_detection(ip)",
                "CREATE INDEX IF NOT EXISTS idx_detection_created_at ON ip_detection(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_detection_source ON ip_detection(source)",
                "CREATE INDEX IF NOT EXISTS idx_detection_attack_type ON ip_detection(attack_type)",
                "CREATE INDEX IF NOT EXISTS idx_detection_confidence ON ip_detection(confidence_score)",
                # 복합 인덱스 (시간 범위 쿼리 최적화)
                "CREATE INDEX IF NOT EXISTS idx_detection_ip_created_at ON ip_detection(ip, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_detection_created_at_source ON ip_detection(created_at, source)",
                "CREATE INDEX IF NOT EXISTS idx_detection_month ON ip_detection(strftime('%Y-%m', created_at))",
                "CREATE INDEX IF NOT EXISTS idx_detection_month_ip ON ip_detection(strftime('%Y-%m', created_at), ip)",
                # daily_stats 테이블 인덱스
                "CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date DESC)",
                "CREATE INDEX IF NOT EXISTS idx_daily_stats_created ON daily_stats(created_at)",
                # 외래키 인덱스
                "CREATE INDEX IF NOT EXISTS idx_detection_blacklist_fk ON ip_detection(blacklist_ip_id)",
                # 전문 검색용 인덱스 (SQLite FTS)
                "CREATE INDEX IF NOT EXISTS idx_blacklist_as_name ON blacklist_ip(as_name)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_city ON blacklist_ip(city)",
            ]

            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    conn.commit()
                    logger.debug(f"인덱스 생성 완료: {index_sql.split()[-1]}")
                except Exception as e:
                    logger.warning(f"Index creation failed: {e}")

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

    def get_session(self):
        """Get database session"""
        return self.Session()

    def get_statistics(self) -> Dict:
        """데이터베이스 통계"""
        stats = {}

        with self.Session() as session:
            # 전체 IP 수
            stats["total_ips"] = session.execute(
                text("SELECT COUNT(DISTINCT ip) FROM blacklist_ip")
            ).scalar()

            # 카테고리별 통계
            category_stats = session.execute(
                text(
                    """
                    SELECT attack_type, COUNT(*) as count
                    FROM blacklist_ip
                    GROUP BY attack_type
                """
                )
            ).fetchall()
            stats["categories"] = {row[0]: row[1] for row in category_stats}

            # 월별 탐지 통계
            monthly_stats = session.execute(
                text(
                    """
                    SELECT strftime('%Y-%m', created_at) as month,
                           COUNT(DISTINCT ip) as unique_ips,
                           COUNT(*) as total_detections
                    FROM blacklist_ip
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
                text("DELETE FROM ip_detection WHERE detection_date < :cutoff"),
                {"cutoff": cutoff_date},
            )
            deleted_count += result.rowcount

            # 연결된 IP가 없는 블랙리스트 항목 삭제
            result = session.execute(
                text(
                    """
                    DELETE FROM blacklist_ip
                    WHERE id NOT IN (
                        SELECT DISTINCT blacklist_ip_id FROM ip_detection
                    )
                """
                )
            )
            deleted_count += result.rowcount

            session.commit()

        logger.info(f"Cleaned up {deleted_count} old records")
        return deleted_count


class MigrationManager:
    """데이터베이스 마이그레이션 관리"""

    def __init__(self, db_manager: DatabaseManager):
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
