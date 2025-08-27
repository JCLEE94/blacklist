"""
자율 모니터링 시스템 API 라우트

실시간 모니터링 상태, 알림, 메트릭 히스토리, 자가 치유 제어를 위한
RESTful API 엔드포인트를 제공합니다.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

try:
    from src.core.automation.autonomous_monitor import (
        AlertLevel,
        SystemMetrics,
        get_autonomous_monitor,
    )
    from src.utils.decorators.auth import require_api_key
    from src.utils.decorators.cache import cached
    from src.utils.decorators.validation import validate_json_input
    from src.utils.structured_logging import get_logger
except ImportError:
    # Fallback imports
    def get_autonomous_monitor():
        return None

    def require_api_key(f):
        return f

    def validate_json_input(*args):
        def decorator(f):
            return f

        return decorator

    def cached(*args, **kwargs):
        def decorator(f):
            return f

        return decorator

    class AlertLevel:
        INFO = "info"
        WARNING = "warning"
        CRITICAL = "critical"
        EMERGENCY = "emergency"

    class SystemMetrics:
        GIT_CHANGES = "git_changes"
        TEST_COVERAGE = "test_coverage"
        API_PERFORMANCE = "api_performance"

    def get_logger(name):
        return logging.getLogger(name)


logger = get_logger(__name__)

# Blueprint 생성
autonomous_monitoring_bp = Blueprint(
    "autonomous_monitoring", __name__, url_prefix="/api/monitoring/autonomous"
)


@autonomous_monitoring_bp.route("/status", methods=["GET"])
@cached(ttl=10)
def get_monitoring_status():
    """모니터링 시스템 현재 상태 조회"""
    try:
        monitor = get_autonomous_monitor()
        if not monitor:
            return (
                jsonify(
                    {
                        "error": "Monitoring system not available",
                        "status": "unavailable",
                    }
                ),
                503,
            )

        status = monitor.get_current_status()

        return jsonify(
            {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "monitoring_active": status["is_running"],
                    "auto_healing_enabled": status["auto_healing_enabled"],
                    "monitoring_interval_seconds": status["monitoring_interval"],
                    "recent_alerts": status["recent_alerts_count"],
                    "latest_metrics": status["latest_snapshot"],
                },
                "message": "모니터링 상태 조회 완료",
            }
        )

    except Exception as e:
        logger.error(f"모니터링 상태 조회 오류: {e}")
        return (
            jsonify({"error": "Failed to get monitoring status", "details": str(e)}),
            500,
        )


@autonomous_monitoring_bp.route("/metrics/current", methods=["GET"])
@cached(ttl=30)
def get_current_metrics():
    """현재 시스템 메트릭 조회"""
    try:
        monitor = get_autonomous_monitor()
        if not monitor or not monitor.metrics_history:
            return (
                jsonify({"error": "No metrics available", "status": "unavailable"}),
                404,
            )

        latest_snapshot = monitor.metrics_history[-1]

        return jsonify(
            {
                "status": "success",
                "timestamp": latest_snapshot.timestamp.isoformat(),
                "data": {
                    "git_changes": {
                        "count": latest_snapshot.git_changes_count,
                        "threshold": monitor.thresholds[
                            SystemMetrics.GIT_CHANGES
                        ].warning,
                        "status": (
                            "warning"
                            if latest_snapshot.git_changes_count > 100
                            else "normal"
                        ),
                    },
                    "test_coverage": {
                        "percentage": latest_snapshot.test_coverage,
                        "target": 95.0,
                        "status": (
                            "critical"
                            if latest_snapshot.test_coverage < 30
                            else "normal"
                        ),
                    },
                    "api_performance": {
                        "response_time_ms": latest_snapshot.api_response_time,
                        "baseline": 65.0,
                        "status": (
                            "warning"
                            if latest_snapshot.api_response_time > 100
                            else "normal"
                        ),
                    },
                    "system_resources": {
                        "memory_usage": latest_snapshot.memory_usage,
                        "cpu_usage": latest_snapshot.cpu_usage,
                        "status": (
                            "warning"
                            if max(
                                latest_snapshot.memory_usage, latest_snapshot.cpu_usage
                            )
                            > 70
                            else "normal"
                        ),
                    },
                    "file_violations": {
                        "count": latest_snapshot.file_violations_count,
                        "max_allowed": 5,
                        "status": (
                            "warning"
                            if latest_snapshot.file_violations_count > 5
                            else "normal"
                        ),
                    },
                    "deployment": {
                        "health": latest_snapshot.deployment_health,
                        "status": (
                            "healthy"
                            if latest_snapshot.deployment_health == "healthy"
                            else "degraded"
                        ),
                    },
                },
                "message": "현재 메트릭 조회 완료",
            }
        )

    except Exception as e:
        logger.error(f"현재 메트릭 조회 오류: {e}")
        return (
            jsonify({"error": "Failed to get current metrics", "details": str(e)}),
            500,
        )


@autonomous_monitoring_bp.route("/metrics/history", methods=["GET"])
def get_metrics_history():
    """메트릭 히스토리 조회 (시계열 데이터)"""
    try:
        monitor = get_autonomous_monitor()
        if not monitor or not monitor.metrics_history:
            return (
                jsonify(
                    {"error": "No metrics history available", "status": "unavailable"}
                ),
                404,
            )

        # 쿼리 파라미터 처리
        hours = request.args.get("hours", 24, type=int)
        limit = request.args.get("limit", 100, type=int)

        # 시간 범위 필터링
        cutoff_time = datetime.now() - timedelta(hours=hours)
        filtered_history = [
            snapshot
            for snapshot in monitor.metrics_history
            if snapshot.timestamp > cutoff_time
        ]

        # 제한 적용
        if len(filtered_history) > limit:
            filtered_history = filtered_history[-limit:]

        # 응답 데이터 구성
        history_data = []
        for snapshot in filtered_history:
            history_data.append(
                {
                    "timestamp": snapshot.timestamp.isoformat(),
                    "git_changes": snapshot.git_changes_count,
                    "test_coverage": snapshot.test_coverage,
                    "api_response_time": snapshot.api_response_time,
                    "memory_usage": snapshot.memory_usage,
                    "cpu_usage": snapshot.cpu_usage,
                    "file_violations": snapshot.file_violations_count,
                    "deployment_health": snapshot.deployment_health,
                    "alerts_count": snapshot.alerts_count,
                }
            )

        return jsonify(
            {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "history": history_data,
                    "total_records": len(history_data),
                    "time_range_hours": hours,
                    "oldest_record": (
                        filtered_history[0].timestamp.isoformat()
                        if filtered_history
                        else None
                    ),
                    "newest_record": (
                        filtered_history[-1].timestamp.isoformat()
                        if filtered_history
                        else None
                    ),
                },
                "message": f"메트릭 히스토리 조회 완료 ({len(history_data)}개 레코드)",
            }
        )

    except Exception as e:
        logger.error(f"메트릭 히스토리 조회 오류: {e}")
        return (
            jsonify({"error": "Failed to get metrics history", "details": str(e)}),
            500,
        )


@autonomous_monitoring_bp.route("/alerts/active", methods=["GET"])
@cached(ttl=15)
def get_active_alerts():
    """활성 알림 목록 조회"""
    try:
        monitor = get_autonomous_monitor()
        if not monitor:
            return (
                jsonify(
                    {
                        "error": "Monitoring system not available",
                        "status": "unavailable",
                    }
                ),
                503,
            )

        # 최근 1시간 이내의 알림만 조회
        cutoff_time = datetime.now() - timedelta(hours=1)
        active_alerts = [
            alert for alert in monitor.alerts_history if alert.timestamp > cutoff_time
        ]

        # 레벨별 분류
        alerts_by_level = {"emergency": [], "critical": [], "warning": [], "info": []}

        for alert in active_alerts:
            alert_data = {
                "timestamp": alert.timestamp.isoformat(),
                "metric_type": alert.metric_type.value,
                "current_value": alert.current_value,
                "threshold": alert.threshold,
                "message": alert.message,
                "auto_fix_attempted": alert.auto_fix_attempted,
                "auto_fix_success": alert.auto_fix_success,
            }
            alerts_by_level[alert.level.value].append(alert_data)

        # 통계 계산
        total_alerts = len(active_alerts)
        auto_fixed = len([a for a in active_alerts if a.auto_fix_success])

        return jsonify(
            {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "alerts_by_level": alerts_by_level,
                    "statistics": {
                        "total_alerts": total_alerts,
                        "auto_fixed_count": auto_fixed,
                        "auto_fix_rate": (
                            (auto_fixed / total_alerts * 100) if total_alerts > 0 else 0
                        ),
                        "emergency_count": len(alerts_by_level["emergency"]),
                        "critical_count": len(alerts_by_level["critical"]),
                        "warning_count": len(alerts_by_level["warning"]),
                    },
                },
                "message": f"활성 알림 조회 완료 ({total_alerts}개)",
            }
        )

    except Exception as e:
        logger.error(f"활성 알림 조회 오류: {e}")
        return jsonify({"error": "Failed to get active alerts", "details": str(e)}), 500


@autonomous_monitoring_bp.route("/dashboard", methods=["GET"])
@cached(ttl=30)
def get_monitoring_dashboard():
    """실시간 모니터링 대시보드 데이터"""
    try:
        monitor = get_autonomous_monitor()
        if not monitor or not monitor.metrics_history:
            return (
                jsonify(
                    {"error": "Dashboard data not available", "status": "unavailable"}
                ),
                404,
            )

        latest_snapshot = monitor.metrics_history[-1]

        # 최근 1시간 알림
        cutoff_time = datetime.now() - timedelta(hours=1)
        recent_alerts = [
            alert for alert in monitor.alerts_history if alert.timestamp > cutoff_time
        ]

        # 트렌드 계산 (최근 5개 데이터포인트)
        recent_metrics = (
            monitor.metrics_history[-5:]
            if len(monitor.metrics_history) >= 5
            else monitor.metrics_history
        )

        trends = {}
        if len(recent_metrics) >= 2:
            trends = {
                "git_changes": monitor._calculate_trend(
                    [m.git_changes_count for m in recent_metrics]
                ),
                "test_coverage": monitor._calculate_trend(
                    [m.test_coverage for m in recent_metrics]
                ),
                "api_performance": monitor._calculate_trend(
                    [m.api_response_time for m in recent_metrics]
                ),
                "memory_usage": monitor._calculate_trend(
                    [m.memory_usage for m in recent_metrics]
                ),
            }

        # 자동화 진행률
        automation_progress = monitor._calculate_automation_progress(latest_snapshot)

        return jsonify(
            {
                "status": "success",
                "timestamp": latest_snapshot.timestamp.isoformat(),
                "data": {
                    "current_metrics": {
                        "git_changes": latest_snapshot.git_changes_count,
                        "test_coverage": latest_snapshot.test_coverage,
                        "api_response_time": latest_snapshot.api_response_time,
                        "memory_usage": latest_snapshot.memory_usage,
                        "cpu_usage": latest_snapshot.cpu_usage,
                        "file_violations": latest_snapshot.file_violations_count,
                        "deployment_health": latest_snapshot.deployment_health,
                    },
                    "trends": trends,
                    "alert_summary": {
                        "total_recent": len(recent_alerts),
                        "emergency": len(
                            [a for a in recent_alerts if a.level.value == "emergency"]
                        ),
                        "critical": len(
                            [a for a in recent_alerts if a.level.value == "critical"]
                        ),
                        "warning": len(
                            [a for a in recent_alerts if a.level.value == "warning"]
                        ),
                    },
                    "automation_status": {
                        "progress_percentage": automation_progress,
                        "auto_healing_enabled": monitor.auto_healing_enabled,
                        "monitoring_active": monitor.is_running,
                        "next_actions": monitor._suggest_next_actions(
                            latest_snapshot, recent_alerts
                        ),
                    },
                    "system_health": {
                        "overall_status": monitor._calculate_overall_risk(),
                        "uptime_status": "running" if monitor.is_running else "stopped",
                        "last_check": latest_snapshot.timestamp.isoformat(),
                    },
                },
                "message": "대시보드 데이터 조회 완료",
            }
        )

    except Exception as e:
        logger.error(f"대시보드 데이터 조회 오류: {e}")
        return (
            jsonify({"error": "Failed to get dashboard data", "details": str(e)}),
            500,
        )


@autonomous_monitoring_bp.route("/control/start", methods=["POST"])
@require_api_key
def start_monitoring():
    """모니터링 시작"""
    try:
        monitor = get_autonomous_monitor()
        if not monitor:
            return jsonify({"error": "Monitoring system not available"}), 503

        if monitor.is_running:
            return jsonify(
                {
                    "status": "already_running",
                    "message": "모니터링이 이미 실행 중입니다.",
                }
            )

        # 비동기적으로 모니터링 시작
        import threading

        def run_monitoring():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(monitor.start_monitoring())

        monitoring_thread = threading.Thread(target=run_monitoring, daemon=True)
        monitoring_thread.start()

        return jsonify(
            {
                "status": "success",
                "message": "자율 모니터링 시스템이 시작되었습니다.",
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"모니터링 시작 오류: {e}")
        return jsonify({"error": "Failed to start monitoring", "details": str(e)}), 500


@autonomous_monitoring_bp.route("/control/stop", methods=["POST"])
@require_api_key
def stop_monitoring():
    """모니터링 중지"""
    try:
        monitor = get_autonomous_monitor()
        if not monitor:
            return jsonify({"error": "Monitoring system not available"}), 503

        monitor.stop_monitoring()

        return jsonify(
            {
                "status": "success",
                "message": "자율 모니터링 시스템이 중지되었습니다.",
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"모니터링 중지 오류: {e}")
        return jsonify({"error": "Failed to stop monitoring", "details": str(e)}), 500


@autonomous_monitoring_bp.route("/control/auto-healing/enable", methods=["POST"])
@require_api_key
def enable_auto_healing():
    """자가 치유 활성화"""
    try:
        monitor = get_autonomous_monitor()
        if not monitor:
            return jsonify({"error": "Monitoring system not available"}), 503

        monitor.enable_auto_healing()

        return jsonify(
            {
                "status": "success",
                "message": "자가 치유 시스템이 활성화되었습니다.",
                "auto_healing_enabled": True,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"자가 치유 활성화 오류: {e}")
        return (
            jsonify({"error": "Failed to enable auto-healing", "details": str(e)}),
            500,
        )


@autonomous_monitoring_bp.route("/control/auto-healing/disable", methods=["POST"])
@require_api_key
def disable_auto_healing():
    """자가 치유 비활성화"""
    try:
        monitor = get_autonomous_monitor()
        if not monitor:
            return jsonify({"error": "Monitoring system not available"}), 503

        monitor.disable_auto_healing()

        return jsonify(
            {
                "status": "success",
                "message": "자가 치유 시스템이 비활성화되었습니다.",
                "auto_healing_enabled": False,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"자가 치유 비활성화 오류: {e}")
        return (
            jsonify({"error": "Failed to disable auto-healing", "details": str(e)}),
            500,
        )


@autonomous_monitoring_bp.route("/thresholds", methods=["GET"])
@cached(ttl=300)  # 5분 캐시
def get_monitoring_thresholds():
    """모니터링 임계값 설정 조회"""
    try:
        monitor = get_autonomous_monitor()
        if not monitor:
            return jsonify({"error": "Monitoring system not available"}), 503

        thresholds_data = {}
        for metric, threshold in monitor.thresholds.items():
            thresholds_data[metric.value] = {
                "warning": threshold.warning,
                "critical": threshold.critical,
                "emergency": threshold.emergency,
                "unit": threshold.unit,
            }

        return jsonify(
            {
                "status": "success",
                "data": {
                    "thresholds": thresholds_data,
                    "baseline_metrics": monitor.baseline_metrics,
                },
                "message": "임계값 설정 조회 완료",
            }
        )

    except Exception as e:
        logger.error(f"임계값 조회 오류: {e}")
        return jsonify({"error": "Failed to get thresholds", "details": str(e)}), 500


@autonomous_monitoring_bp.route("/health", methods=["GET"])
def monitoring_health_check():
    """모니터링 시스템 헬스체크"""
    try:
        monitor = get_autonomous_monitor()
        if not monitor:
            return (
                jsonify(
                    {
                        "status": "unhealthy",
                        "message": "Monitoring system not available",
                    }
                ),
                503,
            )

        status = monitor.get_current_status()

        health_status = {
            "status": "healthy" if status["is_running"] else "stopped",
            "monitoring_active": status["is_running"],
            "auto_healing_enabled": status["auto_healing_enabled"],
            "recent_alerts": status["recent_alerts_count"],
            "last_update": (
                status["latest_snapshot"]["timestamp"]
                if status["latest_snapshot"]
                else None
            ),
            "timestamp": datetime.now().isoformat(),
        }

        return jsonify(health_status)

    except Exception as e:
        logger.error(f"모니터링 헬스체크 오류: {e}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


# Blueprint 등록 함수
def register_autonomous_monitoring_routes(app):
    """Flask 앱에 자율 모니터링 라우트 등록"""
    app.register_blueprint(autonomous_monitoring_bp)
    logger.info("자율 모니터링 API 라우트가 등록되었습니다.")


if __name__ == "__main__":
    # 테스트용 실행
    from flask import Flask

    app = Flask(__name__)
    register_autonomous_monitoring_routes(app)
    app.run(debug=False, port=5001)  # Security: Never use debug=True in production
