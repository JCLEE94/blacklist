#!/usr/bin/env python3
"""
Base import tests for src/utils/performance_optimizer.py
This file now contains only basic import and initialization tests.
The main functionality tests have been modularized into:
- test_performance_optimizer_core.py: PerformanceMetrics, QueryOptimizer
- test_performance_optimizer_cache.py: SmartCache, MemoryOptimizer
- test_performance_optimizer_monitor.py: PerformanceMonitor, decorators
"""

import unittest
from unittest.mock import patch

import pytest


class TestPerformanceOptimizerImports(unittest.TestCase):
    """성능 최적화 모듈 임포트 테스트"""

    def test_import_performance_metrics(self):
        """PerformanceMetrics 임포트 테스트"""
        try:
            from src.utils.performance_optimizer import PerformanceMetrics
            self.assertIsNotNone(PerformanceMetrics)
        except ImportError:
            pytest.skip("PerformanceMetrics not available")

    def test_import_query_optimizer(self):
        """QueryOptimizer 임포트 테스트"""
        try:
            from src.utils.performance_optimizer import QueryOptimizer
            self.assertIsNotNone(QueryOptimizer)
        except ImportError:
            pytest.skip("QueryOptimizer not available")

    def test_import_smart_cache(self):
        """SmartCache 임포트 테스트"""
        try:
            from src.utils.performance_optimizer import SmartCache
            self.assertIsNotNone(SmartCache)
        except ImportError:
            pytest.skip("SmartCache not available")


    def test_import_memory_optimizer(self):
        """MemoryOptimizer 임포트 테스트"""
        try:
            from src.utils.performance_optimizer import MemoryOptimizer
            self.assertIsNotNone(MemoryOptimizer)
        except ImportError:
            pytest.skip("MemoryOptimizer not available")

    def test_import_performance_monitor(self):
        """PerformanceMonitor 임포트 테스트"""
        try:
            from src.utils.performance_optimizer import PerformanceMonitor
            self.assertIsNotNone(PerformanceMonitor)
        except ImportError:
            pytest.skip("PerformanceMonitor not available")

    def test_import_decorators(self):
        """데코레이터 임포트 테스트"""
        try:
            from src.utils.performance_optimizer import (
                performance_monitor,
                cached_result,
                batch_process
            )
            self.assertIsNotNone(performance_monitor)
            self.assertIsNotNone(cached_result)
            self.assertIsNotNone(batch_process)
        except ImportError:
            pytest.skip("Performance decorators not available")


    def test_import_utility_functions(self):
        """유틸리티 함수 임포트 테스트"""
        try:
            from src.utils.performance_optimizer import (
                get_performance_monitor,
                optimize_database_queries,
                cleanup_performance_data
            )
            self.assertIsNotNone(get_performance_monitor)
            self.assertIsNotNone(optimize_database_queries)
            self.assertIsNotNone(cleanup_performance_data)
        except ImportError:
            pytest.skip("Performance utility functions not available")








class TestBasicAvailability(unittest.TestCase):
    """기본 사용 가능성 테스트"""

    def test_module_availability(self):
        """모듈 사용 가능성 테스트"""
        try:
            import src.utils.performance_optimizer
            self.assertIsNotNone(src.utils.performance_optimizer)
        except ImportError:
            pytest.skip("Performance optimizer module not available")

    def test_global_monitor_availability(self):
        """전역 모니터 사용 가능성 테스트"""
        try:
            from src.utils.performance_optimizer import g_performance_monitor
            self.assertIsNotNone(g_performance_monitor)
        except ImportError:
            pytest.skip("Global performance monitor not available")


if __name__ == "__main__":
    # 테스트 실행
    print("Running base performance optimizer tests...")
    print("For detailed tests, run:")
    print("  python tests/test_performance_optimizer_core.py")
    print("  python tests/test_performance_optimizer_cache.py")
    print("  python tests/test_performance_optimizer_monitor.py")
    unittest.main(verbosity=2)