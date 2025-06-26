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
from .exceptions import ValidationError, handle_exception
from .validators import validate_ip
from src.utils.unified_decorators import public_endpoint, api_endpoint

logger = logging.getLogger(__name__)

# 통합 라우트 블루프린트
unified_bp = Blueprint('unified', __name__)

# 통합 서비스 인스턴스
service = get_unified_service()

# === 웹 인터페이스 ===

@unified_bp.route('/api/docs', methods=['GET'])
@public_endpoint(cache_ttl=300)
def api_dashboard():
    """API 문서 - 대시보드로 리다이렉트"""
    return redirect('/dashboard', code=302)

@unified_bp.route('/dashboard', methods=['GET'])
@public_endpoint(cache_ttl=60)
def simple_dashboard():
    """간단한 대시보드 (JSON)"""
    try:
        # 시스템 상태 정보 수집
        health = service.get_health()
        collection_status = service.get_collection_status()
        result = asyncio.run(service.get_statistics())
        
        stats = result.get('statistics', {}) if result.get('success') else {}
        
        # 소스별 분포 계산
        from .root_route import calculate_source_distribution
        source_distribution = calculate_source_distribution(stats)
        
        return jsonify({
            'dashboard': '🛡️ Blacklist Management Dashboard',
            'timestamp': datetime.now().isoformat(),
            'system': {
                'status': health.status,
                'version': health.version,
                'service': 'blacklist-unified'
            },
            'collection': {
                'enabled': collection_status.get('status', {}).get('collection_enabled', False),
                'sources': collection_status.get('status', {}).get('sources', {}),
                'summary': collection_status.get('status', {}).get('summary', {})
            },
            'statistics': stats,
            'source_distribution': source_distribution,
            'links': {
                'health': '/health',
                'active_ips': '/api/blacklist/active',
                'fortigate': '/api/fortigate', 
                'collection_status': '/api/collection/status'
            }
        })
    except Exception as e:
        logger.error(f"간단한 대시보드 실패: {e}")
        return jsonify({'error': str(e)}), 500

# === 헬스 체크 및 상태 ===

@unified_bp.route('/health', methods=['GET'])
@public_endpoint(cache_ttl=60, rate_limit_val=100)
def health_check():
    """통합 서비스 헬스 체크"""
    try:
        health = service.get_health()
        
        # HTTP 상태 코드 결정
        status_code = 200
        if health.status == "degraded":
            status_code = 503
        elif health.status == "stopped":
            status_code = 503
        
        return jsonify({
            'status': health.status,
            'service': 'blacklist-unified',
            'version': health.version,
            'timestamp': health.timestamp.isoformat(),
            'components': health.components
        }), status_code
        
    except Exception as e:
        return handle_exception(e, "헬스 체크 실패")

@unified_bp.route('/api/status', methods=['GET'])
@public_endpoint(cache_ttl=300)
def service_status():
    """서비스 상태 조회"""
    try:
        health = service.get_health()
        collection_status = service.get_collection_status()
        
        return jsonify({
            'service': {
                'name': 'blacklist-unified',
                'version': health.version,
                'status': health.status,
                'timestamp': datetime.now().isoformat()
            },
            'components': health.components,
            'collection': collection_status,
            'healthy': health.status == "healthy"
        })
        
    except Exception as e:
        return handle_exception(e, "서비스 상태 조회 실패")

# === 블랙리스트 조회 ===

@unified_bp.route('/api/blacklist/active', methods=['GET'])
@public_endpoint(cache_ttl=300, rate_limit_val=1000)
def get_active_blacklist():
    """활성 블랙리스트 조회 (플레인 텍스트)"""
    try:
        result = asyncio.run(service.get_active_blacklist(format_type='text'))
        
        if result['success']:
            response = Response(
                '\n'.join(result['data']) + '\n',
                mimetype='text/plain',
                headers={
                    'Cache-Control': 'public, max-age=300',
                    'Content-Disposition': 'inline; filename="blacklist.txt"'
                }
            )
            return response
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        return handle_exception(e, "활성 블랙리스트 조회 실패")

@unified_bp.route('/api/fortigate', methods=['GET'])
@public_endpoint(cache_ttl=300, rate_limit_val=500)
def get_fortigate_format():
    """FortiGate External Connector 형식"""
    try:
        result = asyncio.run(service.get_active_blacklist(format_type='fortigate'))
        
        if result['success']:
            return jsonify(result['data'])
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        return handle_exception(e, "FortiGate 형식 조회 실패")

