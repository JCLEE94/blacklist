"""
성능 대시보드 Flask 라우트

성능 모니터링 대시보드의 웹 인터페이스 라우트를 제공합니다.
"""

from flask import Blueprint
from flask import jsonify
from flask import render_template_string
from loguru import logger

from .dashboard import PerformanceDashboard

# 글로벌 대시보드 인스턴스
_global_dashboard = None


def get_global_dashboard() -> PerformanceDashboard:
    """글로벌 대시보드 인스턴스 반환"""
    global _global_dashboard

    if _global_dashboard is None:
        _global_dashboard = PerformanceDashboard()
        _global_dashboard.start_monitoring()
        logger.info("Global performance dashboard created")

    return _global_dashboard


# Flask 블루프린트
dashboard_bp = Blueprint("performance_dashboard", __name__)


@dashboard_bp.route("/performance")
def performance_dashboard():
    """성능 대시보드 페이지"""
    return render_template_string(DASHBOARD_HTML_TEMPLATE)


@dashboard_bp.route("/api/performance/metrics")
def get_performance_metrics():
    """성능 메트릭 API"""
    try:
        dashboard = get_global_dashboard()
        data = dashboard.get_dashboard_data()
        return jsonify(data)
    except Exception as e:
        logger.error(f"Performance metrics API error: {e}")
        return jsonify({"error": "Failed to get performance metrics"}), 500


@dashboard_bp.route("/api/performance/reset", methods=["POST"])
def reset_performance_counters():
    """성능 카운터 리셋 API"""
    try:
        dashboard = get_global_dashboard()
        dashboard.reset_counters()
        return jsonify({"success": True, "message": "Performance counters reset"})
    except Exception as e:
        logger.error(f"Performance reset API error: {e}")
        return jsonify({"error": "Failed to reset counters"}), 500


# HTML 템플릿 (기본적인 대시보드 UI)
DASHBOARD_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blacklist System - Performance Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            padding: 30px;
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #f0f0f0;
        }
        .title {
            font-size: 2.5em;
            margin: 0;
            color: #2c3e50;
            font-weight: 700;
        }
        .subtitle {
            font-size: 1.2em;
            color: #7f8c8d;
            margin: 10px 0;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .metric-card {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        .metric-card:hover {
            transform: translateY(-5px);
        }
        .metric-value {
            font-size: 2.5em;
            font-weight: bold;
            margin: 0;
        }
        .metric-label {
            font-size: 1.1em;
            margin-top: 10px;
            opacity: 0.9;
        }
        .chart-container {
            background: white;
            padding: 25px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        .refresh-btn {
            background: #3498db;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            transition: background 0.3s ease;
        }
        .refresh-btn:hover {
            background: #2980b9;
        }
        .grade {
            font-size: 3em;
            font-weight: bold;
            text-align: center;
            margin: 20px 0;
        }
        .grade.A { color: #27ae60; }
        .grade.B { color: #f39c12; }
        .grade.C { color: #e67e22; }
        .grade.D, .grade.F { color: #e74c3c; }
        .alerts {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #7f8c8d;
            font-size: 1.2em;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">📊 Blacklist Performance Dashboard</h1>
            <p class="subtitle">실시간 시스템 성능 모니터링</p>
            <button class="refresh-btn" onclick="refreshData()">🔄 새로고침</button>
        </div>

        <div id="loading" class="loading">
            <div class="spinner"></div>
            데이터를 불러오는 중...
        </div>

        <div id="dashboard" style="display: none;">
            <div class="metrics-grid" id="metricsGrid">
                <!-- Metrics will be populated here -->
            </div>

            <div class="chart-container">
                <canvas id="performanceChart" width="400" height="200"></canvas>
            </div>

            <div id="alerts"></div>
        </div>
    </div>

    <script>
        let performanceChart;

        function formatNumber(num) {
            if (num === undefined || num === null) return '0';
            return num.toLocaleString();
        }

        function formatBytes(bytes) {
            if (bytes === 0) return '0 MB';
            return Math.round(bytes * 100) / 100 + ' MB';
        }

        function formatPercent(percent) {
            if (percent === undefined || percent === null) return '0%';
            return Math.round(percent * 100) / 100 + '%';
        }

        async function fetchMetrics() {
            try {
                const response = await fetch('/api/performance/metrics');
                if (!response.ok) throw new Error('Failed to fetch metrics');
                return await response.json();
            } catch (error) {
                console.error('Error fetching metrics:', error);
                throw error;
            }
        }

        function updateMetrics(data) {
            const current = data.current_metrics;
            const stats = data.statistics;
            const grade = data.performance_grade;

            const metricsGrid = document.getElementById('metricsGrid');
            metricsGrid.innerHTML = `
                <div class="metric-card">
                    <div class="metric-value">${formatNumber(current.response_time_ms)}ms</div>
                    <div class="metric-label">응답 시간</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${formatBytes(current.memory_usage_mb)}</div>
                    <div class="metric-label">메모리 사용량</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${formatPercent(current.cpu_usage_percent)}</div>
                    <div class="metric-label">CPU 사용률</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value grade ${grade.grade.charAt(0)}">${grade.grade}</div>
                    <div class="metric-label">성능 등급 (${grade.total_score}점)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${formatNumber(stats.total_requests)}</div>
                    <div class="metric-label">총 요청 수</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${formatPercent(stats.error_rate_percent)}</div>
                    <div class="metric-label">에러 비율</div>
                </div>
            `;
        }

        function updateChart(data) {
            const timeSeries = data.time_series;

            if (performanceChart) {
                performanceChart.destroy();
            }

            const ctx = document.getElementById('performanceChart').getContext('2d');
            performanceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: timeSeries.timestamps.slice(-20),
                    datasets: [{
                        label: '응답 시간 (ms)',
                        data: timeSeries.response_times.slice(-20),
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        tension: 0.4
                    }, {
                        label: '메모리 사용량 (MB)',
                        data: timeSeries.memory_usage.slice(-20),
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: '실시간 성능 내역'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }

        function updateAlerts(data) {
            const alertsDiv = document.getElementById('alerts');
            const alerts = data.active_alerts || [];

            if (alerts.length === 0) {
                alertsDiv.innerHTML = '';
                return;
            }

            const alertsHtml = alerts.map(alert => `
                <div class="alerts">
                    <strong>[⚠️ ${alert.severity.toUpperCase()}]</strong>
                    ${alert.message}
                    <small style="float: right;">${new Date(alert.timestamp).toLocaleTimeString()}</small>
                </div>
            `).join('');

            alertsDiv.innerHTML = `<h3>활성 알림</h3>${alertsHtml}`;
        }

        async function refreshData() {
            try {
                document.getElementById('loading').style.display = 'block';
                document.getElementById('dashboard').style.display = 'none';

                const data = await fetchMetrics();

                updateMetrics(data);
                updateChart(data);
                updateAlerts(data);

                document.getElementById('loading').style.display = 'none';
                document.getElementById('dashboard').style.display = 'block';

                console.log('Dashboard updated successfully');
            } catch (error) {
                console.error('Failed to refresh data:', error);
                document.getElementById('loading').innerHTML =
                    '<div style="color: #e74c3c;">😨 데이터를 불러오는 데 실패했습니다.</div>';
            }
        }

        // 초기 로드 및 자동 새로고침
        document.addEventListener('DOMContentLoaded', () => {
            refreshData();
            setInterval(refreshData, 30000); // 30초맄다 새로고침
        });
    </script>
</body>
</html>
"""
