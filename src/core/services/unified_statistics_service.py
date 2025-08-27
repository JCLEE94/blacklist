#!/usr/bin/env python3
"""
통합 통계 서비스 - 중복 제거된 단일 통계 서비스 (Refactored with Mixins)
모든 통계 기능을 통합하여 PostgreSQL과 SQLite를 모두 지원

Follows shrimp-rules.md: 500-line file limit through mixin decomposition
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List

try:
    from .mixins import (
        DatabaseStatisticsMixin,
        SourceStatisticsMixin,
        SystemHealthMixin,
        TrendAnalyticsMixin,
    )
except ImportError:
    # Fallback for direct execution
    import os
    import sys

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from mixins.database_statistics_mixin import DatabaseStatisticsMixin
    from mixins.source_statistics_mixin import SourceStatisticsMixin
    from mixins.system_health_mixin import SystemHealthMixin
    from mixins.trend_analytics_mixin import TrendAnalyticsMixin

try:
    import psycopg2
    import psycopg2.extras

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

logger = logging.getLogger(__name__)


class UnifiedStatisticsService(
    DatabaseStatisticsMixin,
    TrendAnalyticsMixin,
    SourceStatisticsMixin,
    SystemHealthMixin,
):
    """
    통합 통계 서비스 - PostgreSQL 우선, SQLite 폴백
    Uses multiple mixins for modular functionality following shrimp-rules.md

    Mixins provide:
    - DatabaseStatisticsMixin: Core database operations
    - TrendAnalyticsMixin: Time-series analysis
    - SourceStatisticsMixin: Source-specific statistics
    - SystemHealthMixin: Health monitoring
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

    def get_daily_collection_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """일별 수집 통계 - 호환성 래퍼"""
        try:
            return self.get_daily_stats(days)
        except Exception as e:
            self.logger.error(f"일별 수집 통계 실패: {e}")
            # 기본값 반환
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

    # Test 2: Mixin 상속 확인
    total_tests += 1
    try:
        service = UnifiedStatisticsService()
        mixin_methods = [
            "get_statistics",  # DatabaseStatisticsMixin
            "get_daily_trend_data",  # TrendAnalyticsMixin
            "get_source_statistics",  # SourceStatisticsMixin
            "get_system_health",  # SystemHealthMixin
        ]

        missing_methods = []
        for method in mixin_methods:
            if not hasattr(service, method):
                missing_methods.append(method)

        if missing_methods:
            all_validation_failures.append(f"Mixin methods missing: {missing_methods}")

    except Exception as e:
        all_validation_failures.append(f"Mixin inheritance: Exception {e}")

    # Test 3: 기본 통계 조회 (데이터베이스 없이)
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

    # Test 4: Mixin 호환성
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
        print("UnifiedStatisticsService with mixins is validated and ready for use")
        sys.exit(0)
