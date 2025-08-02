"""
비동기 처리 최적화 모듈

이 모듈은 Blacklist 시스템의 성능 향상을 위한
비동기 처리, 병렬 실행, 백그라운드 작업 관리 기능을 제공합니다.
"""

import asyncio
import multiprocessing as mp
import queue
import threading
import time
import weakref
from concurrent.futures import (ProcessPoolExecutor, ThreadPoolExecutor,
                                as_completed)
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union

from loguru import logger


@dataclass
class TaskResult:
    """비동기 작업 결과"""

    task_id: str
    success: bool
    result: Any = None
    error: str = None
    execution_time: float = 0.0
    started_at: datetime = None
    completed_at: datetime = None


@dataclass
class ProcessingConfig:
    """비동기 처리 설정"""

    max_workers: int = min(32, (mp.cpu_count() or 1) + 4)
    max_process_workers: int = mp.cpu_count() or 1
    task_timeout: float = 30.0
    enable_process_pool: bool = True
    enable_thread_pool: bool = True
    queue_size: int = 1000


class AsyncProcessor:
    """고성능 비동기 처리 관리자"""

    def __init__(self, config: ProcessingConfig = None):
        self.config = config or ProcessingConfig()

        # 스레드 풀 (I/O 집약적 작업용)
        self.thread_pool = (
            ThreadPoolExecutor(
                max_workers=self.config.max_workers,
                thread_name_prefix="blacklist_thread",
            )
            if self.config.enable_thread_pool
            else None
        )

        # 프로세스 풀 (CPU 집약적 작업용)
        self.process_pool = (
            ProcessPoolExecutor(max_workers=self.config.max_process_workers)
            if self.config.enable_process_pool
            else None
        )

        # 작업 큐
        self.task_queue = asyncio.Queue(maxsize=self.config.queue_size)
        self.background_tasks = set()

        # 작업 추적
        self.active_tasks = {}
        self.completed_tasks = {}
        self.task_stats = {
            "total_submitted": 0,
            "total_completed": 0,
            "total_failed": 0,
            "average_execution_time": 0.0,
        }

        self._shutdown = False
        logger.info(
            f"AsyncProcessor initialized with {self.config.max_workers} thread workers, "
            f"{self.config.max_process_workers} process workers"
        )

    async def submit_async_task(
        self,
        func: Callable,
        *args,
        task_id: str = None,
        use_process_pool: bool = False,
        **kwargs,
    ) -> str:
        """비동기 작업 제출"""
        if task_id is None:
            task_id = f"task_{int(time.time() * 1000000)}"

        if self._shutdown:
            raise RuntimeError("AsyncProcessor is shutting down")

        started_at = datetime.now()

        try:
            if use_process_pool and self.process_pool:
                # CPU 집약적 작업을 프로세스 풀에서 실행
                future = self.process_pool.submit(func, *args, **kwargs)
            elif self.thread_pool:
                # I/O 집약적 작업을 스레드 풀에서 실행
                future = self.thread_pool.submit(func, *args, **kwargs)
            else:
                # 풀이 없으면 동기 실행
                result = func(*args, **kwargs)
                return self._create_task_result(
                    task_id, True, result, started_at=started_at
                )

            # 작업 추적 등록
            self.active_tasks[task_id] = {
                "future": future,
                "started_at": started_at,
                "function": func.__name__ if hasattr(func, "__name__") else str(func),
            }

            self.task_stats["total_submitted"] += 1

            # 백그라운드에서 완료 대기
            background_task = asyncio.create_task(
                self._wait_for_completion(task_id, future, started_at)
            )
            self.background_tasks.add(background_task)
            background_task.add_done_callback(self.background_tasks.discard)

            return task_id

        except Exception as e:
            logger.error(f"Failed to submit task {task_id}: {e}")
            return self._create_task_result(
                task_id, False, error=str(e), started_at=started_at
            )

    async def _wait_for_completion(self, task_id: str, future, started_at: datetime):
        """작업 완료 대기 및 결과 처리"""
        try:
            # 타임아웃 설정
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._get_future_result, future)

            execution_time = (datetime.now() - started_at).total_seconds()

            # 성공 결과 저장
            task_result = TaskResult(
                task_id=task_id,
                success=True,
                result=result,
                execution_time=execution_time,
                started_at=started_at,
                completed_at=datetime.now(),
            )

            self.completed_tasks[task_id] = task_result
            self.task_stats["total_completed"] += 1
            self._update_average_execution_time(execution_time)

        except Exception as e:
            # 실패 결과 저장
            execution_time = (datetime.now() - started_at).total_seconds()
            task_result = TaskResult(
                task_id=task_id,
                success=False,
                error=str(e),
                execution_time=execution_time,
                started_at=started_at,
                completed_at=datetime.now(),
            )

            self.completed_tasks[task_id] = task_result
            self.task_stats["total_failed"] += 1
            logger.error(f"Task {task_id} failed: {e}")

        finally:
            # 활성 작업에서 제거
            self.active_tasks.pop(task_id, None)

    def _get_future_result(self, future):
        """Future 결과 획득 (타임아웃 적용)"""
        try:
            return future.result(timeout=self.config.task_timeout)
        except Exception as e:
            raise e

    def _create_task_result(
        self, task_id: str, success: bool, result=None, error=None, started_at=None
    ):
        """작업 결과 객체 생성"""
        now = datetime.now()
        return TaskResult(
            task_id=task_id,
            success=success,
            result=result,
            error=error,
            execution_time=(now - started_at).total_seconds() if started_at else 0.0,
            started_at=started_at or now,
            completed_at=now,
        )

    def _update_average_execution_time(self, execution_time: float):
        """평균 실행 시간 업데이트"""
        total_completed = self.task_stats["total_completed"]
        current_avg = self.task_stats["average_execution_time"]

        if total_completed == 1:
            self.task_stats["average_execution_time"] = execution_time
        else:
            # 이동 평균 계산
            self.task_stats["average_execution_time"] = (
                current_avg * (total_completed - 1) + execution_time
            ) / total_completed

    async def batch_process(
        self,
        func: Callable,
        items: List[Any],
        batch_size: int = None,
        use_process_pool: bool = False,
    ) -> List[TaskResult]:
        """배치 처리 (병렬 실행)"""
        if batch_size is None:
            batch_size = min(len(items), self.config.max_workers)

        # 아이템들을 배치로 분할
        batches = [items[i : i + batch_size] for i in range(0, len(items), batch_size)]

        # 모든 배치를 병렬 실행
        task_ids = []
        for i, batch in enumerate(batches):
            task_id = await self.submit_async_task(
                func,
                batch,
                task_id=f"batch_{i}_{int(time.time() * 1000)}",
                use_process_pool=use_process_pool,
            )
            task_ids.append(task_id)

        # 모든 작업 완료 대기
        results = []
        while task_ids:
            await asyncio.sleep(0.1)  # CPU 과부하 방지
            completed_ids = []

            for task_id in task_ids:
                if task_id in self.completed_tasks:
                    results.append(self.completed_tasks[task_id])
                    completed_ids.append(task_id)

            for completed_id in completed_ids:
                task_ids.remove(completed_id)

        logger.info(f"Batch processing completed: {len(results)} batches processed")
        return results

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """작업 상태 조회"""
        if task_id in self.completed_tasks:
            task_result = self.completed_tasks[task_id]
            return {
                "status": "completed",
                "success": task_result.success,
                "execution_time": task_result.execution_time,
                "started_at": task_result.started_at.isoformat(),
                "completed_at": task_result.completed_at.isoformat(),
                "error": task_result.error,
            }
        elif task_id in self.active_tasks:
            active_task = self.active_tasks[task_id]
            return {
                "status": "running",
                "started_at": active_task["started_at"].isoformat(),
                "function": active_task["function"],
            }
        else:
            return {"status": "not_found"}

    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        active_count = len(self.active_tasks)
        completed_count = len(self.completed_tasks)

        # 성공률 계산
        success_rate = 0.0
        if self.task_stats["total_completed"] > 0:
            successful_tasks = (
                self.task_stats["total_completed"] - self.task_stats["total_failed"]
            )
            success_rate = (successful_tasks / self.task_stats["total_completed"]) * 100

        return {
            **self.task_stats,
            "active_tasks": active_count,
            "completed_tasks": completed_count,
            "success_rate_percent": round(success_rate, 2),
            "thread_pool_workers": self.config.max_workers if self.thread_pool else 0,
            "process_pool_workers": self.config.max_process_workers
            if self.process_pool
            else 0,
            "queue_size": self.task_queue.qsize()
            if hasattr(self.task_queue, "qsize")
            else 0,
        }

    def cleanup_completed_tasks(self, keep_recent: int = 100):
        """완료된 작업 정리 (메모리 관리)"""
        if len(self.completed_tasks) <= keep_recent:
            return

        # 완료 시간 기준으로 정렬
        sorted_tasks = sorted(
            self.completed_tasks.items(), key=lambda x: x[1].completed_at, reverse=True
        )

        # 최근 작업만 유지
        self.completed_tasks = dict(sorted_tasks[:keep_recent])
        logger.info(
            f"Cleaned up old completed tasks, keeping {len(self.completed_tasks)} recent tasks"
        )

    async def shutdown(self, wait_for_completion: bool = True):
        """비동기 처리 시스템 종료"""
        self._shutdown = True
        logger.info("AsyncProcessor shutdown initiated...")

        if wait_for_completion:
            # 활성 작업 완료 대기
            while self.active_tasks:
                logger.info(
                    f"Waiting for {len(self.active_tasks)} active tasks to complete..."
                )
                await asyncio.sleep(1)

        # 백그라운드 작업 취소
        for task in self.background_tasks:
            task.cancel()

        # 풀 종료
        if self.thread_pool:
            self.thread_pool.shutdown(wait=wait_for_completion)

        if self.process_pool:
            self.process_pool.shutdown(wait=wait_for_completion)

        logger.info("AsyncProcessor shutdown completed")


