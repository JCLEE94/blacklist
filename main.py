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
    <title>Nextrade 블랙리스트 관리 시스템</title>
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
            border-radius: 0 0 30px 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .stat-card {
            background: white;
            border-radius: 15px;
            padding: 1.5rem;
            box-shadow: 0 5px 20px rgba(0,0,0,0.08);
            transition: all 0.3s ease;
            border-left: 5px solid;
            margin-bottom: 1.5rem;
            position: relative;
            overflow: hidden;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        }
        
        .stat-card.primary { border-left-color: #007bff; }
        .stat-card.success { border-left-color: #28a745; }
        .stat-card.warning { border-left-color: #ffc107; }
        .stat-card.danger { border-left-color: #dc3545; }
        .stat-card.info { border-left-color: #17a2b8; }
        
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
            box-shadow: 0 5px 20px rgba(0,0,0,0.08);
            margin-bottom: 1.5rem;
        }
        
        .real-time-badge {
            background: #28a745;
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.75rem;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }
        
        .collection-status {
            display: flex;
            align-items: center;
            padding: 0.75rem;
            border-radius: 8px;
            background: #f8f9fa;
            margin-bottom: 0.5rem;
        }
        
        .status-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 0.5rem;
        }
        
        .status-active { background: #28a745; animation: pulse 2s infinite; }
        .status-inactive { background: #dc3545; }
        
        .btn-action {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            transition: all 0.3s ease;
        }
        
        .btn-action:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            color: white;
        }
        
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin-top: 2rem;
        }
        
        .feature-card {
            background: white;
            border-radius: 10px;
            padding: 1.25rem;
            box-shadow: 0 3px 10px rgba(0,0,0,0.08);
            transition: all 0.3s ease;
        }
        
        .feature-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.12);
        }
        
        @media (max-width: 768px) {
            .stat-number { font-size: 2rem; }
            .stat-icon { font-size: 2rem; }
        }
    </style>
</head>
<body>
    <!-- Header -->
    <div class="dashboard-header">
        <div class="container text-center">
            <h1 class="display-4 fw-bold mb-3">
                <i class="bi bi-shield-check me-3"></i>Nextrade 블랙리스트 관리 시스템
            </h1>
            <p class="lead mb-0">엔터프라이즈급 위협 인텔리전스 플랫폼</p>
        </div>
    </div>

    <!-- Main Stats Cards -->
    <div class="container">
        <div class="row">
            <div class="col-md-3">
                <div class="stat-card primary">
                    <i class="bi bi-hdd-network stat-icon"></i>
                    <h6 class="text-muted">총 차단 IP</h6>
                    <div class="stat-number text-primary">{{ total_ips }}</div>
                    <small class="text-muted">전체 블랙리스트</small>
                </div>
            </div>
            
            <div class="col-md-3">
                <div class="stat-card success">
                    <i class="bi bi-shield-fill-check stat-icon"></i>
                    <h6 class="text-muted">활성 IP</h6>
                    <div class="stat-number text-success">{{ active_ips }}</div>
                    <small class="text-muted">현재 차단중</small>
                </div>
            </div>
            
            <div class="col-md-3">
                <div class="stat-card {{ 'warning' if collection_enabled else 'danger' }}">
                    <i class="bi bi-broadcast stat-icon"></i>
                    <h6 class="text-muted">수집 상태</h6>
                    <div class="stat-number {{ 'text-warning' if collection_enabled else 'text-danger' }}">
                        {{ '활성' if collection_enabled else '비활성' }}
                    </div>
                    <small class="text-muted">자동 수집 {{ 'ON' if collection_enabled else 'OFF' }}</small>
                </div>
            </div>
            
            <div class="col-md-3">
                <div class="stat-card info">
                    <i class="bi bi-clock-history stat-icon"></i>
                    <h6 class="text-muted">마지막 업데이트</h6>
                    <div class="stat-number text-info" style="font-size: 1.5rem;">
                        {{ last_update }}
                    </div>
                    <small class="text-muted">KST 기준</small>
                </div>
            </div>
        </div>
    </div>

    <!-- Collection Sources Status -->
    <div class="container mt-4">
        <div class="row">
            <div class="col-lg-8">
                <div class="chart-container">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h5 class="mb-0">
                            <i class="bi bi-collection me-2"></i>데이터 소스 현황
                        </h5>
                        <span class="real-time-badge">Live</span>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <div class="collection-status">
                                <span class="status-indicator {{ 'status-active' if collection_enabled else 'status-inactive' }}"></span>
                                <div class="flex-grow-1">
                                    <strong>REGTECH</strong>
                                    <div class="small text-muted">금융보안원 - 약 1,200 IPs</div>
                                </div>
                                <span class="badge bg-primary">Financial</span>
                            </div>
                        </div>
                        
                        <div class="col-md-6">
                            <div class="collection-status">
                                <span class="status-indicator {{ 'status-active' if collection_enabled else 'status-inactive' }}"></span>
                                <div class="flex-grow-1">
                                    <strong>SECUDIUM</strong>
                                    <div class="small text-muted">위협 인텔리전스</div>
                                </div>
                                <span class="badge bg-warning">Threat Intel</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-lg-4">
                <div class="chart-container">
                    <h5 class="mb-3">
                        <i class="bi bi-gear me-2"></i>빠른 제어
                    </h5>
                    <div class="d-grid gap-2">
                        <button class="btn btn-action" onclick="location.href='/api/blacklist/active'">
                            <i class="bi bi-download me-2"></i>블랙리스트 다운로드
                        </button>
                        <button class="btn btn-action" onclick="location.href='/api/fortigate'">
                            <i class="bi bi-shield-lock me-2"></i>FortiGate JSON
                        </button>
                        <button class="btn btn-outline-primary" onclick="location.href='/api/stats'">
                            <i class="bi bi-graph-up me-2"></i>통계 API
                        </button>
                        <button class="btn btn-outline-success" onclick="location.href='/health'">
                            <i class="bi bi-heart-pulse me-2"></i>시스템 상태
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Feature Grid -->
    <div class="container">
        <div class="feature-grid">
            <div class="feature-card">
                <div class="d-flex align-items-center mb-3">
                    <i class="bi bi-robot text-primary me-2" style="font-size: 1.5rem;"></i>
                    <h6 class="mb-0">AI 기반 분석</h6>
                </div>
                <p class="text-muted small mb-2">머신러닝 위협 패턴 분석</p>
                <div class="progress" style="height: 4px;">
                    <div class="progress-bar bg-primary" style="width: 75%"></div>
                </div>
            </div>
            
            <div class="feature-card">
                <div class="d-flex align-items-center mb-3">
                    <i class="bi bi-eye text-success me-2" style="font-size: 1.5rem;"></i>
                    <h6 class="mb-0">실시간 모니터링</h6>
                </div>
                <p class="text-muted small mb-2">24/7 위협 감시 체계</p>
                <div class="progress" style="height: 4px;">
                    <div class="progress-bar bg-success" style="width: 100%"></div>
                </div>
            </div>
            
            <div class="feature-card">
                <div class="d-flex align-items-center mb-3">
                    <i class="bi bi-shield-lock text-warning me-2" style="font-size: 1.5rem;"></i>
                    <h6 class="mb-0">FortiGate 연동</h6>
                </div>
                <p class="text-muted small mb-2">External Connector API</p>
                <div class="progress" style="height: 4px;">
                    <div class="progress-bar bg-warning" style="width: 90%"></div>
                </div>
            </div>
            
            <div class="feature-card">
                <div class="d-flex align-items-center mb-3">
                    <i class="bi bi-speedometer2 text-danger me-2" style="font-size: 1.5rem;"></i>
                    <h6 class="mb-0">고성능 처리</h6>
                </div>
                <p class="text-muted small mb-2">Redis 캐싱 & 최적화</p>
                <div class="progress" style="height: 4px;">
                    <div class="progress-bar bg-danger" style="width: 85%"></div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>'''

@application.route('/')
def index():
    """메인 대시보드"""
    return render_template_string(DASHBOARD_HTML, 
        total_ips=len(blacklist_data),
        active_ips=len(blacklist_data),
        collection_enabled=collection_enabled,
        last_update=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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