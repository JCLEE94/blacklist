#!/usr/bin/env python3
"""
Performance monitoring and decorators tests for src/utils/performance_optimizer.py
PerformanceMonitor, decorators, and utility functions tests
"""

import threading
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.utils.performance_optimizer import (
    PerformanceMetrics,
    PerformanceMonitor,
    batch_process,
    cached_result,
    cleanup_performance_data,
    g_performance_monitor,
    performance_monitor,
)


class TestPerformanceMonitor(unittest.TestCase):
    """PerformanceMonitor 클래스 테스트"""

    def setUp(self):
        """테스트 셋업"""
        self.monitor = PerformanceMonitor()

    def test_initialization(self):
        """PerformanceMonitor 초기화 테스트"""
        self.assertIsInstance(self.monitor.metrics_history, list)
        self.assertIsInstance(self.monitor.request_times, list)
        self.assertIsInstance(self.monitor.lock, threading.Lock)
        self.assertIsNotNone(self.monitor.query_optimizer)
        self.assertIsNotNone(self.monitor.smart_cache)
        self.assertIsNotNone(self.monitor.memory_optimizer)

    def test_record_request_time(self):
        """요청 시간 기록 테스트"""
        self.monitor.record_request_time(0.1)
        self.monitor.record_request_time(0.2)
        self.monitor.record_request_time(0.15)

        self.assertEqual(len(self.monitor.request_times), 3)
        self.assertIn(0.1, self.monitor.request_times)
        self.assertIn(0.2, self.monitor.request_times)
        self.assertIn(0.15, self.monitor.request_times)

    def test_record_request_time_limit(self):
        """요청 시간 기록 제한 테스트"""
        # 1001개 기록
        for i in range(1001):
            self.monitor.record_request_time(i * 0.001)

        # 최근 1000개만 유지되어야 함
        self.assertEqual(len(self.monitor.request_times), 1000)

        # 첫 번째 기록은 제거되어야 함
        self.assertNotIn(0.0, self.monitor.request_times)

    def test_record_request_time_thread_safety(self):
        """요청 시간 기록 스레드 안전성 테스트"""

        def record_times():
            for i in range(10):
                self.monitor.record_request_time(i * 0.01)

        threads = []
        for _ in range(5):
            thread = threading.Thread(target=record_times)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 모든 시간이 기록되었는지 확인
        self.assertEqual(len(self.monitor.request_times), 50)

    def test_get_current_metrics_no_requests(self):
        """요청이 없는 경우 현재 메트릭 조회 테스트"""
        metrics = self.monitor.get_current_metrics()

        self.assertEqual(metrics.total_requests, 0)
        self.assertEqual(metrics.avg_response_time, 0.0)
        self.assertIsInstance(metrics.timestamp, datetime)

    def test_get_current_metrics_with_requests(self):
        """요청이 있는 경우 현재 메트릭 조회 테스트"""
        self.monitor.record_request_time(0.1)  # 100ms
        self.monitor.record_request_time(0.2)  # 200ms
        self.monitor.record_request_time(0.3)  # 300ms

        metrics = self.monitor.get_current_metrics()

        self.assertEqual(metrics.total_requests, 3)
        self.assertEqual(metrics.avg_response_time, 200.0)  # (100+200+300)/3 = 200ms

    def test_clear_metrics(self):
        """메트릭 초기화 테스트"""
        self.monitor.record_request_time(0.1)
        self.monitor.metrics_history.append("test_metric")
        self.monitor.query_optimizer._record_query_stats("test", 0.1)

        self.monitor.clear_metrics()

        self.assertEqual(len(self.monitor.request_times), 0)
        self.assertEqual(len(self.monitor.metrics_history), 0)
        self.assertEqual(len(self.monitor.query_optimizer.query_stats), 0)


