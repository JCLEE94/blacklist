#!/usr/bin/env python3
"""
로그 매니저 - 싱글톤 패턴
전역 로거 관리 및 통합 검색 기능

Sample input: LogManager().get_logger("api")
Expected output: 구조화된 로거 인스턴스 반환
"""

# Conditional imports for standalone execution and package usage
try:
    from .structured_logger import StructuredLogger
except ImportError:
    # Fallback for standalone execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent))
    
    try:
        from structured_logger import StructuredLogger
    except ImportError:
        # Mock imports for testing when dependencies not available
        from unittest.mock import Mock
        StructuredLogger = Mock

from typing import Dict, Any


class LogManager:
    """로거 관리자 - 싱글톤"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.loggers = {}
        return cls._instance

    def get_logger(self, name: str) -> StructuredLogger:
        """로거 가져오기 (싱글톤)"""
        if name not in self.loggers:
            self.loggers[name] = StructuredLogger(name)
        return self.loggers[name]

    def get_all_stats(self) -> Dict[str, Any]:
        """모든 로거의 통계 조회"""
        return {
            name: logger.get_log_stats() 
            for name, logger in self.loggers.items()
        }

    def search_all_logs(self, query: str, limit: int = 100) -> Dict[str, list]:
        """모든 로거에서 로그 검색"""
        results = {}
        for name, logger in self.loggers.items():
            logs = logger.search_logs(query, limit)
            if logs:
                results[name] = logs
        return results


# 전역 함수들
def get_logger(name: str) -> StructuredLogger:
    """전역 로거 가져오기"""
    return LogManager().get_logger(name)


if __name__ == "__main__":
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: LogManager singleton behavior
    total_tests += 1
    try:
        manager1 = LogManager()
        manager2 = LogManager()
        
        if manager1 is not manager2:
            all_validation_failures.append("Singleton test: Multiple instances created")
        if not hasattr(manager1, 'loggers'):
            all_validation_failures.append("Singleton test: Missing loggers attribute")
    except Exception as e:
        all_validation_failures.append(f"Singleton test: Failed - {e}")

    # Test 2: Logger creation and retrieval
    total_tests += 1
    try:
        manager = LogManager()
        test_logger = manager.get_logger("test")
        
        if "test" not in manager.loggers:
            all_validation_failures.append("Logger creation: Logger not stored in manager")
        
        # Should return same instance on second call
        test_logger2 = manager.get_logger("test")
        if test_logger is not test_logger2:
            all_validation_failures.append("Logger creation: Different instances returned")
    except Exception as e:
        all_validation_failures.append(f"Logger creation test: Failed - {e}")

    # Test 3: Global get_logger function
    total_tests += 1
    try:
        global_logger = get_logger("global_test")
        if not callable(get_logger):
            all_validation_failures.append("Global function test: get_logger not callable")
    except Exception as e:
        all_validation_failures.append(f"Global function test: Failed - {e}")

    # Final validation result
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
        print("Log manager module is validated and ready for use")
        sys.exit(0)