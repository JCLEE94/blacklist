#!/usr/bin/env python3
"""
Collection Monitoring - Alerts System Module

수집 모니터링 시스템의 경고 및 알림 관리를 담당하는 모듈입니다.
경고 생성, 활성 경고 관리, 로깅 기능을 제공합니다.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional


class CollectionAlertManager:
    """수집기 경고 관리 시스템"""

    def __init__(self):
        """경고 관리자 초기화"""
        self.logger = logging.getLogger(f"{__name__}.alerts")
        self._alerts: List[Dict[str, Any]] = []
        self._max_alerts = 100  # 최대 경고 보관 수
        self._active_alert_duration = 3600  # 1시간 (초)

    def add_alert(self, level: str, message: str, collector_name: Optional[str] = None):
        """경고 추가

        Args:
            level: 경고 수준 (info, warning, error, critical)
            message: 경고 메시지
            collector_name: 관련 수집기 이름 (선택사항)
        """
        alert = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "collector": collector_name,
        }

        self._alerts.append(alert)

        # 경고 목록 크기 제한
        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[-self._max_alerts :]

        # 로그 레벨 결정 및 로깅
        log_level = getattr(logging, level.upper(), logging.INFO)
        log_message = f"Alert: {message}"
        if collector_name:
            log_message += f" (collector: {collector_name})"

        self.logger.log(log_level, log_message)

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """활성 경고 목록 조회

        Returns:
            활성 경고 목록 (최근 1시간 이내)
        """
        current_time = datetime.now()
        active_alerts = []

        for alert in self._alerts:
            try:
                alert_time = datetime.fromisoformat(alert.get("timestamp", ""))
                time_diff = (current_time - alert_time).total_seconds()

                # 설정된 시간 이내의 경고만 활성으로 간주
                if time_diff <= self._active_alert_duration:
                    active_alerts.append(alert)
            except (ValueError, TypeError):
                # 잘못된 타임스탬프 형식의 경우 무시
                continue

        return active_alerts

    def get_alerts_by_level(self, level: str) -> List[Dict[str, Any]]:
        """특정 레벨의 경고 조회

        Args:
            level: 경고 레벨 (info, warning, error, critical)

        Returns:
            해당 레벨의 활성 경고 목록
        """
        active_alerts = self.get_active_alerts()
        return [alert for alert in active_alerts if alert.get("level") == level]

    def get_alerts_by_collector(self, collector_name: str) -> List[Dict[str, Any]]:
        """특정 수집기의 경고 조회

        Args:
            collector_name: 수집기 이름

        Returns:
            해당 수집기의 활성 경고 목록
        """
        active_alerts = self.get_active_alerts()
        return [
            alert for alert in active_alerts if alert.get("collector") == collector_name
        ]

    def get_alert_summary(self) -> Dict[str, Any]:
        """경고 요약 정보 조회

        Returns:
            경고 통계 및 요약 정보
        """
        active_alerts = self.get_active_alerts()

        # 레벨별 카운트
        level_counts = {}
        collector_counts = {}

        for alert in active_alerts:
            level = alert.get("level", "unknown")
            collector = alert.get("collector")

            level_counts[level] = level_counts.get(level, 0) + 1

            if collector:
                collector_counts[collector] = collector_counts.get(collector, 0) + 1

        return {
            "total_active": len(active_alerts),
            "total_stored": len(self._alerts),
            "by_level": level_counts,
            "by_collector": collector_counts,
            "most_recent": active_alerts[-1] if active_alerts else None,
        }

    def clear_alerts(self, collector_name: Optional[str] = None):
        """경고 삭제

        Args:
            collector_name: 특정 수집기의 경고만 삭제 (None이면 모든 경고 삭제)
        """
        if collector_name is None:
            # 모든 경고 삭제
            self._alerts.clear()
            self.logger.info("모든 경고가 삭제되었습니다.")
        else:
            # 특정 수집기의 경고만 삭제
            original_count = len(self._alerts)
            self._alerts = [
                alert
                for alert in self._alerts
                if alert.get("collector") != collector_name
            ]
            deleted_count = original_count - len(self._alerts)
            self.logger.info(f"수집기 '{collector_name}'의 경고 {deleted_count}개가 삭제되었습니다.")

    def clear_old_alerts(self, max_age_hours: int = 24):
        """오래된 경고 정리

        Args:
            max_age_hours: 보관할 최대 시간 (시간 단위)
        """
        if not self._alerts:
            return

        current_time = datetime.now()
        max_age_seconds = max_age_hours * 3600
        original_count = len(self._alerts)

        self._alerts = [
            alert
            for alert in self._alerts
            if self._is_alert_recent(alert, current_time, max_age_seconds)
        ]

        deleted_count = original_count - len(self._alerts)
        if deleted_count > 0:
            self.logger.info(f"{deleted_count}개의 오래된 경고가 정리되었습니다.")

    def _is_alert_recent(
        self, alert: Dict[str, Any], current_time: datetime, max_age_seconds: int
    ) -> bool:
        """경고가 최근 것인지 확인"""
        try:
            alert_time = datetime.fromisoformat(alert.get("timestamp", ""))
            time_diff = (current_time - alert_time).total_seconds()
            return time_diff <= max_age_seconds
        except (ValueError, TypeError):
            # 잘못된 타임스탬프의 경우 삭제 대상으로 간주
            return False

    def set_alert_retention(
        self, max_alerts: int = 100, active_duration_hours: int = 1
    ):
        """경고 보관 정책 설정

        Args:
            max_alerts: 최대 보관할 경고 수
            active_duration_hours: 활성 경고 기준 시간 (시간 단위)
        """
        self._max_alerts = max_alerts
        self._active_alert_duration = active_duration_hours * 3600

        # 현재 저장된 경고 수가 새 제한을 초과하면 정리
        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[-self._max_alerts :]

        self.logger.info(
            f"경고 보관 정책 업데이트: 최대 {max_alerts}개, " f"활성 기간 {active_duration_hours}시간"
        )
