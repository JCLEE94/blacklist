#!/usr/bin/env python3
"""
REGTECH 수집기 - 모듈화된 구조 (메인 진입점)
BaseCollector 상속 및 강화된 에러 핸들링
이 파일은 다른 모듈들을 조합하는 메인 진입점 역할만 합니다.
"""

# Re-export the main collector from the core module
from .regtech_collector_core import RegtechCollector

__all__ = ["RegtechCollector"]


if __name__ == "__main__":
    # 모듈화된 REGTECH 컴렉터 테스트
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: 기본 컴렉터 생성
    total_tests += 1
    try:
        from .unified_collector import CollectionConfig

        config = CollectionConfig()
        collector = RegtechCollector(config)
        if not hasattr(collector, "auth_module") or not hasattr(
            collector, "data_module"
        ):
            all_validation_failures.append("필수 컴포넌트 누락")
    except Exception as e:
        all_validation_failures.append(f"컴렉터 생성 실패: {e}")

    # Test 2: 메서드 존재 확인
    total_tests += 1
    try:
        from .unified_collector import CollectionConfig

        config = CollectionConfig()
        collector = RegtechCollector(config)
        required_methods = [
            "_collect_data",
            "collect_from_web",
        ]
        for method_name in required_methods:
            if not hasattr(collector, method_name):
                all_validation_failures.append(f"필수 메서드 누락: {method_name}")
    except Exception as e:
        all_validation_failures.append(f"메서드 확인 테스트 실패: {e}")

    # Test 3: 쿠키 설정 테스트
    total_tests += 1
    try:
        from .unified_collector import CollectionConfig

        config = CollectionConfig()
        collector = RegtechCollector(config)
        collector.set_cookie_string("test_cookie=test_value")
        # 에러 없이 실행되면 성공
    except Exception as e:
        all_validation_failures.append(f"쿠키 설정 테스트 실패: {e}")

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
        print("Modularized RegtechCollector is validated and ready for use")
        sys.exit(0)
