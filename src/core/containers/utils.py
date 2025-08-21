"""
컨테이너 유틸리티 함수들

컨테이너 사용을 위한 헬퍼 함수들과 데코레이터를 제공합니다.
"""

import functools
import logging
from typing import Any, TypeVar

from .blacklist_container import BlacklistContainer

logger = logging.getLogger(__name__)

T = TypeVar("T")

# 글로벌 컨테이너 인스턴스
_container: BlacklistContainer = None


def get_container() -> BlacklistContainer:
    """글로벌 컨테이너 인스턴스 반환"""
    global _container
    if _container is None:
        _container = BlacklistContainer()
        logger.info("Global blacklist container created")
    return _container


def reset_container():
    """컨테이너 리셋 (테스트용)"""
    global _container
    if _container:
        _container.shutdown()
    _container = None
    logger.info("Container reset")


def inject(service_name: str):
    """
    서비스 의존성 주입 데코레이터

    Usage:
        @inject('blacklist_manager')
        def my_function(blacklist_manager):
            return blacklist_manager.get_active_ips()
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            container = get_container()
            service = container.get(service_name)
            return func(service, *args, **kwargs)

        return wrapper

    return decorator


def resolve_service(service_name: str) -> Any:
    """서비스 해결 헬퍼 함수"""
    container = get_container()
    return container.get(service_name)


# 편의 함수들
def get_blacklist_manager():
    """
    Blacklist Manager 인스턴스 반환"""
    return resolve_service("blacklist_manager")


def get_cache_manager():
    """
    Cache Manager 인스턴스 반환"""
    return resolve_service("cache_manager")


def get_collection_manager():
    """
    Collection Manager 인스턴스 반환"""
    try:
        return resolve_service("collection_manager")
    except ValueError:
        logger.warning("Collection manager not available")
        return None


def get_auth_manager():
    """
    Auth Manager 인스턴스 반환"""
    return resolve_service("auth_manager")


def get_unified_service():
    """
    Unified Service 인스턴스 반환"""
    try:
        return resolve_service("unified_service")
    except ValueError:
        logger.warning("Unified service not available in container")
        # Fallback to factory
        from ..services.unified_service_factory import (
            get_unified_service as factory_get,
        )

        return factory_get()
