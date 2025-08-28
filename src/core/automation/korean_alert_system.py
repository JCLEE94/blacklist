"""
한국어 알림 시스템

AI 자동화 플랫폼의 실시간 한국어 알림 및 보고 시스템
- 계층적 알림 레벨 관리
- 실시간 진행 상황 보고
- 자동화 단계별 상태 업데이트
- 사용자 친화적 한국어 메시지
"""

import logging
import queue
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

try:
    from src.utils.structured_logging import get_logger
except ImportError:

    def get_logger(name):
        return logging.getLogger(name)


logger = get_logger(__name__)


class AlertPriority(Enum):
    """알림 우선순위"""

    INFO = "info"  # ℹ️ 정보
    SUCCESS = "success"  # ✅ 성공
    WARNING = "warning"  # ⚠️ 경고
    CRITICAL = "critical"  # 🔴 위험
    EMERGENCY = "emergency"  # 🚨 긴급


class AlertCategory(Enum):
    """알림 카테고리"""

    SYSTEM = "system"  # 시스템 상태
    AUTOMATION = "automation"  # 자동화 진행
    GIT_OPERATIONS = "git"  # Git 작업
    TEST_COVERAGE = "test"  # 테스트 커버리지
    DEPLOYMENT = "deployment"  # 배포 관련
    PERFORMANCE = "performance"  # 성능 관련
    SECURITY = "security"  # 보안 관련
    BACKUP = "backup"  # 백업/복구
    USER_ACTION = "user_action"  # 사용자 액션


@dataclass
class KoreanAlert:
    """한국어 알림 메시지"""

    alert_id: str
    timestamp: datetime
    priority: AlertPriority
    category: AlertCategory
    title: str
    message: str
    details: Optional[str] = None
    action_required: bool = False
    action_description: Optional[str] = None
    progress_percentage: Optional[float] = None
    estimated_completion: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    dismissed: bool = False
    auto_dismiss_after: Optional[timedelta] = None


