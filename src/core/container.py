"""
의존성 주입 컨테이너 (Dependency Injection Container)

시스템의 모든 의존성을 중앙에서 관리하고 주입하는 컨테이너입니다.
이를 통해 모듈 간 결합도를 낮추고 테스트 가능성을 높입니다.
"""
import os
import logging
from typing import Dict, Any, TypeVar, Type, Optional, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class ServiceDefinition:
    """서비스 정의 클래스"""
    service_type: Type
    factory: Optional[Callable] = None
    singleton: bool = True
    dependencies: Optional[Dict[str, str]] = None


class ServiceContainer:
    """
    서비스 컨테이너 - 의존성 주입을 관리합니다
    
    Features:
    - 싱글톤 및 팩토리 패턴 지원
    - 순환 의존성 감지
    - 라이프사이클 관리
    - 구성 기반 서비스 등록
    """
    
    def __init__(self):
        self._services: Dict[str, ServiceDefinition] = {}
        self._instances: Dict[str, Any] = {}
        self._resolving: set = set()
        self._initialized = False
    
    def register(self, name: str, service_type: Type[T], 
                 factory: Optional[Callable] = None,
                 singleton: bool = True,
                 dependencies: Optional[Dict[str, str]] = None) -> 'ServiceContainer':
        """서비스 등록"""
        if self._initialized:
            raise RuntimeError("Cannot register services after container initialization")
        
        self._services[name] = ServiceDefinition(
            service_type=service_type,
            factory=factory,
            singleton=singleton,
            dependencies=dependencies or {}
        )
        
        logger.debug(f"Registered service: {name} -> {service_type.__name__}")
        return self
    
    def register_instance(self, name: str, instance: Any) -> 'ServiceContainer':
        """인스턴스 직접 등록"""
        if self._initialized:
            raise RuntimeError("Cannot register instances after container initialization")
        
        self._instances[name] = instance
        logger.debug(f"Registered instance: {name} -> {type(instance).__name__}")
        return self
    
    def register_factory(self, name: str, factory: Callable[[], T], 
                        singleton: bool = True) -> 'ServiceContainer':
        """팩토리 함수 등록"""
        return self.register(name, type(None), factory=factory, singleton=singleton)
    
    def resolve(self, name: str) -> Any:
        """서비스 해결"""
        if not self._initialized:
            self.initialize()
        
        # 이미 생성된 인스턴스가 있는지 확인
        if name in self._instances:
            return self._instances[name]
        
        # 순환 의존성 확인
        if name in self._resolving:
            raise RuntimeError(f"Circular dependency detected: {name}")
        
        if name not in self._services:
            raise KeyError(f"Service '{name}' not registered")
        
        service_def = self._services[name]
        
        try:
            self._resolving.add(name)
            
            # 의존성 해결
            resolved_deps = {}
            for dep_name, dep_service in service_def.dependencies.items():
                resolved_deps[dep_name] = self.resolve(dep_service)
            
            # 인스턴스 생성
            if service_def.factory:
                instance = service_def.factory(**resolved_deps)
            else:
                instance = service_def.service_type(**resolved_deps)
            
            # 싱글톤인 경우 캐시
            if service_def.singleton:
                self._instances[name] = instance
            
            logger.debug(f"Resolved service: {name}")
            return instance
            
        finally:
            self._resolving.discard(name)
    
    def initialize(self) -> 'ServiceContainer':
        """컨테이너 초기화"""
        if self._initialized:
            return self
        
        logger.info("Initializing service container...")
        
        # 모든 등록된 서비스의 의존성 검증
        self._validate_dependencies()
        
        self._initialized = True
        logger.info("Service container initialized")
        return self
    
    def _validate_dependencies(self):
        """의존성 검증"""
        for service_name, service_def in self._services.items():
            for dep_name, dep_service in service_def.dependencies.items():
                if dep_service not in self._services and dep_service not in self._instances:
                    raise KeyError(f"Service '{service_name}' depends on unregistered service '{dep_service}'")
    
    def get_service_info(self) -> Dict[str, Dict[str, Any]]:
        """서비스 정보 조회"""
        info = {}
        
        for name, service_def in self._services.items():
            info[name] = {
                'type': service_def.service_type.__name__,
                'singleton': service_def.singleton,
                'dependencies': list(service_def.dependencies.keys()),
                'instantiated': name in self._instances
            }
        
        for name, instance in self._instances.items():
            if name not in info:
                info[name] = {
                    'type': type(instance).__name__,
                    'singleton': True,
                    'dependencies': [],
                    'instantiated': True
                }
        
        return info
    
    def clear(self):
        """컨테이너 정리"""
        self._instances.clear()
        self._services.clear()
        self._resolving.clear()
        self._initialized = False
        logger.debug("Service container cleared")


