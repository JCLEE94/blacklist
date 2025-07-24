"""
Utility functions module for Blacklist Manager

이 모듈은 시스템 전반에 사용되는 유틸리티 함수들을 제공합니다:
- 통합 데코레이터 시스템
- 캐싱 시스템 (Redis/In-memory)
- 인증 및 권한 관리
- 모니터링 및 성능 추적
- 구성 관리
"""
# Unified decorators - imported directly to avoid circular imports
# from .unified_decorators import (
#     unified_cache,
#     unified_rate_limit,
#     unified_auth,
#     unified_monitoring,
#     unified_validation,
#     api_endpoint,
#     admin_endpoint,
#     public_endpoint,
#     initialize_decorators
# )
from .cache import CacheManager, get_cache, cached
from .auth import AuthManager, RateLimiter
from .monitoring import (
    get_metrics_collector,
    get_health_checker,
    track_performance,
    MetricsCollector,
    HealthChecker,
)
from .performance import (
    get_profiler,
    get_response_optimizer,
    get_connection_manager,
    profile_function,
    measure_performance,
)

# Configuration utilities moved to core.constants

__all__ = [
    # Cache utilities
    "CacheManager",
    "get_cache",
    "cached",
    # Authentication utilities
    "AuthManager",
    "RateLimiter",
    # Monitoring utilities
    "get_metrics_collector",
    "get_health_checker",
    "track_performance",
    "MetricsCollector",
    "HealthChecker",
    # Performance utilities
    "get_profiler",
    "get_response_optimizer",
    "get_connection_manager",
    "profile_function",
    "measure_performance",
]

__version__ = "2.1.0-unified"
__author__ = "Blacklist Team"
__description__ = "Unified utility functions for Blacklist Manager"
