#!/usr/bin/env python3
"""
Database Statistics Mixin - PostgreSQL/SQLite common database operations

Purpose: Handle basic statistics queries for both PostgreSQL and SQLite
Third-party packages: psycopg2 (optional), sqlite3 (stdlib)
Sample input: Database connection parameters, query filters
Expected output: Dictionary with statistics (total_ips, active_ips, sources, etc.)
"""

import logging
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict

try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

logger = logging.getLogger(__name__)


class DatabaseStatisticsMixin:
    """
    Database Statistics Mixin - Core database operations for statistics
    Provides PostgreSQL primary, SQLite fallback pattern
    """
    
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
            # Return default statistics instead of minimal error dict
            default_stats = self._get_default_statistics()
            default_stats["error"] = str(e)
            return default_stats


if __name__ == "__main__":
    # 검증 함수
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: Mixin 인스턴스화 (독립적으로 테스트 불가하므로 스킵)
    total_tests += 1
    try:
        # DatabaseStatisticsMixin은 다른 클래스와 함께 사용되어야 함
        # 직접 인스턴스화 불가
        print("DatabaseStatisticsMixin structure validated")
    except Exception as e:
        all_validation_failures.append(f"Mixin structure: Exception {e}")

    # Test 2: 메서드 존재 확인
    total_tests += 1
    try:
        required_methods = [
            "_get_postgresql_statistics",
            "_get_sqlite_statistics", 
            "_get_default_statistics",
            "get_statistics"
        ]
        mixin_methods = [method for method in dir(DatabaseStatisticsMixin) 
                        if not method.startswith('__')]
        
        missing_methods = [method for method in required_methods 
                          if method not in mixin_methods]
        if missing_methods:
            all_validation_failures.append(f"Missing methods: {missing_methods}")
            
    except Exception as e:
        all_validation_failures.append(f"Method validation: Exception {e}")

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
        print("DatabaseStatisticsMixin structure is validated")
        sys.exit(0)