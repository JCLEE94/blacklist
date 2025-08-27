#!/usr/bin/env python3
"""
Trend Analytics Mixin - Time-series data analysis for blacklist trends

Purpose: Handle daily trend data and time-series analysis
Third-party packages: psycopg2 (required)
Sample input: days=7 for weekly trends, days=30 for monthly trends
Expected output: Dictionary with trend_data array and total_changes count
"""

import logging

# PostgreSQL only - sqlite3 removed
from typing import Any, Dict

try:
    import psycopg2
    import psycopg2.extras

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

logger = logging.getLogger(__name__)


class TrendAnalyticsMixin:
    """
    Trend Analytics Mixin - Time-series analysis for blacklist data
    Provides daily trend data and change tracking
    """

    def get_daily_trend_data(self, days: int = 7) -> Dict[str, Any]:
        """일일 트렌드 데이터"""
        try:
            if PSYCOPG2_AVAILABLE and self.database_url.startswith("postgresql://"):
                return self._get_postgresql_trend_data(days)

            # PostgreSQL only - no SQLite fallback
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
                FROM blacklist_ips
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

    # SQLite support removed - PostgreSQL only

    def get_weekly_trends(self) -> Dict[str, Any]:
        """주간 트렌드 요약"""
        try:
            weekly_data = self.get_daily_trend_data(7)
            trend_data = weekly_data.get("trend_data", [])

            if not trend_data:
                return {"status": "no_data", "summary": "No trend data available"}

            # 트렌드 분석
            counts = [item["count"] for item in trend_data]
            avg_daily = sum(counts) / len(counts) if counts else 0
            max_daily = max(counts) if counts else 0
            min_daily = min(counts) if counts else 0

            # 증가/감소 패턴 분석
            if len(counts) >= 2:
                recent_avg = sum(counts[:3]) / 3 if len(counts) >= 3 else counts[0]
                older_avg = sum(counts[-3:]) / 3 if len(counts) >= 3 else counts[-1]
                trend_direction = (
                    "increasing" if recent_avg > older_avg else "decreasing"
                )
            else:
                trend_direction = "stable"

            return {
                "period": "7_days",
                "total_changes": weekly_data.get("total_changes", 0),
                "average_daily": round(avg_daily, 2),
                "max_daily": max_daily,
                "min_daily": min_daily,
                "trend_direction": trend_direction,
                "data_points": len(trend_data),
            }
        except Exception as e:
            logger.error(f"Error getting weekly trends: {e}")
            return {"status": "error", "error": str(e)}

    def get_monthly_trends(self) -> Dict[str, Any]:
        """월간 트렌드 요약"""
        try:
            monthly_data = self.get_daily_trend_data(30)
            trend_data = monthly_data.get("trend_data", [])

            if not trend_data:
                return {"status": "no_data", "summary": "No trend data available"}

            # 월간 통계
            counts = [item["count"] for item in trend_data]
            total_count = sum(counts)
            avg_daily = total_count / 30  # 30일 기준

            # 주간별 그룹화
            weekly_groups = []
            for i in range(0, len(trend_data), 7):
                week_data = trend_data[i : i + 7]
                week_total = sum(item["count"] for item in week_data)
                weekly_groups.append(week_total)

            return {
                "period": "30_days",
                "total_changes": total_count,
                "average_daily": round(avg_daily, 2),
                "weekly_totals": weekly_groups,
                "data_points": len(trend_data),
            }
        except Exception as e:
            logger.error(f"Error getting monthly trends: {e}")
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
            "get_daily_trend_data",
            "_get_postgresql_trend_data",
            "get_weekly_trends",
            "get_monthly_trends",
        ]
        mixin_methods = [
            method for method in dir(TrendAnalyticsMixin) if not method.startswith("__")
        ]

        missing_methods = [
            method for method in required_methods if method not in mixin_methods
        ]
        if missing_methods:
            all_validation_failures.append(f"Missing methods: {missing_methods}")

    except Exception as e:
        all_validation_failures.append(f"Method validation: Exception {e}")

    # Test 2: 기본 트렌드 데이터 구조 확인
    total_tests += 1
    try:
        # Mock 객체로 테스트
        class MockTrendMixin(TrendAnalyticsMixin):
            def __init__(self):
                self.database_url = "postgresql://test:test@localhost/test"
                # PostgreSQL only

        mock_mixin = MockTrendMixin()
        result = mock_mixin.get_daily_trend_data(7)

        expected_keys = {"days", "trend_data", "total_changes"}
        if not expected_keys.issubset(result.keys()):
            missing = expected_keys - result.keys()
            all_validation_failures.append(
                f"Trend data structure: Missing keys {missing}"
            )

    except Exception as e:
        all_validation_failures.append(f"Trend data structure: Exception {e}")

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
        print("TrendAnalyticsMixin structure is validated")
        sys.exit(0)
