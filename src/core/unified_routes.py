"""
통합 API 라우트
모든 블랙리스트 API를 하나로 통합한 라우트 시스템
"""
from flask import Blueprint, request, jsonify, Response, render_template
from typing import Dict, Any
import logging
import asyncio
from datetime import datetime

from .unified_service import get_unified_service
from .exceptions import ValidationError, handle_exception, create_error_response
from .validators import validate_ip
# Decorators removed to fix Flask endpoint conflicts
# from src.utils.unified_decorators import public_endpoint, api_endpoint

logger = logging.getLogger(__name__)

# 통합 라우트 블루프린트
unified_bp = Blueprint('unified', __name__)

# 통합 서비스 인스턴스
service = get_unified_service()

# === 웹 인터페이스 ===

def _get_dashboard_data():
    """대시보드 데이터 준비 (공통 함수)"""
    from datetime import datetime
    
    try:
        # 실제 통계 데이터 수집
        stats = service.get_system_health()
    except Exception as e:
        logger.error(f"Dashboard data collection error: {e}")
        # 기본값 사용
        stats = {
            'total_ips': 0,
            'active_ips': 0,
            'regtech_count': 0,
            'secudium_count': 0,
            'public_count': 0
        }
    
    # 템플릿 데이터 준비
    template_data = {
        'total_ips': stats.get('total_ips', 0),
        'active_ips': stats.get('active_ips', 0),
        'active_sources': ['REGTECH', 'SECUDIUM', 'Public'],
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'monthly_data': [
            {'month': '11월', 'count': 1200},
            {'month': '12월', 'count': 1350},
            {'month': '1월', 'count': 1500}
        ],
        'source_distribution': {
            'regtech': {'count': stats.get('regtech_count', 0), 'percentage': 45},
            'secudium': {'count': stats.get('secudium_count', 0), 'percentage': 30},
            'public': {'count': stats.get('public_count', 0), 'percentage': 25}
        }
    }
    return template_data

@unified_bp.route('/', methods=['GET'])
def index():
    """메인페이지 - 대시보드"""
    try:
        return render_template('dashboard.html', **_get_dashboard_data())
    except Exception as e:
        logger.error(f"Dashboard template error: {e}")
        return jsonify({
            'error': 'Dashboard rendering failed',
            'message': str(e),
            'fallback': 'Try /test for a simple page'
        }), 500

@unified_bp.route('/dashboard', methods=['GET'])
def dashboard():
    """대시보드 (메인페이지와 동일)"""
    try:
        return render_template('dashboard.html', **_get_dashboard_data())
    except Exception as e:
        logger.error(f"Dashboard template error: {e}")
        return jsonify({
            'error': 'Dashboard rendering failed',
            'message': str(e),
            'fallback': 'Try /test for a simple page'
        }), 500

@unified_bp.route('/api/docs', methods=['GET'])
def api_dashboard():
    """API 문서"""
    return jsonify({
        'message': 'API Documentation',
        'dashboard_url': '/',
        'note': 'Visit / or /dashboard for the web interface',
        'api_endpoints': {
            'health': '/health',
            'stats': '/api/stats', 
            'blacklist': '/api/blacklist/active',
            'fortigate': '/api/fortigate',
            'collection': '/api/collection/status'
        }
    })

@unified_bp.route('/test', methods=['GET'])
def test_page():
    """간단한 테스트 페이지"""
    return "<html><body><h1>Test Page Working</h1><p>Simple HTML without templates</p></body></html>"

@unified_bp.route('/docker/logs', methods=['GET'])
def docker_logs_page():
    """Docker 로그 조회 페이지"""
    return render_template('docker_logs.html')

# === Additional web pages ===

@unified_bp.route('/search', methods=['GET'])
def blacklist_search():
    """IP 검색 페이지"""
    try:
        return render_template('blacklist_search.html')
    except Exception as e:
        logger.error(f"Search page error: {e}")
        return jsonify({
            'error': 'Search page not available',
            'message': str(e),
            'fallback': 'Use /api/search/<ip> for direct search'
        }), 500

@unified_bp.route('/collection-control', methods=['GET'])
def collection_control():
    """수집 제어 패널 페이지"""
    try:
        return render_template('collection_control.html')
    except Exception as e:
        logger.error(f"Collection control page error: {e}")
        return jsonify({
            'error': 'Collection control page not available',
            'message': str(e),
            'fallback': 'Use /api/collection/status for status'
        }), 500

@unified_bp.route('/connection-status', methods=['GET'])
def connection_status():
    """연결 상태 페이지"""
    try:
        return render_template('connection_status.html')
    except Exception as e:
        logger.error(f"Connection status page error: {e}")
        return jsonify({
            'error': 'Connection status page not available',
            'message': str(e),
            'fallback': 'Use /health for system health'
        }), 500

