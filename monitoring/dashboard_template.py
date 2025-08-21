#!/usr/bin/env python3
"""
Dashboard HTML Template Module

Contains the HTML template for the deployment dashboard web interface.
Separated from web_interface.py to reduce file size and improve maintainability.

Links:
- Chart.js documentation: https://www.chartjs.org/
- Socket.IO documentation: https://socket.io/

Sample input: Used by importing DASHBOARD_TEMPLATE
Expected output: Provides HTML template string for dashboard rendering
"""

# HTML Dashboard Template
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blacklist Deployment Dashboard</title>
    <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a1a; color: #ffffff; line-height: 1.6;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { color: #00d4aa; font-size: 2.5em; margin-bottom: 10px; }
        .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .status-card { 
            background: #2a2a2a; border-radius: 10px; padding: 20px; border-left: 4px solid #00d4aa;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        .status-card h3 { color: #00d4aa; margin-bottom: 15px; font-size: 1.2em; }
        .metric { display: flex; justify-content: space-between; margin: 10px 0; }
        .metric-label { color: #cccccc; }
        .metric-value { font-weight: bold; }
        .status-indicator { 
            display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 0.8em;
            text-transform: uppercase; font-weight: bold;
        }
        .status-healthy { background: #28a745; color: white; }
        .status-warning { background: #ffc107; color: black; }
        .status-error { background: #dc3545; color: white; }
        .status-unknown { background: #6c757d; color: white; }
        .chart-container { 
            background: #2a2a2a; border-radius: 10px; padding: 20px; margin: 20px 0;
            height: 400px;
        }
        .chart-container h3 { color: #00d4aa; margin-bottom: 15px; }
        .deployment-history {
            background: #2a2a2a; border-radius: 10px; padding: 20px; margin: 20px 0;
        }
        .deployment-history h3 { color: #00d4aa; margin-bottom: 15px; }
        .history-item {
            background: #3a3a3a; border-radius: 5px; padding: 10px; margin: 10px 0;
            border-left: 3px solid #00d4aa;
        }
        .history-time { color: #888; font-size: 0.9em; }
        .history-details { margin-top: 5px; }
        .refresh-indicator {
            position: fixed; top: 20px; right: 20px; 
            background: #00d4aa; color: white; padding: 10px 15px; border-radius: 5px;
            opacity: 0; transition: opacity 0.3s;
        }
        .refresh-indicator.show { opacity: 1; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        .loading { animation: pulse 2s infinite; }
    </style>
</head>
<body>
    <div class="refresh-indicator" id="refreshIndicator">업데이트 중...</div>
    
    <div class="container">
        <header class="header">
            <h1>🛡️ Blacklist Deployment Dashboard</h1>
            <p>실시간 시스템 모니터링 및 배포 상태</p>
            <p id="lastUpdate" class="history-time">마지막 업데이트: --</p>
        </header>
        
        <div class="status-grid">
            <div class="status-card">
                <h3>API 서비스</h3>
                <div id="apiStatus">
                    <div class="metric loading">
                        <span class="metric-label">상태:</span>
                        <span class="metric-value">로딩 중...</span>
                    </div>
                </div>
            </div>
            
            <div class="status-card">
                <h3>Docker 서비스</h3>
                <div id="dockerStatus">
                    <div class="metric loading">
                        <span class="metric-label">상태:</span>
                        <span class="metric-value">로딩 중...</span>
                    </div>
                </div>
            </div>
            
            <div class="status-card">
                <h3>시스템 성능</h3>
                <div id="performanceStatus">
                    <div class="metric loading">
                        <span class="metric-label">상태:</span>
                        <span class="metric-value">로딩 중...</span>
                    </div>
                </div>
            </div>
            
            <div class="status-card">
                <h3>배포 정보</h3>
                <div id="deploymentInfo">
                    <div class="metric loading">
                        <span class="metric-label">상태:</span>
                        <span class="metric-value">로딩 중...</span>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="chart-container">
            <h3>응답 시간 추이</h3>
            <canvas id="responseTimeChart"></canvas>
        </div>
        
        <div class="chart-container">
            <h3>시스템 리소스 사용률</h3>
            <canvas id="resourceChart"></canvas>
        </div>
        
        <div class="deployment-history">
            <h3>배포 히스토리</h3>
            <div id="historyContainer">
                <div class="history-item loading">로딩 중...</div>
            </div>
        </div>
    </div>
    
    <script>
        // Socket.IO connection
        const socket = io();
        
        // Chart instances
        let responseTimeChart, resourceChart;
        
        // Chart data storage
        let responseTimeData = [];
        let resourceData = [];
        
        // Initialize charts
        function initCharts() {
            const ctx1 = document.getElementById('responseTimeChart').getContext('2d');
            responseTimeChart = new Chart(ctx1, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'API 응답 시간 (ms)',
                        data: [],
                        borderColor: '#00d4aa',
                        backgroundColor: 'rgba(0, 212, 170, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#ffffff' } } },
                    scales: {
                        x: { ticks: { color: '#cccccc' }, grid: { color: '#444' } },
                        y: { ticks: { color: '#cccccc' }, grid: { color: '#444' } }
                    }
                }
            });
            
            const ctx2 = document.getElementById('resourceChart').getContext('2d');
            resourceChart = new Chart(ctx2, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'CPU (%)',
                            data: [],
                            borderColor: '#ff6b6b',
                            backgroundColor: 'rgba(255, 107, 107, 0.1)'
                        },
                        {
                            label: 'Memory (%)',
                            data: [],
                            borderColor: '#4ecdc4',
                            backgroundColor: 'rgba(78, 205, 196, 0.1)'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#ffffff' } } },
                    scales: {
                        x: { ticks: { color: '#cccccc' }, grid: { color: '#444' } },
                        y: { 
                            ticks: { color: '#cccccc' }, 
                            grid: { color: '#444' },
                            min: 0,
                            max: 100
                        }
                    }
                }
            });
        }
        
        function getStatusClass(status) {
            const statusMap = {
                'healthy': 'status-healthy',
                'degraded': 'status-warning',
                'unhealthy': 'status-error',
                'error': 'status-error',
                'unreachable': 'status-error'
            };
            return statusMap[status] || 'status-unknown';
        }
        
        function formatTimestamp(timestamp) {
            return new Date(timestamp).toLocaleString('ko-KR');
        }
        
        function updateMetrics(metrics) {
            document.getElementById('refreshIndicator').classList.add('show');
            setTimeout(() => {
                document.getElementById('refreshIndicator').classList.remove('show');
            }, 2000);
            
            // Update last update time
            document.getElementById('lastUpdate').textContent = 
                `마지막 업데이트: ${formatTimestamp(metrics.timestamp)}`;
            
            // Update API status
            if (metrics.services && metrics.services.api) {
                const api = metrics.services.api;
                document.getElementById('apiStatus').innerHTML = `
                    <div class="metric">
                        <span class="metric-label">상태:</span>
                        <span class="status-indicator ${getStatusClass(api.status)}">${api.status}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">응답 시간:</span>
                        <span class="metric-value">${Math.round(api.response_time || 0)}ms</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">버전:</span>
                        <span class="metric-value">${api.version || 'Unknown'}</span>
                    </div>
                `;
                
                // Update response time chart
                const now = new Date().toLocaleTimeString();
                if (responseTimeData.length >= 20) {
                    responseTimeData.shift();
                    responseTimeChart.data.labels.shift();
                    responseTimeChart.data.datasets[0].data.shift();
                }
                
                responseTimeData.push(api.response_time || 0);
                responseTimeChart.data.labels.push(now);
                responseTimeChart.data.datasets[0].data.push(api.response_time || 0);
                responseTimeChart.update();
            }
            
            // Update Docker status
            if (metrics.services && metrics.services.docker) {
                const docker = metrics.services.docker;
                document.getElementById('dockerStatus').innerHTML = `
                    <div class="metric">
                        <span class="metric-label">상태:</span>
                        <span class="status-indicator ${getStatusClass(docker.status)}">${docker.status}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">실행 중:</span>
                        <span class="metric-value">${docker.running_count || 0}/${docker.total_count || 0}</span>
                    </div>
                `;
            }
            
            // Update performance status
            if (metrics.performance && typeof metrics.performance === 'object' && !metrics.performance.error) {
                const perf = metrics.performance;
                document.getElementById('performanceStatus').innerHTML = `
                    <div class="metric">
                        <span class="metric-label">CPU:</span>
                        <span class="metric-value">${Math.round(perf.cpu_percent || 0)}%</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Memory:</span>
                        <span class="metric-value">${Math.round(perf.memory_percent || 0)}%</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Disk:</span>
                        <span class="metric-value">${Math.round(perf.disk_percent || 0)}%</span>
                    </div>
                `;
                
                // Update resource chart
                const now = new Date().toLocaleTimeString();
                if (resourceData.length >= 20) {
                    resourceChart.data.labels.shift();
                    resourceChart.data.datasets[0].data.shift();
                    resourceChart.data.datasets[1].data.shift();
                }
                
                resourceChart.data.labels.push(now);
                resourceChart.data.datasets[0].data.push(perf.cpu_percent || 0);
                resourceChart.data.datasets[1].data.push(perf.memory_percent || 0);
                resourceChart.update();
            } else {
                document.getElementById('performanceStatus').innerHTML = `
                    <div class="metric">
                        <span class="metric-label">상태:</span>
                        <span class="status-indicator status-unknown">사용할 수 없음</span>
                    </div>
                `;
            }
            
            // Update deployment info
            if (metrics.deployment) {
                const deploy = metrics.deployment;
                document.getElementById('deploymentInfo').innerHTML = `
                    <div class="metric">
                        <span class="metric-label">총 IP:</span>
                        <span class="metric-value">${deploy.total_ips || 0}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">활성 IP:</span>
                        <span class="metric-value">${deploy.active_ips || 0}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">만료 IP:</span>
                        <span class="metric-value">${deploy.expired_ips || 0}</span>
                    </div>
                `;
            }
        }
        
        function loadDeploymentHistory() {
            fetch('/api/deployment-history?limit=10')
                .then(response => response.json())
                .then(history => {
                    const container = document.getElementById('historyContainer');
                    if (history.length === 0) {
                        container.innerHTML = '<div class="history-item">배포 히스토리가 없습니다.</div>';
                        return;
                    }
                    
                    container.innerHTML = history.map(event => `
                        <div class="history-item">
                            <div class="history-time">${formatTimestamp(event.timestamp)}</div>
                            <div class="history-details">
                                <strong>${event.event_type}</strong>
                                ${event.version ? `- Version: ${event.version}` : ''}
                                ${event.status ? `- Status: ${event.status}` : ''}
                                ${event.duration_seconds ? `- Duration: ${event.duration_seconds}s` : ''}
                            </div>
                            ${event.details ? `<div style="margin-top: 5px; color: #ccc;">${event.details}</div>` : ''}
                        </div>
                    `).join('');
                })
                .catch(error => {
                    console.error('Failed to load deployment history:', error);
                    document.getElementById('historyContainer').innerHTML = 
                        '<div class="history-item">히스토리 로드 실패</div>';
                });
        }
        
        // Socket event handlers
        socket.on('connect', function() {
            console.log('Connected to dashboard');
        });
        
        socket.on('metrics_update', function(metrics) {
            updateMetrics(metrics);
        });
        
        socket.on('disconnect', function() {
            console.log('Disconnected from dashboard');
        });
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            initCharts();
            loadDeploymentHistory();
            
            // Request initial metrics
            socket.emit('request_metrics');
            
            // Reload deployment history every 5 minutes
            setInterval(loadDeploymentHistory, 5 * 60 * 1000);
        });
    </script>
</body>
</html>
'''


if __name__ == "__main__":
    # Validation test for template module
    import sys
    
    all_validation_failures = []
    total_tests = 0
    
    # Test 1: Template is a non-empty string
    total_tests += 1
    try:
        if isinstance(DASHBOARD_TEMPLATE, str) and len(DASHBOARD_TEMPLATE) > 1000:
            pass  # Test passed
        else:
            all_validation_failures.append(f"Invalid dashboard template: {type(DASHBOARD_TEMPLATE)}, length: {len(DASHBOARD_TEMPLATE)}")
    except Exception as e:
        all_validation_failures.append(f"Dashboard template validation failed: {e}")
    
    # Test 2: Template contains required elements
    total_tests += 1
    try:
        required_elements = [
            "<!DOCTYPE html>",
            "<title>Blacklist Deployment Dashboard</title>",
            "socket.io",
            "chart.js",
            "<canvas id=\"responseTimeChart\"></canvas>",
            "<canvas id=\"resourceChart\"></canvas>"
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in DASHBOARD_TEMPLATE:
                missing_elements.append(element)
        
        if not missing_elements:
            pass  # Test passed
        else:
            all_validation_failures.append(f"Missing required template elements: {missing_elements}")
    except Exception as e:
        all_validation_failures.append(f"Template element validation failed: {e}")
    
    # Test 3: Template has valid HTML structure
    total_tests += 1
    try:
        # Basic HTML structure validation
        html_tags = ["<html", "<head>", "<body>", "</html>", "</head>", "</body>"]
        
        for tag in html_tags:
            if tag not in DASHBOARD_TEMPLATE:
                all_validation_failures.append(f"Missing HTML tag: {tag}")
                break
        else:
            pass  # Test passed
    except Exception as e:
        all_validation_failures.append(f"HTML structure validation failed: {e}")
    
    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Dashboard template module is validated and ready for use")
        sys.exit(0)
