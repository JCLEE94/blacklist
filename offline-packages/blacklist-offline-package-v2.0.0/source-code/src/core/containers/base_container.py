"""
기본 서비스 컨테이너

의존성 주입을 위한 기본 컨테이너 구현을 제공합니다.
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Type, TypeVar

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
    ) -> None:
        """서비스 등록"""
        if name in self._services:
            logger.warning(f"Service '{name}' is already registered. Overriding.")

        self._services[name] = ServiceDefinition(
            service_type=service_type,
            factory=factory,
            singleton=singleton,
            dependencies=dependencies or {},
        )

        logger.debug(f"Registered service: {name} -> {service_type.__name__}")

    def get(self, name: str) -> Any:
        """서비스 인스턴스 반환"""
        if name not in self._services:
            raise ValueError("Service '{name}' is not registered")

        service_def = self._services[name]

        # 싱글톤 패턴 처리
        if service_def.singleton and name in self._instances:
            return self._instances[name]

        # 순환 의존성 검사
        if name in self._resolving:
            raise ValueError("Circular dependency detected: {name}")

        try:
            self._resolving.add(name)
            instance = self._create_instance(name, service_def)

            if service_def.singleton:
                self._instances[name] = instance

            return instance
        finally:
            self._resolving.discard(name)

    def _create_instance(self, name: str, service_def: ServiceDefinition) -> Any:
        """서비스 인스턴스 생성"""
        try:
            if service_def.factory:
                # 팩토리 함수를 사용한 생성
                dependencies = self._resolve_dependencies(
                    service_def.dependencies or {}
                )
                return service_def.factory(**dependencies)
            else:
                # 기본 생성자 사용
                dependencies = self._resolve_dependencies(
                    service_def.dependencies or {}
                )
                return service_def.service_type(**dependencies)
        except Exception as e:
            logger.error(f"Failed to create service '{name}': {e}")
            raise RuntimeError("Service creation failed: {name}") from e

    def _resolve_dependencies(self, dependencies: Dict[str, str]) -> Dict[str, Any]:
        """의존성 해결"""
        resolved = {}
        for param_name, service_name in dependencies.items():
            resolved[param_name] = self.get(service_name)
        return resolved

    def has_service(self, name: str) -> bool:
        """서비스 등록 여부 확인"""
        return name in self._services

    def list_services(self) -> Dict[str, Type]:
        """등록된 서비스 목록 반환"""
        return {
            name: service_def.service_type
            for name, service_def in self._services.items()
        }

    def clear_instances(self):
        """싱글톤 인스턴스 모두 삭제"""
        self._instances.clear()
        logger.debug("All singleton instances cleared")

    def shutdown(self):
        """컨테이너 종료 및 리소스 정리"""
        # 인스턴스들의 cleanup 메서드 호출
        for name, instance in self._instances.items():
            if hasattr(instance, "shutdown"):
                try:
                    instance.shutdown()
                    logger.debug(f"Shutdown service: {name}")
                except Exception as e:
                    logger.error(f"Failed to shutdown service {name}: {e}")

        self.clear_instances()
        logger.info("Service container shut down")

    def get_health_status(self) -> Dict[str, Any]:
        """컨테이너 건강 상태 반환"""
        healthy_services = 0
        unhealthy_services = []

        for name, instance in self._instances.items():
            try:
                if hasattr(instance, "health_check"):
                    if instance.health_check():
                        healthy_services += 1
                    else:
                        unhealthy_services.append(name)
                else:
                    healthy_services += 1  # 건강 검사가 없으면 정상으로 간주
            except Exception as e:
                logger.warning(f"Health check failed for {name}: {e}")
                unhealthy_services.append(name)

        return {
            "total_services": len(self._services),
            "active_instances": len(self._instances),
            "healthy_services": healthy_services,
            "unhealthy_services": unhealthy_services,
            "status": "healthy" if not unhealthy_services else "unhealthy",
        }
