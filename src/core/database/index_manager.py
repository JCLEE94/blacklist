"""
인덱스 관리 모듈

데이터베이스 인덱스를 생성하고 최적화합니다.
"""

import logging
import sqlite3

logger = logging.getLogger(__name__)


class IndexManager:
    """인덱스 관리 클래스"""

    @staticmethod
    def create_indexes(conn: sqlite3.Connection):
        """인덱스 생성"""
        indexes = [
            # 블랙리스트 항목 인덱스
            "CREATE INDEX IF NOT EXISTS idx_blacklist_ip ON blacklist_entries(ip_address)",
            "CREATE INDEX IF NOT EXISTS idx_blacklist_active ON blacklist_entries(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_blacklist_source ON blacklist_entries(source)",
            "CREATE INDEX IF NOT EXISTS idx_blacklist_last_seen ON blacklist_entries(last_seen)",
            "CREATE INDEX IF NOT EXISTS idx_blacklist_threat_level ON blacklist_entries(threat_level)",
            # 수집 로그 인덱스
            "CREATE INDEX IF NOT EXISTS idx_collection_timestamp ON collection_logs(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_collection_source ON collection_logs(source)",
            "CREATE INDEX IF NOT EXISTS idx_collection_status ON collection_logs(status)",
            # 인증 시도 인덱스
            "CREATE INDEX IF NOT EXISTS idx_auth_timestamp ON auth_attempts(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_auth_ip ON auth_attempts(ip_address)",
            "CREATE INDEX IF NOT EXISTS idx_auth_success ON auth_attempts(success)",
            "CREATE INDEX IF NOT EXISTS idx_auth_service ON auth_attempts(service)",
            "CREATE INDEX IF NOT EXISTS idx_auth_suspicious ON auth_attempts(is_suspicious)",
            "CREATE INDEX IF NOT EXISTS idx_auth_blocked ON auth_attempts(blocked_until)",
            # 시스템 상태 인덱스
            "CREATE INDEX IF NOT EXISTS idx_status_timestamp ON system_status(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_status_component ON system_status(component)",
            "CREATE INDEX IF NOT EXISTS idx_status_status ON system_status(status)",
            "CREATE INDEX IF NOT EXISTS idx_status_alert_level ON system_status(alert_level)",
            # 캐시 인덱스
            "CREATE INDEX IF NOT EXISTS idx_cache_created ON cache_entries(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_cache_accessed ON cache_entries(accessed_at)",
            "CREATE INDEX IF NOT EXISTS idx_cache_type ON cache_entries(cache_type)",
            # 메타데이터 인덱스
            "CREATE INDEX IF NOT EXISTS idx_metadata_category ON metadata(category)",
            "CREATE INDEX IF NOT EXISTS idx_metadata_updated ON metadata(updated_at)",
            # 시스템 로그 인덱스
            "CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level)",
            "CREATE INDEX IF NOT EXISTS idx_system_logs_component ON system_logs(component)",
            # 복합 인덱스
            "CREATE INDEX IF NOT EXISTS idx_blacklist_active_source ON blacklist_entries(is_active, source)",
            "CREATE INDEX IF NOT EXISTS idx_auth_ip_timestamp ON auth_attempts(ip_address, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_collection_source_timestamp ON collection_logs(source, timestamp)",
        ]

        for index_sql in indexes:
            try:
                conn.execute(index_sql)
            except Exception as e:
                logger.warning(f"인덱스 생성 중 경고: {e}")

    @staticmethod
    def drop_index(conn: sqlite3.Connection, index_name: str):
        """특정 인덱스 삭제"""
        try:
            conn.execute(f"DROP INDEX IF EXISTS {index_name}")
            logger.info(f"인덱스 삭제: {index_name}")
        except Exception as e:
            logger.warning(f"인덱스 삭제 실패: {index_name} - {e}")

    @staticmethod
    def analyze_database(conn: sqlite3.Connection):
        """데이터베이스 통계 업데이트"""
        try:
            conn.execute("ANALYZE")
            logger.info("데이터베이스 통계 업데이트 완료")
        except Exception as e:
            logger.warning(f"데이터베이스 통계 업데이트 실패: {e}")
