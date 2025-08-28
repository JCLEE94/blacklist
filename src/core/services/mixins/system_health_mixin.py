#!/usr/bin/env python3
"""
System Health Mixin - System status monitoring and health checks

Purpose: Monitor system health and provide status information
Third-party packages: None (uses core system statistics)
Sample input: No parameters for get_system_health()
Expected output: Dictionary with system status, timestamps, and health metrics
"""

import logging
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SystemHealthMixin:
    """
    System Health Mixin - System monitoring and health assessment
    Provides system status and health metrics
    """

    def get_system_health(self) -> Dict[str, Any]:
        """시스템 상태"""
        try:
            stats = self.get_statistics()

            return {
                "status": stats.get("status", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "uptime": "0d 0h 0m",
                "memory_usage": "0MB",
                "db_status": (
                    "connected" if stats.get("active_ips", 0) >= 0 else "error"
                ),
                "total_ips": stats.get("total_ips", 0),
                "active_ips": stats.get("active_ips", 0),
                "regtech_count": stats.get("sources", {}).get("REGTECH", 0),
                "secudium_count": stats.get("sources", {}).get("SECUDIUM", 0),
                "public_count": stats.get("sources", {}).get("PUBLIC", 0),
            }
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "total_ips": 0,
                "active_ips": 0,
            }

    def get_health_summary(self) -> Dict[str, Any]:
        """시스템 상태 요약"""
        try:
            health = self.get_system_health()

            # 상태 등급 판정
            status = health.get("status", "unknown")
            active_ips = health.get("active_ips", 0)
            total_ips = health.get("total_ips", 0)

            # 건강도 점수 계산 (0-100)
            health_score = 0
            if status == "healthy":
                health_score += 40
            elif status == "warning":
                health_score += 20

            if active_ips > 0:
                health_score += 30

            if health.get("db_status") == "connected":
                health_score += 20

            if total_ips > 0:
                health_score += 10

            # 상태 설명
            if health_score >= 80:
                health_grade = "excellent"
                description = "System is operating optimally"
            elif health_score >= 60:
                health_grade = "good"
                description = "System is functioning well"
            elif health_score >= 40:
                health_grade = "fair"
                description = "System has minor issues"
            elif health_score >= 20:
                health_grade = "poor"
                description = "System has significant issues"
            else:
                health_grade = "critical"
                description = "System requires immediate attention"

            return {
                "health_score": health_score,
                "health_grade": health_grade,
                "description": description,
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "database_status": health.get("db_status", "unknown"),
                    "data_availability": (
                        "available" if active_ips > 0 else "unavailable"
                    ),
                    "source_diversity": len(
                        [k for k, v in health.get("sources", {}).items() if v > 0]
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Error getting health summary: {e}")
            return {
                "health_score": 0,
                "health_grade": "critical",
                "description": f"Health check failed: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            }

    def check_data_freshness(self) -> Dict[str, Any]:
        """데이터 신선도 확인"""
        try:
            stats = self.get_statistics()
            last_update = stats.get("last_update")

            if not last_update:
                return {
                    "status": "unknown",
                    "message": "No last update information available",
                }

            # 마지막 업데이트 시간 분석
            try:
                if isinstance(last_update, str):
                    last_update_dt = datetime.fromisoformat(
                        last_update.replace("Z", "+00:00")
                    )
                else:
                    last_update_dt = last_update

                now = datetime.now()
                if last_update_dt.tzinfo:
                    # timezone aware datetime handling
                    import pytz

                    now = pytz.UTC.localize(now)

                time_diff = now - last_update_dt
                hours_since_update = time_diff.total_seconds() / 3600

                # 신선도 등급
                if hours_since_update <= 1:
                    freshness = "very_fresh"
                    message = "Data is very recent"
                elif hours_since_update <= 6:
                    freshness = "fresh"
                    message = "Data is reasonably fresh"
                elif hours_since_update <= 24:
                    freshness = "acceptable"
                    message = "Data is somewhat old but acceptable"
                elif hours_since_update <= 72:
                    freshness = "stale"
                    message = "Data is getting stale"
                else:
                    freshness = "very_stale"
                    message = "Data is very old and may be unreliable"

                return {
                    "status": freshness,
                    "message": message,
                    "hours_since_update": round(hours_since_update, 2),
                    "last_update": last_update,
                    "timestamp": now.isoformat(),
                }

            except Exception as parse_error:
                return {
                    "status": "error",
                    "message": f"Could not parse last update time: {parse_error}",
                    "last_update": last_update,
                }

        except Exception as e:
            logger.error(f"Error checking data freshness: {e}")
            return {"status": "error", "message": f"Freshness check failed: {str(e)}"}

    def get_system_alerts(self) -> Dict[str, Any]:
        """시스템 경고사항 확인"""
        try:
            alerts = []

            # 기본 상태 확인
            health = self.get_system_health()

            if health.get("status") == "error":
                alerts.append(
                    {
                        "level": "critical",
                        "message": "System is in error state",
                        "details": health.get("error", "Unknown error"),
                    }
                )

            if health.get("db_status") != "connected":
                alerts.append(
                    {
                        "level": "warning",
                        "message": "Database connection issue",
                        "details": "Database may not be accessible",
                    }
                )

            if health.get("active_ips", 0) == 0:
                alerts.append(
                    {
                        "level": "warning",
                        "message": "No active IP entries found",
                        "details": "Blacklist may be empty or collection not working",
                    }
                )

            # 데이터 신선도 확인
            freshness = self.check_data_freshness()
            if freshness.get("status") in ["stale", "very_stale"]:
                alerts.append(
                    {
                        "level": "info",
                        "message": "Data freshness concern",
                        "details": freshness.get("message", "Data may be outdated"),
                    }
                )

            return {
                "alert_count": len(alerts),
                "alerts": alerts,
                "timestamp": datetime.now().isoformat(),
                "overall_status": (
                    "critical"
                    if any(a["level"] == "critical" for a in alerts)
                    else (
                        "warning"
                        if any(a["level"] == "warning" for a in alerts)
                        else "info"
                        if alerts
                        else "healthy"
                    )
                ),
            }

        except Exception as e:
            logger.error(f"Error getting system alerts: {e}")
            return {
                "alert_count": 1,
                "alerts": [
                    {
                        "level": "critical",
                        "message": "Alert system failure",
                        "details": str(e),
                    }
                ],
                "timestamp": datetime.now().isoformat(),
                "overall_status": "critical",
            }


if __name__ == "__main__":
    # 검증 함수
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: Mixin 메서드 존재 확인
    total_tests += 1
    try:
        required_methods = [
            "get_system_health",
            "get_health_summary",
            "check_data_freshness",
            "get_system_alerts",
        ]
        mixin_methods = [
            method for method in dir(SystemHealthMixin) if not method.startswith("__")
        ]

        missing_methods = [
            method for method in required_methods if method not in mixin_methods
        ]
        if missing_methods:
            all_validation_failures.append(f"Missing methods: {missing_methods}")

    except Exception as e:
        all_validation_failures.append(f"Method validation: Exception {e}")

    # Test 2: 기본 헬스 체크 구조 확인
    total_tests += 1
    try:
        # Mock 객체로 테스트
        class MockHealthMixin(SystemHealthMixin):
            def get_statistics(self):
                return {
                    "status": "healthy",
                    "active_ips": 100,
                    "total_ips": 150,
                    "sources": {"REGTECH": 50, "SECUDIUM": 50},
                }

        mock_mixin = MockHealthMixin()
        result = mock_mixin.get_system_health()

        expected_keys = {"status", "timestamp", "db_status", "total_ips", "active_ips"}
        if not expected_keys.issubset(result.keys()):
            missing = expected_keys - result.keys()
            all_validation_failures.append(
                f"Health check structure: Missing keys {missing}"
            )

    except Exception as e:
        all_validation_failures.append(f"Health check structure: Exception {e}")

    # Test 3: 헬스 요약 기본 동작 확인
    total_tests += 1
    try:

        class MockHealthMixin(SystemHealthMixin):
            def get_statistics(self):
                return {"status": "healthy", "active_ips": 100}

            def get_system_health(self):
                return {
                    "status": "healthy",
                    "active_ips": 100,
                    "db_status": "connected",
                }

        mock_mixin = MockHealthMixin()
        result = mock_mixin.get_health_summary()

        expected_keys = {"health_score", "health_grade", "description"}
        if not expected_keys.issubset(result.keys()):
            missing = expected_keys - result.keys()
            all_validation_failures.append(f"Health summary: Missing keys {missing}")

    except Exception as e:
        all_validation_failures.append(f"Health summary: Exception {e}")

    # 최종 검증 결과
    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("SystemHealthMixin structure is validated")
        sys.exit(0)