# 글로벌 비동기 처리기
_global_async_processor = None


def get_global_async_processor() -> AsyncProcessor:
    """글로벌 비동기 처리기 반환"""
    global _global_async_processor

    if _global_async_processor is None:
        _global_async_processor = AsyncProcessor()

    return _global_async_processor


def async_task(use_process_pool: bool = False):
    """비동기 작업 데코레이터"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            processor = get_global_async_processor()
            task_id = await processor.submit_async_task(
                func, *args, use_process_pool=use_process_pool, **kwargs
            )

            # 작업 완료 대기
            while task_id not in processor.completed_tasks:
                await asyncio.sleep(0.01)

            result = processor.completed_tasks[task_id]
            if result.success:
                return result.result
            else:
                raise Exception(result.error)

        return wrapper

    return decorator


if __name__ == "__main__":
    """비동기 처리 시스템 검증"""
    import sys

    async def test_async_processor():
        processor = AsyncProcessor()
        all_tests_passed = True

        try:
            # 테스트 1: 기본 비동기 작업
            def simple_task(x):
                time.sleep(0.1)
                return x * 2

            task_id = await processor.submit_async_task(simple_task, 5)

            # 완료 대기
            while task_id not in processor.completed_tasks:
                await asyncio.sleep(0.01)

            result = processor.completed_tasks[task_id]
            if not result.success or result.result != 10:
                print(f"❌ 기본 비동기 작업 테스트 실패: {result}")
                all_tests_passed = False

            # 테스트 2: 배치 처리
            def batch_task(items):
                return [item * 3 for item in items]

            test_items = list(range(10))
            batch_results = await processor.batch_process(
                batch_task, test_items, batch_size=3
            )

            if not all(r.success for r in batch_results):
                print("❌ 배치 처리 테스트 실패")
                all_tests_passed = False

            # 테스트 3: 성능 통계
            stats = processor.get_performance_stats()
            if stats["total_completed"] == 0:
                print("❌ 성능 통계 테스트 실패")
                all_tests_passed = False

            # 정리
            await processor.shutdown()

            if all_tests_passed:
                print("✅ 비동기 처리 시스템 검증 완료 - 모든 테스트 통과")
                print(f"📊 최종 통계: {stats}")
                return 0
            else:
                print("❌ 일부 테스트 실패")
                return 1

        except Exception as e:
            print(f"❌ 테스트 중 오류 발생: {e}")
            import traceback

            traceback.print_exc()
            return 1

    # 비동기 테스트 실행
    exit_code = asyncio.run(test_async_processor())
    sys.exit(exit_code)
