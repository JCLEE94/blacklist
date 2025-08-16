#!/usr/bin/env python3
"""
데이터베이스 운영 기능

데이터베이스 초기화, 테이블 관리, 트랜잭션 처리 등 DB 관련 기능을 제공합니다.
"""

import os
import sqlite3
from datetime import datetime
from typing import Any, Dict


class DatabaseOperationsMixin:
    """데이터베이스 운영 기능을 제공하는 믹스인"""

    def initialize_database_tables(self) -> Dict[str, Any]:
        """데이터베이스 테이블 강제 초기화"""
        try:
            # Use blacklist_manager's database path
            if hasattr(self.blacklist_manager, "db_path"):
                db_path = self.blacklist_manager.db_path
            else:
                db_path = os.path.join(
                    "/app" if os.path.exists("/app") else ".", "instance/blacklist.db"
                )

            self.logger.info(f"Initializing database tables at: {db_path}")

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Create blacklist_entries table (aligned with main schema)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS blacklist_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_address TEXT NOT NULL UNIQUE,
                    first_seen TEXT,
                    last_seen TEXT,
                    detection_months TEXT,
                    is_active BOOLEAN DEFAULT 1,
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

            # Create collection_logs table if not exists
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

            conn.commit()
            conn.close()

            return {
                "success": True,
                "message": "Database tables initialized successfully",
                "db_path": db_path,
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
        """수집 로그 테이블 생성 확인"""
        try:
            # Use instance directory from current working directory or temp
            import tempfile

            if os.path.exists("instance"):
                db_path = "instance/blacklist.db"
            elif os.path.exists("/tmp"):
                db_path = os.path.join(
                    tempfile.gettempdir(), "blacklist_instance", "blacklist.db"
                )
            else:
                db_path = "/app/instance/blacklist.db"

            if not os.path.exists(os.path.dirname(db_path)):
                os.makedirs(os.path.dirname(db_path), exist_ok=True)

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.warning(f"Failed to ensure log table: {e}")

    def _save_log_to_db(self, log_entry: Dict):
        """로그를 데이터베이스에 저장"""
        try:
            import json

            db_path = "/app/instance/blacklist.db"
            conn = sqlite3.connect(db_path)
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
                conn = sqlite3.connect(self.blacklist_manager.db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM collection_logs")
                conn.commit()
                conn.close()

            self.logger.info("수집 로그가 클리어되었습니다")
        except Exception as e:
            self.logger.error(f"로그 클리어 실패: {e}")
