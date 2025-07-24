"""
Core business logic module for Blacklist Manager

이 모듈은 시스템의 핵심 비즈니스 로직을 제공합니다:
- UnifiedBlacklistManager: 통합 블랙리스트 관리
- UnifiedAPIRoutes: 통합 API 라우트
- DatabaseManager: 데이터베이스 관리
- 각종 검증자 및 상수
"""
from .constants import (API_VERSION, DEFAULT_CACHE_TTL,
                        DEFAULT_DATA_RETENTION_DAYS, SUPPORTED_IP_FORMATS)
# from .app_compact import create_compact_app  # Remove to avoid circular import
# Import managers directly when needed to avoid circular imports
# from .blacklist_unified import UnifiedBlacklistManager
# from .routes_unified import UnifiedAPIRoutes
from .database import DatabaseManager
from .exceptions import (BlacklistError, CacheError, DatabaseError,
                         ValidationError)
from .models import BlacklistEntry, MonthData, SystemHealth
from .validators import (sanitize_ip, validate_ip, validate_ip_list,
                         validate_month_format)

__all__ = [
    # Main application factory
    # 'create_compact_app',  # Remove to avoid circular import
    # Core managers
    # 'UnifiedBlacklistManager',
    # 'UnifiedAPIRoutes',
    "DatabaseManager",
    # Validators
    "validate_ip",
    "validate_ip_list",
    "validate_month_format",
    "sanitize_ip",
    # Constants
    "DEFAULT_CACHE_TTL",
    "DEFAULT_DATA_RETENTION_DAYS",
    "API_VERSION",
    "SUPPORTED_IP_FORMATS",
    # Models
    "BlacklistEntry",
    "SystemHealth",
    "MonthData",
    # Exceptions
    "BlacklistError",
    "ValidationError",
    "CacheError",
    "DatabaseError",
]

__version__ = "2.1.2-unified"
__author__ = "Blacklist Team"
__description__ = "Unified Blacklist Management System Core"
