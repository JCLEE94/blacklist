"""
성능 최적화 유틸리티
메모리 사용량 최적화, 쿼리 최적화, 캐시 전략 등
"""

import logging
import threading
import time
import weakref
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """성능 메트릭"""

    total_requests: int = 0
    avg_response_time: float = 0.0
    cache_hit_rate: float = 0.0
    memory_usage_mb: float = 0.0
    database_query_time: float = 0.0
    active_connections: int = 0
    error_rate: float = 0.0
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class QueryOptimizer:
    """데이터베이스 쿼리 최적화"""

    def __init__(self):
        self.query_cache = {}
        self.query_stats = {}
        self.cache_lock = threading.Lock()

    @contextmanager
    def measure_query_time(self, query_name: str):
        """쿼리 실행 시간 측정"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self._record_query_stats(query_name, duration)

    def _record_query_stats(self, query_name: str, duration: float):
        """쿼리 통계 기록"""
        with self.cache_lock:
            if query_name not in self.query_stats:
                self.query_stats[query_name] = {
                    "count": 0,
                    "total_time": 0.0,
                    "avg_time": 0.0,
                    "max_time": 0.0,
                }

            stats = self.query_stats[query_name]
            stats["count"] += 1
            stats["total_time"] += duration
            stats["avg_time"] = stats["total_time"] / stats["count"]
            stats["max_time"] = max(stats["max_time"], duration)

    def get_slow_queries(self, threshold: float = 1.0) -> Dict[str, Dict]:
        """느린 쿼리 목록 반환"""
        with self.cache_lock:
            return {
                name: stats
                for name, stats in self.query_stats.items()
                if stats["avg_time"] > threshold
            }

    def clear_stats(self):
        """통계 초기화"""
        with self.cache_lock:
            self.query_stats.clear()


class SmartCache:
    """지능형 캐싱 시스템"""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = {}
        self.access_times = {}
        self.hit_count = 0
        self.miss_count = 0
        self.lock = threading.Lock()

    def get(self, key: str) -> Any:
        """캐시에서 값 조회"""
        with self.lock:
            if key in self.cache:
                # TTL 확인
                if time.time() - self.cache[key]["timestamp"] < self.ttl_seconds:
                    self.access_times[key] = time.time()
                    self.hit_count += 1
                    return self.cache[key]["value"]
                else:
                    # 만료된 항목 제거
                    del self.cache[key]
                    del self.access_times[key]

            self.miss_count += 1
            return None

    def set(self, key: str, value: Any):
        """캐시에 값 저장"""
        with self.lock:
            current_time = time.time()

            # 캐시 크기 제한 확인
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_least_recently_used()

            self.cache[key] = {"value": value, "timestamp": current_time}
            self.access_times[key] = current_time

    def _evict_least_recently_used(self):
        """LRU 기반 캐시 제거"""
        if not self.access_times:
            return

        oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        del self.cache[oldest_key]
        del self.access_times[oldest_key]

    def clear_expired(self):
        """만료된 캐시 항목 정리"""
        with self.lock:
            current_time = time.time()
            expired_keys = []

            for key, data in self.cache.items():
                if current_time - data["timestamp"] >= self.ttl_seconds:
                    expired_keys.append(key)

            for key in expired_keys:
                del self.cache[key]
                del self.access_times[key]

            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": round(hit_rate, 2),
            "ttl_seconds": self.ttl_seconds,
        }


class MemoryOptimizer:
    """메모리 사용량 최적화"""

    def __init__(self):
        self.weak_references = weakref.WeakSet()
        self.object_pools = {}

    def create_object_pool(self, name: str, factory: Callable, max_size: int = 10):
        """객체 풀 생성"""
        self.object_pools[name] = {
            "factory": factory,
            "pool": [],
            "max_size": max_size,
            "lock": threading.Lock(),
        }

    def get_from_pool(self, pool_name: str):
        """객체 풀에서 객체 획득"""
        if pool_name not in self.object_pools:
            raise ValueError("Unknown pool: {pool_name}")

        pool_info = self.object_pools[pool_name]
        with pool_info["lock"]:
            if pool_info["pool"]:
                return pool_info["pool"].pop()
            else:
                return pool_info["factory"]()

    def return_to_pool(self, pool_name: str, obj: Any):
        """객체를 풀에 반환"""
        if pool_name not in self.object_pools:
            return

        pool_info = self.object_pools[pool_name]
        with pool_info["lock"]:
            if len(pool_info["pool"]) < pool_info["max_size"]:
                # 객체 초기화 (필요한 경우)
                if hasattr(obj, "reset"):
                    obj.reset()
                pool_info["pool"].append(obj)

    def optimize_large_list(
        self, data: List[Any], chunk_size: int = 1000
    ) -> List[List[Any]]:
        """큰 리스트를 청크로 분할하여 메모리 최적화"""
        return [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

    def memory_efficient_join(self, items: List[str], separator: str = "") -> str:
        """메모리 효율적인 문자열 조인"""
        if len(items) < 1000:
            return separator.join(items)

        # 큰 리스트의 경우 청크 단위로 처리
        chunks = self.optimize_large_list(items, 1000)
        return separator.join(separator.join(chunk) for chunk in chunks)


class PerformanceMonitor:
    """성능 모니터링"""

    def __init__(self):
        self.metrics_history = []
        self.request_times = []
        self.lock = threading.Lock()
        self.query_optimizer = QueryOptimizer()
        self.smart_cache = SmartCache()
        self.memory_optimizer = MemoryOptimizer()

    def record_request_time(self, duration: float):
        """요청 처리 시간 기록"""
        with self.lock:
            self.request_times.append(duration)
            # 최근 1000개만 유지
            if len(self.request_times) > 1000:
                self.request_times = self.request_times[-1000:]

    def get_current_metrics(self) -> PerformanceMetrics:
        """현재 성능 메트릭 반환"""
        with self.lock:
            if not self.request_times:
                avg_response_time = 0.0
            else:
                avg_response_time = sum(self.request_times) / len(self.request_times)

            cache_stats = self.smart_cache.get_stats()

            return PerformanceMetrics(
                total_requests=len(self.request_times),
                avg_response_time=round(avg_response_time * 1000, 2),  # ms
                cache_hit_rate=cache_stats["hit_rate"],
                timestamp=datetime.now(),
            )

    def clear_metrics(self):
        """메트릭 초기화"""
        with self.lock:
            self.request_times.clear()
            self.metrics_history.clear()
            self.query_optimizer.clear_stats()


def performance_monitor(func: Callable) -> Callable:
    """성능 모니터링 데코레이터"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            # 전역 성능 모니터에 기록
            if hasattr(g_performance_monitor, "record_request_time"):
                g_performance_monitor.record_request_time(duration)

    return wrapper


