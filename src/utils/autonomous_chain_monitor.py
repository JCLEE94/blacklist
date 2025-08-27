#!/usr/bin/env python3
"""
자율적 워크플로우 체인 모니터링 시스템 (Step 6: Infinite Workflow Chaining)
실시간 모니터링, 한국어 진행 상황 보고, 자동 복구 기능 제공
"""

import json
import sqlite3
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .structured_logging import get_logger


class ChainStatus(Enum):
    """체인 실행 상태"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class ChainPriority(Enum):
    """체인 우선순위"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ChainExecutionMetrics:
    """체인 실행 메트릭"""

    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    success_rate: float = 0.0
    retry_count: int = 0
    max_retries: int = 3
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    error_count: int = 0
    warning_count: int = 0

    def calculate_duration(self):
        """실행 시간 계산"""
        if self.end_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        return self.duration_seconds


@dataclass
class ChainExecutionContext:
    """체인 실행 컨텍스트"""

    chain_id: str
    chain_name: str
    task_id: str
    status: ChainStatus = ChainStatus.PENDING
    priority: ChainPriority = ChainPriority.NORMAL
    metrics: Optional[ChainExecutionMetrics] = None
    dependencies: List[str] = None
    progress_percentage: float = 0.0
    current_step: str = ""
    error_message: str = ""
    korean_status_message: str = ""

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.metrics is None:
            self.metrics = ChainExecutionMetrics(start_time=datetime.now())


