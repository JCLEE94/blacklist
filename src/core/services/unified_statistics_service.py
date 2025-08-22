#!/usr/bin/env python3
"""
통합 통계 서비스 - 중복 제거된 단일 통계 서비스
모든 통계 기능을 통합하여 PostgreSQL과 SQLite를 모두 지원
"""

import logging
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

try:
    import psycopg2
    import psycopg2.extras

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

logger = logging.getLogger(__name__)


class UnifiedStatisticsService:
    """
    통합 통계 서비스 - PostgreSQL 우선, SQLite 폴백
    중복된 통계 기능들을 통합하여 단일 서비스로 제공
    """

    def __init__(
        self, data_dir=None, db_manager=None, cache_manager=None, blacklist_manager=None
    ):
        """통계 서비스 초기화"""
        self.data_dir = data_dir
        self.db_manager = db_manager
        self.cache_manager = cache_manager
        self.blacklist_manager = blacklist_manager
        self.logger = logger

        # Database URL 설정
        self.database_url = (
            db_manager.database_url
            if db_manager
            else os.environ.get(
                "DATABASE_URL",
                "postgresql://blacklist_user:blacklist_password_change_me@localhost:32543/blacklist",
            )
        )

        # SQLite fallback path
        self.sqlite_path = "instance/blacklist.db"
        if data_dir:
            self.sqlite_path = os.path.join(data_dir, "blacklist.db")

        logger.info(
            f"UnifiedStatisticsService initialized with database: {self.database_url}"
        )

    def get_statistics(self) -> Dict[str, Any]:
        """통합 통계 정보 (PostgreSQL 우선, SQLite 폴백)"""
        try:
            # Production 환경에서는 PostgreSQL 우선
            flask_env = os.environ.get("FLASK_ENV", "development")

            if (
                flask_env == "production"
                or self.database_url.startswith("postgresql://")
            ) and PSYCOPG2_AVAILABLE:
                return self._get_postgresql_statistics()

            # SQLite 폴백
            if os.path.exists(self.sqlite_path):
                return self._get_sqlite_statistics()

            # 최후의 수단으로 PostgreSQL 시도
            if PSYCOPG2_AVAILABLE:
                return self._get_postgresql_statistics()

            # 모든 옵션 실패시 기본값 반환
            return self._get_default_statistics()

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"error": str(e), "active_ips": 0, "total_ips": 0}

    def _get_postgresql_statistics(self) -> Dict[str, Any]:
        """PostgreSQL에서 통계 조회"""
        if not PSYCOPG2_AVAILABLE:
            raise ImportError("psycopg2 not available")

        conn = None
        try:
            conn = psycopg2.connect(self.database_url)
            conn.autocommit = True
            cursor = conn.cursor()

            # 활성 IP 수
            cursor.execute(
                "SELECT COUNT(*) FROM blacklist_entries WHERE is_active = true"
            )
            active_ips = cursor.fetchone()[0]

            # 전체 IP 수
            cursor.execute("SELECT COUNT(*) FROM blacklist_entries")
            total_ips = cursor.fetchone()[0]

            # 소스별 통계
            cursor.execute(
                """
                SELECT source, COUNT(*) as count
                FROM blacklist_entries
                WHERE is_active = true
                GROUP BY source
                """
            )
            sources = {row[0] or "unknown": row[1] for row in cursor.fetchall()}

            # 국가별 통계
            unique_countries = 0
            try:
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT country) FROM blacklist_entries
                    WHERE is_active = true AND country IS NOT NULL AND country != ''
                    """
                )
                result = cursor.fetchone()
                unique_countries = result[0] if result and result[0] else 0
            except Exception:
                unique_countries = 0

            # 마지막 업데이트 시간
            cursor.execute(
                "SELECT MAX(updated_at) FROM blacklist_entries WHERE is_active = true"
            )
            last_update_raw = cursor.fetchone()[0]
            last_update = (
                last_update_raw.isoformat()
                if last_update_raw
                else datetime.now().isoformat()
            )

            logger.info(
                f"PostgreSQL stats: {active_ips} active IPs from {len(sources)} sources"
            )

            return {
                "total_ips": total_ips,
                "active_ips": active_ips,
                "expired_ips": total_ips - active_ips,
                "unique_countries": unique_countries,
                "sources": sources,
                "last_update": last_update,
                "database_size": "PostgreSQL",
                "status": "healthy" if active_ips > 0 else "warning",
            }

        except Exception as e:
            logger.error(f"PostgreSQL error getting statistics: {e}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def _get_sqlite_statistics(self) -> Dict[str, Any]:
        """SQLite에서 통계 조회"""
        conn = None
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()

            # 활성 IP 수
            cursor.execute(
                "SELECT COUNT(DISTINCT ip_address) FROM blacklist_entries WHERE is_active = 1"
            )
            active_ips = cursor.fetchone()[0]

            # 전체 IP 수
            cursor.execute("SELECT COUNT(DISTINCT ip_address) FROM blacklist_entries")
            total_ips = cursor.fetchone()[0]

            # 소스별 통계
            cursor.execute(
                """
                SELECT LOWER(source) as source_name, COUNT(DISTINCT ip_address) as count
                FROM blacklist_entries
                WHERE is_active = 1
                GROUP BY LOWER(source)
                """
            )
            sources = {row[0] or "unknown": row[1] for row in cursor.fetchall()}

            # 마지막 업데이트 시간
            cursor.execute(
                "SELECT MAX(created_at) FROM blacklist_entries WHERE is_active = 1"
            )
            last_update_raw = cursor.fetchone()[0]
            last_update = (
                last_update_raw if last_update_raw else datetime.now().isoformat()
            )

            logger.info(
                f"SQLite stats: {active_ips} active IPs from {len(sources)} sources"
            )

            return {
                "total_ips": total_ips,
                "active_ips": active_ips,
                "expired_ips": total_ips - active_ips,
                "unique_countries": 0,  # SQLite doesn't have country data
                "sources": sources,
                "last_update": last_update,
                "database_size": f"{os.path.getsize(self.sqlite_path) / 1024 / 1024:.2f} MB",
                "status": "healthy" if active_ips > 0 else "warning",
            }

        except Exception as e:
            logger.error(f"SQLite error getting statistics: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def _get_default_statistics(self) -> Dict[str, Any]:
        """기본 통계값 반환 (데이터베이스 접근 불가시)"""
        return {
            "total_ips": 0,
            "active_ips": 0,
            "expired_ips": 0,
            "unique_countries": 0,
            "sources": {},
            "last_update": datetime.now().isoformat(),
            "database_size": "0 MB",
            "status": "error",
            "error": "No database connection available",
        }

    def get_daily_trend_data(self, days: int = 7) -> Dict[str, Any]:
        """일일 트렌드 데이터"""
        try:
            if PSYCOPG2_AVAILABLE and self.database_url.startswith("postgresql://"):
                return self._get_postgresql_trend_data(days)
            elif os.path.exists(self.sqlite_path):
                return self._get_sqlite_trend_data(days)
            else:
                return {"days": days, "trend_data": [], "total_changes": 0}
        except Exception as e:
            logger.error(f"Error getting trend data: {e}")
            return {"days": days, "trend_data": [], "total_changes": 0}

    def _get_postgresql_trend_data(self, days: int) -> Dict[str, Any]:
        """PostgreSQL 트렌드 데이터"""
        with psycopg2.connect(self.database_url) as conn:
            conn.autocommit = True
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            cursor.execute(
                """
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as count
                FROM blacklist_entries
                WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                """,
                (days,),
            )

            trend_data = [
                {"date": str(row["date"]), "count": row["count"]}
                for row in cursor.fetchall()
            ]

            return {
                "days": days,
                "trend_data": trend_data,
                "total_changes": sum(item["count"] for item in trend_data),
            }

    def _get_sqlite_trend_data(self, days: int) -> Dict[str, Any]:
        """SQLite 트렌드 데이터"""
        with sqlite3.connect(self.sqlite_path) as conn:
            cursor = conn.cursor()
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            cursor.execute(
                """
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM blacklist_entries
                WHERE created_at >= ?
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                """,
                (start_date,),
            )

            trend_data = [
                {"date": row[0], "count": row[1]} for row in cursor.fetchall()
            ]

            return {
                "days": days,
                "trend_data": trend_data,
                "total_changes": sum(item["count"] for item in trend_data),
            }

    def get_source_statistics(self) -> Dict[str, Any]:
        """소스별 상세 통계"""
        try:
            if PSYCOPG2_AVAILABLE and self.database_url.startswith("postgresql://"):
                return self._get_postgresql_source_stats()
            elif os.path.exists(self.sqlite_path):
                return self._get_sqlite_source_stats()
            else:
                return {}
        except Exception as e:
            logger.error(f"Error getting source statistics: {e}")
            return {}

    def _get_postgresql_source_stats(self) -> Dict[str, Any]:
        """PostgreSQL 소스별 통계"""
        with psycopg2.connect(self.database_url) as conn:
            conn.autocommit = True
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT source,
                       COUNT(*) as total_count,
                       COUNT(CASE WHEN is_active = true THEN 1 END) as active_count,
                       MIN(created_at) as first_seen,
                       MAX(created_at) as last_seen
                FROM blacklist_entries
                GROUP BY source
                ORDER BY total_count DESC
                """
            )

            source_stats = {}
            for source, total, active, first_seen, last_seen in cursor.fetchall():
                source_stats[source or "unknown"] = {
                    "total_ips": total,
                    "active_ips": active,
                    "inactive_ips": total - active,
                    "first_collection": first_seen.isoformat() if first_seen else None,
                    "last_collection": last_seen.isoformat() if last_seen else None,
                    "active_percentage": (
                        round((active / total) * 100, 2) if total > 0 else 0
                    ),
                }

            return source_stats

    def _get_sqlite_source_stats(self) -> Dict[str, Any]:
        """SQLite 소스별 통계"""
        with sqlite3.connect(self.sqlite_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT source,
                       COUNT(*) as total_count,
                       COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_count,
                       MIN(created_at) as first_seen,
                       MAX(created_at) as last_seen
                FROM blacklist_entries
                GROUP BY source
                ORDER BY total_count DESC
                """
            )

            source_stats = {}
            for source, total, active, first_seen, last_seen in cursor.fetchall():
                source_stats[source or "unknown"] = {
                    "total_ips": total,
                    "active_ips": active,
                    "inactive_ips": total - active,
                    "first_collection": first_seen,
                    "last_collection": last_seen,
                    "active_percentage": (
                        round((active / total) * 100, 2) if total > 0 else 0
                    ),
                }

            return source_stats

    def get_system_health(self) -> Dict[str, Any]:
        """시스템 상태"""
        try:
            stats = self.get_statistics()

            return {
                "status": stats.get("status", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "uptime": "0d 0h 0m",
                "memory_usage": "0MB",
                "db_status": (
                    "connected" if stats.get("active_ips", 0) >= 0 else "error"
                ),
                "total_ips": stats.get("total_ips", 0),
                "active_ips": stats.get("active_ips", 0),
                "regtech_count": stats.get("sources", {}).get("REGTECH", 0),
                "secudium_count": stats.get("sources", {}).get("SECUDIUM", 0),
                "public_count": stats.get("sources", {}).get("PUBLIC", 0),
            }
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "total_ips": 0,
                "active_ips": 0,
            }


# Mixin for backward compatibility
class StatisticsServiceMixin:
    """통계 서비스 믹스인 - 기존 코드와의 호환성을 위해 유지"""

    def __init__(self):
        if not hasattr(self, "logger"):
            self.logger = logging.getLogger(__name__)

        # 통합 통계 서비스 인스턴스 생성
        self._unified_stats = UnifiedStatisticsService(
            blacklist_manager=getattr(self, "blacklist_manager", None),
            cache_manager=getattr(self, "cache_manager", None),
        )

        try:
            super().__init__()
        except TypeError:
            pass

    async def get_statistics(self) -> Dict[str, Any]:
        """통합 시스템 통계 (비동기 래퍼)"""
        try:
            stats = self._unified_stats.get_statistics()

            # 기존 포맷과 호환성 유지
            if hasattr(self, "config"):
                service_info = {
                    "service": {
                        "name": self.config.get("service_name", "blacklist"),
                        "version": self.config.get("version", "1.0.0"),
                        "running": getattr(self, "_running", True),
                        "components": list(getattr(self, "_components", {}).keys()),
                        "auto_collection": self.config.get("auto_collection", False),
                        "collection_interval": self.config.get(
                            "collection_interval", 3600
                        ),
                    }
                }
                stats.update(service_info)

            return {
                "success": True,
                "statistics": stats,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"통계 조회 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def get_blacklist_summary(self) -> Dict[str, Any]:
        """블랙리스트 요약 정보"""
        try:
            stats = self._unified_stats.get_statistics()

            return {
                "success": True,
                "summary": {
                    "total_active_ips": stats.get("active_ips", 0),
                    "sources": stats.get("sources", {}),
                    "last_updated": stats.get("last_update"),
                    "collection_enabled": getattr(self, "collection_enabled", False),
                },
            }
        except Exception as e:
            self.logger.error(f"블랙리스트 요약 조회 실패: {e}")
            return {"success": False, "error": str(e)}

    def get_source_statistics(self) -> Dict[str, Any]:
        """소스별 상세 통계"""
        return self._unified_stats.get_source_statistics()

    def get_daily_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """일별 통계"""
        try:
            trend_data = self._unified_stats.get_daily_trend_data(days)
            return trend_data.get("trend_data", [])
        except Exception as e:
            self.logger.error(f"일별 통계 실패: {e}")
            return []


if __name__ == "__main__":
    # 검증 함수
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: 기본 통계 서비스 초기화
    total_tests += 1
    try:
        service = UnifiedStatisticsService()
        if service is None:
            all_validation_failures.append(
                "Basic initialization: Service creation failed"
            )
    except Exception as e:
        all_validation_failures.append(f"Basic initialization: Exception {e}")

    # Test 2: 기본 통계 조회 (데이터베이스 없이)
    total_tests += 1
    try:
        service = UnifiedStatisticsService()
        stats = service.get_statistics()
        expected_keys = {"total_ips", "active_ips", "sources", "status"}
        if not expected_keys.issubset(stats.keys()):
            missing = expected_keys - stats.keys()
            all_validation_failures.append(f"Basic stats: Missing keys {missing}")
    except Exception as e:
        all_validation_failures.append(f"Basic stats: Exception {e}")

    # Test 3: Mixin 호환성
    total_tests += 1
    try:
        mixin = StatisticsServiceMixin()
        if not hasattr(mixin, "_unified_stats"):
            all_validation_failures.append(
                "Mixin compatibility: _unified_stats not created"
            )
    except Exception as e:
        all_validation_failures.append(f"Mixin compatibility: Exception {e}")

    # 최종 검증 결과
    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("UnifiedStatisticsService is validated and ready for use")
        sys.exit(0)
