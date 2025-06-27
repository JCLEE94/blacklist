#!/usr/bin/env python3
"""
통합 블랙리스트 관리 시스템 - 단일 통합 앱
"""
import os
import json
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template_string, Response

# 통합 Flask 애플리케이션
application = Flask(__name__)

# 애플리케이션 시작 시간
START_TIME = datetime.utcnow()

# 기본 데이터
blacklist_data = []
collection_enabled = False

# 대시보드 HTML
DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blacklist Management System - Nextrade</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f2f5;
        }
        
        .dashboard-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem 0;
            margin-bottom: 2rem;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .stat-card {
            background: white;
            border-radius: 15px;
            padding: 1.5rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            border-left: 5px solid;
            margin-bottom: 1.5rem;
            position: relative;
            overflow: hidden;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.15);
        }
        
        .stat-card.primary { border-left-color: #007bff; }
        .stat-card.success { border-left-color: #28a745; }
        .stat-card.warning { border-left-color: #ffc107; }
        .stat-card.danger { border-left-color: #dc3545; }
        .stat-card.info { border-left-color: #17a2b8; }
        .stat-card.purple { border-left-color: #6f42c1; }
        
        .stat-icon {
            font-size: 3rem;
            opacity: 0.1;
            position: absolute;
            right: 1rem;
            top: 50%;
            transform: translateY(-50%);
        }
        
        .stat-number {
            font-size: 2.5rem;
            font-weight: bold;
            line-height: 1;
        }
        
        .chart-container {
            background: white;
            border-radius: 15px;
            padding: 1.5rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-bottom: 1.5rem;
        }
        
        .real-time-badge {
            animation: pulse 2s infinite;
            background: #28a745;
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 20px;
            font-size: 0.75rem;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-top: 2rem;
        }
        
        .feature-card {
            background: white;
            border-radius: 15px;
            padding: 1.5rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }
        
        .feature-card:hover {
            transform: translateY(-3px);
        }
        
        .collection-status {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
            padding: 0.75rem;
            border-radius: 8px;
            background: #f8f9fa;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        .status-active { background: #28a745; }
        .status-inactive { background: #6c757d; }
        .status-error { background: #dc3545; }
        
        .btn-action {
            background: linear-gradient(45deg, #667eea, #764ba2);
            border: none;
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: 25px;
            transition: all 0.3s ease;
        }
        
        .btn-action:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
            color: white;
        }
        
        .text-purple { color: #6f42c1 !important; }
        
        /* Quick Actions Floating Panel */
        .quick-actions {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            z-index: 1000;
        }
        
        .quick-actions-panel {
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            padding: 1.5rem;
            min-width: 250px;
        }
        
        @media (max-width: 768px) {
            .stat-number { font-size: 2rem; }
            .stat-icon { font-size: 2rem; }
            .quick-actions { bottom: 1rem; right: 1rem; }
        }
    </style>
</head>
<body>
    <!-- Dashboard Header -->
    <div class="container-fluid">
        <div class="dashboard-header text-center">
            <h1 class="display-4 mb-3">
                <i class="bi bi-shield-shaded"></i> 
                Blacklist Management System
            </h1>
            <p class="lead mb-0">
                Multi-source threat intelligence platform
                <span class="real-time-badge ms-2">
                    <i class="bi bi-broadcast"></i> LIVE
                </span>
            </p>
            <small class="d-block mt-2">마지막 업데이트: <span id="lastUpdate">{{ last_update }}</span></small>
        </div>
    </div>

    <!-- Enhanced Statistics Cards -->
    <div class="container-fluid">
        <div class="row">
            <div class="col-lg-2 col-md-6">
                <div class="stat-card primary position-relative">
                    <i class="bi bi-database stat-icon"></i>
                    <div class="stat-number">{{ "{:,}".format(total_ips) }}</div>
                    <div class="text-muted">전체 IP</div>
                    <small class="text-primary">Active</small>
                </div>
            </div>
            <div class="col-lg-2 col-md-6">
                <div class="stat-card success position-relative">
                    <i class="bi bi-shield-check stat-icon"></i>
                    <div class="stat-number">{{ "{:,}".format(active_ips) }}</div>
                    <div class="text-muted">활성 IP</div>
                    <small class="text-success">Live</small>
                </div>
            </div>
            <div class="col-lg-2 col-md-6">
                <div class="stat-card warning position-relative">
                    <i class="bi bi-exclamation-triangle stat-icon"></i>
                    <div class="stat-number">{{ "{:,}".format(threat_count|default(1234)) }}</div>
                    <div class="text-muted">위협 탐지</div>
                    <small class="text-warning">24h</small>
                </div>
            </div>
            <div class="col-lg-2 col-md-6">
                <div class="stat-card info position-relative">
                    <i class="bi bi-arrow-clockwise stat-icon"></i>
                    <div class="stat-number">{{ collection_sources|default(3) }}</div>
                    <div class="text-muted">수집 소스</div>
                    <small class="text-info">Sources</small>
                </div>
            </div>
            <div class="col-lg-2 col-md-6">
                <div class="stat-card danger position-relative">
                    <i class="bi bi-geo-alt stat-icon"></i>
                    <div class="stat-number">{{ countries_count|default(50) }}</div>
                    <div class="text-muted">탐지 국가</div>
                    <small class="text-danger">Global</small>
                </div>
            </div>
            <div class="col-lg-2 col-md-6">
                <div class="stat-card purple position-relative">
                    <i class="bi bi-cpu stat-icon"></i>
                    <div class="stat-number">{{ performance_score|default(98) }}%</div>
                    <div class="text-muted">시스템 성능</div>
                    <small class="text-purple">Optimized</small>
                </div>
            </div>
        </div>
    </div>

    <!-- Enhanced Charts and Analytics -->
    <div class="container-fluid mt-4">
        <div class="row">
            <!-- Real-time Threat Timeline -->
            <div class="col-lg-8">
                <div class="chart-container">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h5 class="mb-0">
                            <i class="bi bi-graph-up-arrow"></i> Threat Timeline
                        </h5>
                        <span class="real-time-badge">Live</span>
                    </div>
                    <canvas id="threatTimelineChart" height="100"></canvas>
                </div>
            </div>
            
            <!-- Collection Sources Status -->
            <div class="col-lg-4">
                <div class="chart-container">
                    <h5 class="mb-3">
                        <i class="bi bi-collection"></i> Sources Status
                    </h5>
                    <div id="collectionStatus">
                        <div class="collection-status">
                            <span class="status-indicator {{ 'status-active' if collection_enabled else 'status-inactive' }}"></span>
                            <strong>REGTECH</strong>
                            <span class="ms-auto {{ 'text-success' if collection_enabled else 'text-danger' }}">
                                {{ '활성' if collection_enabled else '비활성' }}
                            </span>
                        </div>
                        <div class="small text-muted mb-2">Financial Security - 1,200+ IPs</div>
                        
                        <div class="collection-status">
                            <span class="status-indicator {{ 'status-active' if collection_enabled else 'status-inactive' }}"></span>
                            <strong>SECUDIUM</strong>
                            <span class="ms-auto {{ 'text-success' if collection_enabled else 'text-danger' }}">
                                {{ '활성' if collection_enabled else '비활성' }}
                            </span>
                        </div>
                        <div class="small text-muted mb-3">Threat Intelligence Platform</div>
                        
                        <button class="btn btn-action w-100" onclick="refreshCollectionStatus()">
                            <i class="bi bi-arrow-clockwise"></i> Refresh
                        </button>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mt-4">
            <!-- Daily IP Statistics -->
            <div class="col-lg-12">
                <div class="chart-container">
                    <h5 class="mb-3">
                        <i class="bi bi-calendar3"></i> Daily IP Statistics (Last 30 Days)
                    </h5>
                    <canvas id="dailyChart" height="100"></canvas>
                </div>
            </div>
        </div>
        
        <div class="row mt-4">
            <!-- Geographic Distribution -->
            <div class="col-lg-6">
                <div class="chart-container">
                    <h5 class="mb-3">
                        <i class="bi bi-globe2"></i> Geographic Distribution
                    </h5>
                    <canvas id="geoChart" height="150"></canvas>
                </div>
            </div>
            
            <!-- Threat Categories -->
            <div class="col-lg-6">
                <div class="chart-container">
                    <h5 class="mb-3">
                        <i class="bi bi-pie-chart"></i> Threat Categories
                    </h5>
                    <canvas id="categoryChart" height="150"></canvas>
                </div>
            </div>
        </div>
    </div>

    <!-- Enhanced Feature Grid -->
    <div class="container-fluid">
        <div class="feature-grid">
            <!-- AI-Powered Analytics -->
            <div class="feature-card">
                <div class="d-flex align-items-center mb-3">
                    <i class="bi bi-robot text-primary me-2" style="font-size: 1.5rem;"></i>
                    <h6 class="mb-0">AI Analytics</h6>
                </div>
                <p class="text-muted small">
                    Machine learning threat pattern analysis
                </p>
                <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-outline-primary">Patterns</button>
                    <button class="btn btn-sm btn-outline-primary">Prediction</button>
                </div>
            </div>
            
            <!-- Real-time Monitoring -->
            <div class="feature-card">
                <div class="d-flex align-items-center mb-3">
                    <i class="bi bi-eye text-success me-2" style="font-size: 1.5rem;"></i>
                    <h6 class="mb-0">Real-time Monitoring</h6>
                </div>
                <p class="text-muted small">
                    24/7 threat detection and alerts
                </p>
                <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-outline-success" onclick="location.href='/api/collection/status'">Status</button>
                    <button class="btn btn-sm btn-outline-success">Alerts</button>
                </div>
            </div>
            
            <!-- Advanced Search -->
            <div class="feature-card">
                <div class="d-flex align-items-center mb-3">
                    <i class="bi bi-search text-info me-2" style="font-size: 1.5rem;"></i>
                    <h6 class="mb-0">고급 검색</h6>
                </div>
                <p class="text-muted small">
                    다중 조건 검색 및 필터링 기능
                </p>
                <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-outline-info">검색하기</button>
                    <button class="btn btn-sm btn-outline-info">고급 필터</button>
                </div>
            </div>
            
            <!-- Data Management -->
            <div class="feature-card">
                <div class="d-flex align-items-center mb-3">
                    <i class="bi bi-database-gear text-warning me-2" style="font-size: 1.5rem;"></i>
                    <h6 class="mb-0">데이터 관리</h6>
                </div>
                <p class="text-muted small">
                    다중 소스 데이터 수집 및 통합 관리
                </p>
                <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-outline-warning">관리하기</button>
                    <button class="btn btn-sm btn-outline-warning">자동화 설정</button>
                </div>
            </div>
            
            <!-- API Integration -->
            <div class="feature-card">
                <div class="d-flex align-items-center mb-3">
                    <i class="bi bi-code-slash text-danger me-2" style="font-size: 1.5rem;"></i>
                    <h6 class="mb-0">API 통합</h6>
                </div>
                <p class="text-muted small">
                    RESTful API 및 웹훅 지원
                </p>
                <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-outline-danger" onclick="showApiDocs()">API 문서</button>
                    <button class="btn btn-sm btn-outline-danger">키 관리</button>
                </div>
            </div>
            
            <!-- Export & Reporting -->
            <div class="feature-card">
                <div class="d-flex align-items-center mb-3">
                    <i class="bi bi-file-earmark-bar-graph text-purple me-2" style="font-size: 1.5rem;"></i>
                    <h6 class="mb-0">보고서 생성</h6>
                </div>
                <p class="text-muted small">
                    자동화된 위협 보고서 및 통계 생성
                </p>
                <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-outline-secondary" onclick="location.href='/api/fortigate'">JSON</button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="location.href='/api/blacklist/active'">TXT</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Quick Actions Floating Panel -->
    <div class="quick-actions">
        <div class="quick-actions-panel">
            <h6 class="mb-3">
                <i class="bi bi-lightning-fill text-warning"></i> 빠른 작업
            </h6>
            <div class="d-grid gap-2">
                <button class="btn btn-primary btn-sm" onclick="triggerDataUpdate()">
                    <i class="bi bi-arrow-clockwise"></i> 데이터 업데이트
                </button>
                <button class="btn btn-success btn-sm" onclick="runHealthCheck()">
                    <i class="bi bi-heart-pulse"></i> 시스템 점검
                </button>
                <button class="btn btn-info btn-sm" onclick="exportReport()">
                    <i class="bi bi-download"></i> 보고서 생성
                </button>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
    // 실시간 업데이트
    let updateInterval;

    document.addEventListener('DOMContentLoaded', function() {
        initializeCharts();
        startRealTimeUpdates();
    });

    function initializeCharts() {
        // Threat Timeline Chart
        const timelineCtx = document.getElementById('threatTimelineChart').getContext('2d');
        new Chart(timelineCtx, {
            type: 'line',
            data: {
                labels: Array.from({length: 24}, (_, i) => `${i}:00`),
                datasets: [{
                    label: 'Threat Detection',
                    data: Array.from({length: 24}, () => Math.floor(Math.random() * 100)),
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
        
        // Daily IP Statistics Chart
        const dailyCtx = document.getElementById('dailyChart').getContext('2d');
        const dailyChart = new Chart(dailyCtx, {
            type: 'bar',
            data: {
                labels: ['06-10', '06-11', '06-12', '06-13', '06-14', '06-15', '06-16', '06-17'],
                datasets: [{
                    label: 'Total IPs',
                    data: [48000, 48050, 48100, 48120, 48132, 48132, 48132, {{ total_ips }}],
                    backgroundColor: 'rgba(54, 162, 235, 0.6)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
        
        // Geographic Chart
        const geoCtx = document.getElementById('geoChart').getContext('2d');
        new Chart(geoCtx, {
            type: 'bar',
            data: {
                labels: ['중국', '러시아', '미국', '브라질', '인도'],
                datasets: [{
                    label: '위협 IP 수',
                    data: [450, 320, 180, 150, 120],
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 205, 86, 0.8)',
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(153, 102, 255, 0.8)'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } }
            }
        });
        
        // Category Chart
        const categoryCtx = document.getElementById('categoryChart').getContext('2d');
        new Chart(categoryCtx, {
            type: 'doughnut',
            data: {
                labels: ['멀웨어', '스팸', '피싱', '봇넷', '기타'],
                datasets: [{
                    data: [35, 25, 20, 15, 5],
                    backgroundColor: [
                        '#FF6384',
                        '#36A2EB',
                        '#FFCE56',
                        '#4BC0C0',
                        '#9966FF'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    function startRealTimeUpdates() {
        updateInterval = setInterval(updateDashboard, 30000); // 30초마다 업데이트
    }

    function updateDashboard() {
        // 마지막 업데이트 시간 갱신
        document.getElementById('lastUpdate').textContent = new Date().toLocaleString();
        
        // 수집 상태 확인
        fetch('/api/collection/status')
            .then(response => response.json())
            .then(data => {
                console.log('Collection status updated:', data);
            })
            .catch(error => {
                console.error('Failed to update collection status:', error);
            });
    }

    function refreshCollectionStatus() {
        const btn = event.target;
        btn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> 새로고침 중...';
        btn.disabled = true;
        
        fetch('/api/collection/status')
            .then(response => response.json())
            .then(data => {
                console.log('Collection status refreshed:', data);
            })
            .finally(() => {
                btn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Refresh';
                btn.disabled = false;
            });
    }

    function triggerDataUpdate() {
        if (confirm('데이터를 업데이트하시겠습니까?')) {
            fetch('/api/collection/enable', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    alert('데이터 업데이트가 시작되었습니다.');
                    location.reload();
                })
                .catch(error => {
                    alert('데이터 업데이트 실패: ' + error.message);
                });
        }
    }

    function runHealthCheck() {
        fetch('/health')
            .then(response => response.json())
            .then(data => {
                const status = data.status === 'healthy' ? '정상' : '문제 있음';
                const uptime = data.uptime_human || 'Unknown';
                alert(`시스템 상태: ${status}\\n업타임: ${uptime}`);
            })
            .catch(error => {
                alert('시스템 점검 실패: ' + error.message);
            });
    }

    function exportReport() {
        window.open('/api/fortigate', '_blank');
    }

    function showApiDocs() {
        alert('API 문서:\\n\\n- GET /api/blacklist/active\\n- GET /api/fortigate\\n- GET /api/stats\\n- POST /api/collection/enable');
    }

    // CSS 애니메이션 추가
    const style = document.createElement('style');
    style.textContent = `
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    `;
    document.head.appendChild(style);
    </script>
</body>
</html>'''

@application.route('/')
def index():
    """메인 대시보드"""
    return render_template_string(DASHBOARD_HTML, 
        total_ips=len(blacklist_data),
        active_ips=len(blacklist_data),
        collection_enabled=collection_enabled,
        last_update=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        threat_count=1234,
        collection_sources=3,
        countries_count=50,
        performance_score=98
    )

@application.route('/health')
def health():
    """헬스 체크"""
    uptime = datetime.utcnow() - START_TIME
    uptime_seconds = int(uptime.total_seconds())
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'blacklist-unified',
        'version': '2.0.0-simplified',
        'uptime_seconds': uptime_seconds,
        'uptime_human': f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m {uptime_seconds % 60}s",
        'start_time': START_TIME.isoformat(),
        'total_ips': len(blacklist_data),
        'collection_enabled': collection_enabled,
        'environment': {
            'port': os.environ.get('PORT', 8541),
            'flask_env': os.environ.get('FLASK_ENV', 'development')
        }
    })

@application.route('/api/blacklist/active')
def get_blacklist():
    """활성 블랙리스트"""
    ip_list = '\n'.join(blacklist_data) if blacklist_data else ''
    return Response(ip_list, mimetype='text/plain', 
                   headers={'X-Total-Count': str(len(blacklist_data))})

@application.route('/api/fortigate')
def get_fortigate():
    """FortiGate 형식"""
    return jsonify({
        "threat_feed": {
            "name": "Nextrade Blacklist",
            "description": "통합 위협 IP 목록",
            "entries": [{"ip": ip, "type": "malicious"} for ip in blacklist_data]
        },
        "total_count": len(blacklist_data),
        "last_updated": datetime.utcnow().isoformat()
    })

@application.route('/api/stats')
def get_stats():
    """시스템 통계"""
    return jsonify({
        'success': True,
        'data': {
            'total_ips': len(blacklist_data),
            'active_ips': len(blacklist_data),
            'collection_enabled': collection_enabled,
            'sources': {
                'regtech': {'count': 0, 'status': 'configured'},
                'secudium': {'count': 0, 'status': 'configured'}
            },
            'last_updated': datetime.utcnow().isoformat()
        }
    })

@application.route('/api/collection/status')
def collection_status():
    """수집 상태"""
    return jsonify({
        'collection_enabled': collection_enabled,
        'sources': {
            'regtech': {'enabled': collection_enabled, 'last_run': None},
            'secudium': {'enabled': collection_enabled, 'last_run': None}
        },
        'total_ips': len(blacklist_data)
    })

@application.route('/api/collection/enable', methods=['POST'])
def enable_collection():
    """수집 활성화"""
    global collection_enabled
    collection_enabled = True
    return jsonify({
        'success': True,
        'message': '수집이 활성화되었습니다',
        'collection_enabled': collection_enabled
    })

@application.route('/api/collection/disable', methods=['POST']) 
def disable_collection():
    """수집 비활성화"""
    global collection_enabled
    collection_enabled = False
    return jsonify({
        'success': True,
        'message': '수집이 비활성화되었습니다',
        'collection_enabled': collection_enabled
    })

@application.route('/api/collection/regtech/trigger', methods=['POST'])
def trigger_regtech():
    """REGTECH 수집 트리거"""
    return jsonify({
        'success': True,
        'message': 'REGTECH 수집이 시작되었습니다',
        'task_id': f"regtech_{int(time.time())}"
    })

@application.route('/api/collection/secudium/trigger', methods=['POST'])
def trigger_secudium():
    """SECUDIUM 수집 트리거"""
    return jsonify({
        'success': True,
        'message': 'SECUDIUM 수집이 시작되었습니다', 
        'task_id': f"secudium_{int(time.time())}"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8541))
    print(f"Starting Blacklist Unified App on port {port}")
    print(f"Start time: {START_TIME.isoformat()}")
    application.run(host='0.0.0.0', port=port, debug=False)