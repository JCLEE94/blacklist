#!/usr/bin/env python3
"""
수집기 팩토리 - 모든 수집기를 생성하고 관리
"""

import logging
import os
from typing import TYPE_CHECKING
from typing import Dict
from typing import Optional

if TYPE_CHECKING:
    from ..collectors.secudium_collector import SecudiumCollector

from .regtech_collector import RegtechCollector
from .unified_collector import CollectionConfig
from .unified_collector import UnifiedCollectionManager

logger = logging.getLogger(__name__)


class CollectorFactory:
    """수집기 팩토리 클래스"""

    def __init__(self):
        self.manager = None
        self._initialized = False

    def create_collection_manager(self) -> UnifiedCollectionManager:
        """통합 수집 관리자 생성 및 수집기 등록"""
        if self.manager is None:
            self.manager = UnifiedCollectionManager()
            self._register_all_collectors()
        return self.manager

    def _register_all_collectors(self):
        """모든 수집기를 관리자에 등록"""
        try:
            # REGTECH 수집기 등록
            regtech_collector = self._create_regtech_collector()
            if regtech_collector:
                self.manager.register_collector(regtech_collector)
                logger.info("REGTECH 수집기 등록 완료")

            # SECUDIUM 수집기 등록 (비활성화 상태)
            secudium_collector = self._create_secudium_collector()
            if secudium_collector:
                self.manager.register_collector(secudium_collector)
                logger.info("SECUDIUM 수집기 등록 완료 (비활성화)")

            self._initialized = True
            logger.info("모든 수집기 등록 완료")

        except Exception as e:
            logger.error(f"수집기 등록 실패: {e}")
            raise

    def _create_regtech_collector(self) -> Optional[RegtechCollector]:
        """REGTECH 수집기 생성"""
        try:
            # 환경 변수 확인
            username = os.getenv("REGTECH_USERNAME")
            password = os.getenv("REGTECH_PASSWORD")

            if not username or not password:
                logger.warning("REGTECH 계정 정보가 없어 수집기를 비활성화합니다")
                enabled = False
            else:
                enabled = self._should_enable_collection("REGTECH")

            # 설정 생성
            config = CollectionConfig(
                enabled=enabled,
                interval=int(os.getenv("REGTECH_INTERVAL", "3600")),  # 1시간
                max_retries=int(os.getenv("REGTECH_MAX_RETRIES", "3")),
                timeout=int(os.getenv("REGTECH_TIMEOUT", "300")),  # 5분
                settings={
                    "collection_days": int(os.getenv("REGTECH_COLLECTION_DAYS", "30")),
                    "max_pages": int(os.getenv("REGTECH_MAX_PAGES", "100")),
                    "page_size": int(os.getenv("REGTECH_PAGE_SIZE", "100")),
                },
            )

            return RegtechCollector(config)

        except Exception as e:
            logger.error(f"REGTECH 수집기 생성 실패: {e}")
            return None

    def _create_secudium_collector(self) -> Optional["SecudiumCollector"]:
        """SECUDIUM 수집기 생성"""
        try:
            from ..collectors.secudium_collector import SecudiumCollector

            # 설정 생성 (비활성화 상태)
            config = CollectionConfig(
                enabled=False,  # 계정 이슈로 비활성화
                interval=int(os.getenv("SECUDIUM_INTERVAL", "3600")),
                max_retries=int(os.getenv("SECUDIUM_MAX_RETRIES", "3")),
                timeout=int(os.getenv("SECUDIUM_TIMEOUT", "300")),
                settings={
                    "collection_days": int(os.getenv("SECUDIUM_COLLECTION_DAYS", "30"))
                },
            )

            return SecudiumCollector(config)

        except Exception as e:
            logger.error(f"SECUDIUM 수집기 생성 실패: {e}")
            return None

    def _should_enable_collection(self, source: str) -> bool:
        """수집 활성화 여부 결정"""
        try:
            # 전역 수집 비활성화 확인
            force_disable = (
                os.getenv("FORCE_DISABLE_COLLECTION", "false").lower() == "true"
            )
            if force_disable:
                logger.info(f"{source} 수집기: FORCE_DISABLE_COLLECTION으로 비활성화")
                return False

            # 개별 수집기 활성화 확인
            collection_enabled = (
                os.getenv("COLLECTION_ENABLED", "false").lower() == "true"
            )
            if not collection_enabled:
                logger.info(f"{source} 수집기: COLLECTION_ENABLED=false로 비활성화")
                return False

            # 개별 소스 활성화 확인
            source_enabled = os.getenv("{source}_ENABLED", "true").lower() == "true"
            if not source_enabled:
                logger.info(f"{source} 수집기: {source}_ENABLED=false로 비활성화")
                return False

            logger.info(f"{source} 수집기: 활성화됨")
            return True

        except Exception as e:
            logger.error(f"{source} 수집기 활성화 여부 확인 실패: {e}")
            return False

    def get_collector_status(self) -> Dict[str, any]:
        """모든 수집기 상태 반환"""
        if not self.manager:
            return {"error": "Collection manager not initialized"}

        return self.manager.get_status()

    def enable_collector(self, name: str) -> bool:
        """특정 수집기 활성화"""
        if not self.manager:
            return False

        try:
            self.manager.enable_collector(name)
            logger.info(f"수집기 활성화: {name}")
            return True
        except Exception as e:
            logger.error(f"수집기 활성화 실패 ({name}): {e}")
            return False

    def disable_collector(self, name: str) -> bool:
        """특정 수집기 비활성화"""
        if not self.manager:
            return False

        try:
            self.manager.disable_collector(name)
            logger.info(f"수집기 비활성화: {name}")
            return True
        except Exception as e:
            logger.error(f"수집기 비활성화 실패 ({name}): {e}")
            return False

    async def collect_from_source(self, source_name: str) -> Dict[str, any]:
        """특정 소스에서 수집"""
        if not self.manager:
            return {"success": False, "error": "Collection manager not initialized"}

        try:
            result = await self.manager.collect_single(source_name)
            if result:
                return {"success": True, "result": result.to_dict()}
            else:
                return {
                    "success": False,
                    "error": "Collector '{source_name}' not found",
                }
        except Exception as e:
            logger.error(f"소스별 수집 실패 ({source_name}): {e}")
            return {"success": False, "error": str(e)}

    async def collect_all(self) -> Dict[str, any]:
        """모든 소스에서 수집"""
        if not self.manager:
            return {"success": False, "error": "Collection manager not initialized"}

        try:
            results = await self.manager.collect_all()
            return {
                "success": True,
                "results": {name: result.to_dict() for name, result in results.items()},
            }
        except Exception as e:
            logger.error(f"전체 수집 실패: {e}")
            return {"success": False, "error": str(e)}


# 전역 팩토리 인스턴스
_collector_factory = None


def get_collector_factory() -> CollectorFactory:
    """전역 수집기 팩토리 인스턴스 반환"""
    global _collector_factory
    if _collector_factory is None:
        _collector_factory = CollectorFactory()
    return _collector_factory


def get_collection_manager() -> UnifiedCollectionManager:
    """전역 수집 관리자 인스턴스 반환"""
    factory = get_collector_factory()
    return factory.create_collection_manager()
