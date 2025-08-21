#!/usr/bin/env python3
"""
Caching and Memory optimization tests for src/utils/performance_optimizer.py
SmartCache, MemoryOptimizer, and related functionality tests
"""

import threading
import time
import unittest
import weakref
from unittest.mock import MagicMock, patch

import pytest

from src.utils.performance_optimizer import MemoryOptimizer, SmartCache


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


if __name__ == "__main__":
    # 테스트 실행
    unittest.main(verbosity=2)
