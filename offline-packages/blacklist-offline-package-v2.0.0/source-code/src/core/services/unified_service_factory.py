#!/usr/bin/env python3
"""
통합 블랙리스트 서비스 팩토리
서비스 인스턴스를 생성하고 관리하는 팩토리 함수
"""

import logging
from typing import Optional

from .unified_service_core import UnifiedBlacklistService

logger = logging.getLogger(__name__)

# 싱글턴 인스턴스
_unified_service_instance: Optional[UnifiedBlacklistService] = None


def get_unified_service() -> UnifiedBlacklistService:
    """
    통합 디블랙리스트 서비스 인스턴스 반환
    싱글턴 패턴으로 하나의 인스턴스만 생성하여 반환
    """
    global _unified_service_instance

    if _unified_service_instance is None:
        logger.info("🔄 Creating new UnifiedBlacklistService instance...")
        _unified_service_instance = UnifiedBlacklistService()
        logger.info("✅ UnifiedBlacklistService instance created successfully")

    return _unified_service_instance


def reset_unified_service() -> None:
    """
    통합 서비스 인스턴스 리셋 (테스트용)
    """
    global _unified_service_instance
    _unified_service_instance = None
    logger.info("🔄 UnifiedBlacklistService instance reset")


def is_service_initialized() -> bool:
    """
    서비스가 초기화되었는지 확인
    """
    return _unified_service_instance is not None
