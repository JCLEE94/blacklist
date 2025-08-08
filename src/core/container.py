"""
의존성 주입 컨테이너 (Dependency Injection Container)

시스템의 모든 의존성을 중앙에서 관리하고 주입하는 컨테이너입니다.
이를 통해 모듈 간 결합도를 낮추고 테스트 가능성을 높입니다.

참고: 이 모듈은 하위 호환성을 위해 유지됩니다.
새로운 코드는 src.core.containers 패키지를 직접 사용하세요.
"""

# 하위 호환성을 위한 임포트 - 새로운 모듈 구조에서 가져옴
from .containers import (BlacklistContainer, ServiceContainer,
                         ServiceDefinition, get_auth_manager,
                         get_blacklist_manager, get_cache_manager,
                         get_collection_manager, get_container, inject,
                         reset_container, resolve_service)
# 테스트 모듈 임포트 제거 - 모듈이 누락됨

# 하위 호환성을 위한 별칭
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

# 이 파일은 하위 호환성을 위해 유지됩니다.
# 새로운 코드는 src.core.containers 패키지를 직접 사용하세요.
