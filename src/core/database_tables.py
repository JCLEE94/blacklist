"""
데이터베이스 테이블 생성 모듈 (< 300 lines)
"""

import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)


def create_all_tables(engine):
    """PostgreSQL 전용 테이블 생성"""
    with engine.connect() as conn:
        # blacklist_entries 테이블 (호환성 유지)
        conn.execute(
            text(
                """
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
            """
            )
        )

        # blacklist 테이블 (메인 테이블)
        conn.execute(
            text(
                """
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
            """
            )
        )

        # collection_logs 테이블
        conn.execute(
            text(
                """
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
            """
            )
        )

        # metadata 테이블
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            )
        )

        # auth_attempts 테이블 (인증 시도 추적)
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS auth_attempts (
                id SERIAL PRIMARY KEY,
                service TEXT NOT NULL,
                success BOOLEAN DEFAULT false,
                ip_address TEXT,
                attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                error_message TEXT,
                user_agent TEXT
            )
            """
            )
        )

        # collection_history 테이블 (수집 이력)
        conn.execute(
            text(
                """
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
            """
            )
        )

        # collection_settings 테이블 (수집 설정)
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS collection_settings (
                id SERIAL PRIMARY KEY,
                source TEXT NOT NULL UNIQUE,
                enabled BOOLEAN DEFAULT true,
                schedule_cron TEXT,
                config JSONB,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by TEXT
            )
            """
            )
        )

        # collection_credentials 테이블 (수집기 자격증명)
        conn.execute(
            text(
                """
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
            """
            )
        )

        # collection_sources 테이블 (데이터 소스 정보)
        conn.execute(
            text(
                """
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
            """
            )
        )

        # system_logs 테이블 (시스템 로그)
        conn.execute(
            text(
                """
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
            """
            )
        )

        # cache_entries 테이블 (캐시 관리)
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS cache_entries (
                key TEXT PRIMARY KEY,
                value TEXT,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            )
        )

        # system_status 테이블 (시스템 상태)
        conn.execute(
            text(
                """
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
            """
            )
        )

        # 업데이트 트리거 함수 생성
        conn.execute(
            text(
                """
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
            """
            )
        )

        # 트리거 적용 (updated_at 컬럼이 있는 테이블에만)
        tables_with_updated_at = [
            "blacklist",
            "blacklist_entries",
            "metadata",
            "collection_credentials",
            "collection_sources",
        ]
        for table in tables_with_updated_at:
            conn.execute(
                text(
                    f"""
                DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};
                CREATE TRIGGER update_{table}_updated_at
                    BEFORE UPDATE ON {table}
                    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                """
                )
            )

        conn.commit()
        logger.info("PostgreSQL tables created successfully")
