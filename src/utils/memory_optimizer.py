"""
메모리 사용량 최적화 모듈

이 모듈은 Blacklist 시스템의 메모리 효율성을 향상시키기 위한
대량 데이터 처리, 메모리 풀링, 가비지 컬렉션 최적화 기능을 제공합니다.
"""

import gc
import sqlite3
import sys
import threading
import time
import weakref
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, Union

import psutil

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

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


class MemoryOptimizer:
    """메모리 사용량 최적화 관리자"""

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
            f"MemoryOptimizer initialized: max_memory={max_memory_percent}%, "
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

    def optimize_database_operations(
        self, db_path: str, operations: List[str]
    ) -> List[Any]:
        """데이터베이스 연산 메모리 최적화"""
        results = []

        # 단일 연결로 모든 작업 수행
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA cache_size = -64000")  # 64MB 캐시
            conn.execute("PRAGMA temp_store = MEMORY")

            cursor = conn.cursor()

            try:
                for i, operation in enumerate(operations):
                    cursor.execute(operation)

                    # 결과가 있는 경우에만 fetchall
                    if operation.strip().upper().startswith("SELECT"):
                        result = cursor.fetchall()
                        results.append(result)
                    else:
                        results.append(cursor.rowcount)

                    # 주기적 커밋 (메모리 효율성)
                    if i % 100 == 0:
                        conn.commit()

                conn.commit()

            except Exception as e:
                conn.rollback()
                logger.error(f"Database operation failed: {e}")
                raise

        return results

    def efficient_ip_processing(self, ip_list: List[str]) -> List[str]:
        """대량 IP 처리 메모리 최적화"""
        if not ip_list:
            return []

        # numpy 사용 가능하면 벡터화 처리
        if HAS_NUMPY and len(ip_list) > 10000:
            logger.info(f"Using numpy for efficient processing of {len(ip_list)} IPs")

            # numpy 배열로 변환 (메모리 효율적)
            ip_array = np.array(ip_list, dtype="U15")  # 최대 15자 IP 주소

            # 중복 제거 (numpy는 메모리 효율적)
            unique_ips = np.unique(ip_array)

            return unique_ips.tolist()

        else:
            # 표준 Python 최적화
            logger.info(f"Using standard Python for processing {len(ip_list)} IPs")

            # 집합을 사용한 중복 제거 (메모리 효율적)
            unique_ips = set()

            # 청크 단위로 처리
            with self.chunked_processing(ip_list, chunk_size=5000) as chunks:
                for chunk_num, chunk, total_chunks in chunks:
                    unique_ips.update(chunk)

                    if chunk_num % 5 == 0:
                        logger.debug(f"Processed chunk {chunk_num}/{total_chunks}")

            return list(unique_ips)

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

    def get_optimization_report(self) -> Dict[str, Any]:
        """메모리 최적화 보고서"""
        current_stats = self.get_memory_stats()

        # 풀 효율성 계산
        total_pool_requests = (
            self.optimization_stats["pool_hits"]
            + self.optimization_stats["pool_misses"]
        )
        pool_hit_rate = (
            self.optimization_stats["pool_hits"] / total_pool_requests * 100
            if total_pool_requests > 0
            else 0
        )

        # 메모리 히스토리 분석
        if len(self.memory_history) > 1:
            memory_trend = (
                self.memory_history[-1].memory_percent
                - self.memory_history[0].memory_percent
            )
        else:
            memory_trend = 0

        return {
            "current_memory": {
                "total_mb": current_stats.total_memory_mb,
                "used_mb": current_stats.used_memory_mb,
                "available_mb": current_stats.available_memory_mb,
                "usage_percent": current_stats.memory_percent,
                "process_mb": current_stats.process_memory_mb,
            },
            "optimization_stats": {
                **self.optimization_stats,
                "pool_hit_rate_percent": round(pool_hit_rate, 2),
                "memory_trend_percent": round(memory_trend, 2),
            },
            "pool_status": {
                pool_type: len(objects)
                for pool_type, objects in self.object_pools.items()
            },
            "recommendations": self._generate_recommendations(current_stats),
            "timestamp": current_stats.timestamp.isoformat(),
        }

    def _generate_recommendations(self, stats: MemoryStats) -> List[str]:
        """메모리 최적화 권장사항 생성"""
        recommendations = []

        if stats.memory_percent > 90:
            recommendations.append(
                "🚨 Critical: System memory usage > 90%. Immediate optimization needed."
            )
        elif stats.memory_percent > 80:
            recommendations.append(
                "⚠️ Warning: High memory usage. Consider enabling chunked processing."
            )

        if stats.process_memory_mb > 500:
            recommendations.append(
                "💡 Process memory > 500MB. Consider using object pools."
            )

        if self.optimization_stats["gc_forced"] > 10:
            recommendations.append(
                "🔄 Frequent GC detected. Review data processing patterns."
            )

        pool_efficiency = (
            self.optimization_stats["pool_hits"]
            / (
                self.optimization_stats["pool_hits"]
                + self.optimization_stats["pool_misses"]
            )
            if self.optimization_stats["pool_hits"]
            + self.optimization_stats["pool_misses"]
            > 0
            else 0
        )

        if pool_efficiency < 0.5:
            recommendations.append(
                "📊 Low object pool efficiency. Review pool usage patterns."
            )

        if not recommendations:
            recommendations.append("✅ Memory usage is optimal.")

        return recommendations


