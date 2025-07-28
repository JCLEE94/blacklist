"""
실시간 성능 모니터링 대시보드

이 모듈은 Blacklist 시스템의 성능을 실시간으로 모니터링하고
시각화하는 대시보드 기능을 제공합니다.
"""

import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import threading
from collections import defaultdict, deque
import psutil
import sqlite3

from flask import Blueprint, render_template_string, jsonify, request
from loguru import logger

try:
    from src.utils.performance_cache import get_global_performance_cache
    from src.utils.async_processor import get_global_async_processor
    from src.utils.memory_optimizer import get_global_memory_optimizer
except ImportError:
    # 폴백 임포트
    get_global_performance_cache = lambda: None
    get_global_async_processor = lambda: None
    get_global_memory_optimizer = lambda: None


@dataclass
class PerformanceMetric:
    """성능 메트릭"""
    timestamp: datetime
    response_time_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    active_connections: int
    cache_hit_rate: float
    database_queries: int
    errors_count: int


@dataclass
class AlertRule:
    """알림 규칙"""
    name: str
    condition: str  # "response_time > 1000", "memory_usage > 80"
    severity: str   # "warning", "critical"
    enabled: bool = True
    last_triggered: Optional[datetime] = None


class PerformanceDashboard:
    """실시간 성능 대시보드"""
    
    def __init__(self, max_metrics: int = 1000):
        self.max_metrics = max_metrics
        self.metrics_history = deque(maxlen=max_metrics)
        self.alert_rules = []
        self.active_alerts = []
        
        # 실시간 데이터
        self.current_connections = 0
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        
        # 스레드 안전성
        self._lock = threading.RLock()
        
        # 모니터링 스레드
        self.monitoring_active = False
        self.monitoring_thread = None
        
        # 기본 알림 규칙 설정
        self._setup_default_alerts()
        
        logger.info("Performance dashboard initialized")

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

    def record_request(self, response_time_ms: float, status_code: int = 200):
        """요청 기록"""
        with self._lock:
            self.request_count += 1
            self.total_response_time += response_time_ms
            
            if status_code >= 400:
                self.error_count += 1

    def record_connection(self, delta: int):
        """연결 수 변경 기록"""
        with self._lock:
            self.current_connections = max(0, self.current_connections + delta)

    def collect_metrics(self) -> PerformanceMetric:
        """현재 성능 메트릭 수집"""
        with self._lock:
            # 시스템 메트릭
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # 프로세스 메트릭
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / 1024 / 1024
            
            # 응답 시간 계산
            avg_response_time = (
                self.total_response_time / self.request_count 
                if self.request_count > 0 else 0.0
            )
            
            # 캐시 메트릭
            cache_hit_rate = 0.0
            try:
                cache = get_global_performance_cache()
                if cache:
                    stats = cache.get_stats()
                    cache_hit_rate = stats.get("hit_rate_percent", 0.0)
            except Exception:
                pass
            
            # 데이터베이스 쿼리 수 (추정)
            db_queries = self.request_count * 1.5  # 평균적으로 요청당 1.5개 쿼리
            
            metric = PerformanceMetric(
                timestamp=datetime.now(),
                response_time_ms=avg_response_time,
                memory_usage_mb=process_memory_mb,
                cpu_usage_percent=cpu_percent,
                active_connections=self.current_connections,
                cache_hit_rate=cache_hit_rate,
                database_queries=int(db_queries),
                errors_count=self.error_count
            )
            
            # 메트릭 히스토리 저장
            self.metrics_history.append(metric)
            
            # 알림 검사
            self._check_alerts(metric)
            
            return metric

    def _check_alerts(self, metric: PerformanceMetric):
        """알림 규칙 검사"""
        metric_dict = asdict(metric)
        current_time = datetime.now()
        
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
                    if (rule.last_triggered is None or 
                        current_time - rule.last_triggered > timedelta(minutes=5)):
                        
                        alert = {
                            "rule_name": rule.name,
                            "severity": rule.severity,
                            "message": f"{rule.name}: {rule.condition}",
                            "timestamp": current_time.isoformat(),
                            "metric_value": metric_dict
                        }
                        
                        self.active_alerts.append(alert)
                        rule.last_triggered = current_time
                        
                        logger.warning(f"Performance alert: {alert['message']}")
                        
                        # 최대 알림 수 제한
                        if len(self.active_alerts) > 100:
                            self.active_alerts = self.active_alerts[-50:]
                
            except Exception as e:
                logger.error(f"Alert rule evaluation failed: {rule.condition} - {e}")

    def get_dashboard_data(self) -> Dict[str, Any]:
        """대시보드 데이터 반환"""
        with self._lock:
            current_metric = self.collect_metrics()
            
            # 히스토리 데이터 (최근 100개)
            recent_metrics = list(self.metrics_history)[-100:]
            
            # 시계열 데이터 준비
            timestamps = [m.timestamp.isoformat() for m in recent_metrics]
            response_times = [m.response_time_ms for m in recent_metrics]
            memory_usage = [m.memory_usage_mb for m in recent_metrics]
            cpu_usage = [m.cpu_usage_percent for m in recent_metrics]
            cache_hit_rates = [m.cache_hit_rate for m in recent_metrics]
            
            # 통계 계산
            if recent_metrics:
                avg_response_time = sum(response_times) / len(response_times)
                max_response_time = max(response_times)
                min_response_time = min(response_times)
                avg_memory_usage = sum(memory_usage) / len(memory_usage)
                avg_cpu_usage = sum(cpu_usage) / len(cpu_usage)
                avg_cache_hit_rate = sum(cache_hit_rates) / len(cache_hit_rates)
            else:
                avg_response_time = max_response_time = min_response_time = 0
                avg_memory_usage = avg_cpu_usage = avg_cache_hit_rate = 0
            
            # 성능 등급 계산
            performance_grade = self._calculate_performance_grade(current_metric)
            
            # 활성 알림 (최근 10개)
            recent_alerts = self.active_alerts[-10:] if self.active_alerts else []
            
            return {
                "current_metrics": asdict(current_metric),
                "statistics": {
                    "avg_response_time_ms": round(avg_response_time, 2),
                    "max_response_time_ms": round(max_response_time, 2),
                    "min_response_time_ms": round(min_response_time, 2),
                    "avg_memory_usage_mb": round(avg_memory_usage, 2),
                    "avg_cpu_usage_percent": round(avg_cpu_usage, 2),
                    "avg_cache_hit_rate": round(avg_cache_hit_rate, 2),
                    "total_requests": self.request_count,
                    "total_errors": self.error_count,
                    "error_rate_percent": round(
                        (self.error_count / self.request_count * 100) 
                        if self.request_count > 0 else 0, 2
                    )
                },
                "time_series": {
                    "timestamps": timestamps,
                    "response_times": response_times,
                    "memory_usage": memory_usage,
                    "cpu_usage": cpu_usage,
                    "cache_hit_rates": cache_hit_rates
                },
                "performance_grade": performance_grade,
                "active_alerts": recent_alerts,
                "system_info": self._get_system_info(),
                "optimization_suggestions": self._get_optimization_suggestions(current_metric)
            }

    def _calculate_performance_grade(self, metric: PerformanceMetric) -> Dict[str, Any]:
        """성능 등급 계산"""
        score = 100
        grade = "A+"
        
        # 응답 시간 점수 (40점)
        if metric.response_time_ms <= 50:
            response_score = 40
        elif metric.response_time_ms <= 200:
            response_score = 35
        elif metric.response_time_ms <= 1000:
            response_score = 25
        elif metric.response_time_ms <= 5000:
            response_score = 10
        else:
            response_score = 0
        
        # 메모리 사용 점수 (25점)
        if metric.memory_usage_mb <= 100:
            memory_score = 25
        elif metric.memory_usage_mb <= 300:
            memory_score = 20
        elif metric.memory_usage_mb <= 500:
            memory_score = 15
        elif metric.memory_usage_mb <= 1000:
            memory_score = 10
        else:
            memory_score = 0
        
        # CPU 사용 점수 (20점)
        if metric.cpu_usage_percent <= 20:
            cpu_score = 20
        elif metric.cpu_usage_percent <= 50:
            cpu_score = 15
        elif metric.cpu_usage_percent <= 80:
            cpu_score = 10
        elif metric.cpu_usage_percent <= 95:
            cpu_score = 5
        else:
            cpu_score = 0
        
        # 캐시 효율성 점수 (15점)
        if metric.cache_hit_rate >= 90:
            cache_score = 15
        elif metric.cache_hit_rate >= 75:
            cache_score = 12
        elif metric.cache_hit_rate >= 50:
            cache_score = 8
        elif metric.cache_hit_rate >= 25:
            cache_score = 4
        else:
            cache_score = 0
        
        total_score = response_score + memory_score + cpu_score + cache_score
        
        # 등급 계산
        if total_score >= 95:
            grade = "A+"
        elif total_score >= 90:
            grade = "A"
        elif total_score >= 85:
            grade = "A-"
        elif total_score >= 80:
            grade = "B+"
        elif total_score >= 75:
            grade = "B"
        elif total_score >= 70:
            grade = "B-"
        elif total_score >= 65:
            grade = "C+"
        elif total_score >= 60:
            grade = "C"
        elif total_score >= 55:
            grade = "C-"
        elif total_score >= 50:
            grade = "D"
        else:
            grade = "F"
        
        return {
            "total_score": total_score,
            "grade": grade,
            "breakdown": {
                "response_time": response_score,
                "memory_usage": memory_score,
                "cpu_usage": cpu_score,
                "cache_efficiency": cache_score
            }
        }

    def _get_system_info(self) -> Dict[str, Any]:
        """시스템 정보 수집"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": round(memory.total / 1024 / 1024 / 1024, 2),
                "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                "disk_free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                "python_version": f"{psutil.version_info}",
                "uptime_seconds": time.time() - psutil.boot_time()
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {}

    def _get_optimization_suggestions(self, metric: PerformanceMetric) -> List[str]:
        """최적화 제안 생성"""
        suggestions = []
        
        if metric.response_time_ms > 1000:
            suggestions.append("🚀 API 응답 시간이 느립니다. 캐싱 전략을 검토하세요.")
        
        if metric.memory_usage_mb > 500:
            suggestions.append("💾 메모리 사용량이 높습니다. 메모리 누수를 확인하세요.")
        
        if metric.cpu_usage_percent > 80:
            suggestions.append("⚡ CPU 사용률이 높습니다. 비동기 처리를 고려하세요.")
        
        if metric.cache_hit_rate < 75:
            suggestions.append("📊 캐시 적중률이 낮습니다. 캐시 TTL 설정을 검토하세요.")
        
        if metric.errors_count > 5:
            suggestions.append("❌ 오류 발생률이 높습니다. 에러 로그를 확인하세요.")
        
        if len(suggestions) == 0:
            suggestions.append("✅ 시스템이 최적 상태로 동작하고 있습니다.")
        
        return suggestions

    def start_monitoring(self, interval: float = 10.0):
        """모니터링 시작"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True,
            name="performance_monitor"
        )
        self.monitoring_thread.start()
        logger.info(f"Performance monitoring started (interval: {interval}s)")

    def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")

    def _monitoring_loop(self, interval: float):
        """모니터링 루프"""
        while self.monitoring_active:
            try:
                self.collect_metrics()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                time.sleep(interval)

    def reset_counters(self):
        """카운터 리셋"""
        with self._lock:
            self.request_count = 0
            self.error_count = 0
            self.total_response_time = 0.0
            self.active_alerts.clear()
            logger.info("Performance counters reset")


