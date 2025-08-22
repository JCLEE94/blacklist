#!/usr/bin/env python3
"""
Source Statistics Mixin - Source-specific analysis and statistics

Purpose: Handle source-based statistics (REGTECH, SECUDIUM, etc.)
Third-party packages: psycopg2 (optional), sqlite3 (stdlib)
Sample input: No parameters for get_source_statistics()
Expected output: Dictionary with source names and their detailed statistics
"""

import logging
import sqlite3
from typing import Any, Dict

try:
    import psycopg2

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

logger = logging.getLogger(__name__)


class SourceStatisticsMixin:
    """
    Source Statistics Mixin - Source-specific data analysis
    Provides detailed statistics for each blacklist source
    """

    def get_source_statistics(self) -> Dict[str, Any]:
        """소스별 상세 통계"""
        try:
            if PSYCOPG2_AVAILABLE and self.database_url.startswith("postgresql://"):
                return self._get_postgresql_source_stats()
            elif hasattr(self, "sqlite_path") and self.sqlite_path:
                import os

                if os.path.exists(self.sqlite_path):
                    return self._get_sqlite_source_stats()

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

    def get_source_summary(self) -> Dict[str, Any]:
        """소스별 요약 정보"""
        try:
            source_stats = self.get_source_statistics()

            if not source_stats:
                return {"status": "no_data", "summary": "No source data available"}

            # 요약 통계 계산
            total_sources = len(source_stats)
            total_ips_all_sources = sum(
                stats["total_ips"] for stats in source_stats.values()
            )
            total_active_all_sources = sum(
                stats["active_ips"] for stats in source_stats.values()
            )

            # 가장 활성 소스 찾기
            most_active_source = max(
                source_stats.items(),
                key=lambda x: x[1]["active_ips"],
                default=(None, {}),
            )

            # 소스별 활성 비율 계산
            source_activity = {}
            for source, stats in source_stats.items():
                if total_active_all_sources > 0:
                    contribution = (
                        stats["active_ips"] / total_active_all_sources
                    ) * 100
                    source_activity[source] = round(contribution, 2)
                else:
                    source_activity[source] = 0

            return {
                "total_sources": total_sources,
                "total_ips_across_sources": total_ips_all_sources,
                "total_active_across_sources": total_active_all_sources,
                "most_active_source": (
                    {
                        "name": most_active_source[0],
                        "active_ips": most_active_source[1].get("active_ips", 0),
                    }
                    if most_active_source[0]
                    else None
                ),
                "source_contributions": source_activity,
                "source_count_by_activity": {
                    "high_activity": len(
                        [
                            s
                            for s, stats in source_stats.items()
                            if stats["active_percentage"] > 80
                        ]
                    ),
                    "medium_activity": len(
                        [
                            s
                            for s, stats in source_stats.items()
                            if 20 <= stats["active_percentage"] <= 80
                        ]
                    ),
                    "low_activity": len(
                        [
                            s
                            for s, stats in source_stats.items()
                            if stats["active_percentage"] < 20
                        ]
                    ),
                },
            }
        except Exception as e:
            logger.error(f"Error getting source summary: {e}")
            return {"status": "error", "error": str(e)}

    def get_source_comparison(self, source_a: str, source_b: str) -> Dict[str, Any]:
        """두 소스 간 비교 분석"""
        try:
            source_stats = self.get_source_statistics()

            if source_a not in source_stats or source_b not in source_stats:
                return {
                    "status": "error",
                    "error": f"One or both sources not found: {source_a}, {source_b}",
                }

            stats_a = source_stats[source_a]
            stats_b = source_stats[source_b]

            comparison = {
                "source_a": {"name": source_a, **stats_a},
                "source_b": {"name": source_b, **stats_b},
                "comparison": {
                    "total_ips_diff": stats_a["total_ips"] - stats_b["total_ips"],
                    "active_ips_diff": stats_a["active_ips"] - stats_b["active_ips"],
                    "activity_rate_diff": stats_a["active_percentage"]
                    - stats_b["active_percentage"],
                    "larger_source": (
                        source_a
                        if stats_a["total_ips"] > stats_b["total_ips"]
                        else source_b
                    ),
                    "more_active_source": (
                        source_a
                        if stats_a["active_ips"] > stats_b["active_ips"]
                        else source_b
                    ),
                },
            }

            return comparison

        except Exception as e:
            logger.error(f"Error comparing sources {source_a} vs {source_b}: {e}")
            return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    # 검증 함수
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: Mixin 메서드 존재 확인
    total_tests += 1
    try:
        required_methods = [
            "get_source_statistics",
            "_get_postgresql_source_stats",
            "_get_sqlite_source_stats",
            "get_source_summary",
            "get_source_comparison",
        ]
        mixin_methods = [
            method
            for method in dir(SourceStatisticsMixin)
            if not method.startswith("__")
        ]

        missing_methods = [
            method for method in required_methods if method not in mixin_methods
        ]
        if missing_methods:
            all_validation_failures.append(f"Missing methods: {missing_methods}")

    except Exception as e:
        all_validation_failures.append(f"Method validation: Exception {e}")

    # Test 2: 기본 소스 통계 구조 확인
    total_tests += 1
    try:
        # Mock 객체로 테스트
        class MockSourceMixin(SourceStatisticsMixin):
            def __init__(self):
                self.database_url = "sqlite:///test.db"
                self.sqlite_path = None  # 파일이 없으므로 빈 딕셔너리 반환

        mock_mixin = MockSourceMixin()
        result = mock_mixin.get_source_statistics()

        # 빈 딕셔너리이거나 적절한 구조여야 함
        if not isinstance(result, dict):
            all_validation_failures.append("Source statistics: Invalid return type")

    except Exception as e:
        all_validation_failures.append(f"Source statistics structure: Exception {e}")

    # Test 3: 소스 요약 기본 동작 확인
    total_tests += 1
    try:

        class MockSourceMixin(SourceStatisticsMixin):
            def __init__(self):
                self.database_url = "sqlite:///test.db"
                self.sqlite_path = None

        mock_mixin = MockSourceMixin()
        result = mock_mixin.get_source_summary()

        # no_data 상태이거나 적절한 구조여야 함
        if "status" not in result:
            all_validation_failures.append("Source summary: Missing status field")

    except Exception as e:
        all_validation_failures.append(f"Source summary: Exception {e}")

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
        print("SourceStatisticsMixin structure is validated")
        sys.exit(0)
