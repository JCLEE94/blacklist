"""
알림 및 경고 시스템

성능 모니터링 알림 규칙 및 알림 처리 기능을 제공합니다.
"""

import threading
from collections import deque
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List

from loguru import logger

from .metrics import AlertRule, PerformanceMetric


class AlertManager:
    """알림 관리자"""

    def __init__(self, max_alerts: int = 100):
        self.max_alerts = max_alerts
        self.alert_rules = []
        self.active_alerts = deque(maxlen=max_alerts)
        self._lock = threading.RLock()

        # 기본 알림 규칙 설정
        self._setup_default_alerts()

    def _setup_default_alerts(self):
        """기본 알림 규칙 설정"""
        default_rules = [
            AlertRule("High Response Time", "response_time_ms > 1000", "warning"),
            AlertRule("Critical Response Time", "response_time_ms > 5000", "critical"),
            AlertRule("High Memory Usage", "memory_usage_mb > 500", "warning"),
            AlertRule("Critical Memory Usage", "memory_usage_mb > 1000", "critical"),
            AlertRule("High CPU Usage", "cpu_usage_percent > 80", "warning"),
            AlertRule("Low Cache Hit Rate", "cache_hit_rate < 50", "warning"),
            AlertRule("High Error Rate", "errors_count > 10", "critical"),
        ]

        self.alert_rules.extend(default_rules)

    def check_alerts(self, metric: PerformanceMetric) -> List[Dict[str, Any]]:
        """알림 규칙 검사"""
        with self._lock:
            metric_dict = asdict(metric)
            current_time = datetime.now()
            new_alerts = []

            for rule in self.alert_rules:
                if not rule.enabled:
                    continue

                try:
                    # 조건 평가
                    condition = rule.condition
                    for key, value in metric_dict.items():
                        if isinstance(value, (int, float)):
                            condition = condition.replace(key, str(value))

                    if eval(condition):
                        # 알림 발생 (중복 방지: 5분 내 동일 알림 무시)
                        if (
                            rule.last_triggered is None
                            or current_time - rule.last_triggered > timedelta(minutes=5)
                        ):
                            alert = {
                                "rule_name": rule.name,
                                "severity": rule.severity,
                                "message": f"{rule.name}: {rule.condition}",
                                "timestamp": current_time.isoformat(),
                                "metric_value": metric_dict,
                            }

                            self.active_alerts.append(alert)
                            new_alerts.append(alert)
                            rule.last_triggered = current_time

                            logger.warning(f"Performance alert: {alert['message']}")

                except Exception as e:
                    logger.error(
                        f"Alert rule evaluation failed: {rule.condition} - {e}"
                    )

            return new_alerts

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """활성 알림 목록 반환"""
        with self._lock:
            return list(self.active_alerts)

    def add_alert_rule(self, rule: AlertRule):
        """알림 규칙 추가"""
        with self._lock:
            self.alert_rules.append(rule)

    def remove_alert_rule(self, rule_name: str) -> bool:
        """알림 규칙 제거"""
        with self._lock:
            for i, rule in enumerate(self.alert_rules):
                if rule.name == rule_name:
                    del self.alert_rules[i]
                    return True
            return False

    def clear_alerts(self):
        """알림 목록 비우기"""
        with self._lock:
            self.active_alerts.clear()
