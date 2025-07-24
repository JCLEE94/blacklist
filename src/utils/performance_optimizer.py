#!/usr/bin/env python3
"""
Performance Optimizer for Blacklist System
고도화된 성능 최적화 모듈
"""

import asyncio
import functools
import gc
import logging
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union

import psutil

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """성능 메트릭 데이터 클래스"""

    operation: str
    duration: float
    memory_before: float
    memory_after: float
    cpu_percent: float
    timestamp: float

    @property
    def memory_delta(self) -> float:
        """메모리 사용량 변화"""
        return self.memory_after - self.memory_before


class PerformanceOptimizer:
    """고도화된 성능 최적화 클래스"""

    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or min(32, (psutil.cpu_count() or 1) + 4)
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        self.process_pool = ProcessPoolExecutor(max_workers=self.max_workers // 2)
        self.metrics: Dict[str, List[PerformanceMetrics]] = defaultdict(list)
        self._cache = {}

    def measure_performance(self, operation_name: str = None):
        """성능 측정 데코레이터"""

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                op_name = operation_name or func.__name__

                # 시작 메트릭
                gc.collect()
                process = psutil.Process()
                memory_before = process.memory_info().rss / 1024 / 1024  # MB
                cpu_before = process.cpu_percent()
                start_time = time.time()

                try:
                    # 함수 실행
                    result = func(*args, **kwargs)

                    # 종료 메트릭
                    end_time = time.time()
                    memory_after = process.memory_info().rss / 1024 / 1024  # MB
                    cpu_after = process.cpu_percent()

                    # 메트릭 저장
                    metric = PerformanceMetrics(
                        operation=op_name,
                        duration=end_time - start_time,
                        memory_before=memory_before,
                        memory_after=memory_after,
                        cpu_percent=(cpu_before + cpu_after) / 2,
                        timestamp=end_time,
                    )
                    self.metrics[op_name].append(metric)

                    # 로깅
                    if metric.duration > 1.0:  # 1초 이상 걸린 작업
                        logger.warning(
                            f"Slow operation detected: {op_name} took {metric.duration:.2f}s, "
                            f"memory delta: {metric.memory_delta:.2f}MB"
                        )

                    return result

                except Exception as e:
                    logger.error(f"Error in {op_name}: {str(e)}")
                    raise

            return wrapper

        return decorator

    def batch_process(
        self,
        items: List[Any],
        processor: Callable,
        batch_size: int = 100,
        use_process_pool: bool = False,
    ) -> List[Any]:
        """배치 처리 최적화"""
        results = []
        pool = self.process_pool if use_process_pool else self.thread_pool

        # 배치로 나누기
        batches = [items[i : i + batch_size] for i in range(0, len(items), batch_size)]

        # 병렬 처리
        with self.measure_performance(f"batch_process_{processor.__name__}")():
            futures = [
                pool.submit(self._process_batch, batch, processor) for batch in batches
            ]
            for future in futures:
                results.extend(future.result())

        return results

    def _process_batch(self, batch: List[Any], processor: Callable) -> List[Any]:
        """배치 처리 헬퍼"""
        return [processor(item) for item in batch]

    def cache_result(self, ttl: int = 300):
        """결과 캐싱 데코레이터"""

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # 캐시 키 생성
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

                # 캐시 확인
                if cache_key in self._cache:
                    cached_time, cached_result = self._cache[cache_key]
                    if time.time() - cached_time < ttl:
                        return cached_result

                # 함수 실행 및 캐싱
                result = func(*args, **kwargs)
                self._cache[cache_key] = (time.time(), result)

                # 오래된 캐시 정리
                self._cleanup_cache(ttl)

                return result

            return wrapper

        return decorator

    def _cleanup_cache(self, ttl: int):
        """오래된 캐시 항목 정리"""
        current_time = time.time()
        expired_keys = [
            key
            for key, (cached_time, _) in self._cache.items()
            if current_time - cached_time > ttl
        ]
        for key in expired_keys:
            del self._cache[key]

    async def async_batch_process(
        self, items: List[Any], processor: Callable, max_concurrent: int = 10
    ) -> List[Any]:
        """비동기 배치 처리"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(item):
            async with semaphore:
                return await asyncio.get_event_loop().run_in_executor(
                    self.thread_pool, processor, item
                )

        tasks = [process_with_semaphore(item) for item in items]
        return await asyncio.gather(*tasks)

    def optimize_memory(self):
        """메모리 최적화"""
        # 가비지 컬렉션 강제 실행
        gc.collect()

        # 캐시 정리
        self._cache.clear()

        # 메모리 사용량 로깅
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        logger.info(f"Memory optimized. Current usage: {memory_mb:.2f}MB")

    def get_performance_report(self) -> Dict[str, Dict[str, float]]:
        """성능 리포트 생성"""
        report = {}

        for operation, metrics in self.metrics.items():
            if not metrics:
                continue

            durations = [m.duration for m in metrics]
            memory_deltas = [m.memory_delta for m in metrics]
            cpu_percents = [m.cpu_percent for m in metrics]

            report[operation] = {
                "count": len(metrics),
                "avg_duration": sum(durations) / len(durations),
                "max_duration": max(durations),
                "min_duration": min(durations),
                "avg_memory_delta": sum(memory_deltas) / len(memory_deltas),
                "avg_cpu_percent": sum(cpu_percents) / len(cpu_percents),
            }

        return report

    def __del__(self):
        """리소스 정리"""
        self.thread_pool.shutdown(wait=False)
        self.process_pool.shutdown(wait=False)


# 전역 인스턴스
optimizer = PerformanceOptimizer()


# 유틸리티 함수들
def optimize_database_query(query: str) -> str:
    """데이터베이스 쿼리 최적화"""
    # 인덱스 힌트 추가
    if "SELECT" in query.upper() and "WHERE" in query.upper():
        if "ip" in query.lower():
            query = query.replace("WHERE", "WHERE /*+ INDEX(blacklist_ip idx_ip) */")

    # LIMIT 추가 (대량 결과 방지)
    if "SELECT" in query.upper() and "LIMIT" not in query.upper():
        query += " LIMIT 10000"

    return query


def chunked_insert(data: List[Dict], table_name: str, chunk_size: int = 1000):
    """대량 INSERT 최적화"""
    for i in range(0, len(data), chunk_size):
        chunk = data[i : i + chunk_size]
        yield chunk


@optimizer.measure_performance("batch_ip_validation")
def validate_ips_batch(ips: List[str]) -> List[bool]:
    """IP 주소 배치 검증 최적화"""
    import ipaddress

    def validate_single(ip: str) -> bool:
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    return optimizer.batch_process(ips, validate_single, batch_size=500)


def optimize_api_response(data: Any) -> Any:
    """API 응답 최적화"""
    if isinstance(data, dict):
        # 불필요한 필드 제거
        optimized = {k: v for k, v in data.items() if v is not None}
        return optimized
    elif isinstance(data, list):
        # 대량 데이터 청킹
        if len(data) > 1000:
            return data[:1000] + [
                {"truncated": f"... and {len(data) - 1000} more items"}
            ]
        return data
    return data


def monitor_performance(func: Callable) -> Callable:
    """성능 모니터링 데코레이터"""
    if callable(func) and hasattr(func, "__name__"):
        return optimizer.measure_performance(func.__name__)(func)
    else:
        # func가 callable이 아닌 경우 원본 반환
        logger.warning(
            f"monitor_performance called on non-callable object: {type(func)}"
        )
        return func


def performance_headers(response_data: Any) -> Dict[str, str]:
    """성능 관련 헤더 생성"""
    return {
        "X-Response-Time": f"{time.time():.3f}",
        "X-Cache-Status": "optimized",
        "X-Performance-Level": "enhanced",
    }
