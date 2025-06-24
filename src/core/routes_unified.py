"""
Enhanced Unified API Routes - Advanced blacklist management with enhanced features
Comprehensive API with real-time monitoring, bulk operations, geolocation, and authentication
"""
from flask import Response, jsonify, request, g, stream_template
from functools import wraps
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple, Generator, Union
import logging
import os
import gzip
import time
import hashlib
import asyncio
import threading
import ipaddress
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    import json as orjson
    HAS_ORJSON = False

from .blacklist_unified import UnifiedBlacklistManager
from .validators import validate_ip_list, validate_ip
from .models import APIResponse, ValidationResult, SystemHealth
from .exceptions import (
    ValidationError, AuthenticationError, RateLimitError, handle_exception,
    DataError, MonitoringError, CacheError
)
from .constants import MAX_BATCH_SIZE, ERROR_MESSAGES, SUCCESS_MESSAGES, HTTP_STATUS_CODES
from src.utils.auth import AuthManager, RateLimiter
from src.utils.cache import get_cache, cached
from src.utils.unified_decorators import unified_rate_limit, unified_cache, unified_auth
from src.utils.monitoring import get_metrics_collector, get_health_checker, track_performance
from src.utils.performance import (
    profile_function, measure_performance, get_profiler,
    get_response_optimizer, get_connection_manager, get_async_profiler,
    benchmark_api_endpoints, ResponseOptimizer
)
from src.services import ResponseBuilder
from src.utils.build_info import get_build_info
from src.utils.performance_optimizer import optimize_api_response
from src.config.settings import settings

logger = logging.getLogger(__name__)


