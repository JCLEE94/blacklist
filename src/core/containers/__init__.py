"""
의존성 주입 컨테이너 패키지

Blacklist 시스템의 의존성 주입을 관리하는 컨테이너 시스템입니다.

주요 구성 요소:
- ServiceDefinition: 서비스 정의 데이터 클래스
- ServiceContainer: 기본 서비스 컨테이너
- BlacklistContainer: Blacklist 전용 컨테이너
- get_container: 글로벌 컨테이너 인스턴스
- inject: 의존성 주입 데코레이터
"""

from .base_container import ServiceContainer, ServiceDefinition
from .blacklist_container import BlacklistContainer
from .utils import (
    get_auth_manager,
    get_blacklist_manager,
    get_cache_manager,
    get_collection_manager,
    get_container,
    inject,
    reset_container,
    resolve_service,
)

__all__ = [
    "ServiceDefinition",
    "ServiceContainer",
    "BlacklistContainer",
    "get_container",
    "reset_container",
    "inject",
    "resolve_service",
    "get_blacklist_manager",
    "get_cache_manager",
    "get_collection_manager",
    "get_auth_manager",
]