# 글로벌 메모리 최적화기
_global_memory_optimizer = None


def get_global_memory_optimizer() -> MemoryOptimizer:
    """글로벌 메모리 최적화기 반환"""
    global _global_memory_optimizer

    if _global_memory_optimizer is None:
        _global_memory_optimizer = MemoryOptimizer()

    return _global_memory_optimizer


def memory_efficient(chunk_size: int = 1000):
    """메모리 효율적 처리 데코레이터"""

    def decorator(func):
        def wrapper(data, *args, **kwargs):
            optimizer = get_global_memory_optimizer()

            if isinstance(data, list) and len(data) > chunk_size:
                results = []
                with optimizer.chunked_processing(data, chunk_size) as chunks:
                    for chunk_num, chunk, total_chunks in chunks:
                        chunk_result = func(chunk, *args, **kwargs)
                        results.extend(
                            chunk_result
                            if isinstance(chunk_result, list)
                            else [chunk_result]
                        )
                return results
            else:
                return func(data, *args, **kwargs)

        return wrapper

    return decorator


if __name__ == "__main__":
    """메모리 최적화 시스템 검증"""
    import sys

    optimizer = MemoryOptimizer()
    all_tests_passed = True

    try:
        # 테스트 1: 메모리 통계
        stats = optimizer.get_memory_stats()
        if stats.total_memory_mb <= 0:
            print("❌ 메모리 통계 테스트 실패")
            all_tests_passed = False

        # 테스트 2: 청크 처리
        test_data = list(range(10000))
        processed_chunks = 0

        with optimizer.chunked_processing(test_data, chunk_size=1000) as chunks:
            for chunk_num, chunk, total_chunks in chunks:
                processed_chunks += 1
                if len(chunk) > 1000:
                    print("❌ 청크 크기 테스트 실패")
                    all_tests_passed = False

        if processed_chunks != 10:
            print(f"❌ 청크 수 테스트 실패: expected 10, got {processed_chunks}")
            all_tests_passed = False

        # 테스트 3: IP 처리 최적화
        test_ips = [f"192.168.1.{i}" for i in range(1000)] * 2  # 중복 포함
        unique_ips = optimizer.efficient_ip_processing(test_ips)

        if len(unique_ips) != 1000:
            print(f"❌ IP 처리 테스트 실패: expected 1000 unique IPs, got {len(unique_ips)}")
            all_tests_passed = False

        # 테스트 4: 객체 풀
        def list_factory():
            return []

        obj1 = optimizer.get_object_from_pool("test_list", list_factory)
        optimizer.return_object_to_pool("test_list", obj1, lambda x: x.clear())
        obj2 = optimizer.get_object_from_pool("test_list")

        if obj1 is not obj2:
            print("❌ 객체 풀 테스트 실패")
            all_tests_passed = False

        # 최종 보고서
        report = optimizer.get_optimization_report()

        if all_tests_passed:
            print("✅ 메모리 최적화 시스템 검증 완료 - 모든 테스트 통과")
            print(f"📊 메모리 사용량: {report['current_memory']['usage_percent']:.1f}%")
            print(f"🎯 최적화 통계: {report['optimization_stats']}")
            sys.exit(0)
        else:
            print("❌ 일부 테스트 실패")
            sys.exit(1)

    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