class AutonomousChainMonitor:
    """자율적 체인 모니터링 시스템"""

    def __init__(self, db_path: str = "instance/chain_monitor.db"):
        self.logger = get_logger("chain_monitor")
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 체인 실행 컨텍스트 저장
        self.active_chains: Dict[str, ChainExecutionContext] = {}
        self.completed_chains: deque = deque(maxlen=1000)
        self.chain_history: List[ChainExecutionContext] = []

        # 모니터링 설정
        self.monitoring_enabled = True
        self.korean_reporting_enabled = True
        self.auto_recovery_enabled = True
        self.max_concurrent_chains = 3

        # 스레드 관리
        self.monitor_thread = None
        self.executor = ThreadPoolExecutor(max_workers=self.max_concurrent_chains)
        self.shutdown_event = threading.Event()

        # 성능 메트릭
        self.system_metrics = {
            "total_chains_executed": 0,
            "successful_chains": 0,
            "failed_chains": 0,
            "average_success_rate": 0.0,
            "total_execution_time": 0.0,
            "last_update": datetime.now(),
        }

        # 실패 복구 설정
        self.retry_delays = [5, 15, 30, 60]  # 지수적 백오프 (초)
        self.failure_callbacks: Dict[str, Callable] = {}

        # 데이터베이스 초기화
        self._initialize_database()

        # 모니터링 시작
        self.start_monitoring()

        self.logger.info(
            "자율적 체인 모니터링 시스템 초기화 완료",
            max_concurrent_chains=self.max_concurrent_chains,
        )

    def _initialize_database(self):
        """데이터베이스 초기화"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 체인 실행 히스토리 테이블
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chain_execution_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chain_id TEXT NOT NULL,
                        chain_name TEXT NOT NULL,
                        task_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        priority INTEGER NOT NULL,
                        start_time DATETIME NOT NULL,
                        end_time DATETIME,
                        duration_seconds REAL,
                        success_rate REAL,
                        retry_count INTEGER,
                        error_message TEXT,
                        korean_status_message TEXT,
                        metrics_json TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # 시스템 메트릭 테이블
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS system_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_name TEXT NOT NULL,
                        metric_value REAL NOT NULL,
                        recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # 인덱스 생성
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_chain_history_id 
                    ON chain_execution_history(chain_id)
                """
                )

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_chain_history_status 
                    ON chain_execution_history(status)
                """
                )

                conn.commit()

        except Exception as e:
            self.logger.error(f"데이터베이스 초기화 실패: {e}", exception=e)

    def start_monitoring(self):
        """모니터링 시작"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            return

        self.monitoring_enabled = True
        self.shutdown_event.clear()
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self.monitor_thread.start()

        self.logger.info("자율적 체인 모니터링 시작됨")

    def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring_enabled = False
        self.shutdown_event.set()

        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)

        self.executor.shutdown(wait=True)
        self.logger.info("자율적 체인 모니터링 중지됨")

    def _monitoring_loop(self):
        """모니터링 루프"""
        while self.monitoring_enabled and not self.shutdown_event.is_set():
            try:
                # 활성 체인 상태 확인
                self._check_active_chains()

                # 시스템 메트릭 업데이트
                self._update_system_metrics()

                # 실패한 체인 복구 시도
                if self.auto_recovery_enabled:
                    self._attempt_chain_recovery()

                # 체인 상태 지속성 저장
                self._persist_chain_states()

                # 5초마다 모니터링
                if self.shutdown_event.wait(5.0):
                    break

            except Exception as e:
                self.logger.error(f"모니터링 루프 오류: {e}", exception=e)

    def register_chain(
        self,
        chain_id: str,
        chain_name: str,
        task_id: str,
        dependencies: List[str] = None,
        priority: ChainPriority = ChainPriority.NORMAL,
    ) -> ChainExecutionContext:
        """체인 등록"""
        context = ChainExecutionContext(
            chain_id=chain_id,
            chain_name=chain_name,
            task_id=task_id,
            dependencies=dependencies or [],
            priority=priority,
        )

        self.active_chains[chain_id] = context

        korean_msg = f"체인 '{chain_name}' 등록됨 (우선순위: {priority.name})"
        context.korean_status_message = korean_msg

        self.logger.info(
            f"체인 등록: {chain_name}",
            chain_id=chain_id,
            task_id=task_id,
            korean_message=korean_msg,
        )

        return context

    def start_chain_execution(
        self, chain_id: str, execution_func: Callable, *args, **kwargs
    ):
        """체인 실행 시작"""
        if chain_id not in self.active_chains:
            raise ValueError(f"등록되지 않은 체인 ID: {chain_id}")

        context = self.active_chains[chain_id]
        context.status = ChainStatus.RUNNING
        context.metrics.start_time = datetime.now()

        korean_msg = f"체인 '{context.chain_name}' 실행 시작"
        context.korean_status_message = korean_msg

        self.logger.info(korean_msg, chain_id=chain_id)

        # 비동기 실행
        future = self.executor.submit(
            self._execute_chain_with_monitoring,
            context,
            execution_func,
            *args,
            **kwargs,
        )

        return future

    def _execute_chain_with_monitoring(
        self, context: ChainExecutionContext, execution_func: Callable, *args, **kwargs
    ):
        """모니터링과 함께 체인 실행"""
        chain_id = context.chain_id

        try:
            # 의존성 체크
            if not self._check_dependencies(context):
                context.status = ChainStatus.PAUSED
                korean_msg = f"체인 '{context.chain_name}' 의존성 대기 중"
                context.korean_status_message = korean_msg
                self.logger.warning(korean_msg, chain_id=chain_id)
                return False

            # 실행 전 상태 업데이트
            context.current_step = "체인 실행 준비"
            context.progress_percentage = 10.0

            # 실제 체인 실행
            result = execution_func(*args, **kwargs)

            # 성공 처리
            context.status = ChainStatus.SUCCESS
            context.progress_percentage = 100.0
            context.metrics.end_time = datetime.now()
            context.metrics.calculate_duration()
            context.metrics.success_rate = 100.0

            korean_msg = f"체인 '{context.chain_name}' 성공적으로 완료 ({context.metrics.duration_seconds:.1f}초)"
            context.korean_status_message = korean_msg

            self.logger.info(korean_msg, chain_id=chain_id, result=str(result)[:200])

            # 완료된 체인을 기록
            self._complete_chain(context)
            return result

        except Exception as e:
            # 실패 처리
            context.status = ChainStatus.FAILED
            context.error_message = str(e)
            context.metrics.error_count += 1

            korean_msg = f"체인 '{context.chain_name}' 실행 실패: {str(e)[:100]}"
            context.korean_status_message = korean_msg

            self.logger.error(korean_msg, chain_id=chain_id, exception=e)

            # 자동 복구 시도
            if (
                self.auto_recovery_enabled
                and context.metrics.retry_count < context.metrics.max_retries
            ):
                self._schedule_chain_retry(context)
            else:
                self._complete_chain(context)

            return False

    def _check_dependencies(self, context: ChainExecutionContext) -> bool:
        """의존성 체크"""
        if not context.dependencies:
            return True

        for dep_chain_id in context.dependencies:
            if dep_chain_id in self.active_chains:
                dep_context = self.active_chains[dep_chain_id]
                if dep_context.status != ChainStatus.SUCCESS:
                    return False
            else:
                # 의존성 체인이 완료되었는지 히스토리에서 확인
                if not self._is_chain_completed_successfully(dep_chain_id):
                    return False

        return True

    def _is_chain_completed_successfully(self, chain_id: str) -> bool:
        """체인이 성공적으로 완료되었는지 확인"""
        for completed_chain in self.completed_chains:
            if (
                completed_chain.chain_id == chain_id
                and completed_chain.status == ChainStatus.SUCCESS
            ):
                return True
        return False

    def _schedule_chain_retry(self, context: ChainExecutionContext):
        """체인 재시도 스케줄링"""
        context.status = ChainStatus.RETRYING
        context.metrics.retry_count += 1

        # 지수적 백오프 딜레이 계산
        delay_index = min(context.metrics.retry_count - 1, len(self.retry_delays) - 1)
        delay = self.retry_delays[delay_index]

        korean_msg = f"체인 '{context.chain_name}' {delay}초 후 재시도 ({context.metrics.retry_count}/{context.metrics.max_retries})"
        context.korean_status_message = korean_msg

        self.logger.warning(korean_msg, chain_id=context.chain_id)

        # 딜레이 후 재시도
        threading.Timer(delay, self._retry_chain, args=[context]).start()

    def _retry_chain(self, context: ChainExecutionContext):
        """체인 재시도"""
        korean_msg = f"체인 '{context.chain_name}' 재시도 중"
        context.korean_status_message = korean_msg
        self.logger.info(korean_msg, chain_id=context.chain_id)

        # 재시도 로직은 구체적인 실행 함수에 따라 구현 필요
        # 여기서는 상태만 업데이트
        context.status = ChainStatus.RUNNING

    def _complete_chain(self, context: ChainExecutionContext):
        """체인 완료 처리"""
        # 활성 체인에서 제거
        if context.chain_id in self.active_chains:
            del self.active_chains[context.chain_id]

        # 완료된 체인 목록에 추가
        self.completed_chains.append(context)

        # 시스템 메트릭 업데이트
        self.system_metrics["total_chains_executed"] += 1
        if context.status == ChainStatus.SUCCESS:
            self.system_metrics["successful_chains"] += 1
        else:
            self.system_metrics["failed_chains"] += 1

        # 평균 성공률 계산
        total = self.system_metrics["total_chains_executed"]
        successful = self.system_metrics["successful_chains"]
        self.system_metrics["average_success_rate"] = (
            (successful / total) * 100 if total > 0 else 0
        )

        # 데이터베이스에 저장
        self._save_chain_to_db(context)

    def _check_active_chains(self):
        """활성 체인 상태 확인"""
        current_time = datetime.now()

        for chain_id, context in list(self.active_chains.items()):
            # 타임아웃 체크 (30분)
            if (
                context.metrics.start_time
                and (current_time - context.metrics.start_time).total_seconds() > 1800
            ):
                korean_msg = f"체인 '{context.chain_name}' 타임아웃으로 취소됨"
                context.korean_status_message = korean_msg
                context.status = ChainStatus.CANCELLED

                self.logger.warning(korean_msg, chain_id=chain_id)
                self._complete_chain(context)

    def _update_system_metrics(self):
        """시스템 메트릭 업데이트"""
        self.system_metrics["last_update"] = datetime.now()

        # 메모리 및 CPU 사용량 (간단한 구현)
        try:
            import psutil

            process = psutil.Process()

            memory_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent()

            # 활성 체인의 메트릭 업데이트
            for context in self.active_chains.values():
                context.metrics.memory_usage_mb = memory_mb
                context.metrics.cpu_usage_percent = cpu_percent

        except ImportError:
            # psutil이 없는 경우 기본값 사용
            pass

    def _attempt_chain_recovery(self):
        """실패한 체인 복구 시도"""
        for chain_id, context in list(self.active_chains.items()):
            if (
                context.status == ChainStatus.FAILED
                and context.metrics.retry_count < context.metrics.max_retries
            ):
                if chain_id in self.failure_callbacks:
                    try:
                        recovery_func = self.failure_callbacks[chain_id]
                        recovery_func(context)
                    except Exception as e:
                        self.logger.error(
                            f"체인 복구 실패: {e}", chain_id=chain_id, exception=e
                        )

    def _persist_chain_states(self):
        """체인 상태 지속성 저장"""
        try:
            # 활성 체인 상태를 파일에 저장 (간단한 구현)
            state_file = Path("instance/active_chains.json")
            state_file.parent.mkdir(exist_ok=True)

            active_chains_data = {}
            for chain_id, context in self.active_chains.items():
                active_chains_data[chain_id] = {
                    "chain_name": context.chain_name,
                    "task_id": context.task_id,
                    "status": context.status.value,
                    "progress": context.progress_percentage,
                    "korean_message": context.korean_status_message,
                    "start_time": (
                        context.metrics.start_time.isoformat()
                        if context.metrics.start_time
                        else None
                    ),
                }

            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(active_chains_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.logger.error(f"체인 상태 저장 실패: {e}", exception=e)

    def _save_chain_to_db(self, context: ChainExecutionContext):
        """체인 실행 기록을 데이터베이스에 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO chain_execution_history
                    (chain_id, chain_name, task_id, status, priority, 
                     start_time, end_time, duration_seconds, success_rate, 
                     retry_count, error_message, korean_status_message, metrics_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        context.chain_id,
                        context.chain_name,
                        context.task_id,
                        context.status.value,
                        context.priority.value,
                        (
                            context.metrics.start_time.isoformat()
                            if context.metrics.start_time
                            else None
                        ),
                        (
                            context.metrics.end_time.isoformat()
                            if context.metrics.end_time
                            else None
                        ),
                        context.metrics.duration_seconds,
                        context.metrics.success_rate,
                        context.metrics.retry_count,
                        context.error_message,
                        context.korean_status_message,
                        json.dumps(
                            asdict(context.metrics), default=str, ensure_ascii=False
                        ),
                    ),
                )

                conn.commit()

        except Exception as e:
            self.logger.error(f"체인 기록 저장 실패: {e}", exception=e)

    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 조회"""
        return {
            "monitoring_enabled": self.monitoring_enabled,
            "active_chains_count": len(self.active_chains),
            "completed_chains_count": len(self.completed_chains),
            "system_metrics": self.system_metrics.copy(),
            "active_chains": {
                chain_id: {
                    "name": context.chain_name,
                    "status": context.status.value,
                    "progress": context.progress_percentage,
                    "korean_message": context.korean_status_message,
                    "retry_count": context.metrics.retry_count,
                }
                for chain_id, context in self.active_chains.items()
            },
        }

    def get_korean_progress_report(self) -> str:
        """한국어 진행 상황 보고서 생성"""
        report = []

        report.append("=== 자율적 워크플로우 체인 실행 현황 ===")
        report.append(f"📊 전체 통계:")
        report.append(
            f"  • 실행된 체인: {self.system_metrics['total_chains_executed']}개"
        )
        report.append(f"  • 성공한 체인: {self.system_metrics['successful_chains']}개")
        report.append(f"  • 실패한 체인: {self.system_metrics['failed_chains']}개")
        report.append(
            f"  • 평균 성공률: {self.system_metrics['average_success_rate']:.1f}%"
        )
        report.append("")

        if self.active_chains:
            report.append(f"🔄 현재 실행 중인 체인 ({len(self.active_chains)}개):")
            for context in self.active_chains.values():
                status_emoji = {
                    ChainStatus.RUNNING: "🏃",
                    ChainStatus.PENDING: "⏳",
                    ChainStatus.RETRYING: "🔄",
                    ChainStatus.PAUSED: "⏸️",
                }.get(context.status, "❓")

                report.append(f"  {status_emoji} {context.chain_name}")
                report.append(f"     상태: {context.korean_status_message}")
                report.append(f"     진행률: {context.progress_percentage:.1f}%")
                if context.metrics.retry_count > 0:
                    report.append(f"     재시도: {context.metrics.retry_count}회")
                report.append("")

        if self.completed_chains:
            recent_completed = list(self.completed_chains)[-5:]  # 최근 5개
            report.append(f"✅ 최근 완료된 체인 ({len(recent_completed)}개):")
            for context in recent_completed:
                status_emoji = "✅" if context.status == ChainStatus.SUCCESS else "❌"
                duration = (
                    f" ({context.metrics.duration_seconds:.1f}초)"
                    if context.metrics.duration_seconds
                    else ""
                )
                report.append(f"  {status_emoji} {context.chain_name}{duration}")
                report.append(f"     {context.korean_status_message}")
                report.append("")

        report.append(
            f"🕐 마지막 업데이트: {self.system_metrics['last_update'].strftime('%Y-%m-%d %H:%M:%S')}"
        )

        return "\n".join(report)

    def register_failure_callback(self, chain_id: str, callback: Callable):
        """실패 복구 콜백 등록"""
        self.failure_callbacks[chain_id] = callback
        self.logger.info(f"실패 복구 콜백 등록됨", chain_id=chain_id)

    def pause_chain(self, chain_id: str):
        """체인 일시 정지"""
        if chain_id in self.active_chains:
            context = self.active_chains[chain_id]
            context.status = ChainStatus.PAUSED
            korean_msg = f"체인 '{context.chain_name}' 일시 정지됨"
            context.korean_status_message = korean_msg
            self.logger.info(korean_msg, chain_id=chain_id)

    def resume_chain(self, chain_id: str):
        """체인 재개"""
        if chain_id in self.active_chains:
            context = self.active_chains[chain_id]
            context.status = ChainStatus.RUNNING
            korean_msg = f"체인 '{context.chain_name}' 재개됨"
            context.korean_status_message = korean_msg
            self.logger.info(korean_msg, chain_id=chain_id)

    def cancel_chain(self, chain_id: str):
        """체인 취소"""
        if chain_id in self.active_chains:
            context = self.active_chains[chain_id]
            context.status = ChainStatus.CANCELLED
            korean_msg = f"체인 '{context.chain_name}' 취소됨"
            context.korean_status_message = korean_msg
            self.logger.info(korean_msg, chain_id=chain_id)
            self._complete_chain(context)


# 전역 체인 모니터 인스턴스
_global_monitor = None


def get_chain_monitor() -> AutonomousChainMonitor:
    """전역 체인 모니터 인스턴스 반환"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = AutonomousChainMonitor()
    return _global_monitor


def initialize_chain_monitoring():
    """체인 모니터링 초기화"""
    monitor = get_chain_monitor()
    return monitor


def shutdown_chain_monitoring():
    """체인 모니터링 종료"""
    global _global_monitor
    if _global_monitor:
        _global_monitor.stop_monitoring()
        _global_monitor = None


# 편의 함수들
def register_chain(
    chain_name: str, task_id: str, dependencies: List[str] = None
) -> str:
    """체인 등록 편의 함수"""
    import uuid

    chain_id = str(uuid.uuid4())
    monitor = get_chain_monitor()
    monitor.register_chain(chain_id, chain_name, task_id, dependencies)
    return chain_id


def execute_chain(chain_id: str, execution_func: Callable, *args, **kwargs):
    """체인 실행 편의 함수"""
    monitor = get_chain_monitor()
    return monitor.start_chain_execution(chain_id, execution_func, *args, **kwargs)


def get_korean_status() -> str:
    """한국어 상태 보고 편의 함수"""
    monitor = get_chain_monitor()
    return monitor.get_korean_progress_report()


def print_korean_status():
    """한국어 상태를 콘솔에 출력"""
    status = get_korean_status()
    print(status)


if __name__ == "__main__":
    # 테스트 코드
    monitor = initialize_chain_monitoring()

    # 테스트 체인 등록
    chain_id = register_chain("테스트 체인", "test-task-123")

    # 테스트 실행 함수
    def test_execution():
        import time

        time.sleep(2)  # 2초 실행 시뮬레이션
        return "테스트 성공"

    # 체인 실행
    future = execute_chain(chain_id, test_execution)

    # 진행 상황 모니터링
    time.sleep(1)
    print_korean_status()

    # 결과 대기
    result = future.result()
    print(f"실행 결과: {result}")

    time.sleep(1)
    print_korean_status()

    # 정리
    shutdown_chain_monitoring()