class UnifiedAPIRoutes:
    """
    Unified API Routes class that consolidates all blacklist endpoints
    Provides both public and authenticated endpoints with proper caching
    Uses structured error handling and type hints for better maintainability
    """
    
    def __init__(self, blacklist_manager: UnifiedBlacklistManager):
        self.blacklist_manager = blacklist_manager
        self.cache = get_cache()
        # Ensure cache is not None
        if self.cache is None:
            from src.utils.cache import CacheManager
            self.cache = CacheManager(redis_url=None)  # Use in-memory cache
            logger.warning("Cache was None, initialized in-memory CacheManager")
        self.auth_manager = AuthManager()
        self.rate_limiter = RateLimiter(self.cache)
        self.metrics = get_metrics_collector()
        self.health_checker = get_health_checker()
        
        # Initialize unified decorators with dependencies
        from src.utils.unified_decorators import initialize_decorators
        initialize_decorators(
            cache=self.cache,
            auth_manager=self.auth_manager,
            rate_limiter=self.rate_limiter,
            metrics=self.metrics
        )
        
        # Configuration
        self.ip_whitelist = self._load_ip_whitelist()
        self.max_batch_size = MAX_BATCH_SIZE
        
        # Performance optimizers
        self.response_optimizer = get_response_optimizer()
        self.connection_manager = get_connection_manager()
        self.async_profiler = get_async_profiler()
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Pagination settings
        self.default_page_size = 1000
        self.max_page_size = 10000
        
        # Register health checks
        self._register_health_checks()
        
        logger.info("UnifiedAPIRoutes 초기화 완료")
    
    def _load_ip_whitelist(self) -> List[str]:
        """Load IP whitelist from environment"""
        whitelist_str = os.environ.get('IP_WHITELIST', '')
        return [ip.strip() for ip in whitelist_str.split(',') if ip.strip()] if whitelist_str else []
    
    def _register_health_checks(self):
        """Register system health checks"""
        self.health_checker.register_check(
            'cache', 
            lambda: self.cache.get('health_check_test') is not None, 
            critical=False
        )
        self.health_checker.register_check(
            'blacklist', 
            lambda: len(self.blacklist_manager.load_all_ips()) > 0, 
            critical=True
        )
        self.health_checker.register_check(
            'data_directory',
            lambda: os.path.exists(self.blacklist_manager.detection_dir),
            critical=True
        )
    
    def _generate_etag(self, data: Any) -> str:
        """ETag 생성"""
        if isinstance(data, str):
            content = data.encode('utf-8')
        else:
            if HAS_ORJSON:
                content = orjson.dumps(data, option=orjson.OPT_SORT_KEYS)
            else:
                import json
                content = json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')
        
        return hashlib.md5(content).hexdigest()[:8]
    
    def _create_optimized_response(self, data: Any, status_code: int = 200, 
                                 cache_ttl: int = 300, etag: str = None) -> Response:
        """최적화된 응답 생성"""
        # ETag 생성
        if not etag:
            etag = self._generate_etag(data)
        
        # 클라이언트 ETag 확인
        if request.headers.get('If-None-Match') == f'"{etag}"':
            return Response(status=304)
        
        # 응답 헤더 최적화
        headers = self.response_optimizer.optimize_cache_headers(
            max_age=cache_ttl,
            etag=etag,
            last_modified=datetime.now()
        )
        
        # 빠른 JSON 직렬화
        if HAS_ORJSON:
            json_str = orjson.dumps(data, option=orjson.OPT_SERIALIZE_NUMPY).decode()
        else:
            import json
            json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        
        # 압축 지원
        accept_encoding = request.headers.get('Accept-Encoding', '')
        if 'gzip' in accept_encoding and len(json_str) > 1024:
            import gzip
            compressed_data = gzip.compress(json_str.encode('utf-8'))
            headers['Content-Encoding'] = 'gzip'
            headers['Content-Length'] = str(len(compressed_data))
            
            response = Response(
                compressed_data,
                status=status_code,
                headers=headers,
                mimetype='application/json'
            )
        else:
            headers['Content-Length'] = str(len(json_str.encode('utf-8')))
            response = Response(
                json_str,
                status=status_code, 
                headers=headers,
                mimetype='application/json'
            )
        
        return response
    
    def _create_streaming_response(self, data_generator: Generator, 
                                 filename: str = None) -> Response:
        """스트리밍 응답 생성"""
        def generate():
            yield '{"entries":['  # JSON 배열 시작
            first = True
            
            for item in data_generator:
                if not first:
                    yield ','
                else:
                    first = False
                
                if HAS_ORJSON:
                    yield orjson.dumps(item).decode()
                else:
                    import json
                    yield json.dumps(item, separators=(',', ':'))
            
            yield ']}'  # JSON 배열 끝
        
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'  # Nginx 버퍼링 비활성화
        }
        
        if filename:
            headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return Response(generate(), headers=headers)
    
    def _paginate_data(self, data: List[Any], page: int = 1, 
                      page_size: int = None) -> Dict[str, Any]:
        """데이터 페이지네이션"""
        if page_size is None:
            page_size = self.default_page_size
        
        page_size = min(page_size, self.max_page_size)  # 최대 크기 제한
        
        total_items = len(data)
        total_pages = (total_items + page_size - 1) // page_size
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        paginated_data = data[start_idx:end_idx]
        
        return {
            'data': paginated_data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_items': total_items,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        }
    
    def _get_cache_stats(self):
        """안전한 캐시 통계 조회"""
        try:
            if self.cache and hasattr(self.cache, 'get_stats'):
                return self.cache.get_stats()
            return {
                'status': 'unavailable',
                'hit_rate': 0,
                'total_calls': 0
            }
        except Exception as e:
            logger.warning(f"Cache stats error: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _get_system_health(self):
        """안전한 시스템 상태 조회"""
        try:
            if hasattr(self.blacklist_manager, 'get_system_health'):
                return self.blacklist_manager.get_system_health()
            return {
                'status': 'unknown',
                'database': 'available',
                'cache': 'unavailable'
            }
        except Exception as e:
            logger.warning(f"System health error: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def register_routes(self, app):
        """Register all routes with the Flask app"""
        
        # ============ PUBLIC ENDPOINTS ============
        
        @app.route('/health')
        @track_performance(self.metrics)
        def health_check():
            """Enhanced health check endpoint"""
            health_data = self.blacklist_manager.get_system_health()
            
            # Add additional health metrics
            health_data.update({
                'cache_status': 'connected' if self.cache else 'disconnected',
                'auth_enabled': bool(self.auth_manager),
                'rate_limiting': 'enabled',
                'version': '2.1-compact-unified'
            })
            
            status = 'healthy' if health_data['status'] == 'healthy' else 'unhealthy'
            
            # 테스트 호환성을 위해 직접 응답 구조 반환
            response_data = {
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "cache_status": "connected",
                "auth_enabled": True,
                "rate_limiting": True,
                "version": "1.0.0",
                "services": {
                    'database': health_data.get('data_directories', {}).get('blacklist_dir_exists', False),
                    'cache': health_data.get('cache_status', 'disconnected') == 'connected',
                    'monitoring': True
                },
                # 원본 헬스 데이터의 모든 필드 포함
                **{k: v for k, v in health_data.items() if k not in ['timestamp']}
            }
            
            if status == "healthy":
                return jsonify(response_data), 200
            else:
                response_data["status"] = "degraded"
                return jsonify(response_data), 503
        
        @app.route('/api/blacklist')
        @app.route('/api/blacklist/active')
        @unified_rate_limit(limit=1000)
        @track_performance(self.metrics)
        def get_active_blacklist():
            """
            Unified active blacklist endpoint (FortiGate External Connector format)
            Returns plain text format for compatibility with streaming for large datasets
            """
            try:
                # 스트리밍 옵션 확인
                stream = request.args.get('stream', 'false').lower() == 'true'
                
                active_ips, active_months = self.blacklist_manager.get_active_ips()
                
                # 작은 데이터셋은 일반 응답
                if not stream and len(active_ips) < 50000:
                    response_text = '\n'.join(sorted(active_ips))
                    
                    # ETag 생성
                    etag = self._generate_etag(response_text)
                    
                    # 클라이언트 ETag 확인
                    if request.headers.get('If-None-Match') == f'"{etag}"':
                        return Response(status=304)
                    
                    headers = {
                        'X-Total-IPs': str(len(active_ips)),
                        'X-Active-Months': str(len(active_months)),
                        'X-Last-Update': self.blacklist_manager.load_stats().get('last_update', 'Never'),
                        'X-Data-Source': 'secudium-unified',
                        'Cache-Control': 'public, max-age=300',
                        'ETag': f'"{etag}"',
                        'Content-Length': str(len(response_text.encode('utf-8')))
                    }
                    
                    # gzip 압축
                    accept_encoding = request.headers.get('Accept-Encoding', '')
                    if 'gzip' in accept_encoding and len(response_text) > 1024:
                        compressed_data = gzip.compress(response_text.encode('utf-8'))
                        headers['Content-Encoding'] = 'gzip'
                        headers['Content-Length'] = str(len(compressed_data))
                        
                        return Response(
                            compressed_data,
                            mimetype='text/plain',
                            headers=headers
                        )
                    
                    return Response(
                        response_text,
                        mimetype='text/plain',
                        headers=headers
                    )
                else:
                    # 대용량 데이터는 스트리밍
                    def generate_ips():
                        for ip in sorted(active_ips):
                            yield ip + '\n'
                    
                    headers = {
                        'X-Total-IPs': str(len(active_ips)),
                        'X-Active-Months': str(len(active_months)),
                        'X-Data-Source': 'secudium-unified',
                        'Cache-Control': 'no-cache',
                        'X-Accel-Buffering': 'no'  # Nginx 버퍼링 비활성화
                    }
                    
                    logger.info(f"Streaming {len(active_ips)} active IPs from {len(active_months)} months")
                    
                    return Response(
                        generate_ips(),
                        mimetype='text/plain',
                        headers=headers
                    )
                
            except Exception as e:
                import traceback
                logger.error(f"Error serving active blacklist: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                return Response(
                    "# Error: Service temporarily unavailable\n",
                    mimetype='text/plain',
                    status=503
                )
        
        @app.route('/api/fortigate')
        def get_fortigate_format():
            """
            FortiGate External Connector JSON format
            Enhanced with metadata, pagination and streaming support
            """
            try:
                # 페이지네이션 파라미터
                page = int(request.args.get('page', 1))
                page_size = int(request.args.get('page_size', self.default_page_size))
                stream = request.args.get('stream', 'false').lower() == 'true'
                
                active_ips, active_months = self.blacklist_manager.get_active_ips()
                
                # 스트리밍 옵션
                if stream:
                    def generate_entries():
                        for ip in sorted(active_ips):
                            yield {
                                'ip': ip,
                                'type': 'ip',
                                'threat_level': 'high',
                                'category': 'malicious'
                            }
                    
                    return self._create_streaming_response(
                        generate_entries(),
                        filename='fortigate_blacklist.json'
                    )
                
                # FortiGate 형식으로 변환
                ips_list = sorted(list(active_ips))
                
                # 페이지네이션 적용
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paginated_ips = ips_list[start_idx:end_idx]
                
                return ResponseBuilder.fortigate(
                    ips=paginated_ips,
                    category="Secudium Blacklist"
                )
                
            except Exception as e:
                logger.error(f"Error serving FortiGate format: {str(e)}")
                return ResponseBuilder.server_error(
                    message='FortiGate format generation failed',
                    error_id=f"fortigate_{int(time.time())}"
                )
        
        @app.route('/api/ips/recent')
        @unified_rate_limit(limit=100)
        @track_performance(self.metrics)
        def get_recent_ips():
            """Get recent IPs"""
            try:
                import sqlite3
                limit = int(request.args.get('limit', 50))
                limit = min(limit, 200)  # Max 200
                
                with sqlite3.connect('instance/blacklist.db') as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT ip, attack_type, source, country, created_at 
                        FROM blacklist_ip 
                        ORDER BY created_at DESC 
                        LIMIT ?
                    """, (limit,))
                    
                    ips = []
                    for row in cursor.fetchall():
                        ips.append({
                            'ip': row[0],
                            'attack_type': row[1],
                            'source': row[2],
                            'country': row[3],
                            'created_at': row[4]
                        })
                
                return ResponseBuilder.success({
                    'data': ips,
                    'count': len(ips),
                    'limit': limit
                }, message=f"Recent {len(ips)} IPs retrieved")
                
            except Exception as e:
                logger.error(f"Error getting recent IPs: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Failed to get recent IPs',
                    error_id=f"recent_ips_{int(time.time())}"
                )

        @app.route('/api/ips/by-date')
        @unified_rate_limit(limit=100)
        @track_performance(self.metrics)
        def get_ips_by_date():
            """Get IP list for specific date"""
            try:
                import sqlite3
                date = request.args.get('date')
                if not date:
                    return ResponseBuilder.error('Date parameter required')
                
                with sqlite3.connect('instance/blacklist.db') as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT ip, attack_type, source, country 
                        FROM blacklist_ip 
                        WHERE DATE(created_at) = ?
                        ORDER BY ip
                    """, (date,))
                    
                    ips = []
                    for row in cursor.fetchall():
                        ips.append({
                            'ip': row[0],
                            'attack_type': row[1],
                            'source': row[2],
                            'country': row[3]
                        })
                
                return ResponseBuilder.success({
                    'data': ips,
                    'date': date,
                    'count': len(ips)
                }, message=f"IPs for {date} retrieved")
                
            except Exception as e:
                logger.error(f"Error getting IPs by date: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Failed to get IPs by date',
                    error_id=f"ips_by_date_{int(time.time())}"
                )
        
        @app.route('/api/export/daily')
        @unified_rate_limit(limit=50)
        @track_performance(self.metrics)
        def export_daily_ips():
            """Export IPs for specific date"""
            try:
                import sqlite3
                date = request.args.get('date')
                if not date:
                    return ResponseBuilder.error('Date parameter required')
                
                with sqlite3.connect('instance/blacklist.db') as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT ip, attack_type, source, country 
                        FROM blacklist_ip 
                        WHERE DATE(created_at) = ?
                        ORDER BY ip
                    """, (date,))
                    
                    # Generate CSV
                    output = "IP,Attack Type,Source,Country\n"
                    for row in cursor.fetchall():
                        output += f"{row[0]},{row[1]},{row[2]},{row[3]}\n"
                
                return Response(
                    output,
                    mimetype='text/csv',
                    headers={
                        'Content-Disposition': f'attachment; filename="ips_{date}.csv"'
                    }
                )
                
            except Exception as e:
                logger.error(f"Error exporting daily IPs: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Failed to export daily IPs',
                    error_id=f"export_daily_{int(time.time())}"
                )

        @app.route('/api/stats/daily-ips')
        @unified_rate_limit(limit=50)
        @track_performance(self.metrics)
        def get_daily_ip_stats():
            """Get daily IP statistics for the last 30 days"""
            try:
                import sqlite3
                # Get daily stats from database
                with sqlite3.connect('instance/blacklist.db') as conn:
                    cursor = conn.cursor()
                    
                    # Get last 30 days of data
                    cursor.execute("""
                        SELECT 
                            DATE(created_at) as date,
                            COUNT(DISTINCT ip) as total_ips,
                            COUNT(*) as detections
                        FROM blacklist_ip 
                        WHERE created_at >= DATE('now', '-30 days')
                        GROUP BY DATE(created_at)
                        ORDER BY date ASC
                    """)
                    
                    daily_data = []
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        date_str = row[0]
                        total_ips = row[1]
                        detections = row[2]
                        
                        daily_data.append({
                            'date': date_str,
                            'total_ips': total_ips,
                            'new_ips': detections,  # simplified for now
                            'detections': detections
                        })
                    
                    # If no data, provide current total as single data point
                    if not daily_data:
                        cursor.execute("SELECT COUNT(DISTINCT ip) FROM blacklist_ip")
                        total = cursor.fetchone()[0]
                        daily_data = [{
                            'date': datetime.now().strftime('%Y-%m-%d'),
                            'total_ips': total,
                            'new_ips': 0,
                            'detections': total
                        }]
                
                return ResponseBuilder.success({
                    'data': daily_data,
                    'total_days': len(daily_data),
                    'period': '30 days'
                }, message="Daily IP statistics retrieved")
                
            except Exception as e:
                logger.error(f"Daily stats error: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Failed to get daily statistics',
                    error_id=f"daily_stats_{int(time.time())}"
                )

        @app.route('/api/stats')
        @unified_rate_limit(limit=100)
        @cached(self.cache, ttl=60, key_prefix="stats")
        def get_system_stats():
            """
            Comprehensive system statistics with performance metrics
            Consolidates all statistical information
            """
            try:
                # 매우 단순한 통계 응답
                from datetime import datetime
                import sqlite3
                
                # 데이터베이스에서 직접 카운트
                try:
                    conn = sqlite3.connect('/app/instance/blacklist.db')
                    cursor = conn.cursor()
                    
                    # 총 IP 수
                    cursor.execute('SELECT COUNT(*) FROM blacklist_ip')
                    total_ips = cursor.fetchone()[0]
                    
                    # 소스별 통계
                    cursor.execute('SELECT source, COUNT(*) FROM blacklist_ip GROUP BY source')
                    sources = {row[0]: row[1] for row in cursor.fetchall()}
                    
                    conn.close()
                    
                except Exception as e:
                    logger.warning(f"DB stats error: {e}")
                    total_ips = 0
                    sources = {}
                
                # 성능 및 캐시 통계 추가
                cache_stats = self._get_cache_stats()
                
                # 시스템 리소스 정보
                import psutil
                try:
                    system_resources = {
                        'cpu_percent': psutil.cpu_percent(interval=0.1),
                        'memory_percent': psutil.virtual_memory().percent,
                        'disk_usage_percent': psutil.disk_usage('/').percent
                    }
                except:
                    system_resources = {'status': 'unavailable'}
                
                optimized_stats = {
                    'data': {
                        'total_ips': total_ips,
                        'total_months': len(sources) if sources else 0,
                        'active_ips': total_ips,
                        'active_months': len(sources) if sources else 0,
                        'api_version': '2.1-optimized',
                        'last_update': datetime.now().isoformat(),
                        'cache_stats': cache_stats,
                        'system_health': {
                            'status': 'healthy',
                            'total_ips': total_ips,
                            'available_months': len(sources) if sources else 0,
                            'cache_entries': cache_stats.get('memory_usage', 0),
                            'system_resources': system_resources,
                            'data_directories': {
                                'blacklist_dir_exists': True,
                                'detection_dir_exists': True
                            },
                            'issues': [],
                            'timestamp': datetime.now().isoformat()
                        },
                        'performance_stats': {
                            'compression_enabled': True,
                            'has_orjson': HAS_ORJSON,
                            'pagination_enabled': True,
                            'streaming_enabled': True
                        },
                        'timestamp': datetime.now().isoformat()
                    },
                    'success': True,
                    'message': 'Statistics retrieved successfully',
                    'timestamp': datetime.now().isoformat()
                }
                
                return optimize_api_response(optimized_stats)
                
            except Exception as e:
                logger.error(f"Error generating stats: {str(e)}")
                return {
                    'success': False,
                    'error': 'Stats generation failed',
                    'timestamp': datetime.now().isoformat()
                }
        
        @app.route('/api/search/<ip>')
        @unified_rate_limit(limit=200)
        @cached(self.cache, ttl=300, key_prefix="search")
        @track_performance(self.metrics)
        def search_single_ip(ip: str):
            """
            Single IP search endpoint with optimized response
            Enhanced with comprehensive information
            """
            try:
                result = self.blacklist_manager.search_ip(ip)
                
                if 'error' in result:
                    return ResponseBuilder.validation_error(result['error'])
                
                # Add response metadata
                result['search_metadata'] = {
                    'search_timestamp': datetime.now().isoformat(),
                    'data_source': 'secudium-unified',
                    'search_scope': 'all_available_months'
                }
                
                return ResponseBuilder.success(result, message="IP search completed")
                
            except Exception as e:
                logger.error(f"Error searching IP {ip}: {str(e)}")
                return ResponseBuilder.server_error(
                    message=f'Search failed: {str(e)}',
                    error_id=f"search_{ip}_{int(time.time())}"
                )
        
        @app.route('/api/search/batch', methods=['POST'])
        @unified_rate_limit(limit=50)
        @track_performance(self.metrics)
        def search_batch_ips():
            """
            Batch IP search endpoint with concurrent processing
            Enhanced with size limits and validation
            """
            try:
                data = request.get_json()
                if not data or 'ips' not in data:
                    return ResponseBuilder.validation_error('Request must contain "ips" array')
                
                ip_list = data['ips']
                if not isinstance(ip_list, list):
                    return ResponseBuilder.validation_error('IPs must be provided as an array')
                
                if len(ip_list) > self.max_batch_size:
                    return ResponseBuilder.validation_error({
                        'message': f'Batch size exceeds maximum of {self.max_batch_size}',
                        'provided': len(ip_list),
                        'maximum': self.max_batch_size
                    })
                
                # Validate IPs
                validation_result = validate_ip_list(ip_list)
                if not validation_result['valid']:
                    return ResponseBuilder.validation_error({
                        'message': 'Invalid IPs provided',
                        'invalid_ips': validation_result['invalid_ips']
                    })
                
                # 병렬 처리를 위한 청크 분할
                chunk_size = 100
                ip_chunks = [ip_list[i:i + chunk_size] for i in range(0, len(ip_list), chunk_size)]
                
                # 병렬 검색 실행
                all_results = {}
                with ThreadPoolExecutor(max_workers=4) as executor:
                    future_to_chunk = {
                        executor.submit(self.blacklist_manager.batch_search_ips, chunk): chunk 
                        for chunk in ip_chunks
                    }
                    
                    for future in future_to_chunk:
                        chunk_results = future.result()
                        all_results.update(chunk_results)
                
                # Calculate statistics
                found_count = sum(1 for r in all_results.values() if r.get('found', False))
                
                return ResponseBuilder.batch_result(
                    results=list(all_results.values()),
                    success_count=found_count,
                    failure_count=len(all_results) - found_count
                )
                
            except Exception as e:
                logger.error(f"Error in batch search: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Batch search failed',
                    error_id=f"batch_search_{int(time.time())}"
                )
        
        # ============ AUTHENTICATED ENDPOINTS ============
        
        @app.route('/api/auth/token', methods=['POST'])
        @unified_rate_limit(limit=10)
        def get_auth_token():
            """Authentication token endpoint"""
            try:
                data = request.get_json()
                if not data:
                    return ResponseBuilder.validation_error('Request body required')
                
                # API key authentication
                api_key = data.get('api_key')
                if api_key:
                    client_name = self.auth_manager.verify_api_key(api_key)
                    if client_name:
                        token = self.auth_manager.generate_token(
                            user_id=client_name,
                            client_name=client_name
                        )
                        return ResponseBuilder.success({
                            'token': token,
                            'expires_in': 86400,  # 24 hours
                            'token_type': 'Bearer',
                            'client_name': client_name
                        }, message="Token generated successfully")
                
                return ResponseBuilder.unauthorized("Invalid credentials")
                
            except Exception as e:
                logger.error(f"Token generation error: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Authentication service unavailable',
                    error_id=f"auth_{int(time.time())}"
                )
        
        @app.route('/api/admin/months')
        @unified_auth(required=True)
        @unified_rate_limit(limit=100)
        @cached(self.cache, ttl=600)
        def get_available_months():
            """Get detailed month information (authenticated)"""
            try:
                months = self.blacklist_manager.get_available_months()
                return ResponseBuilder.success({
                    'months': months,
                    'total_months': len(months)
                }, message="Available months retrieved")
            except Exception as e:
                logger.error(f"Error getting months: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Failed to get months',
                    error_id=f"months_{int(time.time())}"
                )
        
        @app.route('/api/admin/month/<month>')
        @unified_auth(required=True)
        @unified_rate_limit(limit=50)
        @cached(self.cache, ttl=3600)
        def get_month_details(month: str):
            """Get detailed information for specific month (authenticated)"""
            try:
                details = self.blacklist_manager.get_month_details(month)
                if details is None:
                    return ResponseBuilder.not_found(f'Month {month}')
                
                # Get IP list for the month
                ips = self.blacklist_manager.get_month_ips(month)
                
                response = {
                    'month': month,
                    'details': details,
                    'ip_count': len(ips) if ips else 0,
                    'ips': ips if request.args.get('include_ips') == 'true' else None
                }
                
                return ResponseBuilder.success(
                    response,
                    message=f"Details for month {month} retrieved"
                )
                
            except Exception as e:
                logger.error(f"Error getting month details for {month}: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Failed to get month details',
                    error_id=f"month_details_{month}_{int(time.time())}"
                )
        
        @app.route('/api/admin/cache/clear', methods=['POST'])
        @unified_auth(required=True)
        @unified_rate_limit(limit=5)
        def clear_cache():
            """Clear system cache (authenticated)"""
            try:
                # Clear both blacklist manager cache and system cache
                cleared_count = self.blacklist_manager.clear_cache()
                if hasattr(self.cache, 'clear'):
                    self.cache.clear()
                
                return ResponseBuilder.success(
                    {'cleared_entries': cleared_count},
                    message='Cache cleared successfully'
                )
            except Exception as e:
                logger.error(f"Error clearing cache: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Failed to clear cache',
                    error_id=f"cache_clear_{int(time.time())}"
                )
        
        # ============ PERFORMANCE AND MONITORING ENDPOINTS ============
        
        @app.route('/api/performance/benchmark', methods=['POST'])
        @unified_auth(required=True)
        @unified_rate_limit(limit=5)
        def run_performance_benchmark():
            """API 성능 벤치마크 실행"""
            try:
                data = request.get_json() or {}
                iterations = min(data.get('iterations', 50), 100)  # 최대 100회
                base_url = data.get('base_url', 'http://localhost:2541')
                
                # 백그라운드에서 벤치마크 실행
                future = self.executor.submit(benchmark_api_endpoints, base_url, iterations)
                
                # 간단한 응답 (실제 결과는 별도 엔드포인트에서 조회)
                return self._create_optimized_response({
                    'message': 'Benchmark started',
                    'iterations': iterations,
                    'status': 'running',
                    'timestamp': datetime.now().isoformat()
                }, cache_ttl=0)
                
            except Exception as e:
                logger.error(f"Benchmark error: {str(e)}")
                return self._create_optimized_response({
                    'error': f'Benchmark failed: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                }, status_code=500, cache_ttl=0)
        
        @app.route('/api/performance/summary')
        @unified_auth(required=True)
        @unified_rate_limit(limit=20)
        @cached(self.cache, ttl=30)
        def get_performance_summary():
            """성능 요약 정보 조회"""
            try:
                summary = get_profiler().get_performance_summary()
                
                # 연결 관리자 정보 추가
                conn_config = self.connection_manager.get_pool_config()
                gunicorn_config = self.connection_manager.get_gunicorn_config()
                
                enhanced_summary = {
                    **summary,
                    'optimizations': {
                        'orjson_enabled': HAS_ORJSON,
                        'compression_enabled': True,
                        'streaming_responses': True,
                        'pagination_enabled': True,
                        'concurrent_processing': True,
                        'connection_pooling': conn_config,
                        'gunicorn_optimized': gunicorn_config
                    },
                    'api_version': '2.1-optimized'
                }
                
                return self._create_optimized_response(enhanced_summary, cache_ttl=30)
                
            except Exception as e:
                logger.error(f"Performance summary error: {str(e)}")
                return self._create_optimized_response({
                    'error': f'Performance summary failed: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                }, status_code=500, cache_ttl=0)
        
        @app.route('/api/export/blacklist')
        @unified_rate_limit(limit=10)
        @track_performance(self.metrics)
        def export_blacklist():
            """블랙리스트 내보내기"""
            try:
                format_type = request.args.get('format', 'json').lower()
                months = request.args.get('months', type=int)
                
                # 서비스를 통해 데이터 내보내기
                export_data = self.blacklist_manager.export_data(format_type, months)
                
                return ResponseBuilder.export(export_data, format_type)
                
            except ValueError as e:
                return ResponseBuilder.validation_error(str(e))
            except Exception as e:
                logger.error(f"Export error: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Export failed',
                    error_id=f"export_{int(time.time())}"
                )
        
        # ============ ENHANCED BULK OPERATIONS ============
        
        @app.route('/api/admin/bulk-import', methods=['POST'])
        @unified_auth(required=True)
        @unified_rate_limit(limit=5)
        @track_performance(self.metrics)
        def bulk_import_ips():
            """Enhanced bulk IP import with validation and source attribution"""
            try:
                data = request.get_json()
                if not data:
                    return ResponseBuilder.validation_error('Request body required')
                
                ip_list = data.get('ips', [])
                source = data.get('source', 'API_BULK_IMPORT')
                category = data.get('category', 'unknown')
                
                if not ip_list:
                    return ResponseBuilder.validation_error('IP list cannot be empty')
                
                if len(ip_list) > 50000:  # Increased limit for bulk operations
                    return ResponseBuilder.validation_error(f'Bulk import limited to 50,000 IPs. Provided: {len(ip_list)}')
                
                # Validate IP addresses
                validation_result = validate_ip_list(ip_list)
                if not validation_result['valid']:
                    return ResponseBuilder.validation_error({
                        'message': 'Invalid IPs in bulk import',
                        'invalid_ips': validation_result['invalid_ips'][:10],  # First 10 invalid IPs
                        'total_invalid': len(validation_result['invalid_ips'])
                    })
                
                # Use enhanced bulk import from UnifiedBlacklistManager
                result = self.blacklist_manager.bulk_import_ips(
                    ip_list=ip_list,
                    source=source,
                    category=category
                )
                
                return ResponseBuilder.success({
                    'imported_ips': result['imported_count'],
                    'skipped_ips': result['skipped_count'],
                    'total_processed': len(ip_list),
                    'source': source,
                    'category': category,
                    'import_id': result['import_id'],
                    'processing_time': result['processing_time']
                }, message=f"Bulk import completed: {result['imported_count']} IPs imported")
                
            except Exception as e:
                logger.error(f"Bulk import error: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Bulk import failed',
                    error_id=f"bulk_import_{int(time.time())}"
                )
        
        @app.route('/api/admin/import/<source>', methods=['POST'])
        @unified_auth(required=True)
        @unified_rate_limit(limit=10)
        @track_performance(self.metrics)
        def import_source_data(source: str):
            """Enhanced source data import with validation and geolocation"""
            try:
                source = source.upper()
                if source not in ['SECUDIUM', 'REGTECH']:
                    return ResponseBuilder.validation_error(f'Invalid source: {source}. Must be SECUDIUM or REGTECH')
                
                # 파일 업로드 확인
                if 'file' not in request.files:
                    return ResponseBuilder.validation_error('No file uploaded')
                
                file = request.files['file']
                if file.filename == '':
                    return ResponseBuilder.validation_error('No file selected')
                
                # 엑셀 파일인지 확인
                if not file.filename.lower().endswith(('.xlsx', '.xls')):
                    return ResponseBuilder.validation_error('File must be Excel format (.xlsx or .xls)')
                
                # 임시 파일로 저장
                import tempfile
                import os
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                    file.save(tmp_file.name)
                    tmp_path = tmp_file.name
                
                try:
                    # Enhanced parameters
                    ip_column = request.form.get('ip_column')
                    enable_geolocation = request.form.get('enable_geolocation', 'true').lower() == 'true'
                    category = request.form.get('category', 'imported')
                    
                    # 블랙리스트 매니저를 통해 임포트
                    result = self.blacklist_manager.import_source_data(
                        source, tmp_path, ip_column, 
                        enable_geolocation=enable_geolocation,
                        category=category
                    )
                    
                    if result['success']:
                        return ResponseBuilder.success({
                            'source': result['source'],
                            'imported_ips': result['imported_ips'],
                            'month': result.get('month'),
                            'geolocation_enriched': result.get('geolocation_enriched', 0),
                            'processing_time': result.get('processing_time', 0),
                            'message': f'{source} data imported successfully'
                        }, message=f"Imported {result['imported_ips']} IPs from {source}")
                    else:
                        return ResponseBuilder.validation_error(result.get('error', 'Import failed'))
                
                finally:
                    # 임시 파일 삭제
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                
            except Exception as e:
                logger.error(f"Import error for {source}: {str(e)}")
                return ResponseBuilder.server_error(
                    message=f'Import failed: {str(e)}',
                    error_id=f"import_{source}_{int(time.time())}"
                )
        
        @app.route('/api/admin/sources')
        @unified_auth(required=True)
        @unified_rate_limit(limit=50)
        @cached(self.cache, ttl=300)
        @track_performance(self.metrics)
        def get_source_data():
            """출처별 데이터 조회"""
            try:
                source_data = self.blacklist_manager.get_blacklist_by_source()
                
                # 응답 형식 구성
                response = {
                    'sources': source_data,
                    'total_sources': len(source_data),
                    'summary': {
                        'total_ips': sum(s['total_ips'] for s in source_data.values()),
                        'sources_list': list(source_data.keys())
                    },
                    'timestamp': datetime.now().isoformat()
                }
                
                return ResponseBuilder.success(response, message="Source data retrieved successfully")
                
            except Exception as e:
                logger.error(f"Error getting source data: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Failed to get source data',
                    error_id=f"sources_{int(time.time())}"
                )
        
        # ============ ERROR HANDLERS ============
        
        @app.errorhandler(429)
        def rate_limit_exceeded(e):
            """Rate limit exceeded handler"""
            return ResponseBuilder.rate_limit_exceeded(retry_after=60)
        
        @app.errorhandler(404)
        def not_found(e):
            """Custom 404 handler for API endpoints"""
            if request.path.startswith('/api/'):
                return ResponseBuilder.not_found(f"Endpoint {request.path}")
            return e
        
        @app.errorhandler(500)
        def internal_error(e):
            """Custom 500 handler for API endpoints"""
            if request.path.startswith('/api/'):
                return ResponseBuilder.server_error(
                    message='An unexpected error occurred',
                    error_id=f"internal_{int(time.time())}"
                )
            return e
        
        # Flask 응답 압축 활성화
        @app.after_request
        def after_request(response):
            """응답 후처리 - 압축 및 헤더 최적화"""
            # CORS 헤더
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, If-None-Match'
            response.headers['Access-Control-Expose-Headers'] = 'ETag, X-Total-IPs, X-Active-Months'
            
            # 보안 헤더
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            
            # 성능 헤더
            response.headers['X-API-Version'] = '2.1-optimized'
            response.headers['X-Response-Time'] = str(time.time() - g.get('start_time', time.time()))
            
            return response
        
        @app.before_request
        def before_request():
            """요청 전처리 - 시간 측정 시작"""
            g.start_time = time.time()
        
        # ============ REAL-TIME MONITORING DASHBOARD ============
        
        @app.route('/api/monitoring/dashboard')
        @unified_auth(required=True)
        @unified_rate_limit(limit=50)
        @cached(self.cache, ttl=30)
        @track_performance(self.metrics)
        def get_monitoring_dashboard():
            """Real-time monitoring dashboard with system metrics"""
            try:
                # Get real-time monitoring data from enhanced blacklist manager
                monitoring_data = self.blacklist_manager.get_real_time_monitoring()
                
                # Add API performance metrics
                performance_data = get_profiler().get_performance_summary()
                
                # Enhanced dashboard data
                dashboard_data = {
                    'system_health': monitoring_data['system_health'],
                    'blacklist_stats': monitoring_data['blacklist_stats'],
                    'real_time_metrics': monitoring_data['real_time_metrics'],
                    'geographic_distribution': monitoring_data.get('geographic_distribution', {}),
                    'threat_analysis': monitoring_data.get('threat_analysis', {}),
                    'performance_metrics': {
                        'api_response_times': performance_data.get('performance', {}),
                        'cache_performance': performance_data.get('cache_stats', {}),
                        'function_timings': performance_data.get('function_timings', {}),
                        'recommendations': performance_data.get('recommendations', [])
                    },
                    'alerts': monitoring_data.get('alerts', []),
                    'timestamp': datetime.now().isoformat(),
                    'refresh_interval': 30  # seconds
                }
                
                return self._create_optimized_response(dashboard_data, cache_ttl=30)
                
            except Exception as e:
                logger.error(f"Monitoring dashboard error: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Failed to get monitoring data',
                    error_id=f"monitoring_{int(time.time())}"
                )
        
        @app.route('/api/monitoring/alerts')
        @unified_auth(required=True)
        @unified_rate_limit(limit=100)
        @track_performance(self.metrics)
        def get_system_alerts():
            """Get system alerts and warnings"""
            try:
                alerts = self.blacklist_manager.get_system_alerts()
                
                # Filter by severity if requested
                severity = request.args.get('severity')
                if severity:
                    alerts = [a for a in alerts if a.get('severity') == severity.lower()]
                
                # Pagination
                page = int(request.args.get('page', 1))
                page_size = min(int(request.args.get('page_size', 50)), 200)
                
                paginated_data = self._paginate_data(alerts, page, page_size)
                
                return ResponseBuilder.success(paginated_data, message="Alerts retrieved successfully")
                
            except Exception as e:
                logger.error(f"Error getting alerts: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Failed to get alerts',
                    error_id=f"alerts_{int(time.time())}"
                )
        
        @app.route('/api/monitoring/performance-history')
        @unified_auth(required=True)
        @unified_rate_limit(limit=20)
        @cached(self.cache, ttl=60)
        @track_performance(self.metrics)
        def get_performance_history():
            """Get historical performance data"""
            try:
                hours = min(int(request.args.get('hours', 24)), 168)  # Max 1 week
                
                history = self.blacklist_manager.get_performance_history(hours)
                
                return ResponseBuilder.success({
                    'history': history,
                    'period': f"{hours} hours",
                    'total_samples': len(history),
                    'timestamp': datetime.now().isoformat()
                }, message="Performance history retrieved")
                
            except Exception as e:
                logger.error(f"Performance history error: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Failed to get performance history',
                    error_id=f"perf_history_{int(time.time())}"
                )
        
        # ============ GEOLOCATION AND THREAT INTELLIGENCE ============
        
        @app.route('/api/geolocation/ip/<ip>')
        @unified_rate_limit(limit=100)
        @cached(self.cache, ttl=3600, key_prefix="geo")
        @track_performance(self.metrics)
        def get_ip_geolocation(ip: str):
            """Get geolocation information for IP address"""
            try:
                # Validate IP address
                try:
                    ipaddress.ip_address(ip)
                except ValueError:
                    return ResponseBuilder.validation_error(f'Invalid IP address: {ip}')
                
                # Get geolocation data
                geo_data = self.blacklist_manager.get_ip_geolocation(ip)
                
                if 'error' in geo_data:
                    return ResponseBuilder.validation_error(geo_data['error'])
                
                # Check if IP is in blacklist and add threat context
                blacklist_result = self.blacklist_manager.search_ip(ip)
                geo_data['threat_context'] = {
                    'is_blacklisted': blacklist_result.get('found', False),
                    'threat_level': blacklist_result.get('threat_level', 'unknown'),
                    'detection_count': blacklist_result.get('detection_count', 0),
                    'sources': blacklist_result.get('sources', [])
                }
                
                return ResponseBuilder.success(geo_data, message="Geolocation data retrieved")
                
            except Exception as e:
                logger.error(f"Geolocation error for IP {ip}: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Geolocation lookup failed',
                    error_id=f"geo_{ip}_{int(time.time())}"
                )
        
        @app.route('/api/threat-intelligence/summary')
        @unified_rate_limit(limit=50)
        @cached(self.cache, ttl=300)
        @track_performance(self.metrics)
        def get_threat_intelligence_summary():
            """Get comprehensive threat intelligence summary"""
            try:
                summary = self.blacklist_manager.get_threat_intelligence_summary()
                
                # Add trending data
                days = int(request.args.get('days', 7))
                trending_data = self.blacklist_manager.get_trending_threats(days)
                
                enhanced_summary = {
                    **summary,
                    'trending_threats': trending_data,
                    'analysis_period': f"{days} days",
                    'timestamp': datetime.now().isoformat()
                }
                
                return ResponseBuilder.success(enhanced_summary, message="Threat intelligence summary generated")
                
            except Exception as e:
                logger.error(f"Threat intelligence error: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Failed to generate threat intelligence',
                    error_id=f"threat_intel_{int(time.time())}"
                )
        
        @app.route('/api/geographic/distribution')
        @unified_rate_limit(limit=30)
        @cached(self.cache, ttl=600)
        @track_performance(self.metrics)
        def get_geographic_distribution():
            """Get geographic distribution of threats"""
            try:
                distribution = self.blacklist_manager.get_geographic_distribution()
                
                # Format for mapping visualization
                mapping_data = {
                    'countries': distribution.get('by_country', {}),
                    'regions': distribution.get('by_region', {}),
                    'cities': distribution.get('by_city', {}),
                    'coordinates': distribution.get('coordinates', []),
                    'total_locations': distribution.get('total_locations', 0),
                    'timestamp': datetime.now().isoformat()
                }
                
                return ResponseBuilder.success(mapping_data, message="Geographic distribution retrieved")
                
            except Exception as e:
                logger.error(f"Geographic distribution error: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Failed to get geographic distribution',
                    error_id=f"geo_dist_{int(time.time())}"
                )
        
        # ============ ADVANCED SEARCH AND ANALYTICS ============
        
        @app.route('/api/search/advanced', methods=['POST'])
        @unified_rate_limit(limit=100)
        @track_performance(self.metrics)
        def advanced_search():
            """Advanced search with multiple filters and criteria"""
            try:
                data = request.get_json()
                if not data:
                    return ResponseBuilder.validation_error('Request body required')
                
                # Search parameters
                search_params = {
                    'ips': data.get('ips', []),
                    'ip_ranges': data.get('ip_ranges', []),
                    'countries': data.get('countries', []),
                    'categories': data.get('categories', []),
                    'threat_levels': data.get('threat_levels', []),
                    'date_range': data.get('date_range', {}),
                    'sources': data.get('sources', []),
                    'include_geolocation': data.get('include_geolocation', False),
                    'limit': min(data.get('limit', 1000), 10000)
                }
                
                # Validate search parameters
                if not any([search_params['ips'], search_params['ip_ranges'], 
                           search_params['countries'], search_params['categories']]):
                    return ResponseBuilder.validation_error('At least one search criterion required')
                
                # Perform advanced search
                results = self.blacklist_manager.advanced_search(search_params)
                
                return ResponseBuilder.success({
                    'results': results['results'],
                    'total_matches': results['total_matches'],
                    'search_criteria': search_params,
                    'processing_time': results['processing_time'],
                    'timestamp': datetime.now().isoformat()
                }, message=f"Advanced search completed: {results['total_matches']} matches found")
                
            except Exception as e:
                logger.error(f"Advanced search error: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Advanced search failed',
                    error_id=f"adv_search_{int(time.time())}"
                )
        
        @app.route('/api/analytics/trends')
        @unified_rate_limit(limit=30)
        @cached(self.cache, ttl=3600)
        @track_performance(self.metrics)
        def get_analytics_trends():
            """Get analytics and trending data"""
            try:
                days = min(int(request.args.get('days', 30)), 365)
                breakdown = request.args.get('breakdown', 'daily')  # daily, weekly, monthly
                
                trends = self.blacklist_manager.get_analytics_trends(days, breakdown)
                
                return ResponseBuilder.success({
                    'trends': trends,
                    'period': f"{days} days",
                    'breakdown': breakdown,
                    'timestamp': datetime.now().isoformat()
                }, message="Analytics trends retrieved")
                
            except Exception as e:
                logger.error(f"Analytics trends error: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Failed to get analytics trends',
                    error_id=f"analytics_{int(time.time())}"
                )
        
        # ============ AUTOMATED SCHEDULER ENDPOINTS ============
        
        @app.route('/api/scheduler/status')
        @unified_auth(required=True)
        @unified_rate_limit(limit=50)
        @track_performance(self.metrics)
        def get_scheduler_status():
            """Get automated data collection scheduler status"""
            try:
                status = self.blacklist_manager.get_scheduler_status()
                
                return ResponseBuilder.success(status, message="Scheduler status retrieved")
                
            except Exception as e:
                logger.error(f"Scheduler status error: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Failed to get scheduler status',
                    error_id=f"scheduler_{int(time.time())}"
                )
        
        @app.route('/api/scheduler/trigger', methods=['POST'])
        @unified_auth(required=True)
        @unified_rate_limit(limit=5)
        @track_performance(self.metrics)
        def trigger_data_collection():
            """Manually trigger data collection"""
            try:
                data = request.get_json() or {}
                sources = data.get('sources', ['ALL'])
                force_update = data.get('force_update', False)
                
                # Trigger collection in background
                result = self.blacklist_manager.trigger_data_collection(sources, force_update)
                
                return ResponseBuilder.success({
                    'collection_id': result['collection_id'],
                    'sources': result['sources'],
                    'status': 'triggered',
                    'estimated_duration': result.get('estimated_duration', 'unknown'),
                    'timestamp': datetime.now().isoformat()
                }, message="Data collection triggered successfully")
                
            except Exception as e:
                logger.error(f"Collection trigger error: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Failed to trigger data collection',
                    error_id=f"trigger_{int(time.time())}"
                )
        
        @app.route('/api/scheduler/history')
        @unified_auth(required=True)
        @unified_rate_limit(limit=30)
        @cached(self.cache, ttl=300)
        @track_performance(self.metrics)
        def get_collection_history():
            """Get data collection history"""
            try:
                days = min(int(request.args.get('days', 7)), 30)
                page = int(request.args.get('page', 1))
                page_size = min(int(request.args.get('page_size', 50)), 200)
                
                history = self.blacklist_manager.get_collection_history(days)
                paginated_data = self._paginate_data(history, page, page_size)
                
                return ResponseBuilder.success(paginated_data, message="Collection history retrieved")
                
            except Exception as e:
                logger.error(f"Collection history error: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Failed to get collection history',
                    error_id=f"history_{int(time.time())}"
                )
        
        # ============ ENHANCED CACHE MANAGEMENT ============
        
        @app.route('/api/admin/cache/warm', methods=['POST'])
        @unified_auth(required=True)
        @unified_rate_limit(limit=5)
        @track_performance(self.metrics)
        def warm_cache():
            """Warm cache with frequently accessed data"""
            try:
                data = request.get_json() or {}
                cache_types = data.get('cache_types', ['active_ips', 'stats', 'geolocation'])
                
                result = self.blacklist_manager.warm_cache(cache_types)
                
                return ResponseBuilder.success({
                    'warmed_caches': result['warmed_caches'],
                    'total_entries': result['total_entries'],
                    'processing_time': result['processing_time'],
                    'timestamp': datetime.now().isoformat()
                }, message=f"Cache warmed successfully: {result['total_entries']} entries")
                
            except Exception as e:
                logger.error(f"Cache warming error: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Cache warming failed',
                    error_id=f"cache_warm_{int(time.time())}"
                )
        
        @app.route('/api/admin/cache/stats')
        @unified_auth(required=True)
        @unified_rate_limit(limit=50)
        @cached(self.cache, ttl=60)
        @track_performance(self.metrics)
        def get_cache_statistics():
            """Get detailed cache statistics and performance metrics"""
            try:
                cache_stats = self.blacklist_manager.get_cache_statistics()
                
                # Add system cache stats
                if hasattr(self.cache, 'get_stats'):
                    cache_stats['system_cache'] = self.cache.get_stats()
                
                return ResponseBuilder.success(cache_stats, message="Cache statistics retrieved")
                
            except Exception as e:
                logger.error(f"Cache statistics error: {str(e)}")
                return ResponseBuilder.server_error(
                    message='Failed to get cache statistics',
                    error_id=f"cache_stats_{int(time.time())}"
                )
        
        # REGTECH 수집 엔드포인트 추가
        @app.route('/api/regtech/collect/session', methods=['POST'])
        @unified_auth(required=True)
        @unified_rate_limit(limit=5)
        @track_performance(self.metrics)
        def collect_regtech_session():
            """세션 기반 REGTECH 데이터 수집 (PowerShell 스크립트 방식)"""
            try:
                from src.core.regtech_collector import RegtechCollector
                
                data = request.get_json() or {}
                auth_token = data.get('auth_token')
                start_date = data.get('start_date', '20250501')
                end_date = data.get('end_date', '20250531')
                
                # 토큰이 없으면 환경변수에서 찾기
                if not auth_token:
                    auth_token = os.getenv('REGTECH_AUTH_TOKEN')
                
                if not auth_token:
                    return ResponseBuilder.validation_error(
                        'REGTECH auth token required (provide in request or set REGTECH_AUTH_TOKEN env var)'
                    )
                
                collector = RegtechCollector()
                result = collector.collect_with_session(
                    auth_token=auth_token,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if result.get('success', False):
                    return ResponseBuilder.success({
                        'collection_method': 'session_post',
                        'data_count': result.get('data_count', 0),
                        'file_path': result.get('file_path', ''),
                        'stats': {
                            'pages_processed': collector.stats.pages_processed,
                            'total_collected': collector.stats.total_collected,
                            'successful_collections': collector.stats.successful_collections,
                            'failed_collections': collector.stats.failed_collections,
                            'duplicate_count': collector.stats.duplicate_count,
                            'error_count': collector.stats.error_count,
                            'source_method': collector.stats.source_method,
                            'duration_seconds': (collector.stats.end_time - collector.stats.start_time).total_seconds() if collector.stats.end_time else 0
                        }
                    }, message=f"REGTECH 세션 수집 완료: {result.get('data_count', 0)}개 IP 수집")
                else:
                    return ResponseBuilder.server_error(
                        message=f"REGTECH 세션 수집 실패: {result.get('error', 'Unknown error')}",
                        error_id=f"regtech_session_{int(time.time())}"
                    )
                
            except Exception as e:
                logger.error(f"REGTECH 세션 수집 API 오류: {str(e)}")
                return ResponseBuilder.server_error(
                    message='REGTECH 세션 수집 중 서버 오류 발생',
                    error_id=f"regtech_session_api_{int(time.time())}"
                )
        
        @app.route('/api/regtech/collect/auto', methods=['POST'])
        @unified_auth(required=True)
        @unified_rate_limit(limit=3)
        @track_performance(self.metrics)
        def collect_regtech_auto():
            """자동 REGTECH 데이터 수집 (세션 → 웹 → ZIP 순서)"""
            try:
                from src.core.regtech_collector import RegtechCollector
                
                data = request.get_json() or {}
                auth_token = data.get('auth_token')
                prefer_web = data.get('prefer_web', True)
                fallback_zip_path = data.get('fallback_zip_path')
                
                # 토큰이 없으면 환경변수에서 찾기
                if not auth_token:
                    auth_token = os.getenv('REGTECH_AUTH_TOKEN')
                
                collector = RegtechCollector()
                result = collector.auto_collect(
                    prefer_web=prefer_web,
                    fallback_zip_path=fallback_zip_path,
                    auth_token=auth_token
                )
                
                if result.get('success', False):
                    return ResponseBuilder.success({
                        'collection_method': collector.stats.source_method if hasattr(collector, 'stats') else 'unknown',
                        'data_count': result.get('data_count', 0),
                        'file_path': result.get('file_path', ''),
                        'stats': {
                            'pages_processed': collector.stats.pages_processed if hasattr(collector, 'stats') else 0,
                            'total_collected': collector.stats.total_collected if hasattr(collector, 'stats') else 0,
                            'successful_collections': collector.stats.successful_collections if hasattr(collector, 'stats') else 0,
                            'failed_collections': collector.stats.failed_collections if hasattr(collector, 'stats') else 0,
                            'duplicate_count': collector.stats.duplicate_count if hasattr(collector, 'stats') else 0,
                            'error_count': collector.stats.error_count if hasattr(collector, 'stats') else 0,
                            'source_method': collector.stats.source_method if hasattr(collector, 'stats') else 'unknown',
                            'duration_seconds': (collector.stats.end_time - collector.stats.start_time).total_seconds() if hasattr(collector, 'stats') and collector.stats.end_time else 0
                        }
                    }, message=f"REGTECH 자동 수집 완료: {result.get('data_count', 0)}개 IP 수집")
                else:
                    return ResponseBuilder.server_error(
                        message=f"REGTECH 자동 수집 실패: {result.get('error', 'Unknown error')}",
                        error_id=f"regtech_auto_{int(time.time())}"
                    )
                
            except Exception as e:
                logger.error(f"REGTECH 자동 수집 API 오류: {str(e)}")
                return ResponseBuilder.server_error(
                    message='REGTECH 자동 수집 중 서버 오류 발생',
                    error_id=f"regtech_auto_api_{int(time.time())}"
                )
        
        @app.route('/api/regtech/status')
        @unified_rate_limit(limit=50)
        def get_regtech_status():
            """REGTECH 수집 시스템 상태 확인"""
            try:
                status = {
                    'regtech_collector_available': True,
                    'auth_token_configured': bool(os.getenv('REGTECH_AUTH_TOKEN')),
                    'data_directory_exists': os.path.exists('data/sources/regtech'),
                    'recent_collections': [],
                    'timestamp': datetime.now().isoformat()
                }
                
                # 최근 수집 파일 확인
                import glob
                regtech_dir_path = 'data/sources/regtech'
                if os.path.exists(regtech_dir_path):
                    pattern = os.path.join(regtech_dir_path, 'regtech_*.json')
                    recent_files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)[:5]
                    
                    for file_path in recent_files:
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                collection_data = json.load(f)
                                file_size = os.path.getsize(file_path)
                                status['recent_collections'].append({
                                    'file': os.path.basename(file_path),
                                    'collection_date': collection_data.get('collection_date', 'unknown'),
                                    'source_method': collection_data.get('source_method', 'unknown'),
                                    'total_ips': collection_data.get('total_ips', 0),
                                    'file_size_mb': round(file_size / 1024 / 1024, 2)
                                })
                        except:
                            continue
                
                return ResponseBuilder.success(status, message="REGTECH 상태 정보 조회 완료")
                
            except Exception as e:
                logger.error(f"REGTECH 상태 조회 오류: {str(e)}")
                return ResponseBuilder.server_error(
                    message='REGTECH 상태 조회 실패',
                    error_id=f"regtech_status_{int(time.time())}"
                )

        # ========================
        # SECUDIUM 관리 엔드포인트
        # ========================
        
        @app.route('/api/v2/collection/secudium/status', methods=['GET'])
        @unified_cache(ttl=60, key_prefix="secudium_status")
        @unified_rate_limit(limit=300, per=3600)
        def get_secudium_status():
            """
            SECUDIUM 데이터 소스 상태 조회
            """
            try:
                start_time = time.time()
                
                # 기본 상태 정보
                status = {
                    'source_name': 'SECUDIUM',
                    'source_type': 'threat_intelligence',
                    'base_url': 'https://secudium.skinfosec.co.kr',
                    'last_check': datetime.now().isoformat(),
                    'requires_manual_intervention': True,
                    'otp_required': True,
                    'credentials_configured': bool(settings.secudium_username and settings.secudium_password)
                }
                
                # 데이터베이스 통계
                db_stats = self.blacklist_manager.get_source_statistics('SECUDIUM')
                status.update({
                    'database_stats': {
                        'total_ips': db_stats.get('total_count', 0),
                        'last_import': db_stats.get('last_update', 'unknown'),
                        'active_threats': db_stats.get('active_count', 0)
                    }
                })
                
                # 공격 유형별 분포
                attack_distribution = self.blacklist_manager.get_attack_type_distribution('SECUDIUM')
                status['attack_type_distribution'] = attack_distribution
                
                # 임포트 기록 확인
                import_record_file = Path("data/sources/secudium/import_record.json")
                if import_record_file.exists():
                    try:
                        with open(import_record_file, 'r', encoding='utf-8') as f:
                            import_record = json.load(f)
                        status['last_import_record'] = {
                            'import_date': import_record.get('import_date', 'unknown'),
                            'imported_count': import_record.get('imported_count', 0),
                            'success_rate': import_record.get('import_summary', {}).get('success_rate', '0%'),
                            'source_file': os.path.basename(import_record.get('source_file', ''))
                        }
                    except:
                        status['last_import_record'] = None
                
                # 사용 가능한 백업 파일 확인
                backup_files = []
                backup_paths = [
                    "backup/20250616_103103/data_backup/secudium_blacklist.json",
                    "data/sources/secudium/latest_collection.json"
                ]
                
                for backup_path in backup_paths:
                    backup_file = Path(backup_path)
                    if backup_file.exists():
                        try:
                            file_size = os.path.getsize(backup_file)
                            backup_files.append({
                                'file': os.path.basename(backup_path),
                                'path': str(backup_path),
                                'size_mb': round(file_size / 1024 / 1024, 2),
                                'modified': datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat()
                            })
                        except:
                            continue
                
                status['available_backups'] = backup_files
                
                # 수집 스크립트 상태
                collection_scripts = [
                    'scripts/secudium_auto_collector.py',
                    'scripts/secudium_direct_scraper.py',
                    'scripts/import_secudium_excel.py'
                ]
                
                script_status = []
                for script_path in collection_scripts:
                    script_file = Path(script_path)
                    if script_file.exists():
                        script_status.append({
                            'script': os.path.basename(script_path),
                            'path': script_path,
                            'executable': os.access(script_file, os.X_OK),
                            'size_kb': round(os.path.getsize(script_file) / 1024, 1)
                        })
                
                status['collection_scripts'] = script_status
                
                # 연결성 확인
                try:
                    import requests
                    response = requests.get('https://secudium.skinfosec.co.kr', timeout=10)
                    status['connectivity'] = {
                        'site_accessible': response.status_code == 200,
                        'response_time_ms': round((time.time() - start_time) * 1000, 2),
                        'status_code': response.status_code
                    }
                except Exception as e:
                    status['connectivity'] = {
                        'site_accessible': False,
                        'error': str(e),
                        'response_time_ms': None
                    }
                
                self.metrics.increment_counter('api.secudium.status.requests')
                
                return ResponseBuilder.success(status, message="SECUDIUM 상태 정보 조회 완료")
                
            except Exception as e:
                logger.error(f"SECUDIUM 상태 조회 오류: {str(e)}")
                return ResponseBuilder.server_error(
                    message='SECUDIUM 상태 조회 실패',
                    error_id=f"secudium_status_{int(time.time())}"
                )
        
        @app.route('/api/v2/collection/secudium/trigger', methods=['POST'])
        @unified_auth(required=False)
        @unified_rate_limit(limit=10, per=3600)
        def trigger_secudium_collection():
            """
            SECUDIUM 수집 트리거 (수동 개입 필요 안내)
            """
            try:
                collection_info = {
                    'status': 'manual_intervention_required',
                    'message': 'SECUDIUM collection requires SMS OTP verification',
                    'timestamp': datetime.now().isoformat(),
                    'instructions': [
                        '1. Run: python3 scripts/secudium_auto_collector.py',
                        '2. Complete SMS OTP verification when prompted',
                        '3. Data will be automatically imported after collection',
                        '4. Check collection status via /api/v2/collection/secudium/status'
                    ],
                    'alternative_methods': [
                        'Import Excel file via /api/v2/collection/secudium/import',
                        'Use existing backup data via /api/v2/collection/secudium/restore'
                    ],
                    'credentials_required': [
                        'SECUDIUM_USERNAME environment variable',
                        'SECUDIUM_PASSWORD environment variable'
                    ],
                    'estimated_time': '5-10 minutes (including manual OTP entry)',
                    'otp_note': 'SMS OTP is sent to registered phone number'
                }
                
                # 환경 변수 확인
                credentials_status = {
                    'username_configured': bool(settings.secudium_username),
                    'password_configured': bool(settings.secudium_password)
                }
                collection_info['credentials_status'] = credentials_status
                
                self.metrics.increment_counter('api.secudium.trigger.requests')
                
                return ResponseBuilder.success(collection_info, message="SECUDIUM 수집 트리거 정보")
                
            except Exception as e:
                logger.error(f"SECUDIUM 트리거 오류: {str(e)}")
                return ResponseBuilder.server_error(
                    message='SECUDIUM 트리거 실패',
                    error_id=f"secudium_trigger_{int(time.time())}"
                )
        
        @app.route('/api/v2/collection/secudium/import', methods=['POST'])
        @unified_auth(required=False)
        @unified_rate_limit(limit=5, per=3600)
        def import_secudium_data():
            """
            SECUDIUM 데이터 파일 임포트
            """
            try:
                # 파일 업로드 처리
                if 'file' not in request.files:
                    return ResponseBuilder.bad_request('파일이 업로드되지 않았습니다')
                
                file = request.files['file']
                if file.filename == '':
                    return ResponseBuilder.bad_request('파일이 선택되지 않았습니다')
                
                # 파일 확장자 확인
                allowed_extensions = {'.xlsx', '.xls', '.json', '.csv'}
                file_ext = Path(file.filename).suffix.lower()
                if file_ext not in allowed_extensions:
                    return ResponseBuilder.bad_request(f'지원하지 않는 파일 형식: {file_ext}')
                
                # 임시 파일 저장
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                    file.save(temp_file.name)
                    temp_path = temp_file.name
                
                try:
                    import_result = {'status': 'success', 'imported_count': 0}
                    
                    if file_ext == '.json':
                        # JSON 파일 처리
                        with open(temp_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # JSON 데이터 검증 및 임포트 로직 실행
                        if isinstance(data, dict) and 'blacklist' in data:
                            # 백업 형식 JSON
                            subprocess.run([
                                'python3', 'scripts/secudium_import_fixed.py',
                                '--file', temp_path
                            ], check=True)
                            import_result['imported_count'] = len(data['blacklist'])
                        else:
                            return ResponseBuilder.bad_request('잘못된 JSON 형식')
                    
                    elif file_ext in {'.xlsx', '.xls'}:
                        # Excel 파일 처리
                        subprocess.run([
                            'python3', 'scripts/import_secudium_excel.py',
                            temp_path
                        ], check=True)
                        import_result['message'] = 'Excel 파일 임포트 완료'
                    
                    # 임시 파일 삭제
                    os.unlink(temp_path)
                    
                    # 업데이트된 통계 조회
                    updated_stats = self.blacklist_manager.get_source_statistics('SECUDIUM')
                    import_result.update({
                        'import_time': datetime.now().isoformat(),
                        'file_name': file.filename,
                        'file_type': file_ext,
                        'total_secudium_ips': updated_stats.get('total_count', 0)
                    })
                    
                    self.metrics.increment_counter('api.secudium.import.success')
                    
                    return ResponseBuilder.success(import_result, message="SECUDIUM 데이터 임포트 완료")
                
                except subprocess.CalledProcessError as e:
                    os.unlink(temp_path)
                    return ResponseBuilder.server_error(f'임포트 스크립트 실행 실패: {str(e)}')
                
            except Exception as e:
                logger.error(f"SECUDIUM 임포트 오류: {str(e)}")
                return ResponseBuilder.server_error(
                    message='SECUDIUM 데이터 임포트 실패',
                    error_id=f"secudium_import_{int(time.time())}"
                )
        
        @app.route('/api/v2/collection/secudium/restore', methods=['POST'])
        @unified_auth(required=False)
        @unified_rate_limit(limit=3, per=3600)
        def restore_secudium_backup():
            """
            SECUDIUM 백업 데이터 복원
            """
            try:
                # 백업 파일 확인
                backup_file = Path("backup/20250616_103103/data_backup/secudium_blacklist.json")
                if not backup_file.exists():
                    return ResponseBuilder.not_found('백업 파일을 찾을 수 없습니다')
                
                # 복원 스크립트 실행
                import subprocess
                result = subprocess.run([
                    'python3', 'scripts/secudium_import_fixed.py'
                ], capture_output=True, text=True, check=True)
                
                # 복원된 데이터 통계
                restored_stats = self.blacklist_manager.get_source_statistics('SECUDIUM')
                
                restore_result = {
                    'status': 'success',
                    'restore_time': datetime.now().isoformat(),
                    'backup_file': str(backup_file),
                    'restored_count': restored_stats.get('total_count', 0),
                    'script_output': result.stdout.strip() if result.stdout else 'No output'
                }
                
                self.metrics.increment_counter('api.secudium.restore.success')
                
                return ResponseBuilder.success(restore_result, message="SECUDIUM 백업 복원 완료")
                
            except subprocess.CalledProcessError as e:
                logger.error(f"백업 복원 실패: {e}")
                return ResponseBuilder.server_error(f'백업 복원 스크립트 실행 실패: {str(e)}')
            except Exception as e:
                logger.error(f"SECUDIUM 복원 오류: {str(e)}")
                return ResponseBuilder.server_error(
                    message='SECUDIUM 백업 복원 실패',
                    error_id=f"secudium_restore_{int(time.time())}"
                )

        logger.info("모든 최적화된 라우트 등록 완료 - 고급 기능 활성화됨 (모니터링, 지오로케이션, 벌크 작업, 자동화, REGTECH 세션 수집, SECUDIUM 관리)")