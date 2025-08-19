"""
Blacklist 전용 컨테이너

Blacklist 시스템의 모든 핵심 서비스를 등록하고 관리하는 전용 컨테이너입니다.
"""

import logging
import os

from .base_container import ServiceContainer
from src.config.settings import settings

logger = logging.getLogger(__name__)


class BlacklistContainer(ServiceContainer):
    """
    Blacklist 전용 의존성 주입 컨테이너

    시스템의 모든 핵심 서비스를 등록하고 관리합니다.
    """

    def __init__(self):
        super().__init__()
        self._configure_core_services()

    def _configure_core_services(self):
        """핵심 서비스 구성"""
        from src.config.factory import get_config
        from src.utils.advanced_cache import get_cache
        from src.utils.auth import AuthManager

        # Monitoring removed for performance optimization
        from ..blacklist_unified import UnifiedBlacklistManager
        from ..database import DatabaseManager

        # Configuration
        self.register_factory("config", lambda: get_config())

        # Cache
        self.register_factory("cache", lambda: get_cache())
        self.register_factory(
            "cache_manager", lambda: get_cache()
        )  # Alias for cache_manager

        # Database
        self.register(
            "database_manager",
            DatabaseManager,
            factory=lambda config: (
                DatabaseManager(config.SQLALCHEMY_DATABASE_URI)
                if hasattr(config, "SQLALCHEMY_DATABASE_URI")
                and config.SQLALCHEMY_DATABASE_URI
                else None
            ),
            dependencies={"config": "config"},
        )

        # Authentication
        self.register("auth_manager", AuthManager)

        # Monitoring
        # Monitoring services removed for performance optimization

        # Blacklist Manager - 설정에서 데이터베이스 URI 가져오기
        blacklist_db_url = settings.database_uri

        self.register(
            "blacklist_manager",
            UnifiedBlacklistManager,
            factory=lambda cache: UnifiedBlacklistManager(
                "data", cache_backend=cache, db_url=blacklist_db_url
            ),
            dependencies={"cache": "cache"},
        )

        self._configure_collectors()
        self._configure_tracking_services()

    def _configure_collectors(self):
        """데이터 콜렉터 구성"""
        # Collection Manager - Use PostgreSQL database URL
        try:
            from ..collection_manager import CollectionManager

            # Use PostgreSQL database URL from settings
            db_url = settings.database_uri
            config_path = "/app/instance/collection_config.json"

            # 로컬 개발 환경에서는 상대 경로
            if not os.path.exists("/app"):
                config_path = "instance/collection_config.json"

            self.register(
                "collection_manager",
                CollectionManager,
                factory=lambda: CollectionManager(
                    db_path=db_url, config_path=config_path
                ),
                dependencies={},
            )
            logger.info(f"Collection Manager registered with db_url: {db_url}")
        except Exception as e:
            logger.warning(f"Collection Manager registration failed: {e}")

        # Database-driven Collector (통합 수집 시스템)
        try:
            from ..collection_db_collector import DatabaseCollectionSystem

            self.register(
                "db_collector",
                DatabaseCollectionSystem,
                factory=lambda: DatabaseCollectionSystem(),
                dependencies={},
            )
            logger.info("Database-driven Collector registered in container")
        except Exception as e:
            logger.error(f"Database Collector registration failed: {e}")

        # REGTECH Collector (existing integration)
        try:
            from ..collectors.regtech_collector import RegtechCollector

            self.register(
                "regtech_collector",
                RegtechCollector,
                factory=lambda: RegtechCollector(None),  # Uses DB config
                dependencies={},
            )
            logger.info("REGTECH Collector registered in container (DB integrated)")
        except Exception as e:
            logger.warning(f"REGTECH Collector registration failed: {e}")

        # SECUDIUM Collector (existing integration)
        try:
            from ..collectors.secudium_collector import SecudiumCollector

            self.register(
                "secudium_collector",
                SecudiumCollector,
                factory=lambda: SecudiumCollector(None),  # Uses DB config
                dependencies={},
            )
            logger.info("SECUDIUM Collector registered in container (DB integrated)")
        except Exception as e:
            logger.warning(f"SECUDIUM Collector registration failed: {e}")

    def _configure_tracking_services(self):
        """추적 서비스 구성"""
        # Collection Progress Tracker
        try:
            from ..collection_progress import get_progress_tracker

            self.register(
                "progress_tracker",
                type(get_progress_tracker()),  # Get the actual class type
                factory=lambda: get_progress_tracker(),  # Singleton instance
                singleton=True,
                dependencies={},
            )
            logger.info("Collection Progress Tracker registered in container")
        except Exception as e:
            logger.warning(f"Progress Tracker registration failed: {e}")

    def register_factory(self, name: str, factory: callable, singleton: bool = True):
        """팩토리 방식으로 서비스 등록"""
        # 가짜 타입 생성 (팩토리에서 만들어질 인스턴스의 타입)
        mock_type = type("{name.title()}Service", (), {})
        self.register(
            name=name, service_type=mock_type, factory=factory, singleton=singleton
        )

    def configure_flask_app(self, app):
        """
        Flask 앱에 서비스 연결"""
        # Flask g 객체에 서비스 바인딩
        app.before_request(self._inject_services_to_g)

    def _inject_services_to_g(self):
        """
        Flask g 객체에 서비스 주입"""
        from flask import g

        # 주요 서비스들을 g에 주입
        try:
            g.blacklist_manager = self.get("blacklist_manager")
            g.cache_manager = self.get("cache_manager")
            g.auth_manager = self.get("auth_manager")
        except Exception as e:
            logger.warning(f"Failed to inject services to Flask g: {e}")

    def get_unified_service(self):
        """
        Unified Service 반환 (후방 호환성)"""
        try:
            from ..services.unified_service_factory import get_unified_service

            return get_unified_service()
        except ImportError:
            logger.warning("Unified service not available")
            return None
