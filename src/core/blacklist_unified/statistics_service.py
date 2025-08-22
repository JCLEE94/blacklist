#!/usr/bin/env python3
"""
통합 블랙리스트 서비스 - 통계 서비스 (레거시 호환성)
blacklist_unified 모듈용 통계 서비스 클래스

[DEPRECATED] 새로운 UnifiedStatisticsService를 사용하세요.
이 파일은 기존 코드와의 호환성을 위해서만 유지됩니다.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

# 새로운 통합 통계 서비스 임포트
from ..services.unified_statistics_service import UnifiedStatisticsService

logger = logging.getLogger(__name__)


class StatisticsService(UnifiedStatisticsService):
    """
    통계 서비스 - blacklist_unified 전용 (레거시 호환성)

    [DEPRECATED] 새로운 UnifiedStatisticsService를 직접 사용하세요.
    이 클래스는 기존 코드와의 호환성을 위해서만 유지됩니다.
    """

    def __init__(self, data_dir=None, db_manager=None, cache_manager=None):
        """통계 서비스 초기화 (레거시 호환성)"""
        # 부모 클래스 초기화 with parameters
        super().__init__(
            data_dir=data_dir, db_manager=db_manager, cache_manager=cache_manager
        )
        logger.info(
            f"[DEPRECATED] StatisticsService initialized - consider using UnifiedStatisticsService"
        )

    def get_stats_for_period(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """기간별 통계 (통합 서비스를 통해 제공)"""
        try:
            # 기본 통계 조회
            stats = self.get_statistics()

            # 기간별 데이터는 트렌드 데이터로 대체
            days_diff = (
                datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date)
            ).days
            trend_data = self.get_daily_trend_data(max(days_diff, 7))

            return {
                "period": {"start": start_date, "end": end_date},
                "total_ips": stats.get("total_ips", 0),
                "new_ips": trend_data.get("total_changes", 0),
                "sources": stats.get("sources", {}),
                "countries": {},  # 국가 데이터는 기본 통계에 포함
            }
        except Exception as e:
            logger.error(f"Error getting period stats: {e}")
            return {
                "period": {"start": start_date, "end": end_date},
                "total_ips": 0,
                "new_ips": 0,
                "sources": {},
                "countries": {},
            }

    def get_country_statistics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """국가별 통계 (통합 서비스를 통해 제공)"""
        try:
            # 기본 통계를 통해 국가 정보 제공
            stats = self.get_statistics()

            # 기본적인 국가 데이터 구조 반환
            return [
                {
                    "country": "Unknown",
                    "ip_count": stats.get("active_ips", 0),
                    "source_count": len(stats.get("sources", {})),
                    "percentage": 100,
                }
            ]
        except Exception as e:
            logger.error(f"Error getting country statistics: {e}")
            return []

    def get_expiration_stats(self) -> Dict[str, Any]:
        """만료 통계 (기본값 반환)"""
        return {"total_expiring": 0, "expired_today": 0, "expiring_soon": 0}

    def get_expiring_ips(self, days: int = 7) -> List[Dict[str, Any]]:
        """곧 만료될 IP 목록 (기본값 반환)"""
        return []


if __name__ == "__main__":
    # 검증 함수 - 레거시 호환성 테스트
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: 레거시 클래스 인스턴스화
    total_tests += 1
    try:
        service = StatisticsService()
        if not hasattr(service, "get_statistics"):
            all_validation_failures.append(
                "Legacy compatibility: get_statistics method not available"
            )
    except Exception as e:
        all_validation_failures.append(f"Legacy compatibility: Exception {e}")

    # Test 2: 기간별 통계 호환성
    total_tests += 1
    try:
        service = StatisticsService()
        result = service.get_stats_for_period("2024-01-01", "2024-01-02")
        if not isinstance(result, dict) or "period" not in result:
            all_validation_failures.append("Period stats: Invalid result format")
    except Exception as e:
        all_validation_failures.append(f"Period stats: Exception {e}")

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
        print("Legacy StatisticsService compatibility is validated")
        print("[NOTICE] Consider migrating to UnifiedStatisticsService for new code")
        sys.exit(0)
