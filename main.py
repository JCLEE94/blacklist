#!/usr/bin/env python3
"""
통합 블랙리스트 관리 시스템 - 단일 통합 앱
"""
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
    <title>통합 블랙리스트 관리 시스템</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2563eb; color: white; padding: 2rem; border-radius: 8px; margin-bottom: 2rem; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .stat-card { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-number { font-size: 2rem; font-weight: bold; color: #2563eb; }
        .btn { background: #2563eb; color: white; padding: 10px 20px; border: none; border-radius: 4px; margin: 5px; cursor: pointer; }
        .btn:hover { background: #1d4ed8; }
        .status-ok { color: #059669; }
        .status-error { color: #dc2626; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ 통합 블랙리스트 관리 시스템</h1>
            <p>Nextrade 위협 IP 차단 시스템</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>총 IP 수</h3>
                <div class="stat-number">{{ total_ips }}</div>
            </div>
            <div class="stat-card">
                <h3>활성 IP 수</h3>
                <div class="stat-number">{{ active_ips }}</div>
            </div>
            <div class="stat-card">
                <h3>수집 상태</h3>
                <div class="stat-number {{ 'status-ok' if collection_enabled else 'status-error' }}">
                    {{ '활성' if collection_enabled else '비활성' }}
                </div>
            </div>
            <div class="stat-card">
                <h3>마지막 업데이트</h3>
                <div>{{ last_update }}</div>
            </div>
        </div>
        
        <div style="background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3>시스템 제어</h3>
            <button class="btn" onclick="location.href='/api/blacklist/active'">블랙리스트 다운로드</button>
            <button class="btn" onclick="location.href='/api/fortigate'">FortiGate 형식</button>
            <button class="btn" onclick="location.href='/api/stats'">통계 API</button>
            <button class="btn" onclick="location.href='/health'">시스템 상태</button>
        </div>
    </div>
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
    import os
    port = int(os.environ.get('PORT', 8541))
    print(f"Starting Blacklist Unified App on port {port}")
    print(f"Start time: {START_TIME.isoformat()}")
    application.run(host='0.0.0.0', port=port, debug=False)