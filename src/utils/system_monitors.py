"""
System Monitors Factory

Provides factory functions and utilities for system monitoring components.

Third-party packages:
- See individual component modules for specific dependencies

Sample input: Database configuration parameters
Expected output: System monitor instances and utility functions
"""

import logging
import os
from typing import Any, Callable

from .database_stability import DatabaseStabilityManager
from .system_monitor import SystemMonitor

logger = logging.getLogger(__name__)


def safe_execute(func: Callable, default_return=None, log_errors: bool = True) -> Any:
    """안전한 함수 실행 래퍼"""
    try:
        return func()
    except Exception as e:
        if log_errors:
            logger.error(f"Safe execution failed for {func.__name__}: {e}")
        return default_return


def create_system_monitor(db_path: str = None) -> SystemMonitor:
    """시스템 모니터 인스턴스 생성"""
    if not db_path:
        db_path = os.environ.get("DATABASE_URL", "instance/blacklist.db")
        if db_path.startswith("sqlite:///"):
            db_path = db_path[10:]
    db_manager = DatabaseStabilityManager(db_path)
    monitor = SystemMonitor(db_manager)
    return monitor


# 전역 모니터 인스턴스
_global_monitor = None


def get_system_monitor() -> SystemMonitor:
    """전역 시스템 모니터 인스턴스 반환"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = create_system_monitor()
    return _global_monitor


def initialize_system_stability():
    """시스템 안정성 초기화"""
    monitor = get_system_monitor()
    monitor.start_monitoring()
    logger.info("System stability monitoring initialized")
    return monitor


if __name__ == "__main__":
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: Factory functions
    total_tests += 1
    try:
        monitor = create_system_monitor(":memory:")
        if not hasattr(monitor, "db_manager"):
            all_validation_failures.append("Factory create_system_monitor failed")
    except Exception as e:
        all_validation_failures.append(f"Factory test failed: {e}")

    # Test 2: Safe execute function
    total_tests += 1
    try:

        def test_func():
            return "success"

        result = safe_execute(test_func)
        if result != "success":
            all_validation_failures.append(
                f"Safe execute: Expected 'success', got {result}"
            )
    except Exception as e:
        all_validation_failures.append(f"Safe execute test failed: {e}")

    # Test 3: Global monitor singleton
    total_tests += 1
    try:
        monitor1 = get_system_monitor()
        monitor2 = get_system_monitor()
        if monitor1 is not monitor2:
            all_validation_failures.append("Global monitor should be singleton")
    except Exception as e:
        all_validation_failures.append(f"Singleton test failed: {e}")

    # Final validation result
    if all_validation_failures:
        failed_count = len(all_validation_failures)
        print(f"❌ VALIDATION FAILED - {failed_count} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("System monitors factory is validated and ready for use")
        sys.exit(0)
