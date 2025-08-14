"""
데이터베이스 스키마 정의 및 마이그레이션

시스템에서 사용하는 모든 데이터베이스 테이블과 스키마를 정의합니다.
"""

import sqlite3
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseSchema:
    """데이터베이스 스키마 관리 클래스"""

    def __init__(self, db_path: str = "instance/blacklist.db"):
        self.db_path = db_path
        self.schema_version = "2.0.0"
        self._memory_connection = None  # Persistent connection for in-memory DBs
        
        # Handle DATABASE_URL environment variable
        import os
        if os.getenv('DATABASE_URL'):
            database_url = os.getenv('DATABASE_URL')
            if database_url.startswith("sqlite:///"):
                self.db_path = database_url.replace("sqlite:///", "")
            elif database_url == "sqlite:///:memory:":
                self.db_path = ":memory:"
        
    def get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결 반환"""
        
        # For in-memory databases, use persistent connection to avoid losing data
        if self.db_path == ":memory:":
            if self._memory_connection is None:
                self._memory_connection = sqlite3.connect(self.db_path)
                self._memory_connection.row_factory = sqlite3.Row
                self._memory_connection.execute("PRAGMA synchronous=OFF")  # Fast for memory
                self._memory_connection.execute("PRAGMA cache_size=10000")
                self._memory_connection.execute("PRAGMA temp_store=MEMORY")
            return self._memory_connection
        
        # For file-based databases, create new connections as before
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        return conn

    def create_all_tables(self) -> bool:
        """모든 테이블 생성"""
        try:
            with self.get_connection() as conn:
                # 메타데이터 테이블을 먼저 생성 (다른 테이블들이 의존할 수 있음)
                self._create_metadata_table(conn)
                
                # 블랙리스트 항목 테이블
                self._create_blacklist_entries_table(conn)
                
                # 수집 로그 테이블
                self._create_collection_logs_table(conn)
                
                # 인증 시도 테이블 (새로 추가)
                self._create_auth_attempts_table(conn)
                
                # 시스템 상태 테이블
                self._create_system_status_table(conn)
                
                # 캐시 테이블
                self._create_cache_table(conn)
                
                # 스키마 버전 기록
                self._record_schema_version(conn)
                
                # 중간 커밋
                conn.commit()
                
                # 인덱스 생성 (테이블 생성 후)
                self._create_indexes(conn)
                
                conn.commit()
                logger.info("모든 데이터베이스 테이블이 성공적으로 생성되었습니다.")
                return True
                
        except Exception as e:
            logger.error(f"테이블 생성 중 오류: {e}")
            return False

    def _create_blacklist_entries_table(self, conn: sqlite3.Connection):
        """블랙리스트 항목 테이블 생성"""
        conn.execute("""
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
        """)

    def _create_collection_logs_table(self, conn: sqlite3.Connection):
        """수집 로그 테이블 생성"""
        conn.execute("""
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
        """)

    def _create_auth_attempts_table(self, conn: sqlite3.Connection):
        """인증 시도 테이블 생성 (새로 추가)"""
        conn.execute("""
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
        """)

    def _create_system_status_table(self, conn: sqlite3.Connection):
        """시스템 상태 테이블 생성"""
        conn.execute("""
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
        """)

    def _create_cache_table(self, conn: sqlite3.Connection):
        """캐시 테이블 생성"""
        conn.execute("""
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
        """)

    def _create_metadata_table(self, conn: sqlite3.Connection):
        """메타데이터 테이블 생성"""
        conn.execute("""
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
        """)

    def _create_indexes(self, conn: sqlite3.Connection):
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
            
            # 복합 인덱스
            "CREATE INDEX IF NOT EXISTS idx_blacklist_active_source ON blacklist_entries(is_active, source)",
            "CREATE INDEX IF NOT EXISTS idx_auth_ip_timestamp ON auth_attempts(ip_address, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_collection_source_timestamp ON collection_logs(source, timestamp)"
        ]
        
        for index_sql in indexes:
            try:
                conn.execute(index_sql)
            except Exception as e:
                logger.warning(f"인덱스 생성 중 경고: {e}")

    def _record_schema_version(self, conn: sqlite3.Connection):
        """스키마 버전 기록"""
        conn.execute("""
            INSERT OR REPLACE INTO metadata 
            (key, value, value_type, description, category) 
            VALUES (?, ?, ?, ?, ?)
        """, (
            "schema_version", 
            self.schema_version, 
            "string", 
            "데이터베이스 스키마 버전", 
            "system"
        ))

    def get_current_schema_version(self) -> Optional[str]:
        """현재 스키마 버전 조회"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT value FROM metadata WHERE key = ?", 
                    ("schema_version",)
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
            with self.get_connection() as conn:
                # 메타데이터 테이블이 없으면 새로 생성
                if not current_version:
                    logger.info("메타데이터 테이블이 없습니다. 새로 생성합니다.")
                    self._create_metadata_table(conn)
                
                # 1.x에서 2.0으로 마이그레이션
                if not current_version or current_version.startswith("1."):
                    self._migrate_to_v2(conn)
                
                # 추가 마이그레이션이 필요한 경우 여기에 추가
                
                # 스키마 버전 업데이트
                self._record_schema_version(conn)
                conn.commit()
                
                logger.info(f"스키마 마이그레이션 완료: {current_version} -> {self.schema_version}")
                return True
                
        except Exception as e:
            logger.error(f"스키마 마이그레이션 실패: {e}")
            return False

    def _migrate_to_v2(self, conn: sqlite3.Connection):
        """버전 2.0으로 마이그레이션"""
        logger.info("스키마를 버전 2.0으로 마이그레이션합니다...")
        
        # 기존 테이블에 새 컬럼 추가
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
        ]
        
        for table, column, definition in new_columns:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                logger.info(f"컬럼 추가: {table}.{column}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    logger.debug(f"컬럼이 이미 존재함: {table}.{column}")
                else:
                    logger.warning(f"컬럼 추가 실패: {table}.{column} - {e}")
        
        # 새 테이블 생성
        self._create_auth_attempts_table(conn)
        self._create_system_status_table(conn)
        self._create_cache_table(conn)
        self._create_metadata_table(conn)
        
        # 새 인덱스 생성
        self._create_indexes(conn)

    def cleanup_old_data(self, days_to_keep: int = 90) -> int:
        """오래된 데이터 정리"""
        deleted_count = 0
        
        try:
            with self.get_connection() as conn:
                # 오래된 수집 로그 삭제
                cursor = conn.execute("""
                    DELETE FROM collection_logs 
                    WHERE timestamp < datetime('now', '-{} days')
                """.format(days_to_keep))
                deleted_count += cursor.rowcount
                
                # 오래된 인증 시도 기록 삭제 (성공한 것만, 실패한 것은 보안상 더 오래 보관)
                cursor = conn.execute("""
                    DELETE FROM auth_attempts 
                    WHERE timestamp < datetime('now', '-{} days') AND success = 1
                """.format(days_to_keep))
                deleted_count += cursor.rowcount
                
                # 오래된 시스템 상태 기록 삭제
                cursor = conn.execute("""
                    DELETE FROM system_status 
                    WHERE timestamp < datetime('now', '-{} days')
                """.format(days_to_keep))
                deleted_count += cursor.rowcount
                
                # 만료된 캐시 항목 삭제
                cursor = conn.execute("""
                    DELETE FROM cache_entries 
                    WHERE datetime(created_at, '+' || ttl || ' seconds') < datetime('now')
                """)
                deleted_count += cursor.rowcount
                
                conn.commit()
                logger.info(f"데이터 정리 완료: {deleted_count}개 레코드 삭제")
                
        except Exception as e:
            logger.error(f"데이터 정리 중 오류: {e}")
            
        return deleted_count

    def vacuum_database(self) -> bool:
        """데이터베이스 압축"""
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
                logger.info("데이터베이스 압축 완료")
                return True
        except Exception as e:
            logger.error(f"데이터베이스 압축 실패: {e}")
            return False

    def get_table_stats(self) -> Dict[str, Any]:
        """테이블 통계 정보"""
        stats = {}
        
        try:
            with self.get_connection() as conn:
                tables = [
                    "blacklist_entries",
                    "collection_logs", 
                    "auth_attempts",
                    "system_status",
                    "cache_entries",
                    "metadata"
                ]
                
                for table in tables:
                    try:
                        cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
                        count = cursor.fetchone()["count"]
                        
                        cursor = conn.execute(f"""
                            SELECT 
                                MIN(rowid) as min_id,
                                MAX(rowid) as max_id
                            FROM {table}
                        """)
                        ids = cursor.fetchone()
                        
                        stats[table] = {
                            "count": count,
                            "min_id": ids["min_id"],
                            "max_id": ids["max_id"]
                        }
                    except Exception as e:
                        stats[table] = {"error": str(e)}
                        
        except Exception as e:
            logger.error(f"테이블 통계 조회 실패: {e}")
            
        return stats


# 전역 스키마 인스턴스
_schema_instance = None

def get_database_schema(db_path: str = None) -> DatabaseSchema:
    """데이터베이스 스키마 인스턴스 반환"""
    global _schema_instance
    
    if _schema_instance is None or (db_path and _schema_instance.db_path != db_path):
        _schema_instance = DatabaseSchema(db_path or "instance/blacklist.db")
    
    return _schema_instance


def initialize_database(db_path: str = None, force: bool = False) -> bool:
    """데이터베이스 초기화"""
    schema = get_database_schema(db_path)
    
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


def migrate_database(db_path: str = None) -> bool:
    """데이터베이스 마이그레이션"""
    schema = get_database_schema(db_path)
    return schema.migrate_schema()