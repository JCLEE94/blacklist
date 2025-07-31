"""
성능 최적화를 위한 고급 캐싱 시스템

이 모듈은 Blacklist 시스템의 성능을 향상시키기 위한
다층 캐싱 전략과 캐시 최적화 기능을 제공합니다.
"""

import functools
import hashlib
import pickle
import threading
import time
import weakref
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, Union

try:
    import redis

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

try:
    import orjson as json

    HAS_ORJSON = True
except ImportError:
    import json

    HAS_ORJSON = False

from loguru import logger


@dataclass
class CacheConfig:
    """캐시 설정"""

    default_ttl: int = 300  # 5분
    max_memory_items: int = 1000
    compression_threshold: int = 1024  # 1KB 이상 압축
    enable_metrics: bool = True
    redis_prefix: str = "blacklist:"


class PerformanceCache:
    """고성능 다층 캐시 시스템"""

    def __init__(self, config: CacheConfig = None, redis_client=None):
        self.config = config or CacheConfig()
        self.redis_client = redis_client

        # 메모리 캐시 (L1)
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "memory_hits": 0,
            "redis_hits": 0,
            "compression_saves": 0,
        }
        self._lock = threading.RLock()

        # 캐시 크기 제한을 위한 LRU 추적
        self.access_times = {}

        logger.info(
            f"PerformanceCache initialized with Redis: {self.redis_client is not None}"
        )

    def _generate_key(self, key: str) -> str:
        """캐시 키 생성 및 정규화"""
        if isinstance(key, str):
            return f"{self.config.redis_prefix}{key}"
        return f"{self.config.redis_prefix}{hashlib.md5(str(key).encode()).hexdigest()}"

    def _serialize_value(self, value: Any) -> bytes:
        """값 직렬화 및 압축"""
        try:
            if HAS_ORJSON:
                serialized = json.dumps(value)
                if isinstance(serialized, str):
                    serialized = serialized.encode("utf-8")
            else:
                serialized = json.dumps(value).encode("utf-8")

            # 압축 임계값 초과 시 압축
            if len(serialized) > self.config.compression_threshold:
                import gzip

                compressed = gzip.compress(serialized)
                if len(compressed) < len(serialized):
                    self.cache_stats["compression_saves"] += 1
                    return b"GZIP:" + compressed

            return serialized
        except Exception as e:
            logger.warning(f"Serialization failed, using pickle: {e}")
            return b"PICKLE:" + pickle.dumps(value)

    def _deserialize_value(self, data: bytes) -> Any:
        """값 역직렬화 및 압축 해제"""
        try:
            if data.startswith(b"GZIP:"):
                import gzip

                decompressed = gzip.decompress(data[5:])
                if HAS_ORJSON:
                    return json.loads(decompressed)
                else:
                    return json.loads(decompressed.decode("utf-8"))
            elif data.startswith(b"PICKLE:"):
                return pickle.loads(data[7:])
            else:
                if HAS_ORJSON:
                    return json.loads(data)
                else:
                    return json.loads(data.decode("utf-8"))
        except Exception as e:
            logger.error(f"Deserialization failed: {e}")
            return None

    def get(self, key: str) -> Optional[Any]:
        """다층 캐시에서 값 조회"""
        cache_key = self._generate_key(key)

        with self._lock:
            # L1: 메모리 캐시 확인
            if cache_key in self.memory_cache:
                item = self.memory_cache[cache_key]
                if item["expires_at"] > time.time():
                    self.cache_stats["hits"] += 1
                    self.cache_stats["memory_hits"] += 1
                    self.access_times[cache_key] = time.time()
                    return item["value"]
                else:
                    # 만료된 항목 제거
                    del self.memory_cache[cache_key]
                    del self.access_times[cache_key]

            # L2: Redis 캐시 확인
            if self.redis_client:
                try:
                    data = self.redis_client.get(cache_key)
                    if data:
                        value = self._deserialize_value(data)
                        if value is not None:
                            self.cache_stats["hits"] += 1
                            self.cache_stats["redis_hits"] += 1

                            # 메모리 캐시에 백업 저장
                            self._set_memory_cache(
                                cache_key, value, self.config.default_ttl
                            )
                            return value
                except Exception as e:
                    logger.warning(f"Redis get failed: {e}")

            self.cache_stats["misses"] += 1
            return None

    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """다층 캐시에 값 저장"""
        if ttl is None:
            ttl = self.config.default_ttl

        cache_key = self._generate_key(key)

        try:
            with self._lock:
                # L1: 메모리 캐시에 저장
                self._set_memory_cache(cache_key, value, ttl)

                # L2: Redis 캐시에 저장
                if self.redis_client:
                    try:
                        serialized = self._serialize_value(value)
                        self.redis_client.setex(cache_key, ttl, serialized)
                    except Exception as e:
                        logger.warning(f"Redis set failed: {e}")

                self.cache_stats["sets"] += 1
                return True

        except Exception as e:
            logger.error(f"Cache set failed: {e}")
            return False

    def _set_memory_cache(self, cache_key: str, value: Any, ttl: int):
        """메모리 캐시에 값 저장 (LRU 적용)"""
        # 캐시 크기 제한
        while len(self.memory_cache) >= self.config.max_memory_items:
            # 가장 오래된 항목 제거 (LRU)
            oldest_key = min(
                self.access_times.keys(), key=lambda k: self.access_times[k]
            )
            del self.memory_cache[oldest_key]
            del self.access_times[oldest_key]

        expires_at = time.time() + ttl
        self.memory_cache[cache_key] = {
            "value": value,
            "expires_at": expires_at,
            "created_at": time.time(),
        }
        self.access_times[cache_key] = time.time()

    def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        cache_key = self._generate_key(key)

        with self._lock:
            deleted = False

            # 메모리 캐시에서 삭제
            if cache_key in self.memory_cache:
                del self.memory_cache[cache_key]
                del self.access_times[cache_key]
                deleted = True

            # Redis 캐시에서 삭제
            if self.redis_client:
                try:
                    if self.redis_client.delete(cache_key):
                        deleted = True
                except Exception as e:
                    logger.warning(f"Redis delete failed: {e}")

            if deleted:
                self.cache_stats["deletes"] += 1

            return deleted

    def clear(self) -> bool:
        """모든 캐시 항목 삭제"""
        with self._lock:
            self.memory_cache.clear()
            self.access_times.clear()

            if self.redis_client:
                try:
                    # 프리픽스에 해당하는 키들만 삭제
                    pattern = f"{self.config.redis_prefix}*"
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        self.redis_client.delete(*keys)
                except Exception as e:
                    logger.warning(f"Redis clear failed: {e}")

            return True

    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (
            (self.cache_stats["hits"] / total_requests * 100)
            if total_requests > 0
            else 0
        )

        return {
            **self.cache_stats,
            "hit_rate_percent": round(hit_rate, 2),
            "memory_cache_size": len(self.memory_cache),
            "redis_available": self.redis_client is not None,
            "compression_enabled": True,
            "orjson_enabled": HAS_ORJSON,
        }

    def cleanup_expired(self):
        """만료된 메모리 캐시 항목 정리"""
        current_time = time.time()
        expired_keys = []

        with self._lock:
            for key, item in self.memory_cache.items():
                if item["expires_at"] <= current_time:
                    expired_keys.append(key)

            for key in expired_keys:
                del self.memory_cache[key]
                del self.access_times[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache items")


def performance_cached(ttl: int = 300, key_func: Callable = None):
    """고성능 캐싱 데코레이터"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__module__}.{func.__name__}:{hashlib.md5(str(args + tuple(kwargs.items())).encode()).hexdigest()}"

            # 글로벌 캐시 인스턴스 사용
            cache = get_global_performance_cache()

            # 캐시에서 조회
            result = cache.get(cache_key)
            if result is not None:
                return result

            # 캐시 미스 시 함수 실행
            result = func(*args, **kwargs)

            # 결과를 캐시에 저장
            cache.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


# 글로벌 캐시 인스턴스
_global_performance_cache = None


def get_global_performance_cache() -> PerformanceCache:
    """글로벌 성능 캐시 인스턴스 반환"""
    global _global_performance_cache

    if _global_performance_cache is None:
        # Redis 클라이언트 설정 시도
        redis_client = None
        if HAS_REDIS:
            try:
                import os

                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                redis_client = redis.from_url(redis_url)
                redis_client.ping()  # 연결 테스트
                logger.info("Redis client connected for performance cache")
            except Exception as e:
                logger.warning(f"Redis connection failed, using memory-only cache: {e}")
                redis_client = None

        _global_performance_cache = PerformanceCache(redis_client=redis_client)

    return _global_performance_cache


if __name__ == "__main__":
    """성능 캐시 시스템 검증"""
    import sys

    # 테스트 데이터
    test_data = {
        "small_data": "test_value",
        "large_data": {"data": "x" * 2000, "numbers": list(range(1000))},
        "complex_data": {
            "nested": {"deep": {"structure": {"with": "multiple_levels"}}},
            "array": [{"item": i, "value": f"data_{i}"} for i in range(100)],
        },
    }

    cache = get_global_performance_cache()
    all_tests_passed = True

    try:
        # 테스트 1: 기본 캐시 동작
        for key, value in test_data.items():
            cache.set(key, value, ttl=60)
            retrieved = cache.get(key)
            if retrieved != value:
                print(f"❌ 테스트 실패: {key} - 저장된 값과 조회된 값이 다름")
                all_tests_passed = False

        # 테스트 2: TTL 확인
        cache.set("ttl_test", "ttl_value", ttl=1)
        time.sleep(2)
        if cache.get("ttl_test") is not None:
            print("❌ TTL 테스트 실패: 만료된 항목이 여전히 존재")
            all_tests_passed = False

        # 테스트 3: 통계 확인
        stats = cache.get_stats()
        if stats["sets"] == 0:
            print("❌ 통계 테스트 실패: 설정 횟수가 0")
            all_tests_passed = False

        # 테스트 4: 캐시 정리
        cache.clear()
        if len(cache.memory_cache) > 0:
            print("❌ 정리 테스트 실패: 캐시가 완전히 정리되지 않음")
            all_tests_passed = False

        if all_tests_passed:
            print("✅ 성능 캐시 시스템 검증 완료 - 모든 테스트 통과")
            print(f"📊 최종 통계: {cache.get_stats()}")
            sys.exit(0)
        else:
            print("❌ 일부 테스트 실패")
            sys.exit(1)

    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