def cached_result(ttl: int = 3600, key_func: Callable = None):
    """결과 캐싱 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = "{func.__name__}:{hash(str(args) + str(kwargs))}"

            # 캐시에서 조회
            cached_value = g_performance_monitor.smart_cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 캐시 미스 시 실제 함수 실행
            result = func(*args, **kwargs)
            g_performance_monitor.smart_cache.set(cache_key, result)
            return result

        return wrapper

    return decorator


def batch_process(batch_size: int = 100):
    """배치 처리 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(items: List[Any], *args, **kwargs):
            if len(items) <= batch_size:
                return func(items, *args, **kwargs)

            # 배치 단위로 처리
            results = []
            for i in range(0, len(items), batch_size):
                batch = items[i : i + batch_size]
                batch_result = func(batch, *args, **kwargs)
                if isinstance(batch_result, list):
                    results.extend(batch_result)
                else:
                    results.append(batch_result)

            return results

        return wrapper

    return decorator


# 전역 성능 모니터 인스턴스
g_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """성능 모니터 인스턴스 반환"""
    return g_performance_monitor


def optimize_database_queries():
    """데이터베이스 쿼리 최적화 권장사항 출력"""
    slow_queries = g_performance_monitor.query_optimizer.get_slow_queries()
    if slow_queries:
        logger.warning("Slow queries detected:")
        for query_name, stats in slow_queries.items():
            logger.warning(
                "  {query_name}: avg {stats['avg_time']:.3f}s, max {stats['max_time']:.3f}s"
            )

    return slow_queries


def cleanup_performance_data():
    """성능 데이터 정리"""
    expired_count = g_performance_monitor.smart_cache.clear_expired()
    logger.info(f"Cleaned up {expired_count} expired cache entries")

    # 메트릭 히스토리 정리 (7일 이상 된 것)
    cutoff_date = datetime.now() - timedelta(days=7)
    g_performance_monitor.metrics_history = [
        m for m in g_performance_monitor.metrics_history if m.timestamp > cutoff_date
    ]
