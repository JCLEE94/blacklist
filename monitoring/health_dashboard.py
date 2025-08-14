"""
헬스체크 대시보드 (완전 리팩토링됨)

시스템 상태를 실시간으로 모니터링하고 시각화하는 웹 대시보드입니다.
간소화되고 모듈화된 구조로 재작성되었습니다.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from flask import Blueprint, render_template_string, jsonify, request
from dataclasses import asdict

# 모듈화된 컴포넌트 import
try:
    from .health_models import HealthMetric, ServiceStatus, convert_health_status
    from .metrics_collector import SystemMetricsCollector, ApplicationMetricsCollector
except ImportError:
    # 상대 import 실패시 절대 import 시도
    from monitoring.health_models import HealthMetric, ServiceStatus, convert_health_status
    from monitoring.metrics_collector import SystemMetricsCollector, ApplicationMetricsCollector

logger = logging.getLogger(__name__)


class HealthDashboard:
    """헬스체크 대시보드 클래스 (완전 리팩토링됨)"""

    def __init__(self, blacklist_manager=None):
        self.metrics_history = {}
        self.services = {}
        self.alerts = []
        self.start_time = datetime.now()

        # 메트릭 컬렉터 초기화
        self.system_collector = SystemMetricsCollector()
        self.app_collector = ApplicationMetricsCollector(blacklist_manager)

    def collect_all_metrics(self) -> List[HealthMetric]:
        """모든 메트릭 수집 (시스템 + 애플리케이션)"""
        metrics = []

        try:
            # 시스템 메트릭
            metrics.extend(self.system_collector.collect_system_metrics())

            # 애플리케이션 메트릭
            metrics.extend(self.app_collector.collect_application_metrics())

            # 히스토리 업데이트
            self.update_metrics_history(metrics)

        except Exception as e:
            logger.error(f"메트릭 수집 실패: {e}")

        return metrics

    def update_metrics_history(self, metrics: List[HealthMetric]):
        """메트릭 히스토리 업데이트 (최근 24시간만 보관)"""
        cutoff_time = datetime.now() - timedelta(hours=24)

        for metric in metrics:
            if metric.name not in self.metrics_history:
                self.metrics_history[metric.name] = []

            # 새 메트릭 추가
            self.metrics_history[metric.name].append(asdict(metric))

            # 오래된 데이터 제거
            self.metrics_history[metric.name] = [
                m for m in self.metrics_history[metric.name]
                if datetime.fromisoformat(m['timestamp'].replace('T', ' ')) > cutoff_time
            ]

    def get_dashboard_data(self) -> Dict[str, Any]:
        """대시보드 표시용 데이터 반환"""
        metrics = self.collect_all_metrics()

        # 메트릭을 상태별로 그룹화
        healthy_count = sum(1 for m in metrics if m.status == "healthy")
        warning_count = sum(1 for m in metrics if m.status == "warning")
        critical_count = sum(1 for m in metrics if m.status == "critical")

        # 시스템 업타임
        uptime = datetime.now() - self.start_time
        uptime_str = str(uptime).split('.')[0]  # 초 단위 제거

        return {
            "timestamp": datetime.now().isoformat(),
            "uptime": uptime_str,
            "metrics": [asdict(m) for m in metrics],
            "summary": {
                "total": len(metrics),
                "healthy": healthy_count,
                "warning": warning_count,
                "critical": critical_count,
                "overall_status": self._get_overall_status(critical_count, warning_count)
            },
            "services": list(self.services.values()),
            "alerts": self.alerts[-10:]  # 최근 10개 알림만
        }

    def _get_overall_status(
            self,
            critical_count: int,
            warning_count: int) -> str:
        """전체 시스템 상태 결정"""
        if critical_count > 0:
            return "critical"
        elif warning_count > 0:
            return "warning"
        else:
            return "healthy"


# 전역 대시보드 인스턴스
_dashboard_instance = None


def get_dashboard(blacklist_manager=None) -> HealthDashboard:
    """대시보드 싱글톤 인스턴스 반환"""
    global _dashboard_instance

    if _dashboard_instance is None:
        _dashboard_instance = HealthDashboard(blacklist_manager)

    return _dashboard_instance


# Flask 블루프린트
dashboard_bp = Blueprint('health_dashboard', __name__)


@dashboard_bp.route('/monitoring/dashboard')
def dashboard_page():
    """대시보드 HTML 페이지"""
    dashboard = get_dashboard()
    data = dashboard.get_dashboard_data()

    # 간소화된 HTML 템플릿 (기본 부트스트랩 사용)
    html_template = '''
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Blacklist Health Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <meta http-equiv="refresh" content="30">
    </head>
    <body class="bg-light">
        <div class="container-fluid py-4">
            <h1 class="text-center mb-4">🏥 System Health Dashboard</h1>

            <!-- 요약 상태 -->
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="card text-center h-100 border-success">
                        <div class="card-body">
                            <h5 class="card-title text-success">✅ Healthy</h5>
                            <h2 class="text-success">{{ data.summary.healthy }}</h2>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center h-100 border-warning">
                        <div class="card-body">
                            <h5 class="card-title text-warning">⚠️ Warning</h5>
                            <h2 class="text-warning">{{ data.summary.warning }}</h2>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center h-100 border-danger">
                        <div class="card-body">
                            <h5 class="card-title text-danger">🚨 Critical</h5>
                            <h2 class="text-danger">{{ data.summary.critical }}</h2>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center h-100 border-info">
                        <div class="card-body">
                            <h5 class="card-title text-info">⏱️ Uptime</h5>
                            <p class="text-info">{{ data.uptime }}</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 메트릭 그리드 -->
            <div class="row">
                {% for metric in data.metrics %}
                <div class="col-md-4 col-lg-3 mb-3">
                    <div class="card h-100 border-{% if metric.status == 'healthy' %}success{% elif metric.status == 'warning' %}warning{% else %}danger{% endif %}">
                        <div class="card-body">
                            <h6 class="card-title">{{ metric.description or metric.name }}</h6>
                            <h4 class="text-{% if metric.status == 'healthy' %}success{% elif metric.status == 'warning' %}warning{% else %}danger{% endif %}">
                                {{ metric.value }}{% if metric.unit %} {{ metric.unit }}{% endif %}
                            </h4>
                            <small class="text-muted">{{ metric.timestamp[:19] }}</small>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>

            <div class="text-center mt-4">
                <small class="text-muted">Last Updated: {{ data.timestamp[:19] }} | Auto-refresh every 30s</small>
            </div>
        </div>
    </body>
    </html>
    '''

    return render_template_string(html_template, data=data)


@dashboard_bp.route('/api/health/dashboard')
def health_api():
    """대시보드 JSON API"""
    dashboard = get_dashboard()
    return jsonify(dashboard.get_dashboard_data())


@dashboard_bp.route('/api/health/metrics/<metric_name>/history')
def metric_history(metric_name):
    """특정 메트릭의 히스토리 조회"""
    dashboard = get_dashboard()
    history = dashboard.metrics_history.get(metric_name, [])
    return jsonify({
        "metric_name": metric_name,
        "history": history[-100:]  # 최근 100개 포인트
    })