class BlacklistContainer(ServiceContainer):
    """
    Blacklist 전용 의존성 주입 컨테이너
    
    시스템의 모든 핵심 서비스를 등록하고 관리합니다.
    """
    
    def __init__(self):
        super().__init__()
        self._configure_core_services()
    
    def _configure_core_services(self):
        """핵심 서비스 구성"""
        from src.config.factory import get_config
        from src.utils.cache import get_cache
        from src.utils.auth import AuthManager, RateLimiter
        from src.utils.monitoring import get_metrics_collector, get_health_checker
        from .database import DatabaseManager
        from .blacklist_unified import UnifiedBlacklistManager
        from .routes_unified import UnifiedAPIRoutes
        
        # Configuration
        self.register_factory('config', lambda: get_config())
        
        # Cache
        self.register_factory('cache', lambda: get_cache())
        self.register_factory('cache_manager', lambda: get_cache())  # Alias for cache_manager
        
        # Database
        self.register(
            'database_manager',
            DatabaseManager,
            factory=lambda config: DatabaseManager(config.SQLALCHEMY_DATABASE_URI) 
                    if hasattr(config, 'SQLALCHEMY_DATABASE_URI') and config.SQLALCHEMY_DATABASE_URI 
                    else None,
            dependencies={'config': 'config'}
        )
        
        # Authentication
        self.register('auth_manager', AuthManager)
        
        # Rate Limiter
        self.register(
            'rate_limiter',
            RateLimiter,
            dependencies={'cache_manager': 'cache'}
        )
        
        # Monitoring
        self.register_factory('metrics_collector', lambda: get_metrics_collector())
        self.register_factory('health_checker', lambda: get_health_checker())
        
        # Blacklist Manager
        self.register(
            'blacklist_manager',
            UnifiedBlacklistManager,
            factory=lambda cache: UnifiedBlacklistManager('data', cache_backend=cache, db_url='sqlite:///instance/blacklist.db'),
            dependencies={'cache': 'cache'}
        )
        
        # Collection Manager
        try:
            from .collection_manager import CollectionManager
            self.register(
                'collection_manager',
                CollectionManager,
                factory=lambda: CollectionManager(),
                dependencies={}
            )
            logger.info("Collection Manager registered in container")
        except Exception as e:
            logger.warning(f"Collection Manager registration failed: {e}")
        
        # API Routes
        self.register(
            'api_routes',
            UnifiedAPIRoutes,
            dependencies={'blacklist_manager': 'blacklist_manager'}
        )
    
    def configure_flask_app(self, app):
        """Flask 앱에 서비스 연결"""
        # Flask g 객체에 서비스 바인딩
        app.before_request(self._inject_services_to_g)
        
        # Flask 확장으로 서비스 등록
        app.container = self
        app.blacklist_manager = self.resolve('blacklist_manager')
        app.cache = self.resolve('cache')
        app.auth_manager = self.resolve('auth_manager')
        app.metrics = self.resolve('metrics_collector')
        app.health_checker = self.resolve('health_checker')
        
        # 데이터베이스가 구성된 경우에만 등록
        try:
            db_manager = self.resolve('database_manager')
            if db_manager:
                app.db_manager = db_manager
                # 데이터베이스 초기화
                db_manager.init_db()
                db_manager.optimize_database()
        except Exception as e:
            logger.warning(f"Database not configured: {e}")
        
        logger.info("Flask app configured with dependency injection")
    
    def _inject_services_to_g(self):
        """Flask g 객체에 서비스 주입"""
        from flask import g
        
        # 핵심 서비스들을 g에 주입
        g.container = self
        g.blacklist_manager = self.resolve('blacklist_manager')
        g.cache = self.resolve('cache')
        g.auth_manager = self.resolve('auth_manager')


# 글로벌 컨테이너 인스턴스
_container_instance: Optional[BlacklistContainer] = None


def get_container() -> BlacklistContainer:
    """글로벌 컨테이너 인스턴스 반환"""
    global _container_instance
    if _container_instance is None:
        _container_instance = BlacklistContainer()
        _container_instance.initialize()
    return _container_instance


def reset_container():
    """컨테이너 리셋 (주로 테스트용)"""
    global _container_instance
    if _container_instance:
        _container_instance.clear()
    _container_instance = None


# 편의 함수들
def inject(service_name: str):
    """서비스 주입 데코레이터"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            container = get_container()
            service = container.resolve(service_name)
            return func(service, *args, **kwargs)
        return wrapper
    return decorator


def resolve_service(service_name: str) -> Any:
    """서비스 해결 편의 함수"""
    return get_container().resolve(service_name)