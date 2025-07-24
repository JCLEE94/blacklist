"""
Base configuration class
"""
import os
from typing import Any, Dict, List

from src.core.constants import (DEFAULT_DATA_DIR, DEFAULT_DATA_RETENTION_DAYS,
                                DEFAULT_DB_URI, DEFAULT_PORT,
                                DEFAULT_UPDATE_INTERVAL)


class BaseConfig:
    """Base configuration with common settings"""

    # Application Settings
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    PORT = int(os.environ.get("PORT", DEFAULT_PORT))
    DEV_PORT = int(os.environ.get("DEV_PORT", 1541))
    PROD_PORT = int(os.environ.get("PROD_PORT", 2541))
    HOST = os.environ.get("HOST", "0.0.0.0")
    DEBUG = False
    TESTING = False

    # Data Directories
    DATA_DIR = os.environ.get("DATA_DIR", DEFAULT_DATA_DIR)
    BLACKLIST_DIR = os.path.join(DATA_DIR, "blacklist")
    INSTANCE_DIR = os.environ.get("INSTANCE_DIR", "instance")
    LOG_DIR = os.environ.get("LOG_DIR", "logs")
    BACKUP_DIR = os.environ.get("BACKUP_DIR", "backups")

    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", DEFAULT_DB_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # Cache Configuration
    REDIS_URL = os.environ.get("REDIS_URL", "")  # Don't default to redis URL if not set
    CACHE_TYPE = "redis" if REDIS_URL else "simple"
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get("CACHE_DEFAULT_TIMEOUT", 300))
    CACHE_KEY_PREFIX = os.environ.get("CACHE_KEY_PREFIX", "secudium:")

    # Security Configuration
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = int(
        os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 86400)
    )  # 24 hours
    BCRYPT_LOG_ROUNDS = int(os.environ.get("BCRYPT_LOG_ROUNDS", 12))

    # CORS Configuration
    CORS_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
    CORS_ALLOW_HEADERS = ["Content-Type", "Authorization", "X-API-Key"]
    CORS_EXPOSE_HEADERS = ["X-Total-IPs", "X-Active-Months", "X-Cache"]

    # Rate Limiting 비활성화 (안정화를 위해)
    RATELIMIT_STORAGE_URL = REDIS_URL if REDIS_URL else "memory://"
    RATELIMIT_DEFAULT = []
    RATELIMIT_HEADERS_ENABLED = False

    # Blacklist API Configuration
    BLACKLIST_BASE_URL = os.environ.get(
        "BLACKLIST_BASE_URL", "https://platform.blacklist.io"
    )
    BLACKLIST_USERNAME = os.environ.get(
        "BLACKLIST_USERNAME", os.environ.get("REGTECH_USERNAME")
    )
    BLACKLIST_PASSWORD = os.environ.get(
        "BLACKLIST_PASSWORD", os.environ.get("REGTECH_PASSWORD")
    )
    BLACKLIST_TIMEOUT = int(os.environ.get("BLACKLIST_TIMEOUT", 30))

    # Admin Credentials
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

    # IP Whitelist for sensitive endpoints
    IP_WHITELIST = [
        ip.strip() for ip in os.environ.get("IP_WHITELIST", "").split(",") if ip.strip()
    ]

    # Update Configuration
    UPDATE_INTERVAL = int(os.environ.get("UPDATE_INTERVAL", DEFAULT_UPDATE_INTERVAL))
    RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", DEFAULT_DATA_RETENTION_DAYS))
    AUTO_UPDATE_ENABLED = (
        os.environ.get("AUTO_UPDATE_ENABLED", "true").lower() == "true"
    )

    # Scheduler Configuration
    SCHEDULER_ENABLED = os.environ.get("ENABLE_SCHEDULER", "false").lower() == "true"
    SCHEDULER_TIMEZONE = os.environ.get("SCHEDULER_TIMEZONE", "Asia/Seoul")

    # Timezone Configuration
    TIMEZONE = os.environ.get("TIMEZONE", "Asia/Seoul")  # KST 설정

    # Logging Configuration
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
    LOG_FORMAT = os.environ.get(
        "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    LOG_MAX_BYTES = int(os.environ.get("LOG_MAX_BYTES", 10 * 1024 * 1024))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", 5))

    # Monitoring Configuration
    METRICS_ENABLED = os.environ.get("METRICS_ENABLED", "true").lower() == "true"
    HEALTH_CHECK_ENABLED = (
        os.environ.get("HEALTH_CHECK_ENABLED", "true").lower() == "true"
    )
    PERFORMANCE_MONITORING = (
        os.environ.get("PERFORMANCE_MONITORING", "true").lower() == "true"
    )

    # Email Configuration (for alerts)
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    ALERT_EMAIL_RECIPIENTS = [
        email.strip()
        for email in os.environ.get("ALERT_EMAIL_RECIPIENTS", "").split(",")
        if email.strip()
    ]

    @classmethod
    def init_app(cls, app):
        """Initialize application with configuration"""
        pass

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith("_") and not callable(getattr(cls, key))
        }

    @classmethod
    def validate(cls) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []

        # Production 환경에서만 필수 체크
        if not cls.DEBUG and not cls.TESTING:
            # REGTECH/SECUDIUM 인증 정보만 체크
            if not os.environ.get("REGTECH_USERNAME"):
                errors.append("REGTECH_USERNAME environment variable is required")
            if not os.environ.get("REGTECH_PASSWORD"):
                errors.append("REGTECH_PASSWORD environment variable is required")
            if not os.environ.get("SECUDIUM_USERNAME"):
                errors.append("SECUDIUM_USERNAME environment variable is required")
            if not os.environ.get("SECUDIUM_PASSWORD"):
                errors.append("SECUDIUM_PASSWORD environment variable is required")

        return errors

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return not self.DEBUG and not self.TESTING

    @property
    def database_url_safe(self) -> str:
        """Get database URL with credentials masked for logging"""
        url = self.SQLALCHEMY_DATABASE_URI
        if "@" in url:
            return url.split("@")[-1]
        return url
