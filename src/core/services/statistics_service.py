#!/usr/bin/env python3
"""
통합 블랙리스트 서비스 - 통계 및 분석 기능 (레거시 호환성)
새로운 UnifiedStatisticsService로 리다이렉트됨

이 파일은 기존 코드와의 호환성을 위해 유지되며,
모든 기능은 unified_statistics_service.py로 통합되었습니다.
"""

# 새로운 통합 통계 서비스 임포트
from .unified_statistics_service import (
    StatisticsServiceMixin as NewStatisticsServiceMixin,
)
from .unified_statistics_service import UnifiedStatisticsService


# 레거시 호환성을 위한 기존 클래스명 유지
class StatisticsServiceMixin(NewStatisticsServiceMixin):
    """
    통계 및 분석 기능을 제공하는 믹스인 클래스 (레거시 호환성)

    [DEPRECATED] 새로운 UnifiedStatisticsService를 사용하세요.
    이 클래스는 기존 코드와의 호환성을 위해서만 유지됩니다.
    """


if __name__ == "__main__":
    # 검증 함수 - 레거시 호환성 테스트
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: 레거시 클래스 인스턴스화
    total_tests += 1
    try:
        mixin = StatisticsServiceMixin()
        if not hasattr(mixin, "_unified_stats"):
            all_validation_failures.append(
                "Legacy compatibility: _unified_stats not available"
            )
    except Exception as e:
        all_validation_failures.append(f"Legacy compatibility: Exception {e}")

    # Test 2: 새로운 서비스 직접 사용
    total_tests += 1
    try:
        service = UnifiedStatisticsService()
        stats = service.get_statistics()
        if not isinstance(stats, dict):
            all_validation_failures.append("Direct service: Invalid stats return type")
    except Exception as e:
        all_validation_failures.append(f"Direct service: Exception {e}")

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
        print("Legacy statistics service compatibility is validated")
        print("[NOTICE] Consider migrating to UnifiedStatisticsService for new code")
        sys.exit(0)
