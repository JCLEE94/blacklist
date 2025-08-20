"""
데이터베이스 인덱스 생성 모듈 (< 200 lines)
"""

import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)


def create_all_indexes(engine):
    """PostgreSQL 전용 최적화 인덱스 생성"""
    with engine.connect() as conn:
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
                logger.debug(
                    f"인덱스 생성 완료: {index_sql.split()[-1] if 'ON' in index_sql else 'custom'}"
                )
            except Exception as e:
                logger.warning(f"Index creation failed: {e}")

        logger.info("All PostgreSQL indexes created successfully")
