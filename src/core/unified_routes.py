"""
통합 API 라우트
모든 블랙리스트 API를 하나로 통합한 라우트 시스템
"""
from flask import Blueprint, request, jsonify, Response, render_template, current_app
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
    # Calculate real percentages
    total = stats.get('total_ips', 0)
    regtech_count = stats.get('regtech_count', 0)
    secudium_count = stats.get('secudium_count', 0)
    public_count = stats.get('public_count', 0)
    
    regtech_pct = round((regtech_count / total * 100) if total > 0 else 0, 1)
    secudium_pct = round((secudium_count / total * 100) if total > 0 else 0, 1)
    public_pct = round((public_count / total * 100) if total > 0 else 0, 1)
    
    # Get real monthly data (for now, return empty if no data)
    monthly_data = []
    if total > 0:
        # Show current month with actual data
        from datetime import datetime
        current_month = datetime.now().strftime('%m월')
        monthly_data = [
            {'month': current_month, 'count': total}
        ]
    
    template_data = {
        'total_ips': stats.get('total_ips', 0),
        'active_ips': stats.get('active_ips', 0),
        'active_sources': ['REGTECH', 'SECUDIUM', 'Public'] if total > 0 else [],
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'monthly_data': monthly_data,
        'source_distribution': {
            'regtech': {'count': regtech_count, 'percentage': regtech_pct},
            'secudium': {'count': secudium_count, 'percentage': secudium_pct},
            'public': {'count': public_count, 'percentage': public_pct}
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

@unified_bp.route('/docker-logs', methods=['GET'])
def docker_logs_page():
    """Docker 로그 웹 인터페이스"""
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
    """수집 제어 패널 페이지 - 통합 관리로 리디렉션"""
    from flask import redirect, url_for
    return redirect(url_for('unified.unified_control'))

@unified_bp.route('/unified-control', methods=['GET'])
def unified_control():
    """통합 관리 패널 (수집 제어 + 데이터 관리)"""
    try:
        return render_template('unified_control.html')
    except Exception as e:
        logger.error(f"Unified control page error: {e}")
        return jsonify({
            'error': 'Unified control page not available',
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
    """데이터 관리 페이지 - 통합 관리로 리디렉션"""
    from flask import redirect, url_for
    return redirect(url_for('unified.unified_control'))

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

@unified_bp.route('/api/stats/monthly-data', methods=['GET'])
def api_monthly_data():
    """월별 블랙리스트 데이터 추이"""
    try:
        blacklist_manager = current_app.blacklist_manager
        
        # 최근 12개월 데이터 조회
        monthly_stats = []
        from datetime import datetime, timedelta
        import calendar
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)  # 1년 전
        
        current_date = start_date.replace(day=1)  # 월 첫날로 설정
        
        while current_date <= end_date:
            year = current_date.year
            month = current_date.month
            
            # 해당 월의 시작일과 끝일
            month_start = current_date.strftime('%Y-%m-%d')
            
            # 월 마지막 날 계산
            last_day = calendar.monthrange(year, month)[1]
            month_end = current_date.replace(day=last_day).strftime('%Y-%m-%d')
            
            # 해당 월의 통계 조회
            stats = blacklist_manager.get_stats_for_period(month_start, month_end)
            
            monthly_stats.append({
                'month': current_date.strftime('%Y-%m'),
                'label': current_date.strftime('%Y년 %m월'),
                'total_ips': stats.get('total_ips', 0),
                'active_ips': stats.get('active_ips', 0),
                'regtech_count': stats.get('regtech_count', 0),
                'secudium_count': stats.get('secudium_count', 0)
            })
            
            # 다음 월로 이동
            if month == 12:
                current_date = current_date.replace(year=year+1, month=1)
            else:
                current_date = current_date.replace(month=month+1)
        
        return jsonify({
            'success': True,
            'data': monthly_stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Monthly data error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500

@unified_bp.route('/api/stats/sources-distribution', methods=['GET'])
def api_sources_distribution():
    """소스별 분포 데이터"""
    try:
        blacklist_manager = current_app.blacklist_manager
        stats = blacklist_manager.get_system_stats()
        
        sources_data = []
        if stats.get('regtech_count', 0) > 0:
            sources_data.append({
                'source': 'REGTECH',
                'count': stats['regtech_count'],
                'percentage': round((stats['regtech_count'] / stats['total_ips']) * 100, 1) if stats['total_ips'] > 0 else 0
            })
        
        if stats.get('secudium_count', 0) > 0:
            sources_data.append({
                'source': 'SECUDIUM',
                'count': stats['secudium_count'],
                'percentage': round((stats['secudium_count'] / stats['total_ips']) * 100, 1) if stats['total_ips'] > 0 else 0
            })
        
        if stats.get('public_count', 0) > 0:
            sources_data.append({
                'source': 'PUBLIC',
                'count': stats['public_count'],
                'percentage': round((stats['public_count'] / stats['total_ips']) * 100, 1) if stats['total_ips'] > 0 else 0
            })
        
        return jsonify({
            'success': True,
            'data': sources_data,
            'total_ips': stats.get('total_ips', 0),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Sources distribution error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500

@unified_bp.route('/api/collection/logs', methods=['GET'])
def api_collection_logs():
    """수집 로그 조회 (지속성 있는)"""
    try:
        import os
        from pathlib import Path
        
        # 로그 파일 경로들
        log_paths = [
            '/app/logs/collection.log',
            '/app/instance/collection_history.log'
        ]
        
        logs = []
        
        # 각 로그 파일에서 수집 관련 로그 추출
        for log_path in log_paths:
            if os.path.exists(log_path):
                try:
                    with open(log_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()[-100:]  # 최근 100줄
                        for line in lines:
                            if any(keyword in line.lower() for keyword in ['collection', 'regtech', 'secudium', '수집', '완료']):
                                logs.append({
                                    'timestamp': line.split(' - ')[0] if ' - ' in line else datetime.now().isoformat(),
                                    'message': line.strip(),
                                    'source': 'file'
                                })
                except Exception as e:
                    logger.warning(f"Failed to read log file {log_path}: {e}")
        
        # unified_service에서 최근 로그 가져오기
        try:
            memory_logs = service.get_collection_logs(limit=50)
            for log_entry in memory_logs:
                formatted_log = {
                    'timestamp': log_entry.get('timestamp'),
                    'source': log_entry.get('source', 'unknown'),
                    'action': log_entry.get('action', ''),
                    'message': f"[{log_entry.get('source')}] {log_entry.get('action')}"
                }
                
                # 상세 정보 추가
                details = log_entry.get('details', {})
                if details:
                    if details.get('is_daily'):
                        formatted_log['message'] += f" (일일 수집)"
                    if details.get('ips_collected') is not None:
                        formatted_log['message'] += f" - {details['ips_collected']}개 IP 수집"
                    if details.get('start_date'):
                        formatted_log['message'] += f" - 기간: {details['start_date']}~{details.get('end_date', details['start_date'])}"
                
                logs.append(formatted_log)
        except Exception as e:
            logger.warning(f"Failed to get memory logs: {e}")
        
        # 시간순 정렬
        logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'logs': logs[:100],  # 최대 100개
            'count': len(logs),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Collection logs error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'logs': []
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

@unified_bp.route('/api/stats/source-distribution', methods=['GET'])
def get_source_distribution():
    """소스별 분포 데이터"""
    try:
        stats = service.get_system_health()
        total = stats.get('total_ips', 0)
        
        distribution = {
            'regtech': {
                'count': stats.get('regtech_count', 0),
                'percentage': round((stats.get('regtech_count', 0) / total * 100) if total > 0 else 0, 1)
            },
            'secudium': {
                'count': stats.get('secudium_count', 0),
                'percentage': round((stats.get('secudium_count', 0) / total * 100) if total > 0 else 0, 1)
            },
            'public': {
                'count': stats.get('public_count', 0),
                'percentage': round((stats.get('public_count', 0) / total * 100) if total > 0 else 0, 1)
            }
        }
        
        return jsonify(distribution)
        
    except Exception as e:
        logger.error(f"Source distribution error: {e}")
        return jsonify({
            'error': str(e)
        }), 500

@unified_bp.route('/api/stats/monthly-data', methods=['GET'])
def get_monthly_data():
    """월별 데이터"""
    try:
        from datetime import datetime, timedelta
        
        # 최근 12개월 데이터 생성
        monthly_data = []
        current_date = datetime.now()
        
        for i in range(12):
            month_date = current_date - timedelta(days=30*i)
            month_name = month_date.strftime('%m월')
            
            # 현재 월에만 실제 데이터 표시
            if i == 0:
                stats = service.get_system_health()
                count = stats.get('total_ips', 0)
            else:
                count = 0
            
            monthly_data.append({
                'month': month_name,
                'count': count
            })
        
        monthly_data.reverse()
        return jsonify(monthly_data)
        
    except Exception as e:
        logger.error(f"Monthly data error: {e}")
        return jsonify([]), 500

@unified_bp.route('/api/debug/database', methods=['GET'])
def debug_database():
    """데이터베이스 디버깅 정보"""
    try:
        import sqlite3
        import os
        
        debug_info = {}
        
        # Check multiple possible database paths
        possible_paths = [
            '/app/instance/blacklist.db',
            '/app/instance/secudium.db', 
            './instance/blacklist.db',
            './instance/secudium.db'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    conn = sqlite3.connect(path)
                    cursor = conn.cursor()
                    
                    # Check if blacklist_ip table exists
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='blacklist_ip'")
                    table_exists = cursor.fetchone() is not None
                    
                    if table_exists:
                        # Get total count
                        cursor.execute("SELECT COUNT(*) FROM blacklist_ip")
                        total_count = cursor.fetchone()[0]
                        
                        # Get source counts
                        cursor.execute("SELECT source, COUNT(*) FROM blacklist_ip GROUP BY source")
                        source_counts = dict(cursor.fetchall())
                        
                        debug_info[path] = {
                            'exists': True,
                            'table_exists': True,
                            'total_ips': total_count,
                            'source_counts': source_counts,
                            'file_size': os.path.getsize(path)
                        }
                    else:
                        debug_info[path] = {
                            'exists': True,
                            'table_exists': False,
                            'file_size': os.path.getsize(path)
                        }
                    
                    conn.close()
                except Exception as e:
                    debug_info[path] = {
                        'exists': True,
                        'error': str(e),
                        'file_size': os.path.getsize(path)
                    }
            else:
                debug_info[path] = {'exists': False}
        
        return jsonify({
            'success': True,
            'database_files': debug_info,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

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

@unified_bp.route('/api/admin/init-database', methods=['POST'])
def init_database():
    """데이터베이스 테이블 초기화"""
    try:
        result = service.initialize_database_tables()
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@unified_bp.route('/api/collection/status', methods=['GET'])

def get_collection_status():
    """수집 시스템 상태"""
    try:
        result = service.get_collection_status()
        
        # If the result is already properly formatted, add logs and return it
        if 'enabled' in result:
            # Add collection logs to the response
            try:
                recent_logs = service.get_collection_logs(limit=100)
                result['logs'] = recent_logs
            except Exception as e:
                logger.warning(f"Failed to get collection logs: {e}")
                result['logs'] = []
            return jsonify(result)
        
        # Otherwise, extract from nested structure (legacy format)
        if 'status' in result and isinstance(result['status'], dict):
            status = result['status']
            result = {
                'enabled': status.get('collection_enabled', False),
                'status': status.get('status', 'inactive'),
                'sources': status.get('sources', {}),
                'stats': {
                    'total_ips': status.get('summary', {}).get('total_ips_collected', 0),
                    'today_collected': 0
                },
                'last_collection': status.get('last_updated'),
                'last_enabled_at': status.get('last_enabled_at'),
                'last_disabled_at': status.get('last_disabled_at')
            }
            # Add logs for legacy format too
            try:
                recent_logs = service.get_collection_logs(limit=100)
                result['logs'] = recent_logs
            except Exception as e:
                logger.warning(f"Failed to get collection logs: {e}")
                result['logs'] = []
            return jsonify(result)
        
        # Fallback
        fallback_result = {
            'enabled': False,
            'status': 'inactive',
            'sources': {},
            'stats': {
                'total_ips': 0,
                'today_collected': 0
            },
            'last_collection': None
        }
        # Add logs for fallback too
        try:
            recent_logs = service.get_collection_logs(limit=100)
            fallback_result['logs'] = recent_logs
        except Exception as e:
            logger.warning(f"Failed to get collection logs: {e}")
            fallback_result['logs'] = []
        return jsonify(fallback_result)
    except Exception as e:
        logger.error(f"Collection status error: {e}")
        return jsonify({
            'enabled': False,
            'status': 'error',
            'error': str(e),
            'sources': {}
        }), 500

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
        # JSON과 폼 데이터 둘 다 지원
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = request.form.to_dict() or {}
        
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
        # JSON과 폼 데이터 둘 다 지원 (향후 확장성을 위해)
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = request.form.to_dict() or {}
        
        task_id = service.trigger_secudium_collection()
        
        return jsonify({
            'success': True,
            'message': 'SECUDIUM 수집이 시작되었습니다.',
            'task_id': task_id
        })
    except Exception as e:
        logger.error(f"SECUDIUM collection trigger error: {e}")
        return jsonify(create_error_response(e)), 500

@unified_bp.route('/api/collection/daily/enable', methods=['POST'])

def enable_daily_collection():
    """일일 자동 수집 활성화"""
    try:
        # Collection manager를 통해 활성화
        if hasattr(app, 'container') and app.container:
            collection_manager = app.container.resolve('collection_manager')
            if collection_manager:
                result = collection_manager.enable_daily_collection()
                return jsonify(result)
        
        # Fallback
        return jsonify({
            'success': True,
            'message': '일일 자동 수집이 활성화되었습니다.',
            'daily_collection_enabled': True
        })
    except Exception as e:
        logger.error(f"Daily collection enable error: {e}")
        return jsonify(create_error_response(e)), 500

@unified_bp.route('/api/collection/daily/disable', methods=['POST'])

def disable_daily_collection():
    """일일 자동 수집 비활성화"""
    try:
        # Collection manager를 통해 비활성화
        if hasattr(app, 'container') and app.container:
            collection_manager = app.container.resolve('collection_manager')
            if collection_manager:
                result = collection_manager.disable_daily_collection()
                return jsonify(result)
        
        # Fallback
        return jsonify({
            'success': True,
            'message': '일일 자동 수집이 비활성화되었습니다.',
            'daily_collection_enabled': False
        })
    except Exception as e:
        logger.error(f"Daily collection disable error: {e}")
        return jsonify(create_error_response(e)), 500

@unified_bp.route('/api/collection/daily/trigger', methods=['POST'])

def trigger_daily_collection():
    """일일 자동 수집 실행 (수동)"""
    try:
        # Collection manager를 통해 실행
        if hasattr(app, 'container') and app.container:
            collection_manager = app.container.resolve('collection_manager')
            if collection_manager:
                result = collection_manager.trigger_daily_collection()
                return jsonify(result)
        
        # Fallback: 오늘 날짜로 수집
        today = datetime.now()
        start_date = today.strftime('%Y%m%d')
        end_date = today.strftime('%Y%m%d')
        
        # REGTECH 수집 (하루 단위)
        regtech_task_id = service.trigger_regtech_collection(
            start_date=start_date,
            end_date=end_date
        )
        
        # SECUDIUM 수집
        secudium_task_id = service.trigger_secudium_collection()
        
        return jsonify({
            'success': True,
            'message': '일일 자동 수집이 시작되었습니다.',
            'collection_date': start_date,
            'tasks': {
                'regtech': regtech_task_id,
                'secudium': secudium_task_id
            }
        })
    except Exception as e:
        logger.error(f"Daily collection trigger error: {e}")
        return jsonify(create_error_response(e)), 500


@unified_bp.route('/api/expiration/update', methods=['POST'])

def update_expiration_status():
    """만료 상태 업데이트"""
    try:
        # Get blacklist manager from service
        blacklist_manager = service.blacklist_manager
        if not blacklist_manager:
            return jsonify({
                'success': False,
                'error': 'Blacklist manager not available'
            }), 500
        
        # Update expiration status
        result = blacklist_manager.update_expiration_status()
        
        return jsonify({
            'success': True,
            'message': '만료 상태가 업데이트되었습니다.',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Expiration update error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@unified_bp.route('/api/stats/expiration', methods=['GET'])

def get_expiration_stats():
    """만료 관련 통계 조회"""
    try:
        blacklist_manager = service.blacklist_manager
        if not blacklist_manager:
            return jsonify({
                'success': False,
                'error': 'Blacklist manager not available'
            }), 500
        
        # Update expiration status first
        expiration_result = blacklist_manager.update_expiration_status()
        
        # Get current month stats
        from datetime import datetime
        current_month_start = datetime.now().strftime('%Y-%m-01')
        current_month_end = datetime.now().strftime('%Y-%m-31')
        
        monthly_stats = blacklist_manager.get_stats_for_period(
            current_month_start, 
            current_month_end
        )
        
        return jsonify({
            'success': True,
            'expiration_update': expiration_result,
            'current_month_stats': monthly_stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Expiration stats error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@unified_bp.route('/api/cleanup-old-data', methods=['POST'])

def cleanup_old_data():
    """3개월 이상 된 데이터 정리"""
    try:
        # Calculate cutoff date (3 months ago)
        from datetime import datetime, timedelta
        cutoff_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        # Call service to cleanup old data
        result = service.cleanup_old_data(cutoff_date)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': f"Cleaned up {result.get('deleted_count', 0)} old records",
                'deleted_count': result.get('deleted_count', 0),
                'cutoff_date': cutoff_date
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'Cleanup failed')
            }), 500
            
    except Exception as e:
        logger.error(f"Cleanup old data error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

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

@unified_bp.route('/api/v2/analytics/trends', methods=['GET'])
def get_analytics_trends():
    """고급 분석 및 트렌드"""
    try:
        period = request.args.get('period', '7d')  # 7d, 30d, 90d
        group_by = request.args.get('group_by', 'source')  # source, country, attack_type
        
        # 기간별 데이터 수집
        from datetime import datetime, timedelta
        end_date = datetime.now()
        
        if period == '7d':
            start_date = end_date - timedelta(days=7)
        elif period == '30d':
            start_date = end_date - timedelta(days=30)
        elif period == '90d':
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=7)
        
        # 통계 데이터 수집
        stats = service.get_system_health()
        
        # 트렌드 데이터 생성
        trends = {
            'period': period,
            'group_by': group_by,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_ips': stats.get('total_ips', 0),
            'active_ips': stats.get('active_ips', 0),
            'sources': {
                'regtech': stats.get('regtech_count', 0),
                'secudium': stats.get('secudium_count', 0),
                'public': stats.get('public_count', 0)
            },
            'daily_trends': [],
            'top_countries': [],
            'attack_types': []
        }
        
        # 일별 트렌드 데이터 (시뮬레이션)
        for i in range(7):
            date = (end_date - timedelta(days=i)).strftime('%Y-%m-%d')
            trends['daily_trends'].append({
                'date': date,
                'new_ips': stats.get('total_ips', 0) // 7,
                'removed_ips': 0,
                'total': stats.get('total_ips', 0)
            })
        
        return jsonify({
            'success': True,
            'data': trends,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Analytics trends error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@unified_bp.route('/api/v2/sources/status', methods=['GET'])
def get_sources_status():
    """다중 소스 수집 상세 상태"""
    try:
        # 수집 관리자에서 상태 가져오기
        collection_status = service.get_collection_status()
        
        # 각 소스별 상세 상태
        sources_detail = {
            'regtech': {
                'name': 'REGTECH',
                'enabled': collection_status.get('collection_enabled', False),
                'last_collection': None,
                'last_success': None,
                'last_error': None,
                'total_ips': service.get_system_health().get('regtech_count', 0),
                'status': 'active' if collection_status.get('collection_enabled', False) else 'disabled',
                'health': 'healthy',
                'config': {
                    'url': 'https://regtech.fss.or.kr',
                    'auth_required': True,
                    'collection_interval': '24h'
                }
            },
            'secudium': {
                'name': 'SECUDIUM',
                'enabled': collection_status.get('collection_enabled', False),
                'last_collection': None,
                'last_success': None,
                'last_error': None,
                'total_ips': service.get_system_health().get('secudium_count', 0),
                'status': 'active' if collection_status.get('collection_enabled', False) else 'disabled',
                'health': 'healthy',
                'config': {
                    'url': 'https://secudium.com',
                    'auth_required': True,
                    'collection_interval': '24h'
                }
            },
            'public': {
                'name': 'Public Sources',
                'enabled': True,
                'last_collection': None,
                'last_success': None,
                'last_error': None,
                'total_ips': service.get_system_health().get('public_count', 0),
                'status': 'active',
                'health': 'healthy',
                'config': {
                    'sources': ['threatfox', 'alienvault', 'blocklist.de'],
                    'auth_required': False,
                    'collection_interval': '6h'
                }
            }
        }
        
        # 최근 수집 로그에서 정보 업데이트
        recent_logs = service.get_collection_logs(limit=100)
        for log in recent_logs:
            source = log.get('source', '').lower()
            if source in sources_detail:
                action = log.get('action', '')
                timestamp = log.get('timestamp')
                
                if 'complete' in action:
                    sources_detail[source]['last_success'] = timestamp
                    sources_detail[source]['last_collection'] = timestamp
                elif 'error' in action or 'failed' in action:
                    sources_detail[source]['last_error'] = timestamp
                    sources_detail[source]['health'] = 'error'
                elif 'start' in action:
                    sources_detail[source]['last_collection'] = timestamp
        
        return jsonify({
            'success': True,
            'data': {
                'sources': sources_detail,
                'summary': {
                    'total_sources': len(sources_detail),
                    'active_sources': sum(1 for s in sources_detail.values() if s['status'] == 'active'),
                    'healthy_sources': sum(1 for s in sources_detail.values() if s['health'] == 'healthy'),
                    'total_ips': sum(s['total_ips'] for s in sources_detail.values())
                },
                'collection_enabled': collection_status.get('collection_enabled', False),
                'last_update': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Sources status error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# === Docker 모니터링 API ===

@unified_bp.route('/api/docker/containers', methods=['GET'])
def get_docker_containers():
    """Docker 컨테이너 목록 조회"""
    try:
        import subprocess
        import json
        
        # Docker 컨테이너 목록 가져오기
        cmd = ['docker', 'ps', '--format', 'json', '--all']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return jsonify({
                'success': False,
                'error': 'Failed to get container list',
                'message': result.stderr
            }), 500
        
        containers = []
        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    container = json.loads(line)
                    containers.append({
                        'id': container.get('ID', ''),
                        'name': container.get('Names', ''),
                        'image': container.get('Image', ''),
                        'status': container.get('Status', ''),
                        'state': container.get('State', ''),
                        'ports': container.get('Ports', ''),
                        'created': container.get('CreatedAt', ''),
                        'size': container.get('Size', '')
                    })
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse container info: {line}")
        
        return jsonify({
            'success': True,
            'containers': containers,
            'count': len(containers),
            'timestamp': datetime.now().isoformat()
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Docker command timeout'
        }), 504
    except Exception as e:
        logger.error(f"Docker containers error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@unified_bp.route('/api/docker/container/<name>/logs', methods=['GET'])
def get_docker_container_logs(name):
    """Docker 컨테이너 로그 조회"""
    try:
        import subprocess
        
        # 파라미터 파싱
        lines = request.args.get('lines', 100, type=int)
        follow = request.args.get('follow', 'false').lower() == 'true'
        timestamps = request.args.get('timestamps', 'true').lower() == 'true'
        
        # Docker logs 명령어 구성
        cmd = ['docker', 'logs', name, '--tail', str(lines)]
        if timestamps:
            cmd.append('--timestamps')
        
        if follow:
            # 스트리밍 모드
            def generate():
                process = subprocess.Popen(cmd + ['-f'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                try:
                    for line in iter(process.stdout.readline, ''):
                        if line:
                            yield f"data: {json.dumps({'log': line.strip()})}\n\n"
                finally:
                    process.terminate()
            
            return Response(generate(), mimetype='text/event-stream')
        else:
            # 일반 모드
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return jsonify({
                    'success': False,
                    'error': 'Failed to get container logs',
                    'message': result.stderr
                }), 404
            
            logs = result.stdout.strip().split('\n')
            
            return jsonify({
                'success': True,
                'container': name,
                'logs': logs,
                'count': len(logs),
                'timestamp': datetime.now().isoformat()
            })
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Docker command timeout'
        }), 504
    except Exception as e:
        logger.error(f"Docker logs error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



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

@unified_bp.route('/raw-data')
def raw_data_page():
    """Raw data 페이지"""
    return render_template('raw_data_modern.html')

@unified_bp.route('/api/raw-data', methods=['GET'])
def get_raw_data():
    """Raw blacklist data API endpoint"""
    try:
        # Get all blacklist IPs with details
        import sqlite3
        import os
        db_path = os.path.join('/app' if os.path.exists('/app') else '.', 'instance/blacklist.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query all data with detection_date
        query = """
        SELECT 
            id,
            ip,
            source,
            country,
            attack_type,
            detection_date,
            created_at,
            extra_data
        FROM blacklist_ip
        ORDER BY id DESC
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Convert to list of dicts
        data = []
        for row in rows:
            data.append({
                'id': row['id'],
                'ip': row['ip'],
                'source': row['source'],
                'country': row['country'],
                'attack_type': row['attack_type'],
                'detection_date': row['detection_date'],  # 원본 등록일 (엑셀 기준)
                'created_at': row['created_at'],          # 수집일
                'extra_data': row['extra_data']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': data,
            'total': len(data),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get raw data: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@unified_bp.errorhandler(404)
def not_found_error(error):
    """404 에러 핸들러"""
    return jsonify({
        'success': False,
        'error': 'Not found',
        'message': 'The requested resource was not found'
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