class KoreanAlertSystem:
    """한국어 알림 시스템"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.active_alerts: List[KoreanAlert] = []
        self.alert_history: List[KoreanAlert] = []
        self.subscribers: List[Callable[[KoreanAlert], None]] = []
        self.alert_queue = queue.Queue()
        self.is_running = False
        self.processing_thread = None

        # 알림 템플릿
        self.alert_templates = self._initialize_templates()

        # 자동 해제 설정
        self.auto_dismiss_rules = {
            AlertPriority.INFO: timedelta(minutes=5),
            AlertPriority.SUCCESS: timedelta(minutes=3),
            AlertPriority.WARNING: timedelta(minutes=10),
            AlertPriority.CRITICAL: timedelta(hours=1),
            AlertPriority.EMERGENCY: None,  # 수동 해제만
        }

    def start(self):
        """알림 시스템 시작"""
        if not self.is_running:
            self.is_running = True
            self.processing_thread = threading.Thread(
                target=self._process_alerts, daemon=True
            )
            self.processing_thread.start()
            self.logger.info("🚀 한국어 알림 시스템 시작")

    def stop(self):
        """알림 시스템 중지"""
        self.is_running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=2)
        self.logger.info("🛑 한국어 알림 시스템 중지")

    def _process_alerts(self):
        """알림 처리 스레드"""
        while self.is_running:
            try:
                # 자동 해제 처리
                self._process_auto_dismiss()

                # 큐에서 새 알림 처리
                try:
                    alert = self.alert_queue.get(timeout=1)
                    self._handle_new_alert(alert)
                except queue.Empty:
                    continue

            except Exception as e:
                self.logger.error(f"알림 처리 오류: {e}")

    def _handle_new_alert(self, alert: KoreanAlert):
        """새 알림 처리"""
        # 활성 알림에 추가
        self.active_alerts.append(alert)

        # 히스토리에 추가
        self.alert_history.append(alert)

        # 히스토리 크기 제한 (최근 1000개)
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]

        # 구독자들에게 알림 전송
        for subscriber in self.subscribers:
            try:
                subscriber(alert)
            except Exception as e:
                self.logger.error(f"알림 구독자 호출 실패: {e}")

        # 콘솔 출력
        self._print_alert(alert)

    def _process_auto_dismiss(self):
        """자동 해제 처리"""
        now = datetime.now()
        for alert in self.active_alerts[:]:  # 복사본으로 순회
            if alert.auto_dismiss_after and not alert.dismissed:
                if now - alert.timestamp >= alert.auto_dismiss_after:
                    alert.dismissed = True
                    self.active_alerts.remove(alert)
                    self.logger.debug(f"알림 자동 해제: {alert.alert_id}")

    def _print_alert(self, alert: KoreanAlert):
        """알림 콘솔 출력"""
        priority_icons = {
            AlertPriority.INFO: "ℹ️",
            AlertPriority.SUCCESS: "✅",
            AlertPriority.WARNING: "⚠️",
            AlertPriority.CRITICAL: "🔴",
            AlertPriority.EMERGENCY: "🚨",
        }

        icon = priority_icons.get(alert.priority, "📢")
        timestamp_str = alert.timestamp.strftime("%H:%M:%S")

        print(f"\n{icon} [{timestamp_str}] {alert.title}")
        print(f"📁 카테고리: {alert.category.value}")
        print(f"📝 내용: {alert.message}")

        if alert.details:
            print(f"📋 상세: {alert.details}")

        if alert.progress_percentage is not None:
            progress_bar = self._create_progress_bar(alert.progress_percentage)
            print(f"📊 진행률: {progress_bar} {alert.progress_percentage:.1f}%")

        if alert.estimated_completion:
            completion_str = alert.estimated_completion.strftime("%H:%M:%S")
            print(f"⏰ 예상 완료: {completion_str}")

        if alert.action_required and alert.action_description:
            print(f"👤 필요한 작업: {alert.action_description}")

        print("=" * 60)

    def _create_progress_bar(self, percentage: float, width: int = 20) -> str:
        """진행률 바 생성"""
        filled = int(width * percentage / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}]"

    def send_alert(
        self,
        title: str,
        message: str,
        priority: AlertPriority = AlertPriority.INFO,
        category: AlertCategory = AlertCategory.SYSTEM,
        details: Optional[str] = None,
        action_required: bool = False,
        action_description: Optional[str] = None,
        progress_percentage: Optional[float] = None,
        estimated_completion: Optional[datetime] = None,
        metadata: Dict[str, Any] = None,
    ) -> str:
        """알림 전송"""

        alert_id = f"{category.value}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        alert = KoreanAlert(
            alert_id=alert_id,
            timestamp=datetime.now(),
            priority=priority,
            category=category,
            title=title,
            message=message,
            details=details,
            action_required=action_required,
            action_description=action_description,
            progress_percentage=progress_percentage,
            estimated_completion=estimated_completion,
            metadata=metadata or {},
            auto_dismiss_after=self.auto_dismiss_rules.get(priority),
        )

        self.alert_queue.put(alert)
        return alert_id

    def send_progress_update(
        self,
        task_name: str,
        progress: float,
        details: Optional[str] = None,
        estimated_completion: Optional[datetime] = None,
    ) -> str:
        """진행 상황 업데이트 알림"""

        if progress >= 100:
            title = f"✅ {task_name} 완료"
            priority = AlertPriority.SUCCESS
            message = f"{task_name}이(가) 성공적으로 완료되었습니다."
        elif progress >= 75:
            title = f"🔄 {task_name} 거의 완료"
            priority = AlertPriority.INFO
            message = f"{task_name} 진행률: {progress:.1f}% - 거의 완료되었습니다."
        else:
            title = f"🔄 {task_name} 진행 중"
            priority = AlertPriority.INFO
            message = f"{task_name} 진행률: {progress:.1f}%"

        return self.send_alert(
            title=title,
            message=message,
            priority=priority,
            category=AlertCategory.AUTOMATION,
            details=details,
            progress_percentage=progress,
            estimated_completion=estimated_completion,
        )

    def send_automation_step_alert(
        self,
        step_number: int,
        step_name: str,
        status: str,
        details: Optional[str] = None,
        next_steps: List[str] = None,
    ) -> str:
        """자동화 단계별 알림"""

        status_icons = {
            "시작": "🚀",
            "진행중": "🔄",
            "완료": "✅",
            "실패": "❌",
            "건너뛰기": "⏭️",
            "대기": "⏸️",
        }

        icon = status_icons.get(status, "📋")
        title = f"{icon} [Step {step_number}] {step_name}"

        if status == "완료":
            priority = AlertPriority.SUCCESS
            message = f"Step {step_number}: {step_name}이(가) 성공적으로 완료되었습니다."
        elif status == "실패":
            priority = AlertPriority.CRITICAL
            message = f"Step {step_number}: {step_name} 실행에 실패했습니다."
        elif status == "시작":
            priority = AlertPriority.INFO
            message = f"Step {step_number}: {step_name}을(를) 시작합니다."
        else:
            priority = AlertPriority.INFO
            message = f"Step {step_number}: {step_name} - {status}"

        # 다음 단계 정보 추가
        if next_steps:
            if details:
                details += f"\n\n다음 예정 단계:\n" + "\n".join(
                    f"• {step}" for step in next_steps[:3]
                )
            else:
                details = "다음 예정 단계:\n" + "\n".join(
                    f"• {step}" for step in next_steps[:3]
                )

        return self.send_alert(
            title=title,
            message=message,
            priority=priority,
            category=AlertCategory.AUTOMATION,
            details=details,
        )

    def send_system_status_alert(
        self,
        metric_name: str,
        current_value: float,
        threshold: float,
        unit: str = "",
        trend: Optional[str] = None,
    ) -> str:
        """시스템 상태 알림"""

        # 임계값 비교로 우선순위 결정
        if current_value >= threshold * 1.5:
            priority = AlertPriority.EMERGENCY
            status = "심각"
            icon = "🚨"
        elif current_value >= threshold * 1.2:
            priority = AlertPriority.CRITICAL
            status = "위험"
            icon = "🔴"
        elif current_value >= threshold:
            priority = AlertPriority.WARNING
            status = "주의"
            icon = "⚠️"
        else:
            priority = AlertPriority.INFO
            status = "정상"
            icon = "✅"

        title = f"{icon} {metric_name} {status}"
        message = f"{metric_name}: {current_value}{unit} (임계값: {threshold}{unit})"

        details = f"현재 값: {current_value}{unit}\n임계값: {threshold}{unit}"
        if trend:
            trend_icon = {"증가": "📈", "감소": "📉", "안정": "➡️"}.get(trend, "")
            details += f"\n추세: {trend_icon} {trend}"

        return self.send_alert(
            title=title,
            message=message,
            priority=priority,
            category=AlertCategory.SYSTEM,
            details=details,
        )

    def send_git_operation_alert(
        self,
        operation: str,
        files_count: int,
        status: str,
        details: Optional[str] = None,
    ) -> str:
        """Git 작업 알림"""

        operation_icons = {
            "commit": "💾",
            "push": "📤",
            "pull": "📥",
            "merge": "🔀",
            "branch": "🌿",
            "checkout": "↗️",
        }

        icon = operation_icons.get(operation, "📋")

        if status == "성공":
            priority = AlertPriority.SUCCESS
            title = f"{icon} Git {operation.upper()} 완료"
            message = f"{files_count}개 파일에 대한 Git {operation} 작업이 성공했습니다."
        elif status == "실패":
            priority = AlertPriority.CRITICAL
            title = f"{icon} Git {operation.upper()} 실패"
            message = f"Git {operation} 작업이 실패했습니다."
        else:
            priority = AlertPriority.INFO
            title = f"{icon} Git {operation.upper()} {status}"
            message = f"Git {operation} 작업 - {status}"

        return self.send_alert(
            title=title,
            message=message,
            priority=priority,
            category=AlertCategory.GIT_OPERATIONS,
            details=details,
        )

    def send_test_coverage_alert(
        self,
        current_coverage: float,
        target_coverage: float,
        change_delta: Optional[float] = None,
    ) -> str:
        """테스트 커버리지 알림"""

        if current_coverage >= target_coverage:
            priority = AlertPriority.SUCCESS
            icon = "✅"
            status = "목표 달성"
        elif current_coverage >= target_coverage * 0.8:
            priority = AlertPriority.INFO
            icon = "📊"
            status = "목표 근접"
        else:
            priority = AlertPriority.WARNING
            icon = "⚠️"
            status = "개선 필요"

        title = f"{icon} 테스트 커버리지 {status}"
        message = f"현재 커버리지: {current_coverage:.1f}% (목표: {target_coverage:.1f}%)"

        details = f"현재: {current_coverage:.1f}%\n목표: {target_coverage:.1f}%"
        if change_delta is not None:
            if change_delta > 0:
                details += f"\n변화: +{change_delta:.1f}% 📈"
            elif change_delta < 0:
                details += f"\n변화: {change_delta:.1f}% 📉"
            else:
                details += f"\n변화: 변동 없음 ➡️"

        return self.send_alert(
            title=title,
            message=message,
            priority=priority,
            category=AlertCategory.TEST_COVERAGE,
            details=details,
            progress_percentage=(
                (current_coverage / target_coverage * 100)
                if target_coverage > 0
                else None
            ),
        )

    def send_deployment_alert(
        self, environment: str, version: str, status: str, details: Optional[str] = None
    ) -> str:
        """배포 관련 알림"""

        if status == "성공":
            priority = AlertPriority.SUCCESS
            icon = "🚀"
            message = f"{environment} 환경에 버전 {version} 배포가 성공했습니다."
        elif status == "실패":
            priority = AlertPriority.CRITICAL
            icon = "❌"
            message = f"{environment} 환경 배포가 실패했습니다."
        elif status == "시작":
            priority = AlertPriority.INFO
            icon = "⚡"
            message = f"{environment} 환경에 버전 {version} 배포를 시작합니다."
        else:
            priority = AlertPriority.INFO
            icon = "🔄"
            message = f"{environment} 배포 상태: {status}"

        title = f"{icon} 배포 {status.upper()}: {environment}"

        return self.send_alert(
            title=title,
            message=message,
            priority=priority,
            category=AlertCategory.DEPLOYMENT,
            details=details,
        )

    def dismiss_alert(self, alert_id: str) -> bool:
        """알림 해제"""
        for alert in self.active_alerts:
            if alert.alert_id == alert_id:
                alert.dismissed = True
                self.active_alerts.remove(alert)
                self.logger.info(f"알림 해제: {alert_id}")
                return True
        return False

    def dismiss_all_by_category(self, category: AlertCategory) -> int:
        """카테고리별 모든 알림 해제"""
        dismissed_count = 0
        for alert in self.active_alerts[:]:
            if alert.category == category:
                alert.dismissed = True
                self.active_alerts.remove(alert)
                dismissed_count += 1

        if dismissed_count > 0:
            self.logger.info(f"{category.value} 카테고리 알림 {dismissed_count}개 해제")

        return dismissed_count

    def get_active_alerts(
        self,
        category: Optional[AlertCategory] = None,
        priority: Optional[AlertPriority] = None,
    ) -> List[KoreanAlert]:
        """활성 알림 조회"""
        alerts = self.active_alerts

        if category:
            alerts = [a for a in alerts if a.category == category]

        if priority:
            alerts = [a for a in alerts if a.priority == priority]

        return alerts

    def get_alert_statistics(self) -> Dict[str, Any]:
        """알림 통계"""
        total_alerts = len(self.alert_history)
        active_count = len(self.active_alerts)

        # 우선순위별 통계
        priority_stats = {}
        for priority in AlertPriority:
            priority_stats[priority.value] = len(
                [a for a in self.alert_history if a.priority == priority]
            )

        # 카테고리별 통계
        category_stats = {}
        for category in AlertCategory:
            category_stats[category.value] = len(
                [a for a in self.alert_history if a.category == category]
            )

        # 시간대별 통계 (최근 24시간)
        now = datetime.now()
        recent_alerts = [
            a for a in self.alert_history if now - a.timestamp <= timedelta(hours=24)
        ]

        return {
            "총_알림_수": total_alerts,
            "활성_알림_수": active_count,
            "최근_24시간_알림": len(recent_alerts),
            "우선순위별_통계": priority_stats,
            "카테고리별_통계": category_stats,
            "구독자_수": len(self.subscribers),
            "시스템_가동_시간": self.is_running,
        }

    def subscribe(self, callback: Callable[[KoreanAlert], None]):
        """알림 구독"""
        self.subscribers.append(callback)
        self.logger.info("새 구독자 등록")

    def unsubscribe(self, callback: Callable[[KoreanAlert], None]):
        """구독 해제"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
            self.logger.info("구독자 해제")

    def _initialize_templates(self) -> Dict[str, str]:
        """알림 템플릿 초기화"""
        return {
            "step_start": "🚀 [Step {step}] {name} 시작",
            "step_progress": "🔄 [Step {step}] {name} 진행 중 ({progress}%)",
            "step_complete": "✅ [Step {step}] {name} 완료",
            "step_failed": "❌ [Step {step}] {name} 실패",
            "system_warning": "⚠️ 시스템 경고: {metric} {value}{unit}",
            "system_critical": "🔴 시스템 위험: {metric} {value}{unit}",
            "automation_progress": "🤖 자동화 진행률: {progress}%",
            "git_commit": "💾 Git 커밋: {files}개 파일",
            "test_coverage": "📊 테스트 커버리지: {coverage}%",
            "deployment": "🚀 배포 {status}: {environment}",
        }


