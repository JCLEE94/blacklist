#!/usr/bin/env python3
"""
Comprehensive unit tests for src/utils/performance_optimizer.py
테스트 커버리지 향상을 위한 성능 최적화 모듈 포괄적 테스트
"""

import threading
import time
import unittest
import weakref
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.utils.performance_optimizer import (
    MemoryOptimizer,
    PerformanceMetrics,
    PerformanceMonitor,
    QueryOptimizer,
    SmartCache,
    batch_process,
    cached_result,
    cleanup_performance_data,
    g_performance_monitor,
    get_performance_monitor,
    optimize_database_queries,
    performance_monitor,
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
            timestamp=custom_timestamp
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


class TestSmartCache(unittest.TestCase):
    """SmartCache 클래스 테스트"""

    def setUp(self):
        """테스트 셋업"""
        self.cache = SmartCache(max_size=5, ttl_seconds=2)

    def test_initialization(self):
        """SmartCache 초기화 테스트"""
        self.assertEqual(self.cache.max_size, 5)
        self.assertEqual(self.cache.ttl_seconds, 2)
        self.assertEqual(self.cache.hit_count, 0)
        self.assertEqual(self.cache.miss_count, 0)
        self.assertIsInstance(self.cache.cache, dict)
        self.assertIsInstance(self.cache.access_times, dict)

    def test_set_and_get_success(self):
        """캐시 설정 및 조회 성공 테스트"""
        key = "test_key"
        value = "test_value"
        
        self.cache.set(key, value)
        retrieved_value = self.cache.get(key)
        
        self.assertEqual(retrieved_value, value)
        self.assertEqual(self.cache.hit_count, 1)
        self.assertEqual(self.cache.miss_count, 0)

    def test_get_miss(self):
        """캐시 미스 테스트"""
        value = self.cache.get("nonexistent_key")
        
        self.assertIsNone(value)
        self.assertEqual(self.cache.hit_count, 0)
        self.assertEqual(self.cache.miss_count, 1)

    def test_ttl_expiry(self):
        """TTL 만료 테스트"""
        key = "expiry_key"
        value = "expiry_value"
        
        self.cache.set(key, value)
        
        # TTL 시간 대기
        time.sleep(2.1)
        
        retrieved_value = self.cache.get(key)
        
        self.assertIsNone(retrieved_value)
        self.assertEqual(self.cache.miss_count, 1)
        self.assertNotIn(key, self.cache.cache)

    def test_lru_eviction(self):
        """LRU 기반 캐시 제거 테스트"""
        # 캐시 크기 제한까지 채우기
        for i in range(5):
            self.cache.set(f"key_{i}", f"value_{i}")
        
        # 첫 번째 키 접근하여 최근 사용으로 만들기
        self.cache.get("key_0")
        
        # 새 키 추가하여 LRU 제거 트리거
        self.cache.set("new_key", "new_value")
        
        # key_1이 제거되어야 함 (key_0은 최근 접근으로 보호됨)
        self.assertIsNone(self.cache.get("key_1"))
        self.assertIsNotNone(self.cache.get("key_0"))
        self.assertIsNotNone(self.cache.get("new_key"))

    def test_evict_least_recently_used_empty_cache(self):
        """빈 캐시에서 LRU 제거 테스트"""
        # 빈 캐시에서 LRU 제거 시도 - 에러가 발생하지 않아야 함
        self.cache._evict_least_recently_used()
        self.assertEqual(len(self.cache.cache), 0)

    def test_clear_expired(self):
        """만료된 캐시 항목 정리 테스트"""
        # 여러 항목 추가
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        
        # TTL 시간 대기
        time.sleep(2.1)
        
        # 새 항목 추가 (만료되지 않음)
        self.cache.set("key3", "value3")
        
        # 만료된 항목 정리
        expired_count = self.cache.clear_expired()
        
        self.assertEqual(expired_count, 2)
        self.assertNotIn("key1", self.cache.cache)
        self.assertNotIn("key2", self.cache.cache)
        self.assertIn("key3", self.cache.cache)

    def test_get_stats(self):
        """캐시 통계 조회 테스트"""
        # 몇 개 항목 추가 및 조회
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.get("key1")  # hit
        self.cache.get("nonexistent")  # miss
        
        stats = self.cache.get_stats()
        
        self.assertEqual(stats["size"], 2)
        self.assertEqual(stats["max_size"], 5)
        self.assertEqual(stats["hit_count"], 1)
        self.assertEqual(stats["miss_count"], 1)
        self.assertEqual(stats["hit_rate"], 50.0)
        self.assertEqual(stats["ttl_seconds"], 2)

    def test_thread_safety(self):
        """스레드 안전성 테스트"""
        def cache_worker(worker_id):
            for i in range(10):
                key = f"worker_{worker_id}_key_{i}"
                value = f"worker_{worker_id}_value_{i}"
                self.cache.set(key, value)
                retrieved = self.cache.get(key)
                self.assertEqual(retrieved, value)
        
        threads = []
        for worker_id in range(3):
            thread = threading.Thread(target=cache_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 스레드 안전성 확인을 위해 통계 검증
        stats = self.cache.get_stats()
        self.assertGreater(stats["hit_count"], 0)


class TestMemoryOptimizer(unittest.TestCase):
    """MemoryOptimizer 클래스 테스트"""

    def setUp(self):
        """테스트 셋업"""
        self.optimizer = MemoryOptimizer()

    def test_initialization(self):
        """MemoryOptimizer 초기화 테스트"""
        self.assertIsInstance(self.optimizer.weak_references, weakref.WeakSet)
        self.assertIsInstance(self.optimizer.object_pools, dict)

    def test_create_object_pool(self):
        """객체 풀 생성 테스트"""
        pool_name = "test_pool"
        factory = lambda: {"created": True}
        max_size = 5
        
        self.optimizer.create_object_pool(pool_name, factory, max_size)
        
        self.assertIn(pool_name, self.optimizer.object_pools)
        pool_info = self.optimizer.object_pools[pool_name]
        self.assertEqual(pool_info["factory"], factory)
        self.assertEqual(pool_info["max_size"], max_size)
        self.assertIsInstance(pool_info["pool"], list)
        self.assertIsInstance(pool_info["lock"], threading.Lock)

    def test_get_from_pool_new_object(self):
        """객체 풀에서 새 객체 획득 테스트"""
        pool_name = "new_object_pool"
        factory = lambda: {"id": "new_object"}
        
        self.optimizer.create_object_pool(pool_name, factory)
        obj = self.optimizer.get_from_pool(pool_name)
        
        self.assertEqual(obj["id"], "new_object")

    def test_get_from_pool_reused_object(self):
        """객체 풀에서 재사용 객체 획득 테스트"""
        pool_name = "reuse_pool"
        factory = lambda: {"id": "reused_object"}
        
        self.optimizer.create_object_pool(pool_name, factory)
        
        # 객체 생성 후 풀에 반환
        obj1 = self.optimizer.get_from_pool(pool_name)
        self.optimizer.return_to_pool(pool_name, obj1)
        
        # 같은 객체가 재사용되는지 확인
        obj2 = self.optimizer.get_from_pool(pool_name)
        self.assertEqual(obj1, obj2)

    def test_get_from_pool_unknown_pool(self):
        """존재하지 않는 풀에서 객체 획득 테스트"""
        with self.assertRaises(ValueError):
            self.optimizer.get_from_pool("unknown_pool")

    def test_return_to_pool_success(self):
        """객체 풀에 반환 성공 테스트"""
        pool_name = "return_pool"
        factory = lambda: {"counter": 0}
        
        self.optimizer.create_object_pool(pool_name, factory, max_size=2)
        
        obj1 = self.optimizer.get_from_pool(pool_name)
        obj2 = self.optimizer.get_from_pool(pool_name)
        
        # 풀에 반환
        self.optimizer.return_to_pool(pool_name, obj1)
        self.optimizer.return_to_pool(pool_name, obj2)
        
        pool_info = self.optimizer.object_pools[pool_name]
        self.assertEqual(len(pool_info["pool"]), 2)

    def test_return_to_pool_max_size_exceeded(self):
        """객체 풀 최대 크기 초과 시 반환 테스트"""
        pool_name = "max_size_pool"
        factory = lambda: {"counter": 0}
        
        self.optimizer.create_object_pool(pool_name, factory, max_size=1)
        
        obj1 = self.optimizer.get_from_pool(pool_name)
        obj2 = self.optimizer.get_from_pool(pool_name)
        
        # 첫 번째 객체 반환
        self.optimizer.return_to_pool(pool_name, obj1)
        
        # 두 번째 객체 반환 (최대 크기 초과)
        self.optimizer.return_to_pool(pool_name, obj2)
        
        pool_info = self.optimizer.object_pools[pool_name]
        self.assertEqual(len(pool_info["pool"]), 1)  # 최대 크기 유지

    def test_return_to_pool_with_reset_method(self):
        """reset 메소드가 있는 객체 풀 반환 테스트"""
        class ResettableObject:
            def __init__(self):
                self.value = "original"
            
            def reset(self):
                self.value = "reset"
        
        pool_name = "reset_pool"
        factory = ResettableObject
        
        self.optimizer.create_object_pool(pool_name, factory)
        
        obj = self.optimizer.get_from_pool(pool_name)
        obj.value = "modified"
        
        self.optimizer.return_to_pool(pool_name, obj)
        
        # reset 메소드가 호출되었는지 확인
        self.assertEqual(obj.value, "reset")

    def test_return_to_pool_unknown_pool(self):
        """존재하지 않는 풀에 객체 반환 테스트"""
        # 에러가 발생하지 않아야 함
        self.optimizer.return_to_pool("unknown_pool", {})

    def test_optimize_large_list(self):
        """큰 리스트 최적화 테스트"""
        large_list = list(range(2500))  # 2500개 항목
        chunk_size = 1000
        
        chunks = self.optimizer.optimize_large_list(large_list, chunk_size)
        
        # 3개의 청크가 생성되어야 함 (1000, 1000, 500)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(len(chunks[0]), 1000)
        self.assertEqual(len(chunks[1]), 1000)
        self.assertEqual(len(chunks[2]), 500)
        
        # 모든 항목이 보존되는지 확인
        flattened = [item for chunk in chunks for item in chunk]
        self.assertEqual(flattened, large_list)

    def test_optimize_large_list_small_input(self):
        """작은 리스트 최적화 테스트"""
        small_list = [1, 2, 3, 4, 5]
        chunks = self.optimizer.optimize_large_list(small_list, 1000)
        
        # 하나의 청크만 생성되어야 함
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], small_list)

    def test_memory_efficient_join_small_list(self):
        """작은 리스트 메모리 효율적 조인 테스트"""
        small_items = ["a", "b", "c", "d", "e"]
        result = self.optimizer.memory_efficient_join(small_items, "-")
        
        self.assertEqual(result, "a-b-c-d-e")

    def test_memory_efficient_join_large_list(self):
        """큰 리스트 메모리 효율적 조인 테스트"""
        # 1500개 항목 (1000개 이상)
        large_items = [str(i) for i in range(1500)]
        result = self.optimizer.memory_efficient_join(large_items, ",")
        
        # 결과가 올바른지 확인
        expected = ",".join(large_items)
        self.assertEqual(result, expected)

    def test_memory_efficient_join_empty_separator(self):
        """빈 구분자로 메모리 효율적 조인 테스트"""
        items = ["hello", "world", "test"]
        result = self.optimizer.memory_efficient_join(items)
        
        self.assertEqual(result, "helloworldtest")


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
        self.assertIsInstance(self.monitor.query_optimizer, QueryOptimizer)
        self.assertIsInstance(self.monitor.smart_cache, SmartCache)
        self.assertIsInstance(self.monitor.memory_optimizer, MemoryOptimizer)

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


class TestGlobalFunctions(unittest.TestCase):
    """전역 함수 테스트"""

    def test_get_performance_monitor(self):
        """성능 모니터 인스턴스 반환 테스트"""
        monitor = get_performance_monitor()
        
        self.assertIsInstance(monitor, PerformanceMonitor)
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