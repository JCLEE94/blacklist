#!/usr/bin/env python3
"""
데이터베이스 운영 기능 - PostgreSQL 전용

PostgreSQL 데이터베이스 초기화, 테이블 관리, 트랜잭션 처리 등 DB 관련 기능을 제공합니다.
"""

import logging
import os
import psycopg2
from datetime import datetime
from typing import Any, Dict


class DatabaseOperationsMixin:
    """데이터베이스 운영 기능을 제공하는 믹스인"""

    def __init__(self):
        """Initialize database operations mixin"""
        # Initialize logger if not already present
        if not hasattr(self, "logger"):
            self.logger = logging.getLogger(__name__)
        # Call super() with try/except to handle case where there's no parent
        try:
            super().__init__()
        except TypeError:
            # If there's no parent class with __init__, that's okay
            pass

    def initialize_database_tables(self) -> Dict[str, Any]:
        """PostgreSQL 데이터베이스 테이블 강제 초기화"""
        try:
            # Use PostgreSQL database URL from environment
            database_url = os.environ.get(
                "DATABASE_URL",
                "postgresql://blacklist_user:blacklist_standalone_password_change_me@172.25.0.10:5432/blacklist",
            )

            self.logger.info(f"Initializing PostgreSQL database tables: {database_url}")

            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()

            # Create blacklist_ips table (aligned with main schema)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS blacklist_ips (
                    id SERIAL PRIMARY KEY,
                    ip_address VARCHAR(45) NOT NULL UNIQUE,
                    first_seen TIMESTAMP,
                    last_seen TIMESTAMP,
                    detection_months TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
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
                    verification_status TEXT DEFAULT 'unverified'
                )
                """
            )

            # Create collection_logs table if not exists (with correct schema)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_logs (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    items_collected INTEGER DEFAULT 0,
                    items_new INTEGER DEFAULT 0,
                    items_updated INTEGER DEFAULT 0,
                    items_failed INTEGER DEFAULT 0,
                    execution_time_ms REAL DEFAULT 0.0,
                    error_message TEXT,
                    details TEXT,
                    collection_type TEXT DEFAULT 'scheduled',
                    user_id TEXT,
                    session_id TEXT,
                    data_size_bytes INTEGER DEFAULT 0,
                    memory_usage_mb REAL DEFAULT 0.0
                )
                """
            )

            conn.commit()
            conn.close()

            return {
                "success": True,
                "message": "Database tables initialized successfully",
                "db_path": self.blacklist_manager.database_url if self.blacklist_manager else "postgresql://",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _ensure_log_table(self):
        """수집 로그 테이블 생성 확인 - PostgreSQL only"""
        # PostgreSQL only - table created during database initialization
        pass

    def _save_log_to_db(self, log_entry: Dict):
        """로그를 데이터베이스에 저장"""
        try:
            import json

            # PostgreSQL only - no SQLite support
            return []
            cursor = conn.cursor()

            # Use 'status' field instead of 'action' (which doesn't exist)
            status = log_entry.get("status") or log_entry.get("action", "unknown")
            cursor.execute(
                "INSERT INTO collection_logs (timestamp, source, status, details) VALUES (?, ?, ?, ?)",
                (
                    log_entry["timestamp"],
                    log_entry["source"],
                    status,
                    json.dumps(log_entry["details"]),
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.warning(f"Failed to save log to database: {e}")

    def _load_logs_from_db(self, limit: int = 100) -> list[Dict]:
        """데이터베이스에서 로그 로드"""
        try:
            import json

            db_path = "/app/instance/blacklist.db"
            if not os.path.exists(db_path):
                return []

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT timestamp, source, status, details FROM collection_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            )

            logs = []
            for row in cursor.fetchall():
                log_entry = {
                    "timestamp": row[0],
                    "source": row[1],
                    "action": row[2],  # status as action for compatibility
                    "status": row[2],
                    "details": json.loads(row[3]) if row[3] else {},
                    "message": f"[{row[1]}] {row[2]}",
                }
                logs.append(log_entry)

            conn.close()
            return logs

        except Exception as e:
            self.logger.warning(f"Failed to load logs from database: {e}")
            return []

    def clear_collection_logs(self):
        """수집 로그 클리어"""
        try:
            self.collection_logs.clear()
            # 데이터베이스에서도 삭제
            if self.blacklist_manager and hasattr(self.blacklist_manager, "db_path"):
                # PostgreSQL only - no SQLite support
                pass
                cursor = conn.cursor()
                cursor.execute("DELETE FROM collection_logs")
                conn.commit()
                conn.close()

            self.logger.info("수집 로그가 클리어되었습니다")
        except Exception as e:
            self.logger.error(f"로그 클리어 실패: {e}")
