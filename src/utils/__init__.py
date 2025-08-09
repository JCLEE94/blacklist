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
from .advanced_cache import EnhancedSmartCache as CacheManager
from .auth import AuthManager, RateLimiter

try:
    from .advanced_cache import cached, get_cache
except ImportError:
    # Fallback implementations
    def get_cache():
        return None

    def cached(cache, ttl=300, key_prefix=""):
        def decorator(func):
            return func

        return decorator


from .monitoring import (HealthChecker, MetricsCollector, get_health_checker,
                         get_metrics_collector, track_performance)

try:
    from .performance_optimizer import measure_performance, profile_function

    # Fallback implementations for missing functions
    def get_connection_manager():
        return None

    def get_profiler():
        return None

    def get_response_optimizer():
        return None

except ImportError:
    # Fallback implementations
    def get_connection_manager():
        return None

    def get_profiler():
        return None

    def get_response_optimizer():
        return None

    def measure_performance(func):
        return func

    def profile_function(func):
        return func


# Configuration utilities moved to core.constants

# CICD Troubleshooter modules (modularized for 500-line compliance)
try:
    from .cicd_error_patterns import ErrorPatternManager
    from .cicd_fix_strategies import FixStrategyManager
    from .cicd_troubleshooter import (CICDTroubleshooter,
                                      analyze_pipeline_errors,
                                      create_error_manager, create_fix_manager,
                                      create_troubleshooter)
    from .cicd_utils import CICDUtils
except ImportError:
    # Fallback for missing CICD modules
    def create_troubleshooter(*args, **kwargs):
        return None

    def create_error_manager():
        return None

    def create_fix_manager():
        return None

    def analyze_pipeline_errors(*args, **kwargs):
        return None


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
    # CICD Troubleshooter utilities
    "CICDTroubleshooter",
    "ErrorPatternManager",
    "FixStrategyManager",
    "CICDUtils",
    "create_troubleshooter",
    "create_error_manager",
    "create_fix_manager",
    "analyze_pipeline_errors",
]

__version__ = "2.1.0-unified"
__author__ = "Blacklist Team"
__description__ = "Unified utility functions for Blacklist Manager"