@unified_bp.route('/data-management', methods=['GET'])
def data_management():
    """데이터 관리 페이지"""
    try:
        return render_template('data_management.html')
    except Exception as e:
        logger.error(f"Data management page error: {e}")
        return jsonify({
            'error': 'Data management page not available',
            'message': str(e),
            'fallback': 'Use /api/stats for data information'
        }), 500

@unified_bp.route('/system-logs', methods=['GET'])
def system_logs():
    """시스템 로그 페이지"""
    try:
        return render_template('system_logs.html')
    except Exception as e:
        logger.error(f"System logs page error: {e}")
        return redirect(url_for('unified.docker_logs_page'))

@unified_bp.route('/statistics', methods=['GET'])
def statistics():
    """통계 페이지"""
    try:
        return render_template('statistics.html')
    except Exception as e:
        logger.error(f"Statistics page error: {e}")
        return jsonify({
            'error': 'Statistics page not available',
            'message': str(e),
            'fallback': 'Use /api/stats for statistics data'
        }), 500

@unified_bp.route('/export/<format>', methods=['GET'])
def export_data(format):
    """데이터 내보내기"""
    try:
        if format == 'json':
            ips = service.get_active_blacklist_ips()
            return jsonify({
                'success': True,
                'data': ips,
                'count': len(ips),
                'timestamp': datetime.utcnow().isoformat()
            })
        elif format == 'csv':
            # CSV 형식으로 내보내기
            ips = service.get_active_blacklist_ips()
            csv_content = "IP Address\n" + "\n".join(ips)
            response = Response(
                csv_content,
                mimetype='text/csv',
                headers={'Content-Disposition': 'attachment; filename=blacklist.csv'}
            )
            return response
        else:
            return jsonify({
                'success': False,
                'error': 'Unsupported format. Use json or csv.'
            }), 400
    except Exception as e:
        logger.error(f"Export data error: {e}")
        return jsonify(create_error_response(e)), 500

# === 핵심 API 엔드포인트 ===

@unified_bp.route('/health', methods=['GET'])

def health_check():
    """통합 서비스 헬스 체크"""
    try:
        health_info = service.get_system_health()
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'blacklist-unified',
            'version': '2.0.0',
            'details': health_info
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 503

