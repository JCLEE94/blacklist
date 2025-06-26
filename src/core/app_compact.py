#!/usr/bin/env python3
"""
Nextrade Black List Deny System - Extensible Multi-Source IP Management Platform
Advanced architecture with plugin-based IP source system and dependency injection
"""
import os
import time
import logging
from typing import Optional

from flask import Flask, g, request
from flask_cors import CORS
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.middleware.profiler import ProfilerMiddleware

from .container import get_container, BlacklistContainer
from .constants import PRODUCTION_CONFIG, DEVELOPMENT_CONFIG, SECURITY_HEADERS
from .exceptions import BlacklistError, handle_exception, create_error_response

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
            logger.info("orjson 활성화됨 - JSON 직렬화 성능 향상")
        
        # Rate limiting with container-managed cache
        cache = container.resolve('cache')
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=["1000 per hour", "100 per minute"],
            storage_uri=config.REDIS_URL if hasattr(config, 'REDIS_URL') and config.REDIS_URL else 'memory://'
        )
        
        # Configure Flask app with container
        container.configure_flask_app(app)
        
        # Initialize advanced features
        from src.utils.advanced_cache import get_smart_cache
        from src.utils.real_time_monitoring import setup_monitoring
        from src.utils.enhanced_security import get_security_manager
        
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
                logger.error(f"메트릭 수집 실패: {e}")
                return {}
        
        monitor = setup_monitoring(app_metrics_callback)
        app.monitor = monitor
        
        # Setup enhanced security
        security_manager = get_security_manager()
        app.security_manager = security_manager
        
        # Initialize unified decorators with container services
        from src.utils.unified_decorators import initialize_decorators
        initialize_decorators(
            cache=container.resolve('cache'),
            auth_manager=container.resolve('auth_manager'),
            rate_limiter=container.resolve('rate_limiter'),
            metrics=container.resolve('metrics_collector')
        )
        
        # Register unified routes blueprint directly
        from .unified_routes import unified_bp
        app.register_blueprint(unified_bp)
        
        # Enhanced routes disabled (module not found)
        
        # Register Simple V2 API routes (conflict-free version)
        try:
            from .v2_routes_simple import register_simple_v2_routes
            blacklist_manager = container.resolve('blacklist_manager')
            cache_manager = container.resolve('cache')
            register_simple_v2_routes(app, blacklist_manager, cache_manager)
            logger.info("Simple V2 API routes registered successfully")
        except Exception as e:
            logger.error(f"Failed to register Simple V2 API routes: {e}")
        
        # Register simple API routes (fallback)
        try:
            from .simple_api import register_simple_api
            register_simple_api(app)
            logger.info("Simple API routes registered successfully")
        except Exception as e:
            logger.error(f"Failed to register simple API routes: {e}")
            
        # Register simple routes (fallback)
        try:
            from .simple_routes import register_simple_routes
            register_simple_routes(app)
            logger.info("Simple routes registered successfully")
        except Exception as e:
            logger.error(f"Failed to register simple routes: {e}")
        
        # Register simple collection routes
        try:
            from .collection_simple import register_collection_simple
            register_collection_simple(app)
            logger.info("Simple collection routes registered successfully")
        except Exception as e:
            logger.error(f"Failed to register simple collection routes: {e}")
        
        # Register collection management routes
        try:
            from .collection_routes import register_collection_routes
            register_collection_routes(app)
            logger.info("Collection routes registered successfully")
        except Exception as e:
            logger.error(f"Failed to register collection routes: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Register collection control routes (ON/OFF functionality)
        try:
            from .collection_control_routes import register_collection_control_routes
            register_collection_control_routes(app)
            logger.info("Collection Control routes registered successfully")
        except Exception as e:
            logger.error(f"Failed to register Collection Control routes: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # V2 API routes already registered above - avoiding duplicate registration
        
        # Register missing API routes
        try:
            from .missing_routes import register_missing_routes
            register_missing_routes(app)
            logger.info("Missing API routes registered successfully")
        except Exception as e:
            logger.error(f"Failed to register missing API routes: {e}")
            import traceback
            logger.error(traceback.format_exc())

        # Register root routes
        try:
            from .root_route import root_bp
            app.register_blueprint(root_bp)
            logger.info("Root routes registered successfully")
        except Exception as e:
            logger.error(f"Failed to register root routes: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
        # Register web UI blueprint
        try:
            from src.web import web_bp
            app.register_blueprint(web_bp)
            logger.info("Web UI blueprint registered successfully")
        except Exception as e:
            logger.error(f"Failed to register web blueprint: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # REGTECH 분석 메뉴 제거됨 (사용자 요청)
        
        # Store limiter in app
        app.limiter = limiter
        
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
            logger.error(f"Internal error: {error}", exc_info=True)
            
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
            
            logger.info(f"[{g.request_id}] {request.method} {request.path} from {request.remote_addr}")
        
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
        
        logger.info("Blacklist API Server initialized successfully")
        return app
    
    except Exception as e:
        logger.error(f"Failed to create application: {e}", exc_info=True)
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
    
    logger.info(f"Starting Blacklist API Server (Unified v2.1) on port {port}")
    logger.info(f"Environment: {env}")
    logger.info("Features: Unified Components, Compression, Caching, Rate Limiting, Authentication")
    
    if env == 'production':
        logger.info("⚠️  Production mode - use Gunicorn:")
        logger.info(f"gunicorn -w 4 -b 0.0.0.0:{port} core.app_compact:create_compact_app()")
    
    app.run(host='0.0.0.0', port=port, debug=debug)


# WSGI application for Gunicorn
application = create_compact_app()

if __name__ == '__main__':
    main()