class TestDecorators(unittest.TestCase):
    """데코레이터 테스트"""

    def test_performance_monitor_decorator(self):
        """성능 모니터링 데코레이터 테스트"""

        @performance_monitor
        def test_function():
            time.sleep(0.1)
            return "success"

        result = test_function()

        self.assertEqual(result, "success")
        # 전역 모니터에 시간이 기록되었는지 확인
        self.assertGreater(len(g_performance_monitor.request_times), 0)

    def test_performance_monitor_decorator_with_exception(self):
        """성능 모니터링 데코레이터 예외 처리 테스트"""

        @performance_monitor
        def test_function_with_error():
            time.sleep(0.05)
            raise ValueError("Test error")

        with self.assertRaises(ValueError):
            test_function_with_error()

        # 예외가 발생해도 시간이 기록되어야 함
        self.assertGreater(len(g_performance_monitor.request_times), 0)

    def test_cached_result_decorator_basic(self):
        """결과 캐싱 데코레이터 기본 테스트"""
        call_count = 0

        @cached_result(ttl=3600)
        def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        # 첫 번째 호출
        result1 = expensive_function(1, 2)
        self.assertEqual(result1, 3)
        self.assertEqual(call_count, 1)

        # 두 번째 호출 (캐시에서 반환)
        result2 = expensive_function(1, 2)
        self.assertEqual(result2, 3)
        self.assertEqual(call_count, 1)  # 호출 횟수 증가하지 않음

    def test_cached_result_decorator_different_args(self):
        """결과 캐싱 데코레이터 다른 인수 테스트"""
        call_count = 0

        @cached_result(ttl=3600)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_function(5)
        result2 = expensive_function(10)

        self.assertEqual(result1, 10)
        self.assertEqual(result2, 20)
        self.assertEqual(call_count, 2)  # 다른 인수이므로 각각 호출

    def test_cached_result_decorator_with_key_func(self):
        """결과 캐싱 데코레이터 커스텀 키 함수 테스트"""
        call_count = 0

        def custom_key(*args, **kwargs):
            return f"custom_{args[0]}"

        @cached_result(ttl=3600, key_func=custom_key)
        def function_with_custom_key(x, y=None):
            nonlocal call_count
            call_count += 1
            return x

        result1 = function_with_custom_key(1, y="a")
        result2 = function_with_custom_key(1, y="b")  # 다른 y 값이지만 같은 키

        self.assertEqual(result1, 1)
        self.assertEqual(result2, 1)
        self.assertEqual(call_count, 1)  # 커스텀 키 함수로 인해 캐시 히트

    def test_batch_process_decorator_small_batch(self):
        """배치 처리 데코레이터 작은 배치 테스트"""

        @batch_process(batch_size=5)
        def process_items(items):
            return [item * 2 for item in items]

        items = [1, 2, 3]
        result = process_items(items)

        self.assertEqual(result, [2, 4, 6])

    def test_batch_process_decorator_large_batch(self):
        """배치 처리 데코레이터 큰 배치 테스트"""

        @batch_process(batch_size=3)
        def process_items(items):
            return [item * 2 for item in items]

        items = [1, 2, 3, 4, 5, 6, 7]  # 7개 항목
        result = process_items(items)

        expected = [2, 4, 6, 8, 10, 12, 14]
        self.assertEqual(result, expected)

    def test_batch_process_decorator_non_list_result(self):
        """배치 처리 데코레이터 비리스트 결과 테스트"""

        @batch_process(batch_size=2)
        def sum_items(items):
            return sum(items)

        items = [1, 2, 3, 4, 5]
        result = sum_items(items)

        # 각 배치의 합계: [3, 7, 5]
        self.assertEqual(result, [3, 7, 5])


class TestCleanupFunctions(unittest.TestCase):
    """정리 함수 테스트"""

    def test_cleanup_performance_data(self):
        """성능 데이터 정리 테스트"""
        # 만료될 캐시 데이터 추가
        g_performance_monitor.smart_cache.set("test_key", "test_value")

        # 오래된 메트릭 추가
        old_metric = PerformanceMetrics(timestamp=datetime.now() - timedelta(days=8))
        recent_metric = PerformanceMetrics(timestamp=datetime.now() - timedelta(days=1))
        g_performance_monitor.metrics_history = [old_metric, recent_metric]

        cleanup_performance_data()

        # 최근 메트릭만 남아있어야 함
        self.assertEqual(len(g_performance_monitor.metrics_history), 1)
        self.assertEqual(g_performance_monitor.metrics_history[0], recent_metric)


if __name__ == "__main__":
    # 테스트 실행
    unittest.main(verbosity=2)
