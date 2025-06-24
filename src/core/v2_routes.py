#!/usr/bin/env python3
"""
V2 API Routes - Enhanced endpoints with advanced features
고도화된 V2 API 엔드포인트 (Blueprint 중복 등록 이슈 해결)
"""

from flask import Blueprint, jsonify, request, Response, stream_with_context
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime, timedelta
import json
import time
from concurrent.futures import ThreadPoolExecutor

from ..utils.unified_decorators import (
    unified_cache, unified_rate_limit, unified_monitoring, unified_validation
)
from ..utils.cache import CacheManager
from ..utils.performance_optimizer import optimizer, validate_ips_batch
from ..core.blacklist_unified import UnifiedBlacklistManager
from ..utils.enhanced_security import SecurityManager

logger = logging.getLogger(__name__)

# V2 API Blueprint
v2_bp = Blueprint('v2_api', __name__, url_prefix='/api/v2')


class V2APIService:
    """V2 API 서비스 클래스"""
    
    def __init__(self, blacklist_manager: UnifiedBlacklistManager, 
                 cache_manager: CacheManager):
        self.blacklist_manager = blacklist_manager
        self.cache = cache_manager
        self.security = SecurityManager(secret_key="v2-api-security-key-2024")
        self.executor = ThreadPoolExecutor(max_workers=10)
        
    @optimizer.measure_performance("v2_get_enhanced_blacklist")
    def get_enhanced_blacklist(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """향상된 블랙리스트 조회"""
        # 필터 파싱
        limit = filters.get('limit', 1000)
        offset = filters.get('offset', 0)
        source = filters.get('source')
        country = filters.get('country')
        min_risk_score = filters.get('min_risk_score', 0)
        
        # 캐시 키 생성
        cache_key = f"v2:enhanced_blacklist:{json.dumps(filters, sort_keys=True)}"
        
        # 캐시 확인
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data
        
        # 데이터 조회
        all_ips = self.blacklist_manager.get_all_active_ips()
        
        # 필터링
        filtered_ips = []
        for ip_data in all_ips:
            if source and ip_data.get('source') != source:
                continue
            if country and ip_data.get('country') != country:
                continue
            if ip_data.get('risk_score', 0) < min_risk_score:
                continue
            filtered_ips.append(ip_data)
        
        # 페이지네이션
        total = len(filtered_ips)
        filtered_ips = filtered_ips[offset:offset + limit]
        
        # 메타데이터 추가
        result = {
            'data': filtered_ips,
            'meta': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'filters_applied': filters
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # 캐시 저장
        self.cache.set(cache_key, result, ttl=300)
        
        return result
    
    @optimizer.measure_performance("v2_batch_ip_check")
    def batch_ip_check(self, ips: List[str]) -> Dict[str, Any]:
        """대량 IP 확인"""
        # IP 유효성 검증
        validations = validate_ips_batch(ips)
        valid_ips = [ip for ip, valid in zip(ips, validations) if valid]
        invalid_ips = [ip for ip, valid in zip(ips, validations) if not valid]
        
        # 블랙리스트 확인
        results = {}
        blacklist_data = self.blacklist_manager.get_all_active_ips()
        blacklist_set = {item['ip'] for item in blacklist_data}
        
        for ip in valid_ips:
            results[ip] = {
                'is_blacklisted': ip in blacklist_set,
                'checked_at': datetime.utcnow().isoformat()
            }
        
        return {
            'results': results,
            'invalid_ips': invalid_ips,
            'stats': {
                'total_checked': len(ips),
                'valid_ips': len(valid_ips),
                'invalid_ips': len(invalid_ips),
                'blacklisted': sum(1 for r in results.values() if r['is_blacklisted'])
            }
        }
    
    @optimizer.measure_performance("v2_get_analytics")
    def get_analytics(self, period: str = '7d') -> Dict[str, Any]:
        """고급 분석 데이터"""
        # 기간 파싱
        period_map = {
            '1d': 1, '7d': 7, '30d': 30, '90d': 90
        }
        days = period_map.get(period, 7)
        
        # 캐시 확인
        cache_key = f"v2:analytics:{period}"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data
        
        # 데이터 분석
        all_data = self.blacklist_manager.get_all_active_ips()
        
        # 소스별 통계
        source_stats = {}
        country_stats = {}
        daily_stats = {}
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        for item in all_data:
            # 소스별
            source = item.get('source', 'unknown')
            source_stats[source] = source_stats.get(source, 0) + 1
            
            # 국가별
            country = item.get('country', 'unknown')
            country_stats[country] = country_stats.get(country, 0) + 1
            
            # 일별 (최근 기간만)
            if 'detected_at' in item:
                try:
                    detected_date = datetime.fromisoformat(item['detected_at']).date()
                    if detected_date >= cutoff_date.date():
                        date_str = detected_date.isoformat()
                        daily_stats[date_str] = daily_stats.get(date_str, 0) + 1
                except:
                    pass
        
        # 트렌드 계산
        trend_data = []
        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=i)).date().isoformat()
            trend_data.append({
                'date': date,
                'count': daily_stats.get(date, 0)
            })
        trend_data.reverse()
        
        result = {
            'period': period,
            'total_ips': len(all_data),
            'source_distribution': source_stats,
            'country_distribution': dict(sorted(
                country_stats.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:20]),  # Top 20 countries
            'trend': trend_data,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        # 캐시 저장
        self.cache.set(cache_key, result, ttl=3600)  # 1시간
        
        return result


# 서비스 인스턴스 (Flask app context에서 초기화됨)
v2_service = None


# Blueprint 라우트들을 모듈 레벨에서 정의
@v2_bp.route('/blacklist/enhanced', methods=['GET'])
@unified_monitoring
@unified_cache(ttl=300, key_prefix='v2:blacklist')
def get_enhanced_blacklist():
    """향상된 블랙리스트 조회"""
    if not v2_service:
        return jsonify({'error': 'Service not initialized'}), 503
        
    filters = {
        'limit': request.args.get('limit', 1000, type=int),
        'offset': request.args.get('offset', 0, type=int),
        'source': request.args.get('source'),
        'country': request.args.get('country'),
        'min_risk_score': request.args.get('min_risk_score', 0, type=float)
    }
    
    result = v2_service.get_enhanced_blacklist(filters)
    return jsonify(result)


@v2_bp.route('/blacklist/batch-check', methods=['POST'])
@unified_monitoring
@unified_validation
@unified_rate_limit(limit=100, per=3600)  # 100 requests per hour
def batch_ip_check():
    """대량 IP 확인"""
    if not v2_service:
        return jsonify({'error': 'Service not initialized'}), 503
        
    data = request.get_json()
    ips = data.get('ips', [])
    
    if not ips:
        return jsonify({'error': 'No IPs provided'}), 400
    
    if len(ips) > 10000:
        return jsonify({'error': 'Too many IPs (max 10000)'}), 400
    
    result = v2_service.batch_ip_check(ips)
    return jsonify(result)


@v2_bp.route('/analytics/<period>', methods=['GET'])
@unified_monitoring
@unified_cache(ttl=3600, key_prefix='v2:analytics')
def get_analytics(period):
    """고급 분석 데이터"""
    if not v2_service:
        return jsonify({'error': 'Service not initialized'}), 503
        
    if period not in ['1d', '7d', '30d', '90d']:
        return jsonify({'error': 'Invalid period'}), 400
    
    result = v2_service.get_analytics(period)
    return jsonify(result)


@v2_bp.route('/export/<format>', methods=['GET'])
@unified_monitoring
def export_data(format):
    """데이터 내보내기"""
    if not v2_service:
        return jsonify({'error': 'Service not initialized'}), 503
        
    if format not in ['json', 'csv', 'txt']:
        return jsonify({'error': 'Invalid format'}), 400
    
    filters = {
        'limit': request.args.get('limit', 10000, type=int),
        'source': request.args.get('source'),
        'country': request.args.get('country')
    }
    
    try:
        data = v2_service.get_enhanced_blacklist(filters)['data']
        
        if format == 'json':
            return jsonify(data)
        elif format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=blacklist.{format}'
                }
            )
        elif format == 'txt':
            ip_list = '\n'.join([item['ip'] for item in data])
            return Response(
                ip_list,
                mimetype='text/plain',
                headers={
                    'Content-Disposition': f'attachment; filename=blacklist.{format}'
                }
            )
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@v2_bp.route('/health', methods=['GET'])
@unified_monitoring
def health_check():
    """V2 헬스체크"""
    if not v2_service:
        return jsonify({
            'status': 'unhealthy',
            'error': 'Service not initialized',
            'timestamp': datetime.utcnow().isoformat()
        }), 503
    
    checks = {
        'database': False,
        'cache': False,
        'performance': False
    }
    
    # 데이터베이스 체크
    try:
        v2_service.blacklist_manager.get_stats()
        checks['database'] = True
    except:
        pass
    
    # 캐시 체크
    try:
        v2_service.cache.set('health_check', 'ok', ttl=1)
        checks['cache'] = v2_service.cache.get('health_check') == 'ok'
    except:
        pass
    
    # 성능 체크
    try:
        from ..utils.performance_optimizer import optimizer
        report = optimizer.get_performance_report()
        checks['performance'] = True
    except:
        pass
    
    result = {
        'status': 'healthy' if all(checks.values()) else 'unhealthy',
        'checks': checks,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    status_code = 200 if result['status'] == 'healthy' else 503
    return jsonify(result), status_code


@v2_bp.route('/performance', methods=['GET'])
@unified_monitoring
def get_performance_metrics():
    """성능 메트릭 조회"""
    if not v2_service:
        return jsonify({'error': 'Service not initialized'}), 503
        
    try:
        report = optimizer.get_performance_report()
        return jsonify({
            'metrics': report,
            'system': {
                'cpu_count': optimizer.max_workers,
                'memory_usage_mb': optimizer.metrics.get('memory_usage', 0)
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@v2_bp.route('/cache/warm', methods=['POST'])
@unified_monitoring
def warm_cache():
    """캐시 워밍"""
    if not v2_service:
        return jsonify({'error': 'Service not initialized'}), 503
        
    # 주요 데이터 미리 로드
    periods = ['1d', '7d', '30d']
    warmed = []
    
    for period in periods:
        try:
            v2_service.get_analytics(period)
            warmed.append(f'analytics:{period}')
        except:
            pass
    
    # 기본 블랙리스트
    try:
        v2_service.get_enhanced_blacklist({'limit': 1000, 'offset': 0})
        warmed.append('blacklist:default')
    except:
        pass
    
    return jsonify({
        'status': 'success',
        'warmed_keys': warmed,
        'timestamp': datetime.utcnow().isoformat()
    })


@v2_bp.route('/stream/blacklist', methods=['GET'])
@unified_monitoring
def stream_blacklist():
    """블랙리스트 스트리밍"""
    if not v2_service:
        return jsonify({'error': 'Service not initialized'}), 503
        
    def generate():
        all_ips = v2_service.blacklist_manager.get_all_active_ips()
        
        # 청크 단위로 스트리밍
        chunk_size = 100
        for i in range(0, len(all_ips), chunk_size):
            chunk = all_ips[i:i + chunk_size]
            yield json.dumps(chunk) + '\n'
            time.sleep(0.01)  # Rate limiting
    
    return Response(
        stream_with_context(generate()),
        mimetype='application/x-ndjson'
    )


def register_v2_routes(app, blacklist_manager: UnifiedBlacklistManager, 
                      cache_manager: CacheManager):
    """V2 라우트 등록 (Blueprint 중복 등록 방지)"""
    global v2_service
    
    # 서비스 인스턴스 초기화
    v2_service = V2APIService(blacklist_manager, cache_manager)
    
    # Blueprint 등록 (한 번만)
    if 'v2_api' not in app.blueprints:
        app.register_blueprint(v2_bp)
        logger.info("V2 API routes registered successfully")
    else:
        logger.info("V2 API routes already registered, skipping")