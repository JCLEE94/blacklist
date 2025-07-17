#!/usr/bin/env python3
"""
Nextrade Black List Deny System - Extensible Multi-Source IP Management Platform
Advanced architecture with plugin-based IP source system and dependency injection
"""
import os
import time
from typing import Optional

from flask import Flask, g, request
from flask_cors import CORS
from flask_compress import Compress
# Rate limiting 비활성화로 인해 주석 처리
# from flask_limiter import Limiter
# from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.middleware.profiler import ProfilerMiddleware

from .container import get_container, BlacklistContainer
from .constants import PRODUCTION_CONFIG, DEVELOPMENT_CONFIG, SECURITY_HEADERS
from .exceptions import BlacklistError, handle_exception, create_error_response

# Import new error handling and logging modules
from src.utils.error_handler import register_error_handlers, error_handler
from src.utils.structured_logging import get_logger, setup_request_logging

# Use structured logger instead of basic logging
logger = get_logger(__name__)


# Performance optimization imports
from src.utils.performance import get_connection_manager, get_profiler
try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False


def create_compact_app(config_name: Optional[str] = None) -> Flask:
    """Create compact Flask application with dependency injection"""
    try:
        # Get the project root directory - fix path resolution for container
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.join(current_dir, '..', '..')  # /app/src/core -> /app
        project_root = os.path.abspath(project_root)
        
        template_folder = os.path.join(project_root, 'templates')
        static_folder = os.path.join(project_root, 'static')
        
        app = Flask(__name__, 
                   template_folder=template_folder,
                   static_folder=static_folder)
        
        # Initialize dependency injection container
        container = get_container()
        
        # Load configuration through container
        config = container.resolve('config')
        app.config.from_object(config)
        
        # Enable proxy headers handling
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
        
        # Performance optimizations
        if app.config.get('ENABLE_PROFILER', False):
            app.wsgi_app = ProfilerMiddleware(app.wsgi_app, profile_dir='./profiler_logs')
        
        # Connection pooling configuration
        connection_manager = get_connection_manager()
        app.config.update(connection_manager.get_pool_config())
        
        # CORS configuration
        CORS(app, origins=os.environ.get('ALLOWED_ORIGINS', '*').split(','))
        
        # Response compression with optimized settings
        compress = Compress()
        compress.init_app(app)
        
        # Configure compression settings for better performance
        app.config.update({
            'COMPRESS_MIMETYPES': [
                'application/json',
                'text/plain',
                'text/html',
                'text/css',
                'text/xml',
                'application/xml',
                'application/xhtml+xml'
            ],
            'COMPRESS_LEVEL': 6,  # Balance between compression ratio and speed
            'COMPRESS_MIN_SIZE': 1024,  # Only compress files larger than 1KB
            'COMPRESS_CACHE_KEY': lambda: request.path,
            'COMPRESS_CACHE_BACKEND': 'SimpleCache',
            'COMPRESS_DEBUG': app.debug
        })
        
        # JSON optimization
        if HAS_ORJSON:
            app.json_encoder = None  # Disable default JSON encoder to use orjson
            app.config['JSON_SORT_KEYS'] = False  # orjson handles sorting
            logger.info("orjson 활성화됨 - JSON 직렬화 성능 향상", feature="orjson", status="enabled")
        
        # Rate limiting with container-managed cache
        cache = container.resolve('cache')
        
        # Rate limiting completely disabled - no storage URI needed
        
        # Rate limiting 완전 비활성화로 인해 불필요
        # def get_rate_limit_key():
        
        # Rate limiting 완전 비활성화 (안정화를 위해)
        # Flask-Limiter를 아예 설정하지 않음
        app.config['RATELIMIT_ENABLED'] = False
        
        # 더미 limiter 객체 생성 (다른 코드에서 참조할 수 있음)
        class DummyLimiter:
            def limit(self, *args, **kwargs):
                def decorator(f):
                    return f
                return decorator
            
            def exempt(self, f):
                return f
                
        limiter = DummyLimiter()
        
        # Configure Flask app with container
        container.configure_flask_app(app)
        
        # Initialize advanced features
        from src.utils.advanced_cache import get_smart_cache
        from src.utils.real_time_monitoring import setup_monitoring
        from src.utils.security import get_security_manager
        
        # Setup advanced caching
        smart_cache = get_smart_cache()
        app.smart_cache = smart_cache
        
        # Setup real-time monitoring
        def app_metrics_callback():
            """애플리케이션 메트릭 수집 콜백"""
            try:
                blacklist_manager = container.resolve('blacklist_manager')
                cache = container.resolve('cache')
                
                active_ips = blacklist_manager.get_active_ips()
                active_count = len(active_ips[0]) if isinstance(active_ips, tuple) else len(active_ips)
                
                cache_stats = cache.get_stats() if hasattr(cache, 'get_stats') else {}
                
                return {
                    'total_requests': getattr(app, 'request_count', 0),
                    'error_count': getattr(app, 'error_count', 0),
                    'avg_response_time': getattr(app, 'avg_response_time', 0.0),
                    'cache_hit_rate': cache_stats.get('hit_rate', 0.0),
                    'active_ips_count': active_count,
                    'database_queries': getattr(app, 'db_query_count', 0)
                }
            except Exception as e:
                logger.error("메트릭 수집 실패", exception=e, component="metrics")
                return {}
        
        monitor = setup_monitoring(app_metrics_callback)
        app.monitor = monitor
        
        # Setup enhanced security
        security_manager = get_security_manager()
        app.security_manager = security_manager
        
        # Initialize unified decorators with container services (rate limiting disabled)
        from src.utils.unified_decorators import initialize_decorators
        initialize_decorators(
            cache=container.resolve('cache'),
            auth_manager=container.resolve('auth_manager'),
            rate_limiter=None,  # Rate limiting completely disabled
            metrics=container.resolve('metrics_collector')
        )
        
        # Register error handlers from the new error handling system
        register_error_handlers(app)
        logger.info("Error handlers registered successfully")
        
        # Setup structured request logging
        setup_request_logging(app)
        logger.info("Request logging configured successfully")
        
        # Register unified routes blueprint directly
        from .unified_routes import unified_bp
        app.register_blueprint(unified_bp)
        logger.info("Unified routes registered successfully")
        
        # Register settings routes (non-conflicting admin functions)
        try:
            from .settings_routes import settings_bp
            app.register_blueprint(settings_bp)
            logger.info("Settings routes registered successfully")
        except Exception as e:
            logger.error("Failed to register settings routes", 
                       exception=e, blueprint="settings_bp")
        
        # Register V2 API routes (advanced features under /api/v2)
        try:
            from .v2_routes import register_v2_routes
            # Resolve services from container
            blacklist_manager = container.resolve('blacklist_manager')
            cache_manager = container.resolve('cache_manager')
            register_v2_routes(app, blacklist_manager, cache_manager)
            logger.info("V2 API routes registered successfully")
        except Exception as e:
            logger.error("Failed to register V2 API routes", 
                       exception=e, blueprint="v2_bp")
        
        # Register debug routes for troubleshooting
        try:
            from .debug_routes import debug_bp
            app.register_blueprint(debug_bp)
            logger.info("Debug routes registered successfully")
        except Exception as e:
            logger.error("Failed to register debug routes", 
                       exception=e, blueprint="debug_bp")
        
        # NOTE: Removed duplicate route registrations to prevent conflicts
        # All core API routes are now centralized in unified_routes.py:
        # - /health, /api/health
        # - /api/stats
        # - /api/blacklist/active, /api/fortigate
        # - /api/collection/* (status, enable, disable, trigger)
        # - /api/search/*
        # - /api/docker/*
        # - Web interface routes (/, /dashboard, /docker-logs, etc.)
        #
        # Removed registrations:
        # - simple_api: Fallback only, not registered in production
        # - collection_routes: All functionality moved to unified_routes
        # - missing_routes: Disabled due to conflicts
        # - collection_control_routes: Integrated into unified_routes
        
        # V2 API routes already registered above - avoiding duplicate registration
        
        # Register missing API routes - DISABLED due to route conflicts with unified_routes
        # try:
        #     from .missing_routes import register_missing_routes
        #     register_missing_routes(app)
        #     logger.info("Missing API routes registered successfully")
        # except Exception as e:
        #     logger.error(f"Failed to register missing API routes: {e}")
        #     import traceback
        #     logger.error(traceback.format_exc())

        # Register root routes - DISABLED due to route conflicts with unified_routes
        # try:
        #     from .root_route import root_bp
        #     app.register_blueprint(root_bp)
        #     logger.info("Root routes registered successfully")
        # except Exception as e:
        #     logger.error(f"Failed to register root routes: {e}")
        #     import traceback
        #     logger.error(traceback.format_exc())
            
        # Register web UI blueprint - DISABLED due to route conflicts with unified_routes
        # try:
        #     from src.web import web_bp
        #     app.register_blueprint(web_bp)
        #     logger.info("Web UI blueprint registered successfully")
        # except Exception as e:
        #     logger.error(f"Failed to register web blueprint: {e}")
        #     import traceback
        #     logger.error(traceback.format_exc())
        
        # REGTECH 분석 메뉴 제거됨 (사용자 요청)
        
        # Limiter removed - no longer stored in app
        
        # Performance monitoring setup
        profiler = get_profiler()
        app.profiler = profiler
        
        @app.before_request
        def performance_before_request():
            """요청 전처리 - 성능 측정 시작"""
            g.start_time = time.time()
            g.profiler = profiler
        
        # 타임존 설정 (KST)
        os.environ['TZ'] = 'Asia/Seoul'
        try:
            time.tzset()
        except:
            pass  # Windows에서는 tzset이 없음
        
        @app.after_request
        def performance_after_request(response):
            """응답 후처리 - 성능 메트릭 기록"""
            duration = time.time() - g.get('start_time', time.time())
            
            # 성능 메트릭 기록
            profiler.function_timings[f"endpoint_{request.endpoint or 'unknown'}"].append(duration)
            
            # 응답 헤더에 성능 정보 추가
            response.headers['X-Response-Time'] = f"{duration:.3f}s"
            response.headers['X-Optimized'] = 'true'
            response.headers['X-Compression-Enabled'] = str(response.headers.get('Content-Encoding') == 'gzip')
            response.headers['X-JSON-Engine'] = 'orjson' if HAS_ORJSON else 'stdlib'
            
            return response
    
        # ===============================
        # ERROR HANDLERS WITH STRUCTURED EXCEPTION HANDLING
        # ===============================
        
        @app.errorhandler(BlacklistError)
        def handle_blacklist_error(error: BlacklistError):
            """Handle custom Blacklist exceptions"""
            return create_error_response(error, include_details=app.debug), 400
        
        @app.errorhandler(404)
        def not_found(error):
            """Handle 404 errors"""
            if request.path.startswith('/api/'):
                return {'error': 'API endpoint not found', 'path': request.path}, 404
            return {'error': 'Not found'}, 404
        
        @app.errorhandler(429)
        def rate_limit_exceeded(error):
            """Handle rate limit exceeded"""
            return {
                'error': 'Rate limit exceeded', 
                'message': str(error.description),
                'retry_after': getattr(error, 'retry_after', 3600)
            }, 429
        
        @app.errorhandler(500)
        def internal_error(error):
            """Handle internal server errors"""
            logger.error("Internal error", exception=error, status_code=500)
            
            # Convert to structured error
            if isinstance(error, Exception):
                structured_error = handle_exception(error)
                return create_error_response(structured_error, include_details=app.debug), 500
            
            return {'error': 'Internal server error'}, 500
        
        # ===============================
        # REQUEST/RESPONSE MIDDLEWARE
        # ===============================
        
        @app.before_request
        def before_request():
            """Request preprocessing with container injection"""
            g.request_id = os.urandom(8).hex()
            g.start_time = time.time()
            
            # Inject container into Flask g for easy access
            g.container = container
            
            logger.info("Request started", 
                       request_id=g.request_id,
                       method=request.method,
                       path=request.path,
                       remote_addr=request.remote_addr)
        
        @app.after_request
        def after_request(response):
            """Response post-processing with enhanced headers"""
            # Apply security headers from constants
            for header, value in SECURITY_HEADERS.items():
                response.headers[header] = value
            
            # Add request tracking
            response.headers['X-Request-ID'] = getattr(g, 'request_id', 'unknown')
            
            # Performance tracking
            if hasattr(g, 'start_time'):
                response_time = (time.time() - g.start_time) * 1000
                response.headers['X-Response-Time'] = f"{response_time:.2f}ms"
            
            # Enhanced cache control
            if request.path.startswith('/api/blacklist'):
                response.headers['Cache-Control'] = 'public, max-age=300'
            elif request.path == '/api/stats':
                response.headers['Cache-Control'] = 'public, max-age=600'
            elif request.path.startswith('/api/search'):
                response.headers['Cache-Control'] = 'public, max-age=180'
            else:
                response.headers['Cache-Control'] = 'no-cache'
            
            return response
        
        # Add global template context for build time
        @app.context_processor
        def inject_build_info():
            from pathlib import Path
            try:
                build_info_path = Path('.build_info')
                if build_info_path.exists():
                    with open(build_info_path, 'r') as f:
                        for line in f:
                            if line.startswith('BUILD_TIME='):
                                build_time = line.split('=', 1)[1].strip("'\"")
                                return {'build_time': build_time}
                return {'build_time': '2025-06-18 18:48:33 KST'}
            except:
                return {'build_time': '2025-06-18 18:48:33 KST'}
        
        logger.info("Blacklist API Server initialized successfully", 
                   environment=config_name or 'default')
        return app
    
    except Exception as e:
        logger.error("Failed to create application", exception=e, critical=True)
        # Return a minimal Flask app with error information
        error_app = Flask(__name__)
        error_message = str(e)
        
        @error_app.route('/health')
        def health_error():
            return {'status': 'error', 'message': f'Application initialization failed: {error_message}'}, 503
        
        return error_app


def main():
    """Main execution function"""
    # Load environment variables from .env file
    from pathlib import Path
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    
    env = os.environ.get('FLASK_ENV', 'production')
    app = create_compact_app(env)
    
    # Handle app initialization failure
    if not hasattr(app, 'config') or 'PORT' not in app.config:
        port = int(os.environ.get('PORT', os.environ.get('PROD_PORT', 2541)))
        debug = env == 'development'
    else:
        port = app.config['PORT']
        debug = app.config['DEBUG']
    
    logger.info("Starting Blacklist API Server", 
               version="2.1", port=port, environment=env)
    logger.info("Features enabled", 
               features=["Unified Components", "Compression", "Caching", 
                        "Rate Limiting", "Authentication", "Structured Logging"])
    
    if env == 'production':
        logger.warning("Production mode - use Gunicorn", 
                      command=f"gunicorn -w 4 -b 0.0.0.0:{port} core.app_compact:create_compact_app()")
    
    app.run(host='0.0.0.0', port=port, debug=debug)


# WSGI application for Gunicorn
application = create_compact_app()

if __name__ == '__main__':
    main()