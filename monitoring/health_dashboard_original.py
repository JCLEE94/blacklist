"""
헬스체크 대시보드 (리팩토링됨)

시스템 상태를 실시간으로 모니터링하고 시각화하는 웹 대시보드입니다.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from flask import Blueprint, render_template_string, jsonify, request
from dataclasses import asdict

# 모듈화된 컴포넌트 import
from .health_models import HealthMetric, ServiceStatus, convert_health_status
from .metrics_collector import SystemMetricsCollector, ApplicationMetricsCollector

logger = logging.getLogger(__name__)


class HealthDashboard:
    """헬스체크 대시보드 클래스 (리팩토링됨)"""
    
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
        
        # 시스템 메트릭
        metrics.extend(self.system_collector.collect_system_metrics())
        
        # 애플리케이션 메트릭
        metrics.extend(self.app_collector.collect_application_metrics())
        
        # 히스토리 업데이트
        self.update_metrics_history(metrics)
        
        return metrics
        now = datetime.now()
        
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics.append(HealthMetric(
                name="cpu_usage",
                value=cpu_percent,
                status=self._get_status(cpu_percent, 70, 90),
                timestamp=now,
                unit="%",
                threshold_warning=70,
                threshold_critical=90,
                description="CPU 사용률"
            ))
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            metrics.append(HealthMetric(
                name="memory_usage",
                value=memory_percent,
                status=self._get_status(memory_percent, 80, 95),
                timestamp=now,
                unit="%",
                threshold_warning=80,
                threshold_critical=95,
                description="메모리 사용률"
            ))
            
            # 디스크 사용률
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            metrics.append(HealthMetric(
                name="disk_usage",
                value=disk_percent,
                status=self._get_status(disk_percent, 80, 95),
                timestamp=now,
                unit="%",
                threshold_warning=80,
                threshold_critical=95,
                description="디스크 사용률"
            ))
            
            # 네트워크 연결 수
            connections = len(psutil.net_connections())
            metrics.append(HealthMetric(
                name="network_connections",
                value=connections,
                status="healthy" if connections < 1000 else "warning",
                timestamp=now,
                unit="개",
                description="네트워크 연결 수"
            ))
            
            # 프로세스 수
            process_count = len(psutil.pids())
            metrics.append(HealthMetric(
                name="process_count",
                value=process_count,
                status="healthy" if process_count < 500 else "warning",
                timestamp=now,
                unit="개",
                description="실행 중인 프로세스 수"
            ))
            
            # 부하 평균 (Linux/Unix만)
            try:
                load_avg = psutil.getloadavg()[0]  # 1분 평균
                cpu_count = psutil.cpu_count()
                load_percent = (load_avg / cpu_count) * 100
                metrics.append(HealthMetric(
                    name="load_average",
                    value=load_avg,
                    status=self._get_status(load_percent, 70, 90),
                    timestamp=now,
                    unit="",
                    description="시스템 부하 평균 (1분)"
                ))
            except:
                pass  # Windows에서는 지원하지 않음
            
        except Exception as e:
            logger.error(f"시스템 메트릭 수집 실패: {e}")
        
        return metrics
    
    def collect_application_metrics(self) -> List[HealthMetric]:
        """애플리케이션 메트릭 수집"""
        metrics = []
        now = datetime.now()
        
        try:
            # 가동 시간
            uptime = (now - self.start_time).total_seconds()
            metrics.append(HealthMetric(
                name="uptime",
                value=uptime,
                status="healthy",
                timestamp=now,
                unit="초",
                description="시스템 가동 시간"
            ))
            
            # 컨테이너 시스템에서 메트릭 수집 시도
            try:
                from src.core.container import get_container
                container = get_container()
                
                # 통합 서비스 상태
                unified_service = container.get('unified_service')
                if unified_service:
                    try:
                        health_info = unified_service.get_system_health()
                        metrics.append(HealthMetric(
                            name="system_health",
                            value=health_info.get('status', 'unknown'),
                            status=self._convert_health_status(health_info.get('status')),
                            timestamp=now,
                            description="통합 시스템 상태"
                        ))
                        
                        # 캐시 항목 수
                        cache_entries = health_info.get('cache_entries', 0)
                        metrics.append(HealthMetric(
                            name="cache_entries",
                            value=cache_entries,
                            status="healthy" if cache_entries > 0 else "warning",
                            timestamp=now,
                            unit="개",
                            description="캐시 항목 수"
                        ))
                        
                        # 활성 IP 수
                        active_ips = health_info.get('active_ips', 0)
                        metrics.append(HealthMetric(
                            name="active_ips",
                            value=active_ips,
                            status="healthy" if active_ips > 0 else "warning",
                            timestamp=now,
                            unit="개",
                            description="활성 블랙리스트 IP 수"
                        ))
                        
                    except Exception as e:
                        logger.error(f"통합 서비스 메트릭 수집 실패: {e}")
                
            except ImportError:
                logger.warning("컨테이너 시스템을 찾을 수 없습니다.")
            
            # 데이터베이스 상태 확인
            try:
                import sqlite3
                db_path = "instance/blacklist.db"
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM blacklist_entries")
                ip_count = cursor.fetchone()[0]
                conn.close()
                
                metrics.append(HealthMetric(
                    name="database_ips",
                    value=ip_count,
                    status="healthy" if ip_count > 0 else "warning",
                    timestamp=now,
                    unit="개",
                    description="데이터베이스 IP 수"
                ))
                
            except Exception as e:
                logger.error(f"데이터베이스 메트릭 수집 실패: {e}")
                metrics.append(HealthMetric(
                    name="database_status",
                    value="error",
                    status="critical",
                    timestamp=now,
                    description="데이터베이스 연결 상태"
                ))
            
        except Exception as e:
            logger.error(f"애플리케이션 메트릭 수집 실패: {e}")
        
        return metrics
    
    def check_service_health(self, service_name: str, check_function) -> ServiceStatus:
        """서비스 상태 확인"""
        start_time = time.time()
        
        try:
            result = check_function()
            response_time = time.time() - start_time
            
            if result.get('success', False):
                status = "healthy"
                error_message = None
            else:
                status = "unhealthy"
                error_message = result.get('error', 'Unknown error')
            
            return ServiceStatus(
                name=service_name,
                status=status,
                response_time=response_time,
                last_check=datetime.now(),
                error_message=error_message,
                details=result.get('details', {})
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            
            return ServiceStatus(
                name=service_name,
                status="unhealthy",
                response_time=response_time,
                last_check=datetime.now(),
                error_message=str(e)
            )
    
    def _get_status(self, value: float, warning_threshold: float, critical_threshold: float) -> str:
        """임계값 기반 상태 판정"""
        if value >= critical_threshold:
            return "critical"
        elif value >= warning_threshold:
            return "warning"
        else:
            return "healthy"
    
    def _convert_health_status(self, status: str) -> str:
        """헬스 상태 변환"""
        status_map = {
            'healthy': 'healthy',
            'degraded': 'warning',
            'unhealthy': 'critical',
            'unknown': 'warning'
        }
        return status_map.get(status, 'warning')
    
    def update_metrics_history(self, metrics: List[HealthMetric]):
        """메트릭 히스토리 업데이트"""
        for metric in metrics:
            if metric.name not in self.metrics_history:
                self.metrics_history[metric.name] = []
            
            # 최근 24시간 데이터만 유지
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.metrics_history[metric.name] = [
                m for m in self.metrics_history[metric.name]
                if m['timestamp'] > cutoff_time
            ]
            
            # 새 데이터 추가
            self.metrics_history[metric.name].append({
                'timestamp': metric.timestamp,
                'value': metric.value,
                'status': metric.status
            })
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """대시보드 데이터 생성"""
        # 메트릭 수집
        system_metrics = self.collect_system_metrics()
        app_metrics = self.collect_application_metrics()
        all_metrics = system_metrics + app_metrics
        
        # 히스토리 업데이트
        self.update_metrics_history(all_metrics)
        
        # 전체 상태 계산
        critical_count = sum(1 for m in all_metrics if m.status == "critical")
        warning_count = sum(1 for m in all_metrics if m.status == "warning")
        
        if critical_count > 0:
            overall_status = "critical"
        elif warning_count > 0:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        return {
            'overall_status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'uptime': (datetime.now() - self.start_time).total_seconds(),
            'metrics': [asdict(m) for m in all_metrics],
            'services': [asdict(s) for s in self.services.values()],
            'alerts': self.alerts,
            'metrics_history': self.metrics_history,
            'summary': {
                'total_metrics': len(all_metrics),
                'healthy_metrics': sum(1 for m in all_metrics if m.status == "healthy"),
                'warning_metrics': warning_count,
                'critical_metrics': critical_count
            }
        }


# 전역 대시보드 인스턴스
_dashboard = None

def get_dashboard() -> HealthDashboard:
    """전역 대시보드 인스턴스 반환"""
    global _dashboard
    if _dashboard is None:
        _dashboard = HealthDashboard()
    return _dashboard


# Flask 블루프린트
health_dashboard_bp = Blueprint('health_dashboard', __name__, url_prefix='/dashboard')

@health_dashboard_bp.route('/')
def dashboard_page():
    """대시보드 페이지"""
    return render_template_string(DASHBOARD_HTML_TEMPLATE)

@health_dashboard_bp.route('/api/health')
def health_api():
    """헬스 데이터 API"""
    dashboard = get_dashboard()
    data = dashboard.get_dashboard_data()
    return jsonify(data)

@health_dashboard_bp.route('/api/metrics/<metric_name>')
def metric_history(metric_name):
    """특정 메트릭 히스토리"""
    dashboard = get_dashboard()
    history = dashboard.metrics_history.get(metric_name, [])
    
    # 시간 범위 필터링
    hours = request.args.get('hours', 1, type=int)
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    filtered_history = [
        h for h in history
        if h['timestamp'] > cutoff_time
    ]
    
    return jsonify({
        'metric_name': metric_name,
        'history': filtered_history,
        'hours': hours
    })


# HTML 템플릿
DASHBOARD_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>블랙리스트 시스템 헬스 대시보드</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f5f5f7;
            color: #1d1d1f;
        }
        
        .header {
            background: white;
            padding: 1rem 2rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }
        
        .header h1 {
            font-size: 1.5rem;
            font-weight: 600;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-healthy { background: #34d399; }
        .status-warning { background: #fbbf24; }
        .status-critical { background: #ef4444; }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 2rem;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .card h3 {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #374151;
        }
        
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem 0;
            border-bottom: 1px solid #f3f4f6;
        }
        
        .metric:last-child {
            border-bottom: none;
        }
        
        .metric-name {
            font-weight: 500;
        }
        
        .metric-value {
            font-weight: 600;
            font-size: 1.1rem;
        }
        
        .overview-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        
        .overview-card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .overview-number {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        .overview-label {
            color: #6b7280;
            font-size: 0.9rem;
        }
        
        .loading {
            text-align: center;
            padding: 2rem;
            color: #6b7280;
        }
        
        .error {
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 8px;
            padding: 1rem;
            color: #dc2626;
            margin-bottom: 1rem;
        }
        
        .refresh-btn {
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 0.5rem 1rem;
            cursor: pointer;
            font-size: 0.9rem;
            margin-left: 1rem;
        }
        
        .refresh-btn:hover {
            background: #2563eb;
        }
        
        .last-updated {
            color: #6b7280;
            font-size: 0.85rem;
            margin-top: 1rem;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>
            <span id="overall-status-indicator" class="status-indicator"></span>
            블랙리스트 시스템 헬스 대시보드
            <button class="refresh-btn" onclick="refreshData()">새로고침</button>
        </h1>
    </div>
    
    <div class="container">
        <div id="error-message" class="error" style="display: none;"></div>
        
        <div id="loading" class="loading">
            데이터를 로드하는 중...
        </div>
        
        <div id="dashboard-content" style="display: none;">
            <!-- 개요 카드 -->
            <div class="overview-cards">
                <div class="overview-card">
                    <div id="uptime-number" class="overview-number">0</div>
                    <div class="overview-label">가동 시간 (시간)</div>
                </div>
                <div class="overview-card">
                    <div id="healthy-metrics" class="overview-number">0</div>
                    <div class="overview-label">정상 메트릭</div>
                </div>
                <div class="overview-card">
                    <div id="warning-metrics" class="overview-number">0</div>
                    <div class="overview-label">경고 메트릭</div>
                </div>
                <div class="overview-card">
                    <div id="critical-metrics" class="overview-number">0</div>
                    <div class="overview-label">위험 메트릭</div>
                </div>
            </div>
            
            <!-- 메트릭 그리드 -->
            <div class="grid">
                <div class="card">
                    <h3>시스템 메트릭</h3>
                    <div id="system-metrics"></div>
                </div>
                
                <div class="card">
                    <h3>애플리케이션 메트릭</h3>
                    <div id="app-metrics"></div>
                </div>
                
                <div class="card">
                    <h3>서비스 상태</h3>
                    <div id="service-status"></div>
                </div>
            </div>
            
            <div class="last-updated">
                마지막 업데이트: <span id="last-updated-time"></span>
            </div>
        </div>
    </div>

    <script>
        let refreshInterval;
        
        function formatUptime(seconds) {
            const hours = Math.floor(seconds / 3600);
            return hours.toFixed(1);
        }
        
        function formatValue(value, unit) {
            if (typeof value === 'number') {
                return value.toFixed(1) + (unit || '');
            }
            return value;
        }
        
        function getStatusClass(status) {
            return `status-${status}`;
        }
        
        function createMetricElement(metric) {
            return `
                <div class="metric">
                    <div>
                        <span class="status-indicator ${getStatusClass(metric.status)}"></span>
                        <span class="metric-name">${metric.description || metric.name}</span>
                    </div>
                    <div class="metric-value">${formatValue(metric.value, metric.unit)}</div>
                </div>
            `;
        }
        
        function updateDashboard(data) {
            // 전체 상태 업데이트
            const statusIndicator = document.getElementById('overall-status-indicator');
            statusIndicator.className = `status-indicator ${getStatusClass(data.overall_status)}`;
            
            // 개요 카드 업데이트
            document.getElementById('uptime-number').textContent = formatUptime(data.uptime);
            document.getElementById('healthy-metrics').textContent = data.summary.healthy_metrics;
            document.getElementById('warning-metrics').textContent = data.summary.warning_metrics;
            document.getElementById('critical-metrics').textContent = data.summary.critical_metrics;
            
            // 메트릭 분류
            const systemMetrics = data.metrics.filter(m => 
                ['cpu_usage', 'memory_usage', 'disk_usage', 'network_connections', 'process_count', 'load_average'].includes(m.name)
            );
            const appMetrics = data.metrics.filter(m => 
                !['cpu_usage', 'memory_usage', 'disk_usage', 'network_connections', 'process_count', 'load_average'].includes(m.name)
            );
            
            // 시스템 메트릭 업데이트
            const systemMetricsEl = document.getElementById('system-metrics');
            systemMetricsEl.innerHTML = systemMetrics.map(createMetricElement).join('');
            
            // 애플리케이션 메트릭 업데이트
            const appMetricsEl = document.getElementById('app-metrics');
            appMetricsEl.innerHTML = appMetrics.map(createMetricElement).join('');
            
            // 서비스 상태 업데이트
            const serviceStatusEl = document.getElementById('service-status');
            if (data.services && data.services.length > 0) {
                serviceStatusEl.innerHTML = data.services.map(service => `
                    <div class="metric">
                        <div>
                            <span class="status-indicator ${getStatusClass(service.status)}"></span>
                            <span class="metric-name">${service.name}</span>
                        </div>
                        <div class="metric-value">
                            ${service.response_time ? `${(service.response_time * 1000).toFixed(0)}ms` : service.status}
                        </div>
                    </div>
                `).join('');
            } else {
                serviceStatusEl.innerHTML = '<div class="metric">서비스 상태 정보가 없습니다.</div>';
            }
            
            // 마지막 업데이트 시간
            document.getElementById('last-updated-time').textContent = new Date().toLocaleString('ko-KR');
            
            // 로딩 숨기기, 콘텐츠 표시
            document.getElementById('loading').style.display = 'none';
            document.getElementById('dashboard-content').style.display = 'block';
            document.getElementById('error-message').style.display = 'none';
        }
        
        function showError(message) {
            document.getElementById('error-message').textContent = message;
            document.getElementById('error-message').style.display = 'block';
            document.getElementById('loading').style.display = 'none';
        }
        
        function refreshData() {
            fetch('/dashboard/api/health')
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(updateDashboard)
                .catch(error => {
                    console.error('데이터 로드 실패:', error);
                    showError(`데이터 로드 실패: ${error.message}`);
                });
        }
        
        // 초기 로드
        refreshData();
        
        // 30초마다 자동 새로고침
        refreshInterval = setInterval(refreshData, 30000);
        
        // 페이지 언로드 시 인터벌 정리
        window.addEventListener('beforeunload', () => {
            if (refreshInterval) {
                clearInterval(refreshInterval);
            }
        });
    </script>
</body>
</html>
"""