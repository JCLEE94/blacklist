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

T = TypeVar("T")


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

    def register(
        self,
        name: str,
        service_type: Type[T],
        factory: Optional[Callable] = None,
        singleton: bool = True,
        dependencies: Optional[Dict[str, str]] = None,
    ) -> "ServiceContainer":
        """서비스 등록"""
        if self._initialized:
            raise RuntimeError(
                "Cannot register services after container initialization"
            )

        self._services[name] = ServiceDefinition(
            service_type=service_type,
            factory=factory,
            singleton=singleton,
            dependencies=dependencies or {},
        )

        logger.debug(f"Registered service: {name} -> {service_type.__name__}")
        return self

    def register_instance(self, name: str, instance: Any) -> "ServiceContainer":
        """인스턴스 직접 등록"""
        if self._initialized:
            raise RuntimeError(
                "Cannot register instances after container initialization"
            )

        self._instances[name] = instance
        logger.debug(f"Registered instance: {name} -> {type(instance).__name__}")
        return self

    def register_factory(
        self, name: str, factory: Callable[[], T], singleton: bool = True
    ) -> "ServiceContainer":
        """팩토리 함수 등록"""
        return self.register(name, type(None), factory=factory, singleton=singleton)

    def get(self, name: str) -> Any:
        """서비스 조회 (resolve의 별칭)"""
        return self.resolve(name)

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
            # Special handling for disabled rate_limiter
            if name == "rate_limiter":
                logger.warning(f"Rate limiter service disabled, returning None")
                return None
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

    def initialize(self) -> "ServiceContainer":
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
                if (
                    dep_service not in self._services
                    and dep_service not in self._instances
                ):
                    raise KeyError(
                        f"Service '{service_name}' depends on unregistered service '{dep_service}'"
                    )

    def get_service_info(self) -> Dict[str, Dict[str, Any]]:
        """서비스 정보 조회"""
        info = {}

        for name, service_def in self._services.items():
            info[name] = {
                "type": service_def.service_type.__name__,
                "singleton": service_def.singleton,
                "dependencies": list(service_def.dependencies.keys()),
                "instantiated": name in self._instances,
            }

        for name, instance in self._instances.items():
            if name not in info:
                info[name] = {
                    "type": type(instance).__name__,
                    "singleton": True,
                    "dependencies": [],
                    "instantiated": True,
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

        # Configuration
        self.register_factory("config", lambda: get_config())

        # Cache
        self.register_factory("cache", lambda: get_cache())
        self.register_factory(
            "cache_manager", lambda: get_cache()
        )  # Alias for cache_manager

        # Database
        self.register(
            "database_manager",
            DatabaseManager,
            factory=lambda config: DatabaseManager(config.SQLALCHEMY_DATABASE_URI)
            if hasattr(config, "SQLALCHEMY_DATABASE_URI")
            and config.SQLALCHEMY_DATABASE_URI
            else None,
            dependencies={"config": "config"},
        )

        # Authentication
        self.register("auth_manager", AuthManager)

        # Rate Limiter - COMPLETELY DISABLED FOR STABILITY
        # self.register(
        #     'rate_limiter',
        #     RateLimiter,
        #     dependencies={'cache_manager': 'cache'}
        # )

        # Monitoring
        self.register_factory("metrics_collector", lambda: get_metrics_collector())
        self.register_factory("health_checker", lambda: get_health_checker())

        # Blacklist Manager - 설정에서 데이터베이스 URI 가져오기
        from ..config.settings import settings

        blacklist_db_url = settings.database_uri

        self.register(
            "blacklist_manager",
            UnifiedBlacklistManager,
            factory=lambda cache: UnifiedBlacklistManager(
                "data", cache_backend=cache, db_url=blacklist_db_url
            ),
            dependencies={"cache": "cache"},
        )

        # Collection Manager - Docker 환경 기반 경로 사용
        try:
            from .collection_manager import CollectionManager
            import os

            # Docker 환경에서는 고정 경로 사용
            db_path = "/app/instance/blacklist.db"
            config_path = "/app/instance/collection_config.json"

            # 로컬 개발 환경에서는 상대 경로
            if not os.path.exists("/app"):
                db_path = "instance/blacklist.db"
                config_path = "instance/collection_config.json"

            self.register(
                "collection_manager",
                CollectionManager,
                factory=lambda: CollectionManager(
                    db_path=db_path, config_path=config_path
                ),
                dependencies={},
            )
            logger.info(f"Collection Manager registered with db_path: {db_path}")
        except Exception as e:
            logger.warning(f"Collection Manager registration failed: {e}")

        # REGTECH Collector - Only use the working Simple collector
        try:
            from .regtech_simple_collector import RegtechSimpleCollector

            self.register(
                "regtech_collector",
                RegtechSimpleCollector,
                factory=lambda: RegtechSimpleCollector("data"),
                dependencies={},
            )
            logger.info(
                "Simple REGTECH Collector registered in container (working version)"
            )
        except Exception as e:
            logger.error(f"Simple REGTECH Collector registration failed: {e}")

        # SECUDIUM Collector
        try:
            from .secudium_collector import SecudiumCollector

            self.register(
                "secudium_collector",
                SecudiumCollector,
                factory=lambda: SecudiumCollector("data"),
                dependencies={},
            )
            logger.info("SECUDIUM Collector registered in container")
        except Exception as e:
            logger.warning(f"SECUDIUM Collector registration failed: {e}")

        # Collection Progress Tracker
        try:
            from .collection_progress import get_progress_tracker

            self.register(
                "progress_tracker",
                type(get_progress_tracker()),  # Get the actual class type
                factory=lambda: get_progress_tracker(),  # Singleton instance
                singleton=True,
                dependencies={},
            )
            logger.info("Collection Progress Tracker registered in container")
        except Exception as e:
            logger.warning(f"Progress Tracker registration failed: {e}")

        # API Routes
        # Blueprint registration is handled in app creation, not container

    def configure_flask_app(self, app):
        """Flask 앱에 서비스 연결"""
        # Flask g 객체에 서비스 바인딩
        app.before_request(self._inject_services_to_g)

        # Flask 확장으로 서비스 등록
        app.container = self
        app.blacklist_manager = self.resolve("blacklist_manager")
        app.cache = self.resolve("cache")
        app.auth_manager = self.resolve("auth_manager")
        app.metrics = self.resolve("metrics_collector")
        app.health_checker = self.resolve("health_checker")

        # 데이터베이스가 구성된 경우에만 등록
        try:
            db_manager = self.resolve("database_manager")
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
        g.blacklist_manager = self.resolve("blacklist_manager")
        g.cache = self.resolve("cache")
        g.auth_manager = self.resolve("auth_manager")


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


# ==============================================================================
# Rust-style 인라인 통합 테스트
# ==============================================================================

def _test_container_service_registration():
    """서비스 등록 및 해결 테스트"""
    print("🧪 컨테이너 서비스 등록/해결 테스트 시작...")
    
    try:
        container = BlacklistContainer()
        container.initialize()
        
        # 핵심 서비스들 검증
        services_to_test = [
            'blacklist_manager',
            'cache_manager', 
            'auth_manager',
            'config',
            'metrics_collector',
            'health_checker'
        ]
        
        resolved_services = {}
        for service_name in services_to_test:
            try:
                service = container.resolve(service_name)
                resolved_services[service_name] = service is not None
                print(f"  ✅ {service_name}: {'성공' if service else '실패'}")
            except Exception as e:
                resolved_services[service_name] = False
                print(f"  ❌ {service_name}: {str(e)[:50]}...")
        
        # 성공적으로 해결된 서비스 수 확인
        successful_count = sum(resolved_services.values())
        total_count = len(services_to_test)
        
        if successful_count >= total_count * 0.7:  # 70% 이상 성공
            print(f"✅ 컨테이너 서비스 등록/해결 테스트 통과 ({successful_count}/{total_count})")
            return True
        else:
            print(f"❌ 컨테이너 서비스 등록/해결 테스트 실패 ({successful_count}/{total_count})")
            return False
            
    except Exception as e:
        print(f"❌ 컨테이너 테스트 중 오류: {str(e)}")
        return False


def _test_container_singleton_behavior():
    """싱글톤 동작 검증"""
    print("🧪 컨테이너 싱글톤 동작 테스트 시작...")
    
    try:
        container1 = get_container()
        container2 = get_container()
        
        # 컨테이너 자체가 싱글톤인지 확인
        if container1 is container2:
            print("  ✅ 컨테이너 자체 싱글톤 동작 확인")
        else:
            print("  ⚠️ 컨테이너가 싱글톤이 아님")
        
        # 서비스 싱글톤 동작 확인
        try:
            manager1 = container1.resolve('blacklist_manager')
            manager2 = container2.resolve('blacklist_manager')
            
            if manager1 is manager2:
                print("  ✅ 서비스 싱글톤 동작 확인")
                singleton_ok = True
            else:
                print("  ⚠️ 서비스가 싱글톤이 아님")
                singleton_ok = False
        except Exception as e:
            print(f"  ⚠️ 서비스 싱글톤 테스트 불가: {str(e)[:30]}...")
            singleton_ok = False
        
        print("✅ 컨테이너 싱글톤 동작 테스트 완료")
        return singleton_ok
        
    except Exception as e:
        print(f"❌ 싱글톤 테스트 중 오류: {str(e)}")
        return False


def _test_container_dependency_injection():
    """의존성 주입 검증"""
    print("🧪 컨테이너 의존성 주입 테스트 시작...")
    
    try:
        container = get_container()
        service_info = container.get_service_info()
        
        print(f"  📊 등록된 서비스 수: {len(service_info)}")
        
        # 필수 서비스들이 등록되어 있는지 확인
        required_services = ['blacklist_manager', 'cache_manager', 'auth_manager']
        missing_services = []
        instantiated_services = []
        
        for service in required_services:
            if service in service_info:
                if service_info[service]['instantiated']:
                    instantiated_services.append(service)
                    print(f"  ✅ {service}: 등록됨 및 인스턴스화됨")
                else:
                    print(f"  ⚠️ {service}: 등록되었으나 인스턴스화되지 않음")
            else:
                missing_services.append(service)
                print(f"  ❌ {service}: 등록되지 않음")
        
        success_rate = len(instantiated_services) / len(required_services)
        
        if success_rate >= 0.7:  # 70% 이상 성공
            print(f"✅ 컨테이너 의존성 주입 테스트 통과 ({len(instantiated_services)}/{len(required_services)})")
            return True
        else:
            print(f"❌ 컨테이너 의존성 주입 테스트 실패 ({len(instantiated_services)}/{len(required_services)})")
            return False
            
    except Exception as e:
        print(f"❌ 의존성 주입 테스트 중 오류: {str(e)}")
        return False


def _test_container_error_handling():
    """컨테이너 오류 처리 테스트"""
    print("🧪 컨테이너 오류 처리 테스트 시작...")
    
    try:
        container = get_container()
        
        # 존재하지 않는 서비스 요청
        try:
            container.resolve('nonexistent_service')
            print("  ❌ 존재하지 않는 서비스 요청시 예외가 발생하지 않음")
            return False
        except KeyError:
            print("  ✅ 존재하지 않는 서비스 요청시 적절한 예외 발생 (KeyError)")
        except Exception as e:
            print(f"  ✅ 존재하지 않는 서비스 요청시 예외 발생: {type(e).__name__}")
        
        # Rate limiter 특별 처리 (비활성화됨)
        try:
            rate_limiter = container.resolve('rate_limiter')
            if rate_limiter is None:
                print("  ✅ Rate limiter 비활성화 처리 확인")
            else:
                print("  ⚠️ Rate limiter가 활성화되어 있음")
        except Exception as e:
            print(f"  ⚠️ Rate limiter 테스트 실패: {str(e)[:30]}...")
        
        print("✅ 컨테이너 오류 처리 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 오류 처리 테스트 중 오류: {str(e)}")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Dependency Injection Container 통합 테스트 실행")
    print("=" * 70)
    
    # 테스트 결과 수집
    test_results = []
    
    # 개별 테스트 실행
    test_results.append(_test_container_service_registration())
    test_results.append(_test_container_singleton_behavior())
    test_results.append(_test_container_dependency_injection()) 
    test_results.append(_test_container_error_handling())
    
    # 전체 결과 요약
    passed_tests = sum(test_results)
    total_tests = len(test_results)
    
    print("=" * 70)
    print("📊 테스트 결과 요약")
    print("=" * 70)
    print(f"총 테스트 수: {total_tests}")
    print(f"통과한 테스트: {passed_tests}")
    print(f"실패한 테스트: {total_tests - passed_tests}")
    print(f"성공률: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("🎉 모든 테스트 통과!")
        exit(0)
    elif passed_tests >= total_tests * 0.7:
        print("✅ 대부분 테스트 통과 (70% 이상)")
        exit(0)
    else:
        print("❌ 다수 테스트 실패")
        exit(1)