@unified_bp.route('/api/blacklist/json', methods=['GET'])
@public_endpoint(cache_ttl=300)
def get_blacklist_json():
    """블랙리스트 JSON 형식"""
    try:
        result = asyncio.run(service.get_active_blacklist(format_type='json'))
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['data'],
                'count': len(result['data']) if isinstance(result['data'], list) else 0,
                'timestamp': result['timestamp']
            })
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        return handle_exception(e, "JSON 블랙리스트 조회 실패")

# === IP 검색 ===

@unified_bp.route('/api/search/<ip>', methods=['GET'])
@public_endpoint(cache_ttl=600, rate_limit_val=200)
def search_single_ip(ip: str):
    """단일 IP 검색"""
    try:
        # IP 주소 유효성 검사
        if not validate_ip(ip):
            raise ValidationError(f"유효하지 않은 IP 주소: {ip}")
        
        result = asyncio.run(service.search_ip(ip))
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['error']}), 400
            
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return handle_exception(e, f"IP 검색 실패: {ip}")

@unified_bp.route('/api/search', methods=['POST'])
@api_endpoint(cache_ttl=300, rate_limit_val=100)
def search_batch_ips():
    """배치 IP 검색"""
    try:
        data = request.get_json()
        if not data or 'ips' not in data:
            raise ValidationError("IP 목록이 필요합니다")
        
        ips = data['ips']
        if not isinstance(ips, list) or len(ips) > 100:
            raise ValidationError("IP 목록은 배열이며 100개 이하여야 합니다")
        
        results = {}
        for ip in ips:
            if validate_ip(ip):
                result = asyncio.run(service.search_ip(ip))
                results[ip] = result
            else:
                results[ip] = {'success': False, 'error': 'Invalid IP address'}
        
        return jsonify({
            'success': True,
            'results': results,
            'total_searched': len(ips),
            'timestamp': datetime.now().isoformat()
        })
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return handle_exception(e, "배치 IP 검색 실패")

# === 통계 ===

@unified_bp.route('/api/stats', methods=['GET'])
@public_endpoint(cache_ttl=300)
def get_statistics():
    """시스템 통계"""
    try:
        result = asyncio.run(service.get_statistics())
        
        if result['success']:
            return jsonify(result['statistics'])
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        return handle_exception(e, "통계 조회 실패")

