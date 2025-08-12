"""
메모리 최적화 핵심 기능

메모리 모니터링, 가비지 컬렉션, 시스템 리소스 관리 등의 핵심 기능을 제공합니다.
"""

import gc
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

import psutil
from loguru import logger


@dataclass
class MemoryStats:
    """메모리 사용량 통계"""

    total_memory_mb: float
    available_memory_mb: float
    used_memory_mb: float
    memory_percent: float
    process_memory_mb: float
    gc_collections: Dict[int, int]
    timestamp: datetime


class CoreMemoryOptimizer:
    """메모리 최적화 핵심 클래스"""

    def __init__(
        self,
        max_memory_percent: float = 80.0,
        gc_threshold_mb: float = 100.0,
        monitoring_interval: float = 30.0,
    ):
        self.max_memory_percent = max_memory_percent
        self.gc_threshold_mb = gc_threshold_mb
        self.monitoring_interval = monitoring_interval

        # 메모리 풀
        self.object_pools = defaultdict(list)
        self.pool_locks = defaultdict(threading.Lock)

        # 모니터링
        self.memory_history = []
        self.max_history_size = 100
        self.monitoring_active = False
        self.monitoring_thread = None

        # 통계
        self.optimization_stats = {
            "pool_hits": 0,
            "pool_misses": 0,
            "gc_forced": 0,
            "memory_warnings": 0,
            "chunked_operations": 0,
        }

        logger.info(
            f"CoreMemoryOptimizer initialized: max_memory={max_memory_percent}%, "
            f"gc_threshold={gc_threshold_mb}MB"
        )

    def get_memory_stats(self) -> MemoryStats:
        """현재 메모리 사용량 통계"""
        # 시스템 메모리
        memory = psutil.virtual_memory()

        # 프로세스 메모리
        process = psutil.Process()
        process_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 가비지 컬렉션 통계
        gc_stats = {}
        for i in range(3):
            gc_stats[i] = gc.get_count()[i]

        return MemoryStats(
            total_memory_mb=memory.total / 1024 / 1024,
            available_memory_mb=memory.available / 1024 / 1024,
            used_memory_mb=memory.used / 1024 / 1024,
            memory_percent=memory.percent,
            process_memory_mb=process_memory,
            gc_collections=gc_stats,
            timestamp=datetime.now(),
        )

    def check_memory_pressure(self) -> bool:
        """메모리 압박 상황 확인"""
        stats = self.get_memory_stats()

        if stats.memory_percent > self.max_memory_percent:
            self.optimization_stats["memory_warnings"] += 1
            logger.warning(
                f"High memory usage: {stats.memory_percent:.1f}% "
                f"(process: {stats.process_memory_mb:.1f}MB)"
            )
            return True

        return False

    def force_gc_if_needed(self) -> bool:
        """필요시 강제 가비지 컬렉션"""
        stats = self.get_memory_stats()

        if (
            stats.memory_percent > self.max_memory_percent * 0.8
            or stats.process_memory_mb > self.gc_threshold_mb
        ):
            logger.info("Forcing garbage collection...")
            gc.collect()
            self.optimization_stats["gc_forced"] += 1

            # 후 통계
            new_stats = self.get_memory_stats()
            freed_mb = stats.process_memory_mb - new_stats.process_memory_mb
            logger.info(f"GC completed, freed {freed_mb:.1f}MB memory")

            return True

        return False

    @contextmanager
    def chunked_processing(self, data: List[Any], chunk_size: int = 1000):
        """대량 데이터의 청크 단위 처리"""
        self.optimization_stats["chunked_operations"] += 1

        try:
            total_chunks = (len(data) + chunk_size - 1) // chunk_size
            logger.info(
                f"Processing {len(data)} items in {total_chunks} chunks of {chunk_size}"
            )

            for i in range(0, len(data), chunk_size):
                chunk = data[i : i + chunk_size]
                chunk_num = i // chunk_size + 1

                # 메모리 압박 확인
                if chunk_num % 10 == 0:  # 10청크마다 확인
                    if self.check_memory_pressure():
                        self.force_gc_if_needed()

                yield chunk_num, chunk, total_chunks

                # 청크 처리 후 명시적으로 참조 해제
                del chunk

        except Exception as e:
            logger.error(f"Chunked processing error: {e}")
            raise

    def start_memory_monitoring(self):
        """메모리 모니터링 시작"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True, name="memory_monitor"
        )
        self.monitoring_thread.start()
        logger.info("Memory monitoring started")

    def stop_memory_monitoring(self):
        """메모리 모니터링 중지"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Memory monitoring stopped")

    def _monitoring_loop(self):
        """메모리 모니터링 루프"""
        while self.monitoring_active:
            try:
                stats = self.get_memory_stats()

                # 히스토리 저장
                self.memory_history.append(stats)
                if len(self.memory_history) > self.max_history_size:
                    self.memory_history.pop(0)

                # 메모리 압박 확인 및 대응
                if self.check_memory_pressure():
                    self.force_gc_if_needed()

                time.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                time.sleep(self.monitoring_interval)

    def get_object_from_pool(self, object_type: str, factory: callable = None) -> Any:
        """객체 풀에서 객체 획득"""
        with self.pool_locks[object_type]:
            if self.object_pools[object_type]:
                obj = self.object_pools[object_type].pop()
                self.optimization_stats["pool_hits"] += 1
                return obj
            elif factory:
                self.optimization_stats["pool_misses"] += 1
                return factory()
            else:
                self.optimization_stats["pool_misses"] += 1
                return None

    def return_object_to_pool(
        self, object_type: str, obj: Any, reset_func: callable = None
    ):
        """객체를 풀에 반환"""
        if reset_func:
            reset_func(obj)

        with self.pool_locks[object_type]:
            # 풀 크기 제한 (메모리 누수 방지)
            if len(self.object_pools[object_type]) < 50:
                self.object_pools[object_type].append(obj)
