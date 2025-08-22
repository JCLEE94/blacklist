#!/usr/bin/env python3
"""
Nextrade Black List Deny System - Extensible Multi-Source IP Management Platform
Advanced architecture with plugin-based IP source system and dependency injection

This module provides a modular Flask application factory using mixins:
- AppConfigurationMixin: Configuration and optimization setup
- MiddlewareMixin: Request/response processing
- BlueprintRegistrationMixin: Route registration
- ErrorHandlerMixin: Error handling
"""
from flask import Flask

import os
from typing import Optional


from ..utils.structured_logging import get_logger, setup_request_logging
from .app.blueprints import BlueprintRegistrationMixin
from .app.config import AppConfigurationMixin
from .app.error_handlers import ErrorHandlerMixin
from .app.middleware import MiddlewareMixin
from .container import get_container

# Use structured logger instead of basic logging
logger = get_logger(__name__)


# Fallback implementations for performance utilities
def get_connection_manager():
    """Placeholder for connection manager"""

    class DummyConnectionManager:
        def get_pool_config(self):
            return {}

    return DummyConnectionManager()


class CompactFlaskApp(
    AppConfigurationMixin,
    MiddlewareMixin,
    BlueprintRegistrationMixin,
    ErrorHandlerMixin,
):
    """Modular Flask application factory using mixins"""

    def _get_version(self) -> str:
        """Get version from version.txt file or default"""
        try:
            version_file = os.path.join(
                os.path.dirname(__file__), "..", "..", "version.txt"
            )
            if os.path.exists(version_file):
                with open(version_file, "r") as f:
                    return f.read().strip()
        except Exception:
            pass
        return "1.3.1"  # Default version

    def create_app(self, config_name: Optional[str] = None) -> Flask:
        """Create compact Flask application with modular architecture"""
        try:
            # Get the project root directory - fix path resolution for
            # container
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.join(
                current_dir, "..", ".."
            )  # /app/src/core -> /app
            project_root = os.path.abspath(project_root)

            template_folder = os.path.join(project_root, "templates")
            static_folder = os.path.join(project_root, "static")

            app = Flask(
                __name__, template_folder=template_folder, static_folder=static_folder
            )

            # Initialize dependency injection container
            container = get_container()

            # Load configuration through container with explicit config_name
            if config_name:
                from src.config.factory import get_config

                config = get_config(config_name)
            else:
                config = container.get("config")
            app.config.from_object(config)

            # Setup basic configuration (from AppConfigurationMixin)
            self._setup_basic_config(app)
            self._setup_cors(app)
            self._setup_compression(app)
            has_orjson = self._setup_json_optimization(app)
            self._setup_timezone(app)

            # Connection pooling configuration
            connection_manager = get_connection_manager()
            app.config.update(connection_manager.get_pool_config())

            # Rate limiting completely disabled
            app.config["RATELIMIT_ENABLED"] = False

            # Configure Flask app with container
            container.configure_flask_app(app)

            # Initialize advanced features
            self._setup_advanced_features(app, container)

            # Setup request/response middleware (from MiddlewareMixin)
            self._setup_request_middleware(app, container)
            self._setup_performance_middleware(app, container)
            self._setup_build_info_context(app)

            # Setup structured request logging
            setup_request_logging(app)
            logger.info("Request logging configured successfully")

            # Register blueprints (from BlueprintRegistrationMixin)
            self._register_core_blueprints(app, container)
            self._register_v2_blueprints(app, container)
            self._register_security_blueprints(app, container)
            self._register_debug_blueprints(app, container)

            # Setup error handlers (from ErrorHandlerMixin)
            self._setup_error_handlers(app)

            # Initialize system stability monitoring
            try:
                from ..utils.system_stability import initialize_system_stability

                initialize_system_stability()
                logger.info("System stability monitoring initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize system monitoring: {e}")

            # Initialize Prometheus metrics system
            try:
                from .monitoring.prometheus_metrics import init_metrics

                # 메트릭 시스템 초기화 (버전 정보와 함께)
                init_metrics(
                    version=self._get_version(),
                    build_date="2025-08-20",
                    git_commit="latest",
                )
                logger.info("Prometheus metrics system initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Prometheus metrics: {e}")

            logger.info(
                "Blacklist API Server initialized successfully",
                environment=config_name or "default",
                orjson_enabled=has_orjson,
            )
            return app

        except Exception as e:
            logger.error("Failed to create application", exception=e, critical=True)
            # Return a minimal Flask app with error information
            error_app = Flask(__name__)
            error_message = str(e)

            @error_app.route("/health")
            def health_error():
                return {
                    "status": "error",
                    "message": f"Application initialization failed: {error_message}",
                }, 503

            return error_app

    def _setup_advanced_features(self, app, container):
        """Setup advanced caching, monitoring, and security features"""
        try:
            # Initialize advanced features
            from ..utils.advanced_cache import get_smart_cache
            from ..utils.security import get_security_manager

            # Setup advanced caching
            smart_cache = get_smart_cache()
            app.smart_cache = smart_cache

            # Setup enhanced security
            import os

            secret_key = os.getenv(
                "SECRET_KEY", "dev-secret-key-blacklist-management-system-2025"
            )
            jwt_secret = os.getenv(
                "JWT_SECRET_KEY", "dev-jwt-secret-key-blacklist-management-system-2025"
            )
            security_manager = get_security_manager(secret_key, jwt_secret)
            app.security_manager = security_manager

            # Initialize unified decorators with container services
            # (rate limiting disabled)
            from ..utils.unified_decorators import initialize_decorators

            initialize_decorators(
                cache=container.get("cache"),
                auth_manager=container.get("auth_manager"),
                rate_limiter=None,  # Rate limiting completely disabled
                metrics=None,  # Monitoring disabled
            )
        except Exception as e:
            logger.warning("Some advanced features failed to initialize", exception=e)


def create_compact_app(config_name: Optional[str] = None) -> Flask:
    """Factory function for backward compatibility"""
    factory = CompactFlaskApp()
    return factory.create_app(config_name)


def create_app(config_name: Optional[str] = None) -> Flask:
    """Main factory function for Flask app creation"""
    return create_compact_app(config_name)

    # Blueprint registration is now handled by BlueprintRegistrationMixin
    # Error handlers are now handled by ErrorHandlerMixin
    # Middleware setup is now handled by MiddlewareMixin


def main():
    """Main execution function"""
    # Load environment variables from .env file
    from pathlib import Path

    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    env = os.environ.get("FLASK_ENV", "production")
    app = create_compact_app(env)

    # Handle app initialization failure
    if not hasattr(app, "config") or "PORT" not in app.config:
        port = int(os.environ.get("PORT", os.environ.get("PROD_PORT", 2541)))
        debug = env == "development"
    else:
        port = app.config["PORT"]
        debug = app.config["DEBUG"]

    logger.info(
        "Starting Blacklist API Server", version="2.1", port=port, environment=env
    )
    logger.info(
        "Features enabled",
        features=[
            "Unified Components",
            "Compression",
            "Caching",
            "Rate Limiting",
            "Authentication",
            "Structured Logging",
        ],
    )

    if env == "production":
        logger.warning(
            "Production mode - use Gunicorn",
            command=(
                "gunicorn -w 4 -b 0.0.0.0:{port} " "core.main:create_compact_app()"
            ),
        )

    app.run(host="0.0.0.0", port=port, debug=debug)


# WSGI application for Gunicorn
application = create_compact_app()

if __name__ == "__main__":
    main()