@unified_bp.route('/api/v2/analytics/summary', methods=['GET'])
@public_endpoint(cache_ttl=600)
def get_analytics_summary():
    """분석 요약"""
    try:
        result = asyncio.run(service.get_statistics())
        
        if result['success']:
            stats = result['statistics']
            
            # 요약 정보 생성
            summary = {
                'total_ips': stats.get('total_ips', 0),
                'active_ips': stats.get('active_ips', 0),
                'sources': stats.get('sources', {}),
                'last_updated': stats.get('last_updated'),
                'collection_status': service.get_collection_status(),
                'service_health': service.get_health().status
            }
            
            return jsonify({
                'success': True,
                'summary': summary,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        return handle_exception(e, "분석 요약 조회 실패")

# === 수집 관리 ===

@unified_bp.route('/api/collection/status', methods=['GET'])
@public_endpoint(cache_ttl=60)
def get_collection_status():
    """수집 시스템 상태"""
    try:
        status = service.get_collection_status()
        return jsonify(status)
    except Exception as e:
        return handle_exception(e, "수집 상태 조회 실패")

@unified_bp.route('/api/collection/enable', methods=['POST'])
@api_endpoint(rate_limit_val=10)
def enable_collection():
    """수집 시스템 활성화"""
    try:
        result = asyncio.run(service.enable_collection())
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        return handle_exception(e, "수집 시스템 활성화 실패")

@unified_bp.route('/api/collection/disable', methods=['POST'])
@api_endpoint(rate_limit_val=10)
def disable_collection():
    """수집 시스템 비활성화"""
    try:
        result = asyncio.run(service.disable_collection())
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        return handle_exception(e, "수집 시스템 비활성화 실패")

@unified_bp.route('/api/collection/trigger', methods=['POST'])
@api_endpoint(rate_limit_val=5)
def trigger_collection():
    """수동 데이터 수집 트리거"""
    try:
        # 요청 파라미터 확인
        data = request.get_json() or {}
        sources = data.get('sources', ['regtech', 'secudium'])
        force = data.get('force', False)
        
        # 유효한 소스인지 확인
        valid_sources = ['regtech', 'secudium']
        if isinstance(sources, str):
            sources = [sources]
        
        invalid_sources = [s for s in sources if s not in valid_sources]
        if invalid_sources:
            raise ValidationError(f"유효하지 않은 소스: {invalid_sources}")
        
        # 수집 실행
        result = asyncio.run(service.collect_all_data(force=force))
        
        return jsonify({
            'success': result['success'],
            'message': '데이터 수집이 완료되었습니다' if result['success'] else '데이터 수집 중 오류가 발생했습니다',
            'results': result['results'],
            'summary': result['summary']
        })
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return handle_exception(e, "수동 수집 실행 실패")

@unified_bp.route('/api/collection/regtech/trigger', methods=['POST'])
@api_endpoint(rate_limit_val=5)
def trigger_regtech_collection():
    """REGTECH 수집 트리거"""
    try:
        # JSON과 폼 데이터 모두 지원
        data = {}
        if request.is_json:
            data = request.get_json() or {}
        elif request.form:
            data = request.form.to_dict()
        
        force = data.get('force', False)
        
        if 'regtech' not in service._components:
            return jsonify({'error': 'REGTECH 수집기가 비활성화되어 있습니다'}), 400
        
        result = asyncio.run(service._collect_regtech_data(force))
        
        return jsonify({
            'success': result.get('success', False),
            'message': 'REGTECH 수집이 완료되었습니다' if result.get('success') else 'REGTECH 수집 실패',
            'result': result
        })
        
    except Exception as e:
        return handle_exception(e, "REGTECH 수집 실행 실패")

@unified_bp.route('/api/collection/secudium/trigger', methods=['POST'])
@api_endpoint(rate_limit_val=5)
def trigger_secudium_collection():
    """SECUDIUM 수집 트리거"""
    try:
        # JSON과 폼 데이터 모두 지원
        data = {}
        if request.is_json:
            data = request.get_json() or {}
        elif request.form:
            data = request.form.to_dict()
        
        force = data.get('force', False)
        
        if 'secudium' not in service._components:
            return jsonify({'error': 'SECUDIUM 수집기가 비활성화되어 있습니다'}), 400
        
        result = asyncio.run(service._collect_secudium_data(force))
        
        return jsonify({
            'success': result.get('success', False),
            'message': 'SECUDIUM 수집이 완료되었습니다' if result.get('success') else 'SECUDIUM 수집 실패',
            'result': result
        })
        
    except Exception as e:
        return handle_exception(e, "SECUDIUM 수집 실행 실패")

# === 고급 기능 ===

@unified_bp.route('/api/v2/blacklist/enhanced', methods=['GET'])
@public_endpoint(cache_ttl=300)
def get_enhanced_blacklist():
    """향상된 블랙리스트 (메타데이터 포함)"""
    try:
        result = asyncio.run(service.get_active_blacklist(format_type='enhanced'))
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['data'],
                'metadata': {
                    'total_count': len(result['data']) if isinstance(result['data'], list) else 0,
                    'last_updated': result['timestamp'],
                    'sources': list(service._components.keys()),
                    'collection_status': service.get_collection_status()
                }
            })
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        return handle_exception(e, "향상된 블랙리스트 조회 실패")

# === 에러 핸들러 ===

@unified_bp.errorhandler(404)
def not_found(error):
    """404 에러 핸들러"""
    return jsonify({
        'error': 'API 엔드포인트를 찾을 수 없습니다',
        'available_endpoints': [
            '/health',
            '/api/status',
            '/api/blacklist/active',
            '/api/fortigate',
            '/api/search/<ip>',
            '/api/stats',
            '/api/collection/status',
            '/api/collection/trigger'
        ]
    }), 404

@unified_bp.errorhandler(500)
def internal_error(error):
    """500 에러 핸들러"""
    logger.error(f"내부 서버 오류: {error}")
    return jsonify({
        'error': '내부 서버 오류가 발생했습니다',
        'timestamp': datetime.now().isoformat()
    }), 500