#!/usr/bin/env python3
"""
Core tests for src/utils/performance_optimizer.py
PerformanceMetrics, QueryOptimizer, and core functionality tests
"""

import threading
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.utils.performance_optimizer import (
    PerformanceMetrics,
    QueryOptimizer,
    g_performance_monitor,
    get_performance_monitor,
    optimize_database_queries,
)


class TestPerformanceMetrics(unittest.TestCase):
    """PerformanceMetrics 데이터클래스 테스트"""

    def test_initialization_with_defaults(self):
        """기본값으로 초기화 테스트"""
        metrics = PerformanceMetrics()

        # 기본값 확인
        self.assertEqual(metrics.total_requests, 0)
        self.assertEqual(metrics.avg_response_time, 0.0)
        self.assertEqual(metrics.cache_hit_rate, 0.0)
        self.assertEqual(metrics.memory_usage_mb, 0.0)
        self.assertEqual(metrics.database_query_time, 0.0)
        self.assertEqual(metrics.active_connections, 0)
        self.assertEqual(metrics.error_rate, 0.0)
        self.assertIsNotNone(metrics.timestamp)
        self.assertIsInstance(metrics.timestamp, datetime)

    def test_initialization_with_custom_values(self):
        """커스텀 값으로 초기화 테스트"""
        custom_timestamp = datetime(2023, 1, 1, 12, 0, 0)
        metrics = PerformanceMetrics(
            total_requests=100,
            avg_response_time=50.5,
            cache_hit_rate=85.2,
            memory_usage_mb=256.0,
            database_query_time=25.3,
            active_connections=10,
            error_rate=2.5,
            timestamp=custom_timestamp,
        )

        self.assertEqual(metrics.total_requests, 100)
        self.assertEqual(metrics.avg_response_time, 50.5)
        self.assertEqual(metrics.cache_hit_rate, 85.2)
        self.assertEqual(metrics.memory_usage_mb, 256.0)
        self.assertEqual(metrics.database_query_time, 25.3)
        self.assertEqual(metrics.active_connections, 10)
        self.assertEqual(metrics.error_rate, 2.5)
        self.assertEqual(metrics.timestamp, custom_timestamp)

    def test_post_init_timestamp_setting(self):
        """timestamp 자동 설정 테스트"""
        before_creation = datetime.now()
        metrics = PerformanceMetrics()
        after_creation = datetime.now()

        self.assertGreaterEqual(metrics.timestamp, before_creation)
        self.assertLessEqual(metrics.timestamp, after_creation)


