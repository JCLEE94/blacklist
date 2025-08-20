"""
통합 캐시 헬퍼 유틸리티
캐시 키 생성 및 관리 표준화
"""

import hashlib
import json
import logging
from functools import wraps
from typing import Any
from typing import Optional
from typing import Union

logger = logging.getLogger(__name__)


class CacheKeyBuilder:
    """표준화된 캐시 키 생성기"""

    SEPARATORS = {"default": ":", "path": "/", "underscore": "_"}

    @staticmethod
    def build(prefix: str, *parts: Any, separator: str = "default") -> str:
        """
        캐시 키 생성

        Args:
            prefix: 키 프리픽스
            *parts: 키 구성 요소들
            separator: 구분자 타입

        Returns:
            생성된 캐시 키
        """
        sep = CacheKeyBuilder.SEPARATORS.get(separator, ":")

        key_parts = [str(prefix)]

        for part in parts:
            if isinstance(part, (dict, list)):
                # 복잡한 객체는 해시로 변환
                part_str = CacheKeyBuilder._hash_object(part)
            else:
                part_str = str(part)

            key_parts.append(part_str)

        return sep.join(key_parts)

    @staticmethod
    def _hash_object(obj: Union[dict, list]) -> str:
        """객체를 해시 문자열로 변환"""
        json_str = json.dumps(obj, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode()).hexdigest()[:8]

    @staticmethod
    def build_pattern(prefix: str, pattern: str = "*") -> str:
        """캐시 키 패턴 생성 (삭제용)"""
        return "{prefix}:{pattern}"


class CacheHelper:
    """캐시 관련 헬퍼 함수들"""

    @staticmethod
    def cached_result(
        cache_manager,
        key_prefix: str,
        ttl: int = 300,
        key_builder: Optional[callable] = None,
    ):
        """
        결과 캐싱 데코레이터 (표준화된 버전)

        Args:
            cache_manager: 캐시 매니저 인스턴스
            key_prefix: 캐시 키 프리픽스
            ttl: Time To Live (초)
            key_builder: 커스텀 키 생성 함수
        """

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 캐시 키 생성
                if key_builder:
                    cache_key = key_builder(func.__name__, *args, **kwargs)
                else:
                    # 기본 키 생성
                    cache_key = CacheKeyBuilder.build(
                        key_prefix,
                        func.__name__,
                        *args,
                        **{k: v for k, v in kwargs.items() if k != "sel"},
                    )

                # 캐시 조회
                cached_value = cache_manager.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_value

                # 함수 실행
                result = func(*args, **kwargs)

                # 캐시 저장
                if result is not None:  # None이 아닌 경우만 캐싱
                    cache_manager.set(cache_key, result, ttl=ttl)
                    logger.debug(f"Cache set: {cache_key}")

                return result

            # 캐시 클리어 메서드 추가
            wrapper.cache_clear = lambda: cache_manager.clear_pattern(
                CacheKeyBuilder.build_pattern(key_prefix, "*")
            )

            return wrapper

        return decorator

    @staticmethod
    def invalidate_cache_group(cache_manager, prefix: str, *identifiers):
        """
        캐시 그룹 무효화

        Args:
            cache_manager: 캐시 매니저
            prefix: 캐시 키 프리픽스
            *identifiers: 추가 식별자들
        """
        pattern = CacheKeyBuilder.build(prefix, *identifiers, "*")
        count = cache_manager.clear_pattern(pattern)
        logger.info(f"Invalidated {count} cache entries matching {pattern}")
        return count

    @staticmethod
    def get_or_compute(
        cache_manager, cache_key: str, compute_func: callable, ttl: int = 300
    ) -> Any:
        """
        캐시에서 가져오거나 계산 후 저장

        Args:
            cache_manager: 캐시 매니저
            cache_key: 캐시 키
            compute_func: 값을 계산할 함수
            ttl: Time To Live

        Returns:
            캐시된 값 또는 계산된 값
        """
        # 캐시 확인
        cached_value = cache_manager.get(cache_key)
        if cached_value is not None:
            return cached_value

        # 계산 및 캐싱
        value = compute_func()
        if value is not None:
            cache_manager.set(cache_key, value, ttl=ttl)

        return value


class CacheWarmer:
    """캐시 워밍 유틸리티"""

    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.warming_tasks = []

    def register_task(self, name: str, func: callable, cache_key: str, ttl: int = 600):
        """
        캐시 워밍 작업 등록

        Args:
            name: 작업 이름
            func: 실행할 함수
            cache_key: 저장할 캐시 키
            ttl: TTL
        """
        self.warming_tasks.append(
            {"name": name, "func": func, "cache_key": cache_key, "ttl": ttl}
        )

    def warm_all(self) -> dict:
        """모든 등록된 캐시 워밍 실행"""
        results = {"success": 0, "failed": 0, "tasks": []}

        for task in self.warming_tasks:
            try:
                logger.info(f"Warming cache for {task['name']}")
                value = task["func"]()

                if value is not None:
                    self.cache_manager.set(task["cache_key"], value, ttl=task["ttl"])
                    results["success"] += 1
                    results["tasks"].append({"name": task["name"], "status": "success"})
                else:
                    results["failed"] += 1
                    results["tasks"].append({"name": task["name"], "status": "no_data"})

            except Exception as e:
                logger.error(f"Cache warming failed for {task['name']}: {e}")
                results["failed"] += 1
                results["tasks"].append(
                    {"name": task["name"], "status": "error", "error": str(e)}
                )

        return results
