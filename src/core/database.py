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
        # PostgreSQL 전용으로 변경
        self.database_url = database_url or os.environ.get(
            "DATABASE_URL", "postgresql://blacklist_user:blacklist_password_change_me@localhost:5432/blacklist"
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
                "application_name": "blacklist_app"
            }
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
        """PostgreSQL 전용 테이블 생성"""
        with self.engine.connect() as conn:
            # blacklist_entries 테이블 (호환성 유지)
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS blacklist_entries (
                    id SERIAL PRIMARY KEY,
                    ip_address INET NOT NULL,
                    first_seen TEXT,
                    last_seen TEXT,
                    detection_months TEXT,
                    is_active BOOLEAN DEFAULT true,
                    days_until_expiry INTEGER DEFAULT 90,
                    threat_level TEXT DEFAULT 'medium',
                    source TEXT NOT NULL DEFAULT 'unknown',
                    source_details TEXT,
                    country TEXT,
                    reason TEXT,
                    reg_date TEXT,
                    exp_date TEXT,
                    view_count INTEGER DEFAULT 0,
                    uuid TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    severity_score REAL DEFAULT 0.0,
                    confidence_level REAL DEFAULT 1.0,
                    tags TEXT,
                    last_verified TIMESTAMP,
                    verification_status TEXT DEFAULT 'unverified',
                    UNIQUE(ip_address)
                )
                """)
            )

            # blacklist 테이블 (메인 테이블)
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS blacklist (
                    id SERIAL PRIMARY KEY,
                    ip_address INET NOT NULL,
                    source TEXT NOT NULL,
                    threat_level TEXT DEFAULT 'medium',
                    description TEXT,
                    country TEXT,
                    detection_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT true
                )
                """)
            )

            # collection_logs 테이블
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS collection_logs (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    items_collected INTEGER DEFAULT 0,
                    details JSONB,
                    error_message TEXT,
                    duration_seconds REAL,
                    collection_type TEXT,
                    event TEXT NOT NULL
                )
                """)
            )

            # metadata 테이블
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
            )

            # auth_attempts 테이블 (인증 시도 추적)
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS auth_attempts (
                    id SERIAL PRIMARY KEY,
                    service TEXT NOT NULL,
                    success BOOLEAN DEFAULT false,
                    ip_address TEXT,
                    attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT,
                    user_agent TEXT
                )
                """)
            )

            # collection_history 테이블 (수집 이력)
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS collection_history (
                    id SERIAL PRIMARY KEY,
                    source TEXT NOT NULL,
                    collection_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    items_collected INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'completed',
                    details JSONB,
                    error_message TEXT,
                    duration_seconds REAL
                )
                """)
            )

            # collection_settings 테이블 (수집 설정)
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS collection_settings (
                    id SERIAL PRIMARY KEY,
                    source TEXT NOT NULL UNIQUE,
                    enabled BOOLEAN DEFAULT true,
                    schedule_cron TEXT,
                    config JSONB,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_by TEXT
                )
                """)
            )

            # collection_credentials 테이블 (수집기 자격증명)
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS collection_credentials (
                    id SERIAL PRIMARY KEY,
                    source TEXT NOT NULL UNIQUE,
                    username TEXT,
                    password_hash TEXT,
                    api_key TEXT,
                    config JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
                """)
            )

            # collection_sources 테이블 (데이터 소스 정보)
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS collection_sources (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    url TEXT,
                    source_type TEXT DEFAULT 'external',
                    description TEXT,
                    status TEXT DEFAULT 'active',
                    last_collection TIMESTAMP,
                    total_items INTEGER DEFAULT 0,
                    config JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
            )

            # system_logs 테이블 (시스템 로그)
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id SERIAL PRIMARY KEY,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    logger_name TEXT,
                    module TEXT,
                    function_name TEXT,
                    line_number INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    extra_data JSONB
                )
                """)
            )

            # cache_entries 테이블 (캐시 관리)
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
            )

            # system_status 테이블 (시스템 상태)
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS system_status (
                    id SERIAL PRIMARY KEY,
                    component TEXT NOT NULL UNIQUE,
                    status TEXT DEFAULT 'unknown',
                    message TEXT,
                    last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    check_count INTEGER DEFAULT 0,
                    config JSONB,
                    metrics JSONB
                )
                """)
            )

            # 업데이트 트리거 함수 생성
            conn.execute(
                text("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
                """)
            )
            
            # 트리거 적용 (updated_at 컬럼이 있는 테이블에만)
            tables_with_updated_at = [
                'blacklist', 'blacklist_entries', 'metadata',
                'collection_credentials', 'collection_sources'
            ]
            for table in tables_with_updated_at:
                conn.execute(
                    text(f"""
                    DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};
                    CREATE TRIGGER update_{table}_updated_at 
                        BEFORE UPDATE ON {table} 
                        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                    """)
                )
            
            conn.commit()
            logger.info("PostgreSQL tables created successfully")

    def create_indexes(self):
        """PostgreSQL 전용 최적화 인덱스 생성"""
        with self.engine.connect() as conn:
            # PostgreSQL 최적화 인덱스
            indexes = [
                # blacklist_entries 테이블 인덱스
                "CREATE INDEX IF NOT EXISTS idx_blacklist_entries_ip ON blacklist_entries USING btree (ip_address)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_entries_source ON blacklist_entries(source)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_entries_country ON blacklist_entries(country)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_entries_created_at ON blacklist_entries(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_entries_active ON blacklist_entries(is_active)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_entries_threat_level ON blacklist_entries(threat_level)",
                
                # blacklist 테이블 인덱스 (메인 테이블)
                "CREATE INDEX IF NOT EXISTS idx_blacklist_ip ON blacklist USING btree (ip_address)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_source ON blacklist(source)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_date ON blacklist(detection_date)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_active ON blacklist(is_active)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_created ON blacklist(created_at)",
                
                # 복합 인덱스 (쿼리 패턴 기반)
                "CREATE INDEX IF NOT EXISTS idx_blacklist_entries_ip_source ON blacklist_entries(ip_address, source)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_entries_source_active ON blacklist_entries(source, is_active)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_entries_country_threat ON blacklist_entries(country, threat_level)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_entries_created_source ON blacklist_entries(created_at, source)",
                
                # collection_logs 테이블 인덱스
                "CREATE INDEX IF NOT EXISTS idx_collection_logs_timestamp ON collection_logs(timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_collection_logs_source ON collection_logs(source)",
                "CREATE INDEX IF NOT EXISTS idx_collection_logs_status ON collection_logs(status)",
                "CREATE INDEX IF NOT EXISTS idx_collection_logs_source_status ON collection_logs(source, status)",
                
                # metadata 테이블 인덱스
                "CREATE INDEX IF NOT EXISTS idx_metadata_key ON metadata(key)",
                "CREATE INDEX IF NOT EXISTS idx_metadata_created ON metadata(created_at)",
                
                # PostgreSQL 전용 고급 인덱스
                # GIN 인덱스 (JSONB 검색용)
                "CREATE INDEX IF NOT EXISTS idx_collection_logs_details_gin ON collection_logs USING gin(details)",
                # 부분 인덱스 (조건부 인덱스)
                "CREATE INDEX IF NOT EXISTS idx_blacklist_active_only ON blacklist(ip_address) WHERE is_active = true",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_entries_active_only ON blacklist_entries(ip_address) WHERE is_active = true",
            ]

            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    conn.commit()
                    logger.debug(f"인덱스 생성 완료: {index_sql.split()[-1] if 'ON' in index_sql else 'custom'}")
                except Exception as e:
                    logger.warning(f"Index creation failed: {e}")
                    
            logger.info("All PostgreSQL indexes created successfully")

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
                backup_dir, 'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
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
