"""
캐싱 유틸리티 - Redis 및 인메모리 캐싱
"""
import os
import json
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Optional, Union, Callable, List, Dict
import logging

logger = logging.getLogger(__name__)

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, falling back to in-memory cache")


class CacheManager:
    """고성능 캐시 관리자 - Redis 또는 최적화된 인메모리 캐싱"""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl: int = 300,
        max_memory_items: int = 10000,
    ):
        self.default_ttl = default_ttl
        self.max_memory_items = max_memory_items
        self.cache_type = "redis" if REDIS_AVAILABLE and redis_url else "memory"

        # 성능 통계
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0,
            "total_requests": 0,
        }

        if self.cache_type == "redis":
            try:
                # Redis 연결 풀 최적화
                pool = redis.ConnectionPool.from_url(
                    redis_url,
                    max_connections=20,
                    retry_on_timeout=True,
                    health_check_interval=30,
                )
                self.redis_client = redis.Redis(connection_pool=pool)
                self.redis_client.ping()
                logger.info("Redis cache initialized with connection pool")
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                self.cache_type = "memory"

        if self.cache_type == "memory":
            # LRU 캐시 구현
            from collections import OrderedDict

            self.memory_cache = OrderedDict()
            self.memory_expiry = {}
            logger.info(f"In-memory cache initialized (max {max_memory_items} items)")

    def _make_key(self, key: str, prefix: str = "secudium") -> str:
        """캐시 키 생성"""
        return f"{prefix}:{key}"

    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회 (LRU 및 성능 통계 포함)"""
        cache_key = self._make_key(key)
        self.stats["total_requests"] += 1

        if self.cache_type == "redis":
            try:
                value = self.redis_client.get(cache_key)
                if value:
                    self.stats["hits"] += 1
                    return json.loads(value)
                else:
                    self.stats["misses"] += 1
            except Exception as e:
                logger.error(f"Redis get error: {e}")
                self.stats["misses"] += 1
        else:
            # 인메모리 캐시 (LRU)
            if cache_key in self.memory_cache:
                # 만료 확인
                if cache_key in self.memory_expiry:
                    if datetime.now() > self.memory_expiry[cache_key]:
                        del self.memory_cache[cache_key]
                        del self.memory_expiry[cache_key]
                        self.stats["misses"] += 1
                        return None

                # LRU: 최근 사용 항목을 맨 뒤로 이동
                value = self.memory_cache.pop(cache_key)
                self.memory_cache[cache_key] = value
                self.stats["hits"] += 1
                return value
            else:
                self.stats["misses"] += 1

        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """캐시에 값 저장 (LRU 제거 및 통계 포함)"""
        cache_key = self._make_key(key)
        ttl = ttl or self.default_ttl
        self.stats["sets"] += 1

        try:
            # Response 객체 및 기타 직렬화 불가능한 객체 처리
            from flask import Response as FlaskResponse
            from werkzeug.wrappers import Response as WerkzeugResponse

            if isinstance(value, (FlaskResponse, WerkzeugResponse)):
                # Response 객체는 캐시하지 않음
                logger.debug("Skipping cache for Response object")
                return False
            elif hasattr(value, "get_json"):
                try:
                    value = value.get_json()
                except:
                    # JSON 변환 실패시 캐시하지 않음
                    logger.debug("Failed to convert object to JSON, skipping cache")
                    return False
            elif hasattr(value, "data") and not isinstance(value, (str, bytes)):
                value = value.data

            # datetime 객체 처리
            if hasattr(value, "isoformat"):
                value = value.isoformat()

            serialized = json.dumps(value, ensure_ascii=False, default=str)
        except Exception as e:
            logger.debug(f"Serialization skipped for type {type(value)}: {e}")
            return False

        if self.cache_type == "redis":
            try:
                self.redis_client.setex(cache_key, ttl, serialized)
                return True
            except Exception as e:
                logger.error(f"Redis set error: {e}")
                return False
        else:
            # 인메모리 캐시 (LRU 제거)
            # 용량 초과시 가장 오래된 항목 제거
            while len(self.memory_cache) >= self.max_memory_items:
                oldest_key = next(iter(self.memory_cache))
                del self.memory_cache[oldest_key]
                if oldest_key in self.memory_expiry:
                    del self.memory_expiry[oldest_key]
                self.stats["evictions"] += 1

            self.memory_cache[cache_key] = value
            self.memory_expiry[cache_key] = datetime.now() + timedelta(seconds=ttl)
            return True

    def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        cache_key = self._make_key(key)

        if self.cache_type == "redis":
            try:
                self.redis_client.delete(cache_key)
                return True
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
                return False
        else:
            if cache_key in self.memory_cache:
                del self.memory_cache[cache_key]
                if cache_key in self.memory_expiry:
                    del self.memory_expiry[cache_key]
            return True

    def clear_pattern(self, pattern: str) -> int:
        """패턴 매칭으로 캐시 삭제"""
        count = 0
        full_pattern = self._make_key(pattern)

        if self.cache_type == "redis":
            try:
                keys = self.redis_client.keys(full_pattern)
                if keys:
                    count = self.redis_client.delete(*keys)
            except Exception as e:
                logger.error(f"Redis pattern delete error: {e}")
        else:
            # 인메모리 캐시
            keys_to_delete = [
                k
                for k in self.memory_cache.keys()
                if k.startswith(full_pattern.replace("*", ""))
            ]
            for key in keys_to_delete:
                del self.memory_cache[key]
                if key in self.memory_expiry:
                    del self.memory_expiry[key]
                count += 1

        return count

    def cleanup_expired(self) -> int:
        """만료된 인메모리 캐시 정리"""
        if self.cache_type != "memory":
            return 0

        count = 0
        now = datetime.now()
        expired_keys = []

        for key, expiry in self.memory_expiry.items():
            if now > expiry:
                expired_keys.append(key)

        for key in expired_keys:
            del self.memory_cache[key]
            del self.memory_expiry[key]
            count += 1

        return count

    def warm_cache(self, warm_functions: List[Callable] = None) -> Dict[str, Any]:
        """캐시 워밍 - 자주 사용되는 데이터 미리 로드"""
        if not warm_functions:
            return {"status": "no_functions_provided"}

        results = {"warmed_keys": 0, "failed_keys": 0, "duration": 0, "errors": []}

        import time

        start_time = time.time()

        for func in warm_functions:
            try:
                # 함수 실행 및 결과 캐싱
                if hasattr(func, "__call__"):
                    result = func()
                    # 함수명 기반 키 생성
                    key = f"warmed:{func.__name__}"
                    if self.set(key, result, ttl=self.default_ttl * 2):  # 2배 TTL
                        results["warmed_keys"] += 1
                    else:
                        results["failed_keys"] += 1
            except Exception as e:
                results["failed_keys"] += 1
                results["errors"].append(f"{func.__name__}: {str(e)}")
                logger.warning(f"Cache warming failed for {func.__name__}: {e}")

        results["duration"] = time.time() - start_time
        logger.info(
            f"Cache warming completed: {results['warmed_keys']} keys in {results['duration']:.2f}s"
        )

        return results

    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        hit_rate = self.stats["hits"] / max(self.stats["total_requests"], 1)

        # 메모리 캐시 크기 계산
        local_cache_size = len(self.memory_cache) if self.cache_type == "memory" else 0

        stats = {
            "cache_type": self.cache_type,
            "hit_rate": hit_rate * 100,  # CacheService 호환성을 위해 백분율로 반환
            "total_requests": self.stats["total_requests"],
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "sets": self.stats["sets"],
            "deletes": self.stats["deletes"],
            "evictions": self.stats["evictions"],
            "memory_usage": local_cache_size,
            "local_cache_size": local_cache_size,  # CacheService 호환성
            "max_memory_items": self.max_memory_items
            if self.cache_type == "memory"
            else "unlimited",
        }

        # Redis 전용 통계
        if self.cache_type == "redis":
            try:
                info = self.redis_client.info()
                stats["redis_memory"] = info.get("used_memory_human", "unknown")
                stats["redis_keys"] = info.get("db0", {}).get("keys", 0)
                stats["redis_connected_clients"] = info.get("connected_clients", 0)
            except Exception as e:
                logger.warning(f"Failed to get Redis stats: {e}")

        return stats

    def get_stats(self) -> Dict[str, Any]:
        """CacheService 호환성을 위한 별칭"""
        return self.get_cache_stats()

    def create_key(self, prefix: str, *args) -> str:
        """CacheService 호환성을 위한 키 생성 메서드"""
        key_parts = [str(prefix)]
        for arg in args:
            if isinstance(arg, (dict, list)):
                import json

                key_parts.append(
                    hashlib.md5(json.dumps(arg, sort_keys=True).encode()).hexdigest()[
                        :8
                    ]
                )
            else:
                key_parts.append(str(arg))

        return ":".join(key_parts)

    def clear(self) -> int:
        """CacheService 호환성을 위한 전체 캐시 클리어"""
        count = 0

        if self.cache_type == "redis":
            try:
                # Redis 전체 클리어
                count = self.redis_client.flushdb()
                logger.info("Redis cache cleared")
            except Exception as e:
                logger.error(f"Redis clear error: {e}")
        else:
            # 인메모리 캐시 클리어
            count = len(self.memory_cache)
            self.memory_cache.clear()
            self.memory_expiry.clear()
            logger.info(f"Memory cache cleared: {count} items")

        # 통계 초기화
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0,
            "total_requests": 0,
        }

        return count

    def optimize_cache(self) -> Dict[str, Any]:
        """캐시 최적화 실행"""
        optimization_results = {
            "cleaned_expired": 0,
            "memory_before": 0,
            "memory_after": 0,
            "recommendations": [],
        }

        if self.cache_type == "memory":
            optimization_results["memory_before"] = len(self.memory_cache)

            # 만료된 항목 정리
            expired_count = self.cleanup_expired()
            optimization_results["cleaned_expired"] = expired_count
            optimization_results["memory_after"] = len(self.memory_cache)

            # 권장사항 생성
            hit_rate = self.stats["hits"] / max(self.stats["total_requests"], 1)
            if hit_rate < 0.7:
                optimization_results["recommendations"].append(
                    "캐시 히트율이 낮음 - TTL 증가 또는 캐시 워밍 고려"
                )

            if self.stats["evictions"] > self.stats["sets"] * 0.1:
                optimization_results["recommendations"].append(
                    "캐시 제거 빈도가 높음 - max_memory_items 증가 고려"
                )

        elif self.cache_type == "redis":
            try:
                # Redis 메모리 최적화
                info = self.redis_client.info()
                memory_usage = info.get("used_memory", 0)
                max_memory = info.get("maxmemory", 0)

                if max_memory > 0 and memory_usage / max_memory > 0.8:
                    optimization_results["recommendations"].append(
                        "Redis 메모리 사용률이 높음 - 메모리 확장 고려"
                    )

                # 키 만료 정책 확인
                eviction_policy = info.get("maxmemory_policy", "noeviction")
                if eviction_policy == "noeviction":
                    optimization_results["recommendations"].append(
                        "Redis eviction 정책을 'allkeys-lru'로 변경 권장"
                    )

            except Exception as e:
                logger.warning(f"Redis optimization analysis failed: {e}")

        return optimization_results


def cached(cache_manager: CacheManager, ttl: int = 300, key_prefix: str = ""):
    """캐싱 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key = f"{key_prefix}:{func.__name__}"
            if args:
                args_str = ":".join(str(arg) for arg in args)
                cache_key += f":{hashlib.md5(args_str.encode()).hexdigest()[:8]}"
            if kwargs:
                kwargs_str = ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key += f":{hashlib.md5(kwargs_str.encode()).hexdigest()[:8]}"

            # 캐시 조회
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            # 함수 실행
            result = func(*args, **kwargs)

            # 캐시 저장 - Response 객체는 캐시하지 않음
            if cache_manager and hasattr(cache_manager, "set"):
                try:
                    # Flask Response 객체는 캐시하지 않음
                    from flask import Response as FlaskResponse
                    from werkzeug.wrappers import Response as WerkzeugResponse

                    if not isinstance(result, (FlaskResponse, WerkzeugResponse)):
                        cache_manager.set(cache_key, result, ttl)
                        logger.debug(f"Cache set: {cache_key}")
                except Exception as e:
                    logger.warning(f"Failed to cache result: {e}")

            return result

        wrapper.cache_clear = lambda: cache_manager.delete(
            f"{key_prefix}:{func.__name__}:*"
        )
        return wrapper

    return decorator


# SimpleCache alias for backward compatibility
SimpleCache = CacheManager

# 글로벌 캐시 인스턴스
_cache_instance = None


def get_cache() -> CacheManager:
    """글로벌 캐시 인스턴스 반환"""
    global _cache_instance
    if _cache_instance is None:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        try:
            _cache_instance = CacheManager(redis_url)
        except Exception as e:
            logger.warning(
                f"Failed to create cache with Redis, using in-memory cache: {e}"
            )
            _cache_instance = CacheManager(redis_url=None)  # Fallback to in-memory
    return _cache_instance
