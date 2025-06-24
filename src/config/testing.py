"""
Testing environment configuration
"""
import tempfile
import os
from .base import BaseConfig
# Memory database URI for testing


class TestingConfig(BaseConfig):
    """Testing configuration"""
    
    DEBUG = True
    TESTING = True
    
    # Use in-memory database for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # Use simple cache for testing
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 10  # Very short timeout for testing
    
    # Disable rate limiting for testing
    RATELIMIT_ENABLED = False
    RATELIMIT_DEFAULT = ["10000 per hour", "10000 per minute"]
    
    # Use temporary directories for testing
    TEMP_DIR = tempfile.mkdtemp()
    DATA_DIR = os.path.join(TEMP_DIR, 'data')
    INSTANCE_DIR = os.path.join(TEMP_DIR, 'instance')
    LOG_DIR = os.path.join(TEMP_DIR, 'logs')
    BACKUP_DIR = os.path.join(TEMP_DIR, 'backups')
    
    # Testing-specific settings
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    
    # Disable external services for testing
    AUTO_UPDATE_ENABLED = False
    SCHEDULER_ENABLED = False
    METRICS_ENABLED = False
    
    # Fast JWT expiry for testing
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    
    # Minimal logging for testing
    LOG_LEVEL = 'ERROR'
    
    # Test credentials - provide defaults for all required variables
    BLACKLIST_USERNAME = os.environ.get('TEST_BLACKLIST_USERNAME', 'test_user')
    BLACKLIST_PASSWORD = os.environ.get('TEST_BLACKLIST_PASSWORD', 'test_password')
    ADMIN_USERNAME = 'test_admin'
    ADMIN_PASSWORD = 'test_admin_password'
    
    # 환경 변수 기본값 설정
    REDIS_URL = None  # 테스트에서는 Redis 사용 안함
    PORT = 5000
    DEV_PORT = 1541  
    PROD_PORT = 2541
    
    @classmethod
    def init_app(cls, app):
        """Initialize testing-specific settings"""
        import logging
        
        # Minimal logging for tests
        app.logger.setLevel(logging.ERROR)
        app.logger.info('Blacklist Manager startup in testing mode')
        
        # Ensure test directories exist
        for directory in [cls.DATA_DIR, cls.INSTANCE_DIR, cls.LOG_DIR, cls.BACKUP_DIR]:
            os.makedirs(directory, exist_ok=True)
            
        # 테스트용 환경 변수 설정
        if not os.environ.get('BLACKLIST_USERNAME'):
            os.environ['BLACKLIST_USERNAME'] = cls.BLACKLIST_USERNAME
        if not os.environ.get('BLACKLIST_PASSWORD'):
            os.environ['BLACKLIST_PASSWORD'] = cls.BLACKLIST_PASSWORD
    
    @classmethod
    def validate(cls) -> list:
        """Minimal validation for testing"""
        # Always pass validation for testing
        return []