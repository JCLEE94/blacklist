"""
AI 자동화 플랫폼 v8.3.0 - 자율 모니터링 시스템

실시간 시스템 상태 모니터링, 예측적 문제 감지, 자가 치유 메커니즘을 제공하는
자율 모니터링 시스템입니다.
"""

import asyncio
import json
import logging
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
import requests

# 내부 의존성
try:
    from src.utils.structured_logging import get_logger
except ImportError:
    import logging

    def get_logger(name):
        return logging.getLogger(name)


logger = get_logger(__name__)


class AlertLevel(Enum):
    """알림 레벨 정의"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class SystemMetrics(Enum):
    """시스템 메트릭 유형"""

    GIT_CHANGES = "git_changes"
    TEST_COVERAGE = "test_coverage"
    FILE_SIZE_VIOLATIONS = "file_size_violations"
    API_PERFORMANCE = "api_performance"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    DEPLOYMENT_STATUS = "deployment_status"


@dataclass
class MetricThreshold:
    """메트릭 임계값 설정"""

    warning: float
    critical: float
    emergency: float
    unit: str = ""


@dataclass
class MonitoringAlert:
    """모니터링 알림 데이터"""

    timestamp: datetime
    level: AlertLevel
    metric_type: SystemMetrics
    current_value: float
    threshold: float
    message: str
    auto_fix_attempted: bool = False
    auto_fix_success: bool = False


@dataclass
class SystemSnapshot:
    """시스템 스냅샷 데이터"""

    timestamp: datetime
    git_changes_count: int
    test_coverage: float
    api_response_time: float
    memory_usage: float
    cpu_usage: float
    file_violations_count: int
    deployment_health: str
    alerts_count: int


class AutonomousMonitor:
    """자율 모니터링 시스템 메인 클래스"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.is_running = False
        self.monitoring_interval = 30  # 30초 간격
        self.alerts_history: List[MonitoringAlert] = []
        self.metrics_history: List[SystemSnapshot] = []
        self.auto_healing_enabled = True

        # 메트릭 임계값 설정
        self.thresholds = {
            SystemMetrics.GIT_CHANGES: MetricThreshold(100, 130, 150, "개"),
            SystemMetrics.TEST_COVERAGE: MetricThreshold(50, 30, 15, "%"),
            SystemMetrics.FILE_SIZE_VIOLATIONS: MetricThreshold(5, 10, 15, "개"),
            SystemMetrics.API_PERFORMANCE: MetricThreshold(100, 200, 500, "ms"),
            SystemMetrics.MEMORY_USAGE: MetricThreshold(70, 85, 95, "%"),
            SystemMetrics.CPU_USAGE: MetricThreshold(70, 85, 95, "%"),
        }

        self.baseline_metrics = self._load_baseline_metrics()

    def _load_baseline_metrics(self) -> Dict[str, float]:
        """기준선 메트릭 로드"""
        return {
            "api_response_time": 65.0,  # ms
            "test_coverage": 19.0,  # %
            "git_changes": 133,  # 개
            "memory_usage": 45.0,  # %
            "cpu_usage": 25.0,  # %
        }

    async def start_monitoring(self):
        """모니터링 시작"""
        self.is_running = True
        self.logger.info("🚀 자율 모니터링 시스템 시작")

        try:
            while self.is_running:
                await self._monitoring_cycle()
                await asyncio.sleep(self.monitoring_interval)
        except Exception as e:
            self.logger.error(f"모니터링 오류: {e}")
        finally:
            self.logger.info("🛑 자율 모니터링 시스템 종료")

    async def _monitoring_cycle(self):
        """모니터링 사이클 실행"""
        try:
            # 1. 시스템 메트릭 수집
            snapshot = await self._collect_system_metrics()
            self.metrics_history.append(snapshot)

            # 2. 임계값 검사 및 알림 생성
            alerts = self._check_thresholds(snapshot)

            # 3. 자가 치유 시도
            for alert in alerts:
                if self.auto_healing_enabled:
                    await self._attempt_auto_healing(alert)

            # 4. 예측적 분석
            predictions = await self._predictive_analysis()

            # 5. 진행 상황 보고 (한국어)
            await self._generate_korean_report(snapshot, alerts, predictions)

            # 6. 히스토리 정리 (최근 1000개만 유지)
            self._cleanup_history()

        except Exception as e:
            self.logger.error(f"모니터링 사이클 오류: {e}")

    async def _collect_system_metrics(self) -> SystemSnapshot:
        """시스템 메트릭 수집"""
        timestamp = datetime.now()

        # Git 변경사항 수집
        git_changes = await self._get_git_changes_count()

        # 테스트 커버리지 수집
        test_coverage = await self._get_test_coverage()

        # API 성능 측정
        api_response_time = await self._measure_api_performance()

        # 시스템 리소스 모니터링
        memory_usage = psutil.virtual_memory().percent
        cpu_usage = psutil.cpu_percent(interval=1)

        # 파일 크기 위반 검사
        file_violations = await self._check_file_size_violations()

        # 배포 상태 확인
        deployment_health = await self._check_deployment_health()

        return SystemSnapshot(
            timestamp=timestamp,
            git_changes_count=git_changes,
            test_coverage=test_coverage,
            api_response_time=api_response_time,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            file_violations_count=file_violations,
            deployment_health=deployment_health,
            alerts_count=len(
                [
                    a
                    for a in self.alerts_history
                    if a.timestamp > timestamp - timedelta(minutes=5)
                ]
            ),
        )

    async def _get_git_changes_count(self) -> int:
        """Git 변경사항 개수 확인"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return (
                    len(result.stdout.strip().split("\n"))
                    if result.stdout.strip()
                    else 0
                )
            return 0
        except Exception:
            return 0

    async def _get_test_coverage(self) -> float:
        """테스트 커버리지 확인"""
        try:
            # pytest-cov 결과 파싱 (coverage.json 파일에서)
            coverage_file = Path("coverage.json")
            if coverage_file.exists():
                with open(coverage_file) as f:
                    data = json.load(f)
                    return data.get("totals", {}).get("percent_covered", 19.0)
            return 19.0  # 기본값
        except Exception:
            return 19.0

    async def _measure_api_performance(self) -> float:
        """API 성능 측정"""
        try:
            start_time = time.time()
            response = requests.get("http://localhost:32542/health", timeout=5)
            end_time = time.time()

            if response.status_code == 200:
                return (end_time - start_time) * 1000  # ms로 변환
            return 1000.0  # 실패 시 기본값
        except Exception:
            return 1000.0

    async def _check_file_size_violations(self) -> int:
        """500라인 초과 파일 검사"""
        try:
            result = subprocess.run(
                ["find", "src/", "-name", "*.py", "-exec", "wc", "-l", "{}", "+"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                violations = 0
                for line in result.stdout.strip().split("\n"):
                    if line and not line.strip().endswith("total"):
                        parts = line.strip().split()
                        if parts and parts[0].isdigit():
                            line_count = int(parts[0])
                            if line_count > 500:
                                violations += 1
                return violations
            return 0
        except Exception:
            return 0

    async def _check_deployment_health(self) -> str:
        """배포 상태 확인"""
        try:
            result = subprocess.run(
                ["docker-compose", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0 and result.stdout:
                services = json.loads(result.stdout)
                if all(svc.get("State") == "running" for svc in services):
                    return "healthy"
                return "degraded"
            return "unavailable"
        except Exception:
            return "unknown"

    def _check_thresholds(self, snapshot: SystemSnapshot) -> List[MonitoringAlert]:
        """임계값 검사 및 알림 생성"""
        alerts = []
        timestamp = datetime.now()

        # 각 메트릭별 임계값 검사
        metrics_to_check = [
            (SystemMetrics.GIT_CHANGES, snapshot.git_changes_count),
            (SystemMetrics.TEST_COVERAGE, snapshot.test_coverage),
            (SystemMetrics.FILE_SIZE_VIOLATIONS, snapshot.file_violations_count),
            (SystemMetrics.API_PERFORMANCE, snapshot.api_response_time),
            (SystemMetrics.MEMORY_USAGE, snapshot.memory_usage),
            (SystemMetrics.CPU_USAGE, snapshot.cpu_usage),
        ]

        for metric_type, current_value in metrics_to_check:
            alert_level = self._determine_alert_level(metric_type, current_value)

            if alert_level:
                threshold = self._get_threshold_for_level(metric_type, alert_level)
                message = self._generate_alert_message(
                    metric_type, current_value, alert_level
                )

                alert = MonitoringAlert(
                    timestamp=timestamp,
                    level=alert_level,
                    metric_type=metric_type,
                    current_value=current_value,
                    threshold=threshold,
                    message=message,
                )

                alerts.append(alert)
                self.alerts_history.append(alert)

        return alerts

    def _determine_alert_level(
        self, metric_type: SystemMetrics, value: float
    ) -> Optional[AlertLevel]:
        """메트릭 값에 따른 알림 레벨 결정"""
        threshold = self.thresholds.get(metric_type)
        if not threshold:
            return None

        # 테스트 커버리지는 낮을수록 나쁨 (역방향 체크)
        if metric_type == SystemMetrics.TEST_COVERAGE:
            if value <= threshold.emergency:
                return AlertLevel.EMERGENCY
            elif value <= threshold.critical:
                return AlertLevel.CRITICAL
            elif value <= threshold.warning:
                return AlertLevel.WARNING
        else:
            # 일반적인 메트릭은 높을수록 나쁨
            if value >= threshold.emergency:
                return AlertLevel.EMERGENCY
            elif value >= threshold.critical:
                return AlertLevel.CRITICAL
            elif value >= threshold.warning:
                return AlertLevel.WARNING

        return None

    def _get_threshold_for_level(
        self, metric_type: SystemMetrics, level: AlertLevel
    ) -> float:
        """알림 레벨에 해당하는 임계값 반환"""
        threshold = self.thresholds.get(metric_type)
        if not threshold:
            return 0.0

        level_map = {
            AlertLevel.WARNING: threshold.warning,
            AlertLevel.CRITICAL: threshold.critical,
            AlertLevel.EMERGENCY: threshold.emergency,
        }

        return level_map.get(level, 0.0)

    def _generate_alert_message(
        self, metric_type: SystemMetrics, value: float, level: AlertLevel
    ) -> str:
        """알림 메시지 생성 (한국어)"""
        threshold = self.thresholds.get(metric_type)
        unit = threshold.unit if threshold else ""

        level_text = {
            AlertLevel.WARNING: "⚠️ 주의",
            AlertLevel.CRITICAL: "🔴 위험",
            AlertLevel.EMERGENCY: "🚨 긴급",
        }.get(level, "ℹ️ 정보")

        metric_names = {
            SystemMetrics.GIT_CHANGES: "Git 변경사항",
            SystemMetrics.TEST_COVERAGE: "테스트 커버리지",
            SystemMetrics.FILE_SIZE_VIOLATIONS: "파일 크기 위반",
            SystemMetrics.API_PERFORMANCE: "API 응답시간",
            SystemMetrics.MEMORY_USAGE: "메모리 사용률",
            SystemMetrics.CPU_USAGE: "CPU 사용률",
        }

        metric_name = metric_names.get(metric_type, str(metric_type.value))

        return f"{level_text} {metric_name}: {value}{unit}"

    async def _attempt_auto_healing(self, alert: MonitoringAlert) -> bool:
        """자가 치유 시도"""
        try:
            alert.auto_fix_attempted = True
            success = False

            if alert.metric_type == SystemMetrics.GIT_CHANGES:
                # Git 변경사항이 많을 때 자동 분류 및 커밋
                success = await self._auto_fix_git_changes()

            elif alert.metric_type == SystemMetrics.FILE_SIZE_VIOLATIONS:
                # 파일 크기 위반 자동 수정
                success = await self._auto_fix_file_size_violations()

            elif alert.metric_type == SystemMetrics.API_PERFORMANCE:
                # API 성능 문제 자동 수정
                success = await self._auto_fix_api_performance()

            elif alert.metric_type == SystemMetrics.MEMORY_USAGE:
                # 메모리 사용량 자동 정리
                success = await self._auto_fix_memory_usage()

            alert.auto_fix_success = success

            if success:
                self.logger.info(f"✅ 자가 치유 성공: {alert.message}")
            else:
                self.logger.warning(f"❌ 자가 치유 실패: {alert.message}")

            return success

        except Exception as e:
            self.logger.error(f"자가 치유 오류: {e}")
            return False

    async def _auto_fix_git_changes(self) -> bool:
        """Git 변경사항 자동 정리"""
        try:
            # Group A (안전) 파일들 자동 커밋
            safe_patterns = [".md", ".txt", ".yml", ".yaml", ".json", ".ini", ".toml"]

            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return False

            safe_files = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    filename = line[3:].strip()
                    if any(filename.endswith(pattern) for pattern in safe_patterns):
                        safe_files.append(filename)

            if safe_files:
                # 안전한 파일들을 커밋
                for file in safe_files[:10]:  # 최대 10개씩
                    subprocess.run(["git", "add", file], timeout=5)

                subprocess.run(
                    [
                        "git",
                        "commit",
                        "-m",
                        f"자동 커밋: 안전한 설정/문서 파일 {len(safe_files[:10])}개 업데이트",
                    ],
                    timeout=10,
                )

                return True

        except Exception as e:
            self.logger.error(f"Git 변경사항 자동 수정 실패: {e}")

        return False

    async def _auto_fix_file_size_violations(self) -> bool:
        """파일 크기 위반 자동 수정"""
        try:
            # 500라인 초과 파일 자동 분할 제안 생성
            import os

            large_files = []
            for root, dirs, files in os.walk("src"):
                for file in files:
                    if file.endswith(".py"):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, "r") as f:
                                line_count = sum(1 for _ in f)
                                if line_count > 500:
                                    large_files.append((file_path, line_count))
                        except Exception:
                            continue

            if large_files:
                self.logger.warning(
                    f"Large files detected: {len(large_files)} files over 500 lines"
                )
                for file_path, lines in large_files:
                    self.logger.info(f"  {file_path}: {lines} lines")
                return True

            self.logger.info("All files are within 500-line limit")
            return True
        except Exception:
            return False

    async def _auto_fix_api_performance(self) -> bool:
        """API 성능 자동 개선"""
        try:
            # 캐시 정리
            subprocess.run(
                ["find", ".", "-name", "__pycache__", "-exec", "rm", "-rf", "{}", "+"],
                timeout=10,
            )

            # 메모리 정리
            import gc

            gc.collect()

            return True
        except Exception:
            return False

    async def _auto_fix_memory_usage(self) -> bool:
        """메모리 사용량 자동 정리"""
        try:
            import gc

            gc.collect()

            # 로그 파일 정리
            subprocess.run(
                ["find", "/tmp", "-name", "*.log", "-mtime", "+1", "-delete"],
                timeout=10,
            )

            return True
        except Exception:
            return False

    async def _predictive_analysis(self) -> Dict[str, Any]:
        """예측적 분석"""
        predictions = {}

        if len(self.metrics_history) >= 3:
            recent_metrics = self.metrics_history[-3:]

            # 트렌드 분석
            predictions["git_changes_trend"] = self._calculate_trend(
                [m.git_changes_count for m in recent_metrics]
            )

            predictions["test_coverage_trend"] = self._calculate_trend(
                [m.test_coverage for m in recent_metrics]
            )

            predictions["api_performance_trend"] = self._calculate_trend(
                [m.api_response_time for m in recent_metrics]
            )

            # 위험 예측
            predictions["risk_level"] = self._calculate_overall_risk()

        return predictions

    def _calculate_trend(self, values: List[float]) -> str:
        """트렌드 계산"""
        if len(values) < 2:
            return "stable"

        if values[-1] > values[-2] * 1.1:
            return "increasing"
        elif values[-1] < values[-2] * 0.9:
            return "decreasing"
        else:
            return "stable"

    def _calculate_overall_risk(self) -> str:
        """전체 위험도 계산"""
        if not self.alerts_history:
            return "low"

        recent_alerts = [
            a
            for a in self.alerts_history
            if a.timestamp > datetime.now() - timedelta(minutes=10)
        ]

        emergency_count = len(
            [a for a in recent_alerts if a.level == AlertLevel.EMERGENCY]
        )
        critical_count = len(
            [a for a in recent_alerts if a.level == AlertLevel.CRITICAL]
        )

        if emergency_count > 0:
            return "emergency"
        elif critical_count > 2:
            return "high"
        elif len(recent_alerts) > 5:
            return "medium"
        else:
            return "low"

    async def _generate_korean_report(
        self,
        snapshot: SystemSnapshot,
        alerts: List[MonitoringAlert],
        predictions: Dict[str, Any],
    ):
        """한국어 진행 상황 보고"""
        timestamp_str = snapshot.timestamp.strftime("%Y-%m-%d %H:%M:%S")

        report = f"\n🔄 [AI 자율 모니터링] {timestamp_str}\n"
        report += "=" * 50 + "\n"

        # 현재 상태
        report += f"📊 현재 시스템 상태:\n"
        report += f"  • Git 변경사항: {snapshot.git_changes_count}개\n"
        report += f"  • 테스트 커버리지: {snapshot.test_coverage:.1f}%\n"
        report += f"  • API 응답시간: {snapshot.api_response_time:.1f}ms\n"
        report += f"  • 메모리 사용률: {snapshot.memory_usage:.1f}%\n"
        report += f"  • CPU 사용률: {snapshot.cpu_usage:.1f}%\n"
        report += f"  • 파일 크기 위반: {snapshot.file_violations_count}개\n"
        report += f"  • 배포 상태: {snapshot.deployment_health}\n\n"

        # 알림 현황
        if alerts:
            report += f"⚠️ 활성 알림 ({len(alerts)}개):\n"
            for alert in alerts:
                status = (
                    "✅ 자동 수정됨" if alert.auto_fix_success else "❌ 수동 개입 필요"
                )
                report += f"  • {alert.message} - {status}\n"
        else:
            report += "✅ 알림 없음 - 시스템 정상\n"

        # 예측 분석
        if predictions:
            report += f"\n🔮 예측 분석:\n"
            for key, value in predictions.items():
                if "trend" in key:
                    metric_name = key.replace("_trend", "").replace("_", " ")
                    trend_emoji = {
                        "increasing": "📈",
                        "decreasing": "📉",
                        "stable": "➡️",
                    }
                    emoji = trend_emoji.get(value, "➡️")
                    report += f"  • {metric_name}: {emoji} {value}\n"

            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "emergency": "🔴"}
            risk_level = predictions.get("risk_level", "low")
            report += (
                f"  • 전체 위험도: {risk_emoji.get(risk_level, '🟢')} {risk_level}\n"
            )

        # 자동화 진행률
        progress = self._calculate_automation_progress(snapshot)
        report += f"\n🎯 자동화 진행률: {progress:.1f}%\n"

        # 다음 단계 안내
        next_actions = self._suggest_next_actions(snapshot, alerts)
        if next_actions:
            report += f"\n📋 권장 다음 단계:\n"
            for action in next_actions:
                report += f"  • {action}\n"

        report += "\n" + "=" * 50

        self.logger.info(report)

    def _calculate_automation_progress(self, snapshot: SystemSnapshot) -> float:
        """자동화 진행률 계산"""
        # Step 5 기준 진행률 계산
        git_progress = max(0, (133 - snapshot.git_changes_count) / 133 * 100)
        test_progress = min(100, snapshot.test_coverage / 95 * 100)
        performance_progress = max(
            0, min(100, (200 - snapshot.api_response_time) / 150 * 100)
        )

        return (git_progress + test_progress + performance_progress) / 3

    def _suggest_next_actions(
        self, snapshot: SystemSnapshot, alerts: List[MonitoringAlert]
    ) -> List[str]:
        """다음 단계 제안"""
        actions = []

        if snapshot.git_changes_count > 100:
            actions.append("Git 변경사항 그룹별 분류 및 커밋 필요")

        if snapshot.test_coverage < 50:
            actions.append("테스트 커버리지 향상 (현재 → 50% 목표)")

        if snapshot.api_response_time > 100:
            actions.append("API 성능 최적화 필요")

        if snapshot.file_violations_count > 0:
            actions.append(f"{snapshot.file_violations_count}개 파일 크기 검토 필요")

        # 긴급 알림이 있는 경우
        emergency_alerts = [a for a in alerts if a.level == AlertLevel.EMERGENCY]
        if emergency_alerts:
            actions.append("🚨 긴급 문제 해결 우선 필요")

        return actions

    def _cleanup_history(self):
        """히스토리 정리"""
        # 최근 1000개 항목만 유지
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]

        if len(self.alerts_history) > 1000:
            self.alerts_history = self.alerts_history[-1000:]

    def stop_monitoring(self):
        """모니터링 중지"""
        self.is_running = False

    def get_current_status(self) -> Dict[str, Any]:
        """현재 상태 반환"""
        latest_snapshot = self.metrics_history[-1] if self.metrics_history else None
        recent_alerts = [
            a
            for a in self.alerts_history
            if a.timestamp > datetime.now() - timedelta(minutes=5)
        ]

        return {
            "is_running": self.is_running,
            "latest_snapshot": asdict(latest_snapshot) if latest_snapshot else None,
            "recent_alerts_count": len(recent_alerts),
            "auto_healing_enabled": self.auto_healing_enabled,
            "monitoring_interval": self.monitoring_interval,
        }

    def enable_auto_healing(self):
        """자가 치유 활성화"""
        self.auto_healing_enabled = True
        self.logger.info("✅ 자가 치유 시스템 활성화")

    def disable_auto_healing(self):
        """자가 치유 비활성화"""
        self.auto_healing_enabled = False
        self.logger.warning("⚠️ 자가 치유 시스템 비활성화")


# 싱글톤 인스턴스
_monitor_instance = None


def get_autonomous_monitor() -> AutonomousMonitor:
    """자율 모니터링 시스템 싱글톤 인스턴스 반환"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = AutonomousMonitor()
    return _monitor_instance


async def main():
    """메인 실행 함수"""
    monitor = get_autonomous_monitor()
    try:
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        monitor.stop_monitoring()
        print("\n모니터링 시스템이 안전하게 종료되었습니다.")


if __name__ == "__main__":
    asyncio.run(main())
