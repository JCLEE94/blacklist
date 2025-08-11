#!/usr/bin/env python3
"""
통합 블랙리스트 관리 서비스 - 핵심 클래스 (Modularized)
모든 블랙리스트 운영을 하나로 통합한 서비스의 핵심 기능

This module now uses modular mixins for better code organization:
- CoreOperationsMixin: Service lifecycle and health management
- DatabaseOperationsMixin: Database-specific operations
- LoggingOperationsMixin: Logging and monitoring functionality
- CollectionServiceMixin: Collection-related operations
- StatisticsServiceMixin: Analytics and statistics
"""

import logging
import os

from ..container import get_container
from .collection_service import CollectionServiceMixin
from .core_operations import CoreOperationsMixin
from .database_operations import DatabaseOperationsMixin
from .logging_operations import LoggingOperationsMixin
from .statistics_service import StatisticsServiceMixin

logger = logging.getLogger(__name__)


class UnifiedBlacklistService(
    CollectionServiceMixin,
    StatisticsServiceMixin,
    CoreOperationsMixin,
    DatabaseOperationsMixin,
    LoggingOperationsMixin,
):
    """
    통합 블랙리스트 서비스 - 모든 기능을 하나로 통합
    REGTECH, SECUDIUM 수집부터 API 서빙까지 단일 서비스로 처리

    Uses multiple inheritance with specialized mixins for modular functionality.
    """

    def __init__(self):
        self.container = get_container()
        self.logger = logging.getLogger(__name__)

        # 서비스 상태
        self._running = False
        self._components = {}

        # 통합 설정
        self.config = {
            "regtech_enabled": os.getenv("REGTECH_ENABLED", "true").lower() == "true",
            "auto_collection": os.getenv("AUTO_COLLECTION", "true").lower() == "true",
            "collection_interval": int(os.getenv("COLLECTION_INTERVAL", 3600)),
            "service_name": "blacklist-unified",
            "version": "3.0.3-cicd-test",
        }

        # 수집 로그 저장 (메모리, 최대 1000개)
        self.collection_logs = []
        self.max_logs = 1000

        # 수집 상태 관리 (메모리) - 기본값 False
        self.collection_enabled = False
        self.daily_collection_enabled = False

        # Initialize core services immediately
        try:
            self.blacklist_manager = self.container.get("blacklist_manager")
            self.cache = self.container.get("cache_manager")
            # Try to get collection_manager
            try:
                self.collection_manager = self.container.get("collection_manager")
                # CollectionManager의 상태와 동기화
                if self.collection_manager:
                    self.collection_enabled = self.collection_manager.collection_enabled
            except Exception as e:
                self.logger.warning(f"Collection Manager not available: {e}")
                self.collection_manager = None
        except Exception as e:
            self.logger.error(f"Failed to initialize core services: {e}")
            self.blacklist_manager = None
            self.cache = None
            self.collection_manager = None

        # 로그 테이블 초기화 (now from DatabaseOperationsMixin)
        self._ensure_log_table()

        # 데이터베이스에서 기존 로그 로드 (now from DatabaseOperationsMixin)
        try:
            existing_logs = self._load_logs_from_db(100)
            self.collection_logs = existing_logs
        except Exception as e:
            self.logger.warning(f"Failed to load existing logs: {e}")

        # Mark as running for basic health checks
        self._running = True

        # 컴포넌트 즉시 초기화 (웹 서버에서도 사용할 수 있도록)
        self._sync_component_init()

        # 최초 실행 시 자동 수집 수행 (즉시 실행) - now from CoreOperationsMixin
        if (
            self.collection_manager
            and self.collection_manager.is_initial_collection_needed()
        ):
            self.logger.info("🔥 최초 실행 - 즉시 수집 시작")
            self._perform_initial_collection_now()

    def _sync_component_init(self):
        """동기적 컴포넌트 초기화"""
        try:
            from ..regtech_simple_collector import (
                RegtechSimpleCollector as RegtechCollector,
            )

            # REGTECH 수집기 초기화
            if self.config["regtech_enabled"]:
                self._components["regtech"] = RegtechCollector("data")
                self.logger.info("✅ REGTECH 수집기 동기 초기화 완료")
        except Exception as e:
            self.logger.error(f"동기 컴포넌트 초기화 실패: {e}")

    async def _immediate_component_init(self):
        """즉시 컴포넌트 초기화"""
        try:
            await self._initialize_components()
        except Exception as e:
            self.logger.error(f"즉시 컴포넌트 초기화 실패: {e}")
            # 동기적으로 시도
            self._sync_component_init()

    # _perform_initial_collection_now is now provided by CoreOperationsMixin

    # start() and stop() methods are now provided by CoreOperationsMixin

    # All initialization methods are now provided by CoreOperationsMixin

    # All logging methods are now provided by LoggingOperationsMixin and DatabaseOperationsMixin

    # All core operation methods are now provided by CoreOperationsMixin

    # All database operation methods are now provided by DatabaseOperationsMixin
