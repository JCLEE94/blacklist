"""
통합 설정 관리 시스템
모든 하드코딩된 값을 환경변수로 관리
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import timedelta

class Settings:
    """중앙 집중식 설정 관리 클래스"""
    
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        
    # ===== 애플리케이션 기본 설정 =====
    @property
    def app_name(self) -> str:
        return os.getenv('APP_NAME', 'blacklist-management')
    
    @property
    def app_version(self) -> str:
        return os.getenv('APP_VERSION', '3.0.0')
    
    @property
    def environment(self) -> str:
        return os.getenv('ENVIRONMENT', 'development')
    
    @property
    def debug(self) -> bool:
        return os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')
    
    @property
    def secret_key(self) -> str:
        return os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    @property
    def timezone(self) -> str:
        return os.getenv('TIMEZONE', 'Asia/Seoul')
    
    # ===== 서버 설정 =====
    @property
    def host(self) -> str:
        return os.getenv('HOST', '0.0.0.0')
    
    @property
    def port(self) -> int:
        return int(os.getenv('PORT', '8541'))
    
    @property
    def dev_port(self) -> int:
        return int(os.getenv('DEV_PORT', '8541'))
    
    @property
    def prod_port(self) -> int:
        return int(os.getenv('PROD_PORT', '2541'))
    
    @property
    def alt_dev_port(self) -> int:
        return int(os.getenv('ALT_DEV_PORT', '1541'))
    
    # ===== 배포 서버 설정 =====
    @property
    def deploy_host(self) -> str:
        return os.getenv('DEPLOY_HOST', '192.168.50.215')
    
    @property
    def deploy_ssh_port(self) -> int:
        return int(os.getenv('DEPLOY_SSH_PORT', '1111'))
    
    @property
    def deploy_user(self) -> str:
        return os.getenv('DEPLOY_USER', 'docker')
    
    @property
    def docker_registry(self) -> str:
        return os.getenv('DOCKER_REGISTRY', f'{self.deploy_host}:1234')
    
    @property
    def docker_registry_port(self) -> int:
        return int(os.getenv('DOCKER_REGISTRY_PORT', '1234'))
    
    # ===== 데이터베이스 설정 =====
    @property
    def database_uri(self) -> str:
        return os.getenv('DATABASE_URI', f'sqlite:///{self.base_dir}/instance/blacklist.db')
    
    @property
    def redis_url(self) -> str:
        return os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # ===== 외부 서비스 설정 =====
    @property
    def regtech_base_url(self) -> str:
        return os.getenv('REGTECH_BASE_URL', 'https://regtech.fsec.or.kr')
    
    @property
    def regtech_username(self) -> str:
        return os.getenv('REGTECH_USERNAME', '')
    
    @property
    def regtech_password(self) -> str:
        return os.getenv('REGTECH_PASSWORD', '')
    
    @property
    def secudium_base_url(self) -> str:
        return os.getenv('SECUDIUM_BASE_URL', 'https://secudium.skinfosec.co.kr')
    
    @property
    def secudium_username(self) -> str:
        return os.getenv('SECUDIUM_USERNAME', '')
    
    @property
    def secudium_password(self) -> str:
        return os.getenv('SECUDIUM_PASSWORD', '')
    
    @property
    def blacklist_api_url(self) -> str:
        return os.getenv('BLACKLIST_API_URL', 'https://platform.blacklist.io')
    
    # ===== JWT 설정 =====
    @property
    def jwt_secret_key(self) -> str:
        return os.getenv('JWT_SECRET_KEY', self.secret_key)
    
    @property
    def jwt_algorithm(self) -> str:
        return os.getenv('JWT_ALGORITHM', 'HS256')
    
    @property
    def jwt_expiry_hours(self) -> int:
        return int(os.getenv('JWT_EXPIRY_HOURS', '24'))
    
    @property
    def jwt_expiry_delta(self) -> timedelta:
        return timedelta(hours=self.jwt_expiry_hours)
    
    # ===== 캐시 설정 =====
    @property
    def cache_ttl_default(self) -> int:
        return int(os.getenv('CACHE_TTL_DEFAULT', '300'))
    
    @property
    def cache_ttl_long(self) -> int:
        return int(os.getenv('CACHE_TTL_LONG', '3600'))
    
    @property
    def cache_ttl_short(self) -> int:
        return int(os.getenv('CACHE_TTL_SHORT', '60'))
    
    # ===== 속도 제한 설정 =====
    @property
    def rate_limit_public(self) -> str:
        return os.getenv('RATE_LIMIT_PUBLIC', '1000/hour')
    
    @property
    def rate_limit_authenticated(self) -> str:
        return os.getenv('RATE_LIMIT_AUTHENTICATED', '5000/hour')
    
    @property
    def rate_limit_admin(self) -> str:
        return os.getenv('RATE_LIMIT_ADMIN', '10000/hour')
    
    # ===== 시스템 제한 설정 =====
    @property
    def max_memory_mb(self) -> int:
        return int(os.getenv('MAX_MEMORY_MB', '2048'))
    
    @property
    def max_cpu_percent(self) -> int:
        return int(os.getenv('MAX_CPU_PERCENT', '80'))
    
    @property
    def max_disk_percent(self) -> int:
        return int(os.getenv('MAX_DISK_PERCENT', '90'))
    
    # ===== 디렉토리 설정 =====
    @property
    def data_dir(self) -> Path:
        return Path(os.getenv('DATA_DIR', str(self.base_dir / 'data')))
    
    @property
    def logs_dir(self) -> Path:
        return Path(os.getenv('LOGS_DIR', str(self.base_dir / 'logs')))
    
    @property
    def backups_dir(self) -> Path:
        return Path(os.getenv('BACKUPS_DIR', str(self.base_dir / 'backups')))
    
    @property
    def instance_dir(self) -> Path:
        return Path(os.getenv('INSTANCE_DIR', str(self.base_dir / 'instance')))
    
    # ===== 관리자 설정 =====
    @property
    def admin_username(self) -> str:
        return os.getenv('ADMIN_USERNAME', 'admin')
    
    @property
    def admin_email(self) -> str:
        return os.getenv('ADMIN_EMAIL', 'admin@example.com')
    
    # ===== 수집 설정 =====
    @property
    def collection_enabled(self) -> bool:
        return os.getenv('COLLECTION_ENABLED', 'True').lower() in ('true', '1', 'yes')
    
    @property
    def collection_interval_hours(self) -> int:
        return int(os.getenv('COLLECTION_INTERVAL_HOURS', '6'))
    
    @property
    def collection_max_retries(self) -> int:
        return int(os.getenv('COLLECTION_MAX_RETRIES', '3'))
    
    # ===== 설정 검증 =====
    def validate(self) -> Dict[str, Any]:
        """필수 설정 검증"""
        errors = []
        warnings = []
        
        # 필수 환경변수 체크
        if self.environment == 'production':
            if self.secret_key == 'dev-secret-key-change-in-production':
                errors.append("Production SECRET_KEY must be changed!")
            
            if not self.regtech_username or not self.regtech_password:
                warnings.append("REGTECH credentials not set")
            
            if not self.secudium_username or not self.secudium_password:
                warnings.append("SECUDIUM credentials not set")
        
        # 디렉토리 생성
        for dir_path in [self.data_dir, self.logs_dir, self.backups_dir, self.instance_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """모든 설정을 딕셔너리로 반환"""
        return {
            'app': {
                'name': self.app_name,
                'version': self.app_version,
                'environment': self.environment,
                'debug': self.debug,
                'timezone': self.timezone,
            },
            'server': {
                'host': self.host,
                'port': self.port,
                'dev_port': self.dev_port,
                'prod_port': self.prod_port,
            },
            'deployment': {
                'host': self.deploy_host,
                'ssh_port': self.deploy_ssh_port,
                'user': self.deploy_user,
                'registry': self.docker_registry,
            },
            'database': {
                'uri': self.database_uri,
                'redis_url': self.redis_url,
            },
            'external_services': {
                'regtech': {
                    'url': self.regtech_base_url,
                    'username': '***' if self.regtech_username else None,
                },
                'secudium': {
                    'url': self.secudium_base_url,
                    'username': '***' if self.secudium_username else None,
                },
            },
            'directories': {
                'data': str(self.data_dir),
                'logs': str(self.logs_dir),
                'backups': str(self.backups_dir),
                'instance': str(self.instance_dir),
            }
        }

# 싱글톤 인스턴스
settings = Settings()