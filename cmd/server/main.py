#!/usr/bin/env python3
"""
Blacklist Management System - Main Application Entry Point

CNCF-compliant application entry point following cloud-native best practices.

This module serves as the main entry point for the Blacklist Management System,
a cloud-native threat intelligence platform with multi-source data collection
and FortiGate External Connector integration.

Features:
- CNCF Cloud Native compliance
- Multi-source threat intelligence collection
- Real-time IP blacklist management
- Kubernetes-ready deployment
- Production-grade monitoring and health checks

Usage:
    python cmd/server/main.py [--port PORT] [--debug] [--config CONFIG]

Environment Variables:
    PORT: Server port (default: 2541)
    FLASK_ENV: Environment mode (development/production)
    CONFIG_PATH: Path to configuration file
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.core.main import create_app
    from src.utils.structured_logging import setup_logging
    from src.config.factory import get_config
except ImportError as e:
    print(f"Error importing modules: {e}")
    print(f"Project root: {project_root}")
    print(f"Python path: {sys.path[:3]}")
    sys.exit(1)


def setup_environment():
    """Setup environment variables and paths."""
    # Set default values
    os.environ.setdefault("FLASK_ENV", "production")
    os.environ.setdefault("PORT", "2541")

    # Ensure log directory exists
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Blacklist Management System - CNCF Cloud Native Application"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", 2541)),
        help="Port to run the server on (default: 2541)",
    )
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)"
    )

    return parser.parse_args()


def create_application(config_path=None):
    """Create and configure the Flask application."""
    try:
        # Get configuration
        if config_path:
            os.environ["CONFIG_PATH"] = config_path

        config = get_config()

        # Setup logging
        setup_logging()
        logger = logging.getLogger(__name__)

        # Create Flask application
        app = create_app(config)

        logger.info("Application created successfully")
        logger.info(f"Environment: {config.ENV}")
        logger.info(f"Debug mode: {config.DEBUG}")

        return app

    except Exception as e:
        print(f"Failed to create application: {e}")
        logging.exception("Application creation failed")
        sys.exit(1)


def main():
    """Main application entry point."""
    print("🚀 Starting Blacklist Management System")
    print("📊 CNCF Cloud Native Threat Intelligence Platform")
    print("=" * 60)

    # Setup environment
    setup_environment()

    # Parse arguments
    args = parse_arguments()

    # Create application
    app = create_application(args.config)

    # Configure for different environments
    if args.debug or os.environ.get("FLASK_ENV") == "development":
        print(f"🔧 Running in DEBUG mode on {args.host}:{args.port}")
        app.run(host=args.host, port=args.port, debug=True, use_reloader=True)
    else:
        print(f"🌟 Running in PRODUCTION mode on {args.host}:{args.port}")
        print("📈 For production deployment, use: gunicorn cmd.server.main:app")

        # Production server configuration
        try:
            from gunicorn.app.wsgiapp import WSGIApplication

            # Gunicorn configuration
            gunicorn_config = {
                "bind": f"{args.host}:{args.port}",
                "workers": os.cpu_count() * 2 + 1,
                "worker_class": "gevent",
                "worker_connections": 1000,
                "max_requests": 1000,
                "max_requests_jitter": 50,
                "timeout": 30,
                "keepalive": 2,
                "preload_app": True,
                "access_log_format": '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s',
                "accesslog": "-",
                "errorlog": "-",
                "loglevel": "info",
            }

            class StandaloneApplication(WSGIApplication):
                def __init__(self, app, options=None):
                    self.application = app
                    self.options = options or {}
                    super().__init__()

                def load_config(self):
                    for key, value in self.options.items():
                        self.cfg.set(key.lower(), value)

                def load(self):
                    return self.application

            StandaloneApplication(app, gunicorn_config).run()

        except ImportError:
            print("⚠️  Gunicorn not available, using Flask development server")
            print("📝 For production, install gunicorn: pip install gunicorn[gevent]")
            app.run(host=args.host, port=args.port, debug=False, threaded=True)


# WSGI entry point for production deployment
app = None


def get_wsgi_app():
    """Get WSGI application for production deployment."""
    global app
    if app is None:
        setup_environment()
        app = create_application()
    return app


# Gunicorn entry point
def create_wsgi_app():
    """Create WSGI application for Gunicorn."""
    return get_wsgi_app()


if __name__ == "__main__":
    main()