# 글로벌 대시보드 인스턴스
_global_dashboard = None

def get_global_dashboard() -> PerformanceDashboard:
    """글로벌 대시보드 인스턴스 반환"""
    global _global_dashboard
    
    if _global_dashboard is None:
        _global_dashboard = PerformanceDashboard()
        _global_dashboard.start_monitoring()
    
    return _global_dashboard


# Flask 블루프린트
dashboard_bp = Blueprint('performance_dashboard', __name__)

@dashboard_bp.route('/performance')
def performance_dashboard():
    """성능 대시보드 페이지"""
    return render_template_string(DASHBOARD_HTML_TEMPLATE)

@dashboard_bp.route('/api/performance/metrics')
def get_performance_metrics():
    """성능 메트릭 API"""
    dashboard = get_global_dashboard()
    data = dashboard.get_dashboard_data()
    return jsonify(data)

@dashboard_bp.route('/api/performance/reset', methods=['POST'])
def reset_performance_counters():
    """성능 카운터 리셋 API"""
    dashboard = get_global_dashboard()
    dashboard.reset_counters()
    return jsonify({"success": True, "message": "Performance counters reset"})


# HTML 템플릿
DASHBOARD_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blacklist System - Performance Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-value { font-size: 2em; font-weight: bold; color: #333; }
        .metric-label { color: #666; margin-top: 5px; }
        .chart-container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .grade { font-size: 3em; font-weight: bold; text-align: center; padding: 20px; }
        .grade.A { color: #4CAF50; }
        .grade.B { color: #FF9800; }
        .grade.C { color: #FF5722; }
        .grade.D, .grade.F { color: #F44336; }
        .alerts { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .alert { padding: 10px; margin: 5px 0; border-radius: 4px; }
        .alert.warning { background: #FFF3CD; border-left: 4px solid #FF9800; }
        .alert.critical { background: #F8D7DA; border-left: 4px solid #F44336; }
        .suggestions { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Blacklist System Performance Dashboard</h1>
            <p>실시간 성능 모니터링 및 최적화 현황</p>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value" id="response-time">-</div>
                <div class="metric-label">평균 응답시간 (ms)</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="memory-usage">-</div>
                <div class="metric-label">메모리 사용량 (MB)</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="cpu-usage">-</div>
                <div class="metric-label">CPU 사용률 (%)</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="cache-hit-rate">-</div>
                <div class="metric-label">캐시 적중률 (%)</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="active-connections">-</div>
                <div class="metric-label">활성 연결 수</div>
            </div>
            <div class="metric-card">
                <div class="grade" id="performance-grade">-</div>
                <div class="metric-label">성능 등급</div>
            </div>
        </div>

        <div class="chart-container">
            <h3>📈 응답시간 트렌드</h3>
            <canvas id="responseTimeChart" width="400" height="100"></canvas>
        </div>

        <div class="chart-container">
            <h3>💾 리소스 사용량</h3>
            <canvas id="resourceChart" width="400" height="100"></canvas>
        </div>

        <div class="alerts">
            <h3>🚨 활성 알림</h3>
            <div id="alerts-container">로딩 중...</div>
        </div>

        <div class="suggestions">
            <h3>💡 최적화 제안</h3>
            <div id="suggestions-container">로딩 중...</div>
        </div>
    </div>

    <script>
        let responseTimeChart, resourceChart;
        
        function initCharts() {
            // 응답시간 차트
            const rtCtx = document.getElementById('responseTimeChart').getContext('2d');
            responseTimeChart = new Chart(rtCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: '응답시간 (ms)',
                        data: [],
                        borderColor: '#4CAF50',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });

            // 리소스 사용량 차트
            const resCtx = document.getElementById('resourceChart').getContext('2d');
            resourceChart = new Chart(resCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: '메모리 (MB)',
                            data: [],
                            borderColor: '#2196F3',
                            tension: 0.1
                        },
                        {
                            label: 'CPU (%)',
                            data: [],
                            borderColor: '#FF9800',
                            tension: 0.1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }

        function updateDashboard() {
            fetch('/api/performance/metrics')
                .then(response => response.json())
                .then(data => {
                    // 메트릭 업데이트
                    document.getElementById('response-time').textContent = 
                        data.statistics.avg_response_time_ms.toFixed(1);
                    document.getElementById('memory-usage').textContent = 
                        data.current_metrics.memory_usage_mb.toFixed(1);
                    document.getElementById('cpu-usage').textContent = 
                        data.current_metrics.cpu_usage_percent.toFixed(1);
                    document.getElementById('cache-hit-rate').textContent = 
                        data.current_metrics.cache_hit_rate.toFixed(1);
                    document.getElementById('active-connections').textContent = 
                        data.current_metrics.active_connections;

                    // 성능 등급
                    const gradeElement = document.getElementById('performance-grade');
                    gradeElement.textContent = data.performance_grade.grade;
                    gradeElement.className = 'grade ' + data.performance_grade.grade.charAt(0);

                    // 차트 업데이트
                    updateCharts(data.time_series);

                    // 알림 업데이트
                    updateAlerts(data.active_alerts);

                    // 제안 업데이트
                    updateSuggestions(data.optimization_suggestions);
                })
                .catch(error => console.error('Error:', error));
        }

        function updateCharts(timeSeries) {
            const labels = timeSeries.timestamps.map(ts => 
                new Date(ts).toLocaleTimeString()
            );

            // 응답시간 차트
            responseTimeChart.data.labels = labels;
            responseTimeChart.data.datasets[0].data = timeSeries.response_times;
            responseTimeChart.update();

            // 리소스 차트
            resourceChart.data.labels = labels;
            resourceChart.data.datasets[0].data = timeSeries.memory_usage;
            resourceChart.data.datasets[1].data = timeSeries.cpu_usage;
            resourceChart.update();
        }

        function updateAlerts(alerts) {
            const container = document.getElementById('alerts-container');
            if (alerts.length === 0) {
                container.innerHTML = '<p>✅ 활성 알림이 없습니다.</p>';
                return;
            }

            container.innerHTML = alerts.map(alert => 
                `<div class="alert ${alert.severity}">
                    <strong>${alert.rule_name}</strong> - ${alert.message}
                    <br><small>${new Date(alert.timestamp).toLocaleString()}</small>
                </div>`
            ).join('');
        }

        function updateSuggestions(suggestions) {
            const container = document.getElementById('suggestions-container');
            container.innerHTML = suggestions.map(suggestion => 
                `<p>${suggestion}</p>`
            ).join('');
        }

        // 초기화
        document.addEventListener('DOMContentLoaded', function() {
            initCharts();
            updateDashboard();
            setInterval(updateDashboard, 5000); // 5초마다 업데이트
        });
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    """성능 대시보드 검증"""
    import sys
    
    dashboard = PerformanceDashboard()
    dashboard.start_monitoring(interval=1.0)
    
    try:
        # 테스트 데이터 생성
        import random
        
        for i in range(10):
            # 가상 요청 기록
            response_time = random.uniform(50, 500)
            status_code = 200 if random.random() > 0.1 else 500
            dashboard.record_request(response_time, status_code)
            
            # 가상 연결 변화
            if random.random() > 0.5:
                dashboard.record_connection(1)
            else:
                dashboard.record_connection(-1)
            
            time.sleep(0.5)
        
        # 대시보드 데이터 확인
        data = dashboard.get_dashboard_data()
        
        print("✅ 성능 대시보드 검증 완료")
        print(f"📊 현재 메트릭: {data['current_metrics']}")
        print(f"🎯 성능 등급: {data['performance_grade']['grade']} ({data['performance_grade']['total_score']}점)")
        print(f"💡 최적화 제안: {len(data['optimization_suggestions'])}개")
        
        dashboard.stop_monitoring()
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)