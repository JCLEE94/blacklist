"""
Development environment configuration
"""
import os
from .base import BaseConfig


class DevelopmentConfig(BaseConfig):
    """Development configuration"""

    DEBUG = True
    TESTING = False

    # Relaxed security for development
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Permissive CORS for development
    CORS_ORIGINS = ["*"]

    # Verbose logging for development
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG").upper()

    # Rate limiting 비활성화 (개발환경)
    RATELIMIT_DEFAULT = []

    # Database optimizations for development
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": -1,  # No recycling in dev
        "echo": os.environ.get("SQL_ECHO", "false").lower() == "true",
    }

    # Shorter cache timeout for development
    CACHE_DEFAULT_TIMEOUT = 60  # 1 minute

    # Development-specific features
    FLASK_ENV = "development"
    SEND_FILE_MAX_AGE_DEFAULT = 0  # Disable caching for static files

    # Auto-reload for development
    AUTO_UPDATE_ENABLED = True
    SCHEDULER_ENABLED = True

    # Override port for development
    PORT = int(os.environ.get("PORT", 1541))

    # 개발용 기본 자격증명 (환경변수가 설정되지 않은 경우)
    BLACKLIST_USERNAME = os.environ.get("BLACKLIST_USERNAME", "dev_user")
    BLACKLIST_PASSWORD = os.environ.get("BLACKLIST_PASSWORD", "dev_password")
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

    @classmethod
    def init_app(cls, app):
        """Initialize development-specific settings"""
        import logging

        # Setup development logging
        app.logger.setLevel(getattr(logging, cls.LOG_LEVEL))

        # Add console handler for development
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(cls.LOG_FORMAT))
        app.logger.addHandler(console_handler)

        app.logger.info("Blacklist Manager startup in development mode")

    @classmethod
    def validate(cls) -> list:
        """Validation for development (less strict)"""
        # 개발 환경에서는 기본값을 제공하므로 검증 에러 없음
        return []