# 싱글톤 인스턴스
_alert_system = None


def get_korean_alert_system() -> KoreanAlertSystem:
    """한국어 알림 시스템 싱글톤 인스턴스 반환"""
    global _alert_system
    if _alert_system is None:
        _alert_system = KoreanAlertSystem()
        _alert_system.start()
    return _alert_system


# 편의 함수들
def send_info(title: str, message: str, **kwargs) -> str:
    """정보 알림 전송"""
    return get_korean_alert_system().send_alert(
        title, message, AlertPriority.INFO, **kwargs
    )


def send_success(title: str, message: str, **kwargs) -> str:
    """성공 알림 전송"""
    return get_korean_alert_system().send_alert(
        title, message, AlertPriority.SUCCESS, **kwargs
    )


def send_warning(title: str, message: str, **kwargs) -> str:
    """경고 알림 전송"""
    return get_korean_alert_system().send_alert(
        title, message, AlertPriority.WARNING, **kwargs
    )


def send_critical(title: str, message: str, **kwargs) -> str:
    """위험 알림 전송"""
    return get_korean_alert_system().send_alert(
        title, message, AlertPriority.CRITICAL, **kwargs
    )


def send_emergency(title: str, message: str, **kwargs) -> str:
    """긴급 알림 전송"""
    return get_korean_alert_system().send_alert(
        title, message, AlertPriority.EMERGENCY, **kwargs
    )


def send_step_update(step: int, name: str, status: str, **kwargs) -> str:
    """자동화 단계 업데이트"""
    return get_korean_alert_system().send_automation_step_alert(
        step, name, status, **kwargs
    )


def send_progress_update(task: str, progress: float, **kwargs) -> str:
    """진행 상황 업데이트"""
    return get_korean_alert_system().send_progress_update(task, progress, **kwargs)


if __name__ == "__main__":
    # 테스트 실행
    system = get_korean_alert_system()

    # 테스트 알림들
    send_info("시스템 시작", "한국어 알림 시스템이 초기화되었습니다.")
    send_step_update(1, "Git 변경사항 분류", "시작")
    send_progress_update("테스트 커버리지 향상", 45.5)
    send_warning("메모리 사용량 증가", "현재 메모리 사용률이 75%를 초과했습니다.")

    import time

    time.sleep(5)

    send_step_update(1, "Git 변경사항 분류", "완료")
    send_success("단계 완료", "Step 1이 성공적으로 완료되었습니다.")

    # 통계 출력
    stats = system.get_alert_statistics()
    print(f"\n📊 알림 시스템 통계:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    system.stop()