@unified_bp.route('/api/health', methods=['GET'])
def service_status():
    """서비스 상태 조회"""
    try:
        stats = service.get_system_stats()
        return jsonify({
            'success': True,
            'data': {
                'service_status': 'running',
                'database_connected': True,
                'cache_available': True,
                'total_ips': stats.get('total_ips', 0),
                'active_ips': stats.get('active_ips', 0),
                'last_updated': datetime.utcnow().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Service status error: {e}")
        return jsonify(create_error_response(e)), 500

@unified_bp.route('/api/blacklist/active', methods=['GET'])

def get_active_blacklist():
    """활성 블랙리스트 조회 (플레인 텍스트)"""
    try:
        ips = service.get_active_blacklist_ips()
        
        # 플레인 텍스트 형식으로 반환
        ip_list = '\n'.join(ips) if ips else ''
        
        response = Response(
            ip_list,
            mimetype='text/plain',
            headers={
                'Content-Disposition': 'attachment; filename=blacklist.txt',
                'X-Total-Count': str(len(ips))
            }
        )
        return response
    except Exception as e:
        logger.error(f"Active blacklist error: {e}")
        return jsonify(create_error_response(e)), 500

@unified_bp.route('/api/fortigate', methods=['GET'])

def get_fortigate_format():
    """FortiGate External Connector 형식"""
    try:
        ips = service.get_active_blacklist_ips()
        
        # FortiGate 형식으로 변환
        fortigate_data = service.format_for_fortigate(ips)
        return jsonify(fortigate_data)
    except Exception as e:
        logger.error(f"FortiGate format error: {e}")
        return jsonify(create_error_response(e)), 500

@unified_bp.route('/api/blacklist/json', methods=['GET'])
 
def get_blacklist_json():
    """블랙리스트 JSON 형식"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 100, type=int), 1000)
        source = request.args.get('source')
        
        result = service.get_blacklist_paginated(
            page=page,
            per_page=per_page,
            source_filter=source
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Blacklist JSON error: {e}")
        return jsonify(create_error_response(e)), 500

@unified_bp.route('/api/search/<ip>', methods=['GET'])

def search_single_ip(ip: str):
    """단일 IP 검색"""
    try:
        # IP 유효성 검증
        if not validate_ip(ip):
            return jsonify({
                'success': False,
                'error': 'Invalid IP address format'
            }), 400
        
        # IP 검색
        result = service.search_ip(ip)
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        logger.error(f"Single IP search error: {e}")
        return jsonify(create_error_response(e)), 500

@unified_bp.route('/api/search', methods=['POST'])

def search_batch_ips():
    """배치 IP 검색"""
    try:
        data = request.get_json()
        if not data or 'ips' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing ips field in request body'
            }), 400
        
        ips = data['ips']
        if not isinstance(ips, list):
            return jsonify({
                'success': False,
                'error': 'ips must be a list'
            }), 400
        
        # 최대 100개로 제한
        if len(ips) > 100:
            return jsonify({
                'success': False,
                'error': 'Maximum 100 IPs allowed per request'
            }), 400
        
        # 배치 검색
        results = service.search_batch_ips(ips)
        
        return jsonify({
            'success': True,
            'data': results
        })
    except Exception as e:
        logger.error(f"Batch IP search error: {e}")
        return jsonify(create_error_response(e)), 500

@unified_bp.route('/api/stats', methods=['GET'])

def get_system_stats():
    """시스템 통계"""
    try:
        stats = service.get_system_stats()
        return jsonify({
            'success': True,
            'data': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"System stats error: {e}")
        return jsonify(create_error_response(e)), 500

@unified_bp.route('/api/analytics/summary', methods=['GET'])

def get_analytics_summary():
    """분석 요약"""
    try:
        # 분석 기간 파라미터
        days = request.args.get('days', 7, type=int)
        if days > 90:
            days = 90  # 최대 90일
        
        summary = service.get_analytics_summary(days=days)
        
        return jsonify({
            'success': True,
            'data': summary,
            'period_days': days
        })
    except Exception as e:
        logger.error(f"Analytics summary error: {e}")
        return jsonify(create_error_response(e)), 500

# === 수집 관리 API ===

@unified_bp.route('/api/collection/status', methods=['GET'])

def get_collection_status():
    """수집 시스템 상태"""
    try:
        status = service.get_collection_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Collection status error: {e}")
        return jsonify(create_error_response(e)), 500

@unified_bp.route('/api/collection/enable', methods=['POST'])

def enable_collection():
    """수집 시스템 활성화"""
    try:
        result = service.enable_collection()
        return jsonify({
            'success': True,
            'message': '수집이 활성화되었습니다. 기존 데이터가 클리어되었습니다.',
            'data': result
        })
    except Exception as e:
        logger.error(f"Enable collection error: {e}")
        return jsonify(create_error_response(e)), 500

@unified_bp.route('/api/collection/disable', methods=['POST'])

def disable_collection():
    """수집 시스템 비활성화"""
    try:
        result = service.disable_collection()
        return jsonify({
            'success': True,
            'message': '수집이 비활성화되었습니다.',
            'data': result
        })
    except Exception as e:
        logger.error(f"Disable collection error: {e}")
        return jsonify(create_error_response(e)), 500

@unified_bp.route('/api/collection/trigger', methods=['POST'])
  
def trigger_manual_collection():
    """수동 데이터 수집 트리거"""
    try:
        data = request.get_json() or {}
        source = data.get('source', 'all')
        
        if source not in ['all', 'regtech', 'secudium']:
            return jsonify({
                'success': False,
                'error': 'Invalid source. Must be one of: all, regtech, secudium'
            }), 400
        
        # 비동기 수집 시작
        task_id = service.trigger_collection(source=source)
        
        return jsonify({
            'success': True,
            'message': f'수집이 시작되었습니다 (소스: {source})',
            'task_id': task_id
        })
    except Exception as e:
        logger.error(f"Manual collection trigger error: {e}")
        return jsonify(create_error_response(e)), 500

@unified_bp.route('/api/collection/regtech/trigger', methods=['POST'])

def trigger_regtech_collection():
    """REGTECH 수집 트리거"""
    try:
        data = request.get_json() or {}
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # 날짜 파라미터가 있으면 사용, 없으면 기본값
        task_id = service.trigger_regtech_collection(
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify({
            'success': True,
            'message': 'REGTECH 수집이 시작되었습니다.',
            'task_id': task_id,
            'start_date': start_date,
            'end_date': end_date
        })
    except Exception as e:
        logger.error(f"REGTECH collection trigger error: {e}")
        return jsonify(create_error_response(e)), 500

@unified_bp.route('/api/collection/secudium/trigger', methods=['POST'])

def trigger_secudium_collection():
    """SECUDIUM 수집 트리거"""
    try:
        task_id = service.trigger_secudium_collection()
        
        return jsonify({
            'success': True,
            'message': 'SECUDIUM 수집이 시작되었습니다.',
            'task_id': task_id
        })
    except Exception as e:
        logger.error(f"SECUDIUM collection trigger error: {e}")
        return jsonify(create_error_response(e)), 500

# === 시스템 관리 API ===

@unified_bp.route('/api/system/docker/logs', methods=['GET'])

def get_docker_logs():
    """Docker 컨테이너 로그 조회"""
    import subprocess
    import os
    
    try:
        # 쿼리 파라미터
        container_name = request.args.get('container', 'blacklist-app-1')
        lines = min(request.args.get('lines', 100, type=int), 1000)  # 최대 1000줄
        follow = request.args.get('follow', 'false').lower() == 'true'
        since = request.args.get('since', '')  # 예: '10m', '1h', '2023-01-01'
        
        # Docker 명령어 구성
        cmd = ['docker', 'logs']
        
        if since:
            cmd.extend(['--since', since])
        
        if follow:
            cmd.append('-f')
        
        cmd.extend(['-n', str(lines), container_name])
        
        # 보안: 컨테이너 이름 검증
        allowed_containers = [
            'blacklist-app-1', 'blacklist-redis', 'blacklist-unified',
            'blacklist-db', 'blacklist-nginx'
        ]
        
        if container_name not in allowed_containers:
            return jsonify({
                'success': False,
                'error': 'Invalid container name',
                'allowed_containers': allowed_containers
            }), 400
        
        # Docker 명령어 실행
        if follow:
            # 실시간 로그의 경우 스트리밍 응답
            def generate_logs():
                try:
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        bufsize=1
                    )
                    
                    for line in iter(process.stdout.readline, ''):
                        yield f"data: {line}\n\n"
                    
                    process.stdout.close()
                    process.wait()
                except Exception as e:
                    yield f"data: Error: {str(e)}\n\n"
            
            from flask import Response
            return Response(
                generate_logs(),
                mimetype='text/plain',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Container-Name': container_name
                }
            )
        else:
            # 일반 로그 조회
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return jsonify({
                    'success': False,
                    'error': f'Docker logs failed: {result.stderr}',
                    'container': container_name
                }), 500
            
            # 로그 라인을 배열로 변환
            log_lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            return jsonify({
                'success': True,
                'data': {
                    'container': container_name,
                    'lines_count': len(log_lines),
                    'logs': log_lines,
                    'timestamp': datetime.utcnow().isoformat()
                }
            })
    
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Docker logs command timed out',
            'container': container_name
        }), 504
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': 'Docker command not found. Is Docker installed?'
        }), 503
    except Exception as e:
        logger.error(f"Docker logs error: {e}")
        return jsonify(create_error_response(e)), 500

@unified_bp.route('/api/system/docker/containers', methods=['GET'])

def list_docker_containers():
    """Docker 컨테이너 목록 조회"""
    import subprocess
    
    try:
        # Docker ps 명령어 실행
        result = subprocess.run(
            ['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return jsonify({
                'success': False,
                'error': f'Docker ps failed: {result.stderr}'
            }), 500
        
        # 결과 파싱
        lines = result.stdout.strip().split('\n')
        containers = []
        
        if len(lines) > 1:  # 헤더 제외
            for line in lines[1:]:
                parts = line.split('\t')
                if len(parts) >= 4:
                    containers.append({
                        'name': parts[0],
                        'status': parts[1],
                        'ports': parts[2],
                        'image': parts[3]
                    })
        
        return jsonify({
            'success': True,
            'data': {
                'containers': containers,
                'count': len(containers),
                'timestamp': datetime.utcnow().isoformat()
            }
        })
    
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Docker ps command timed out'
        }), 504
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': 'Docker command not found. Is Docker installed?'
        }), 503
    except Exception as e:
        logger.error(f"Docker containers list error: {e}")
        return jsonify(create_error_response(e)), 500

# === 향상된 API (v2) ===

@unified_bp.route('/api/v2/blacklist/enhanced', methods=['GET'])

def get_enhanced_blacklist():
    """향상된 블랙리스트 (메타데이터 포함)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 500)
        include_metadata = request.args.get('metadata', 'true').lower() == 'true'
        source_filter = request.args.get('source')
        
        result = service.get_enhanced_blacklist(
            page=page,
            per_page=per_page,
            include_metadata=include_metadata,
            source_filter=source_filter
        )
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        logger.error(f"Enhanced blacklist error: {e}")
        return jsonify(create_error_response(e)), 500

# === 에러 핸들러 ===

@unified_bp.errorhandler(404)
def not_found_error(error):
    """404 에러 핸들러"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'message': 'The requested API endpoint does not exist',
        'available_endpoints': [
            '/health', '/api/docs', '/dashboard',
            '/api/blacklist/active', '/api/fortigate', 
            '/api/stats', '/api/collection/status'
        ]
    }), 404

@unified_bp.errorhandler(500)
def internal_error(error):
    """500 에러 핸들러"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500