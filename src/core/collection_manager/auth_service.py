#!/usr/bin/env python3
"""
Collection Authentication Service
인증 시도 관리 및 보호 서비스
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class AuthService:
    """인증 서비스 - 인증 시도 추적 및 보호"""

    def __init__(self, db_path: str, max_auth_attempts: int = 10):
        self.db_path = db_path
        self.max_auth_attempts = max_auth_attempts

    def check_auth_attempt_limit(self, source: str) -> bool:
        """인증 시도 횟수 제한 검사"""
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.cursor()

                # 최근 1시간 내 실패 횟수 조회
                one_hour_ago = datetime.now() - timedelta(hours=1)

                cursor.execute(
                    """
                    SELECT COUNT(*) FROM auth_attempts
                    WHERE service = ?
                      AND success = 0
                      AND timestamp > ?
                    """,
                    (source, one_hour_ago.isoformat()),
                )

                failed_attempts = cursor.fetchone()[0]

                if failed_attempts >= self.max_auth_attempts:
                    logger.warning(
                        "Auth limit exceeded for {source}: {failed_attempts}/{self.max_auth_attempts} attempts"
                    )
                    return False

                return True

        except sqlite3.Error as e:
            logger.error(f"Database error checking auth limits: {e}")
            # 오류 시 보수적으로 차단
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking auth limits: {e}")
            return False

    def record_auth_attempt(
        self, source: str, success: bool = False, details: str = None
    ):
        """인증 시도 기록"""
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.cursor()

                # Use existing auth_attempts table from schema
                # No need to create table - it should exist from database
                # initialization

                # 시도 기록 (use schema column names)
                cursor.execute(
                    "INSERT INTO auth_attempts (service, success, ip_address) VALUES (?, ?, ?)",
                    (source, success, "127.0.0.1"),
                )

                conn.commit()

                status = "SUCCESS" if success else "FAILED"
                logger.info(f"Auth attempt recorded: {source} - {status}")

        except Exception as e:
            logger.error(f"Error recording auth attempt: {e}")

    def get_auth_statistics(self, source: str = None, hours: int = 24) -> Dict:
        """인증 통계 조회"""
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.cursor()

                cutoff_time = datetime.now() - timedelta(hours=hours)

                if source:
                    # 특정 소스에 대한 통계
                    cursor.execute(
                        """
                        SELECT
                            COUNT(*) as total_attempts,
                            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_attempts,
                            SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_attempts
                        FROM auth_attempts
                        WHERE service = ? AND timestamp > ?
                        """,
                        (source, cutoff_time.isoformat()),
                    )

                    row = cursor.fetchone()
                    total, success, failed = row if row else (0, 0, 0)

                    return {
                        "source": source,
                        "period_hours": hours,
                        "total_attempts": total or 0,
                        "successful_attempts": success or 0,
                        "failed_attempts": failed or 0,
                        "success_rate": round((success or 0) / (total or 1) * 100, 1),
                        "within_limit": (failed or 0) < self.max_auth_attempts,
                    }
                else:
                    # 전체 통계
                    cursor.execute(
                        """
                        SELECT
                            service,
                            COUNT(*) as total_attempts,
                            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_attempts,
                            SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_attempts
                        FROM auth_attempts
                        WHERE timestamp > ?
                        GROUP BY service
                        ORDER BY total_attempts DESC
                        """,
                        (cutoff_time.isoformat(),),
                    )

                    stats_by_source = {}
                    for row in cursor.fetchall():
                        service, total, success, failed = row
                        stats_by_source[service] = {
                            "total_attempts": total or 0,
                            "successful_attempts": success or 0,
                            "failed_attempts": failed or 0,
                            "success_rate": round(
                                (success or 0) / (total or 1) * 100, 1
                            ),
                            "within_limit": (failed or 0) < self.max_auth_attempts,
                        }

                    return {
                        "period_hours": hours,
                        "sources": stats_by_source,
                        "summary": {
                            "total_sources": len(stats_by_source),
                            "sources_over_limit": sum(
                                1
                                for s in stats_by_source.values()
                                if not s["within_limit"]
                            ),
                        },
                    }

        except Exception as e:
            logger.error(f"Error getting auth statistics: {e}")
            return {"error": str(e)}

    def reset_auth_attempts(self, source: str = None) -> Dict:
        """인증 시도 리셋"""
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.cursor()

                if source:
                    # 특정 소스의 실패 리셋
                    cursor.execute(
                        "DELETE FROM auth_attempts WHERE service = ? AND success = 0",
                        (source,),
                    )
                    cleared = cursor.rowcount

                    logger.info(
                        "Auth attempts reset for {source}: {cleared} records cleared"
                    )
                    return {
                        "success": True,
                        "source": source,
                        "records_cleared": cleared,
                    }
                else:
                    # 모든 실패 리셋
                    cursor.execute("DELETE FROM auth_attempts WHERE success = 0")
                    cleared = cursor.rowcount

                    logger.info(
                        "All failed auth attempts reset: {cleared} records cleared"
                    )
                    return {
                        "success": True,
                        "source": "all",
                        "records_cleared": cleared,
                    }

                conn.commit()

        except Exception as e:
            logger.error(f"Error resetting auth attempts: {e}")
            return {"success": False, "error": str(e)}

    def get_recent_auth_attempts(self, source: str = None, limit: int = 50) -> list:
        """최근 인증 시도 조회"""
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                if source:
                    cursor.execute(
                        """
                        SELECT service, success, ip_address, timestamp
                        FROM auth_attempts
                        WHERE service = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (source, limit),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT service, success, ip_address, timestamp
                        FROM auth_attempts
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (limit,),
                    )

                attempts = []
                for row in cursor.fetchall():
                    attempts.append(
                        {
                            "source": row["source"],
                            "success": bool(row["success"]),
                            "details": row["details"],
                            "timestamp": row["created_at"],
                        }
                    )

                return attempts

        except Exception as e:
            logger.error(f"Error getting recent auth attempts: {e}")
            return []

    def is_source_blocked(self, source: str) -> Tuple[bool, str]:
        """소스가 인증 실패로 차단되었는지 확인"""
        if not self.check_auth_attempt_limit(source):
            recent_failures = self.get_auth_statistics(source, hours=1)
            failed_count = recent_failures.get("failed_attempts", 0)

            return (
                True,
                f"최근 1시간 내 {failed_count}회 인증 실패로 일시 차단 (한도: {self.max_auth_attempts}회)",
            )

        return False, "인증 가능"

    def cleanup_old_auth_records(self, days: int = 7) -> Dict:
        """오래된 인증 기록 정리"""
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.cursor()

                cutoff_date = datetime.now() - timedelta(days=days)

                cursor.execute(
                    "SELECT COUNT(*) FROM auth_attempts WHERE created_at < ?",
                    (cutoff_date.isoformat(),),
                )
                old_records = cursor.fetchone()[0]

                cursor.execute(
                    "DELETE FROM auth_attempts WHERE created_at < ?",
                    (cutoff_date.isoformat(),),
                )

                conn.commit()

                logger.info(
                    "Cleaned up {old_records} auth records older than {days} days"
                )
                return {
                    "success": True,
                    "records_cleaned": old_records,
                    "cutoff_days": days,
                }

        except Exception as e:
            logger.error(f"Error cleaning up old auth records: {e}")
            return {"success": False, "error": str(e)}
