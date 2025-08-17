"""
테이블 정의 모듈

모든 데이터베이스 테이블의 스키마를 정의하고 생성합니다.
"""

import logging
import sqlite3

logger = logging.getLogger(__name__)


class TableDefinitions:
    """테이블 정의 클래스"""

    @staticmethod
    def create_blacklist_entries_table(conn: sqlite3.Connection):
        """블랙리스트 항목 테이블 생성"""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS blacklist_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL UNIQUE,
                first_seen TEXT,
                last_seen TEXT,
                detection_months TEXT,  -- JSON 배열
                is_active BOOLEAN DEFAULT 1,
                days_until_expiry INTEGER DEFAULT 90,
                threat_level TEXT DEFAULT 'medium',
                source TEXT NOT NULL DEFAULT 'unknown',  -- 출처 필드 강제
                source_details TEXT,  -- JSON 객체
                country TEXT,
                reason TEXT,
                reg_date TEXT,
                exp_date TEXT,
                view_count INTEGER DEFAULT 0,
                uuid TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                -- 새로운 필드들
                severity_score REAL DEFAULT 0.0,
                confidence_level REAL DEFAULT 1.0,
                tags TEXT,  -- JSON 배열
                last_verified TIMESTAMP,
                verification_status TEXT DEFAULT 'unverified'
            )
        """
        )

    @staticmethod
    def create_collection_logs_table(conn: sqlite3.Connection):
        """수집 로그 테이블 생성"""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS collection_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT NOT NULL,
                status TEXT NOT NULL,
                items_collected INTEGER DEFAULT 0,
                items_new INTEGER DEFAULT 0,
                items_updated INTEGER DEFAULT 0,
                items_failed INTEGER DEFAULT 0,
                execution_time_ms REAL DEFAULT 0.0,
                error_message TEXT,
                details TEXT,  -- JSON 객체
                -- 새로운 필드들
                collection_type TEXT DEFAULT 'scheduled',
                user_id TEXT,
                session_id TEXT,
                data_size_bytes INTEGER DEFAULT 0,
                memory_usage_mb REAL DEFAULT 0.0
            )
        """
        )

    @staticmethod
    def create_auth_attempts_table(conn: sqlite3.Connection):
        """인증 시도 테이블 생성 (새로 추가)"""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Add created_at for compatibility
                ip_address TEXT NOT NULL,
                user_agent TEXT,
                endpoint TEXT,
                method TEXT DEFAULT 'POST',
                success BOOLEAN NOT NULL,
                username TEXT,
                service TEXT,  -- REGTECH, SECUDIUM, API, WEB
                failure_reason TEXT,
                session_id TEXT,
                geographic_location TEXT,
                -- 보안 분석 필드
                risk_score REAL DEFAULT 0.0,
                is_suspicious BOOLEAN DEFAULT 0,
                blocked_until TIMESTAMP,
                attempt_count INTEGER DEFAULT 1,
                fingerprint TEXT  -- 브라우저/클라이언트 식별자
            )
        """
        )

    @staticmethod
    def create_system_status_table(conn: sqlite3.Connection):
        """시스템 상태 테이블 생성"""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS system_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                component TEXT NOT NULL,
                status TEXT NOT NULL,  -- healthy, degraded, unhealthy
                response_time_ms REAL DEFAULT 0.0,
                cpu_usage REAL DEFAULT 0.0,
                memory_usage REAL DEFAULT 0.0,
                disk_usage REAL DEFAULT 0.0,
                error_count INTEGER DEFAULT 0,
                details TEXT,  -- JSON 객체
                -- 알림 관련 필드
                alert_level TEXT DEFAULT 'info',  -- info, warning, error, critical
                alert_sent BOOLEAN DEFAULT 0,
                resolved_at TIMESTAMP
            )
        """
        )

    @staticmethod
    def create_cache_table(conn: sqlite3.Connection):
        """캐시 테이블 생성"""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache_entries (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,  -- JSON 직렬화된 데이터
                ttl INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                size_bytes INTEGER DEFAULT 0,
                -- 캐시 정책 필드
                priority INTEGER DEFAULT 1,  -- 1=낮음, 5=높음
                cache_type TEXT DEFAULT 'general'  -- api, data, session, temp
            )
        """
        )

    @staticmethod
    def create_metadata_table(conn: sqlite3.Connection):
        """메타데이터 테이블 생성"""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                value_type TEXT DEFAULT 'string',  -- string, json, int, float, bool
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                -- 설정 관리 필드
                category TEXT DEFAULT 'general',
                is_sensitive BOOLEAN DEFAULT 0,
                requires_restart BOOLEAN DEFAULT 0
            )
        """
        )

    # Missing system_logs table that tests expect
    @staticmethod
    def create_system_logs_table(conn: sqlite3.Connection):
        """시스템 로그 테이블 생성 (테스트 호환성)"""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                component TEXT,
                details TEXT,  -- JSON 객체
                additional_data TEXT,  -- JSON 객체 (추가 데이터)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

    @classmethod
    def create_all_tables(cls, conn: sqlite3.Connection):
        """모든 테이블 생성"""
        try:
            # 메타데이터 테이블을 먼저 생성 (다른 테이블들이 의존할 수 있음)
            cls.create_metadata_table(conn)

            # 블랙리스트 항목 테이블
            cls.create_blacklist_entries_table(conn)

            # 수집 로그 테이블
            cls.create_collection_logs_table(conn)

            # 인증 시도 테이블 (새로 추가)
            cls.create_auth_attempts_table(conn)

            # 시스템 상태 테이블
            cls.create_system_status_table(conn)

            # 캐시 테이블
            cls.create_cache_table(conn)

            # 시스템 로그 테이블 (테스트 호환성)
            cls.create_system_logs_table(conn)

            # 중간 커밋
            conn.commit()
            logger.info("모든 데이터베이스 테이블이 성공적으로 생성되었습니다.")
            return True

        except Exception as e:
            logger.error(f"테이블 생성 중 오류: {e}")
            return False