class TestQueryOptimizer(unittest.TestCase):
    """QueryOptimizer 클래스 테스트"""

    def setUp(self):
        """테스트 셋업"""
        self.optimizer = QueryOptimizer()

    def test_initialization(self):
        """QueryOptimizer 초기화 테스트"""
        self.assertIsInstance(self.optimizer.query_cache, dict)
        self.assertIsInstance(self.optimizer.query_stats, dict)
        self.assertIsInstance(self.optimizer.cache_lock, threading.Lock)

    def test_measure_query_time_success(self):
        """쿼리 시간 측정 성공 테스트"""
        query_name = "test_query"

        with self.optimizer.measure_query_time(query_name):
            time.sleep(0.1)  # 0.1초 대기

        # 통계가 기록되었는지 확인
        self.assertIn(query_name, self.optimizer.query_stats)
        stats = self.optimizer.query_stats[query_name]
        self.assertEqual(stats["count"], 1)
        self.assertGreaterEqual(stats["avg_time"], 0.1)
        self.assertGreaterEqual(stats["max_time"], 0.1)

    def test_measure_query_time_with_exception(self):
        """쿼리 시간 측정 중 예외 발생 테스트"""
        query_name = "exception_query"

        try:
            with self.optimizer.measure_query_time(query_name):
                time.sleep(0.05)
                raise ValueError("Test exception")
        except ValueError:
            pass

        # 예외가 발생해도 통계는 기록되어야 함
        self.assertIn(query_name, self.optimizer.query_stats)
        stats = self.optimizer.query_stats[query_name]
        self.assertEqual(stats["count"], 1)
        self.assertGreaterEqual(stats["avg_time"], 0.05)

    def test_record_query_stats_multiple_calls(self):
        """쿼리 통계 기록 - 여러 호출 테스트"""
        query_name = "multi_query"

        # 여러 번 쿼리 실행
        self.optimizer._record_query_stats(query_name, 0.1)
        self.optimizer._record_query_stats(query_name, 0.2)
        self.optimizer._record_query_stats(query_name, 0.3)

        stats = self.optimizer.query_stats[query_name]
        self.assertEqual(stats["count"], 3)
        self.assertEqual(stats["total_time"], 0.6)
        self.assertEqual(stats["avg_time"], 0.2)
        self.assertEqual(stats["max_time"], 0.3)

    def test_record_query_stats_thread_safety(self):
        """쿼리 통계 기록 스레드 안전성 테스트"""
        query_name = "thread_query"

        def record_stats():
            for _ in range(10):
                self.optimizer._record_query_stats(query_name, 0.1)

        threads = []
        for _ in range(5):
            thread = threading.Thread(target=record_stats)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 모든 통계가 정확히 기록되었는지 확인
        stats = self.optimizer.query_stats[query_name]
        self.assertEqual(stats["count"], 50)

    def test_get_slow_queries_with_threshold(self):
        """느린 쿼리 조회 - 임계값 적용 테스트"""
        # 빠른 쿼리
        self.optimizer._record_query_stats("fast_query", 0.1)
        self.optimizer._record_query_stats("fast_query", 0.2)

        # 느린 쿼리
        self.optimizer._record_query_stats("slow_query", 1.5)
        self.optimizer._record_query_stats("slow_query", 2.0)

        # 임계값 1.0으로 느린 쿼리 조회
        slow_queries = self.optimizer.get_slow_queries(threshold=1.0)

        self.assertNotIn("fast_query", slow_queries)
        self.assertIn("slow_query", slow_queries)
        self.assertEqual(slow_queries["slow_query"]["avg_time"], 1.75)

    def test_get_slow_queries_empty(self):
        """느린 쿼리 조회 - 빈 결과 테스트"""
        self.optimizer._record_query_stats("fast_query", 0.1)

        slow_queries = self.optimizer.get_slow_queries(threshold=1.0)
        self.assertEqual(len(slow_queries), 0)

    def test_clear_stats(self):
        """통계 초기화 테스트"""
        self.optimizer._record_query_stats("test_query", 0.1)
        self.assertGreater(len(self.optimizer.query_stats), 0)

        self.optimizer.clear_stats()
        self.assertEqual(len(self.optimizer.query_stats), 0)


class TestGlobalFunctions(unittest.TestCase):
    """전역 함수 테스트"""

    def test_get_performance_monitor(self):
        """성능 모니터 인스턴스 반환 테스트"""
        monitor = get_performance_monitor()

        self.assertIsNotNone(monitor)
        self.assertEqual(monitor, g_performance_monitor)

    def test_optimize_database_queries_no_slow_queries(self):
        """느린 쿼리가 없는 경우 최적화 테스트"""
        # 전역 모니터 초기화
        g_performance_monitor.query_optimizer.clear_stats()

        slow_queries = optimize_database_queries()

        self.assertEqual(len(slow_queries), 0)

    def test_optimize_database_queries_with_slow_queries(self):
        """느린 쿼리가 있는 경우 최적화 테스트"""
        # 느린 쿼리 추가
        g_performance_monitor.query_optimizer._record_query_stats("slow_query", 2.0)

        slow_queries = optimize_database_queries()

        self.assertIn("slow_query", slow_queries)


if __name__ == "__main__":
    # 테스트 실행
    unittest.main(verbosity=2)
