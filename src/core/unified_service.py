#!/usr/bin/env python3
"""
통합 블랙리스트 관리 서비스 - 새로운 모듈화된 버전
모든 블랙리스트 운영을 하나로 통합한 서비스
분리된 모듈들에서 서비스를 가져와서 등록
"""

# Re-export the main service and factory functions for backwards compatibility
from .services.unified_service_core import ServiceHealth, UnifiedBlacklistService
from .services.unified_service_factory import (
    get_unified_service,
    is_service_initialized,
    reset_unified_service,
)

# Export for backwards compatibility
__all__ = [
    "UnifiedBlacklistService",
    "ServiceHealth",
    "get_unified_service",
    "reset_unified_service",
    "is_service_initialized",
]
