"""
Production environment configuration
"""
import os
from .base import BaseConfig


class ProductionConfig(BaseConfig):
    """Production configuration"""
    
    DEBUG = False
    TESTING = False
    
    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Stricter CORS for production
    CORS_ORIGINS = [
        origin.strip() for origin in os.environ.get('ALLOWED_ORIGINS', '').split(',')
        if origin.strip() and origin.strip() != '*'
    ] or ['https://secudium.io']  # Default to secure origins only
    
    # Production logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'WARNING').upper()
    
    # Enhanced rate limiting for production
    RATELIMIT_DEFAULT = ["500 per hour", "50 per minute"]
    
    # Performance optimizations
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 20,
        'max_overflow': 30,
        'pool_timeout': 30,
    }
    
    # Cache optimization
    CACHE_DEFAULT_TIMEOUT = 600  # 10 minutes for production
    
    # Security headers enforcement
    FORCE_HTTPS = os.environ.get('FORCE_HTTPS', 'true').lower() == 'true'
    
    # Ensure production port
    PORT = int(os.environ.get('PORT', 2541))
    
    @classmethod
    def init_app(cls, app):
        """Initialize production-specific settings"""
        import logging
        from logging.handlers import RotatingFileHandler
        
        # Setup production logging
        if not app.debug:
            file_handler = RotatingFileHandler(
                os.path.join(cls.LOG_DIR, 'secudium.log'),
                maxBytes=cls.LOG_MAX_BYTES,
                backupCount=cls.LOG_BACKUP_COUNT
            )
            file_handler.setFormatter(logging.Formatter(cls.LOG_FORMAT))
            file_handler.setLevel(getattr(logging, cls.LOG_LEVEL))
            app.logger.addHandler(file_handler)
            app.logger.setLevel(getattr(logging, cls.LOG_LEVEL))
            app.logger.info('Blacklist Manager startup in production mode')
    
    @classmethod
    def validate(cls) -> list:
        """Enhanced validation for production"""
        errors = super().validate()
        
        # Production에서는 REGTECH/SECUDIUM 인증만 필수
        # 나머지는 선택사항으로 변경
        
        return errors