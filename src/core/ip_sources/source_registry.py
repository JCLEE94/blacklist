"""
IP 소스 레지스트리
사용 가능한 모든 IP 소스 플러그인을 관리
"""

import logging
from typing import Any
from typing import Dict
from typing import List
from typing import Type

from .base_source import BaseIPSource

logger = logging.getLogger(__name__)


class SourceRegistry:
    """IP 소스 플러그인 레지스트리"""

    def __init__(self):
        self._sources: Dict[str, Type[BaseIPSource]] = {}
        self._initialized = False

    def register(self, source_class: Type[BaseIPSource]):
        """
        소스 클래스를 레지스트리에 등록

        Args:
            source_class: BaseIPSource를 상속한 클래스
        """
        if not issubclass(source_class, BaseIPSource):
            raise ValueError(f"Source class must inherit from BaseIPSource")

        # 임시 인스턴스를 생성하여 source_name 획득
        try:
            temp_config = type(
                "TempConfig", (), {"name": "temp", "enabled": True, "settings": {}}
            )()
            temp_instance = source_class(temp_config)
            source_name = temp_instance.source_name
        except Exception as e:
            logger.error(f"Failed to get source name from {source_class.__name__}: {e}")
            source_name = source_class.__name__

        self._sources[source_name] = source_class
        logger.info(f"Registered IP source: {source_name}")

    def get_source_class(self, name: str) -> Type[BaseIPSource]:
        """
        이름으로 소스 클래스 가져오기

        Args:
            name: 소스 이름

        Returns:
            소스 클래스
        """
        if name not in self._sources:
            raise KeyError(f"Unknown source: {name}")
        return self._sources[name]

    def list_sources(self) -> List[str]:
        """등록된 모든 소스 이름 목록"""
        return list(self._sources.keys())

    def get_source_info(self) -> Dict[str, Dict[str, Any]]:
        """
        모든 등록된 소스의 정보 반환

        Returns:
            Dict: 소스별 정보
        """
        info = {}
        for name, source_class in self._sources.items():
            try:
                # 임시 인스턴스로 정보 수집
                temp_config = type(
                    "TempConfig", (), {"name": name, "enabled": True, "settings": {}}
                )()
                temp_instance = source_class(temp_config)

                info[name] = {
                    "class_name": source_class.__name__,
                    "source_type": temp_instance.source_type,
                    "supported_formats": temp_instance.supported_formats,
                    "description": source_class.__doc__ or "No description",
                }
            except Exception as e:
                info[name] = {"class_name": source_class.__name__, "error": str(e)}

        return info

    def auto_discover_sources(self):
        """자동으로 소스 플러그인들을 발견하고 등록"""
        if self._initialized:
            return

        try:
            # Secudium 소스 등록
            from .sources.secudium_source import SecudiumSource

            self.register(SecudiumSource)

            # 추가 소스들 등록
            from .sources.file_source import FileSource

            self.register(FileSource)

            from .sources.url_source import URLSource

            self.register(URLSource)

            # RegTech 소스 등록
            from .sources.regtech_source import RegTechSource

            self.register(RegTechSource)

            # 향후 추가될 소스들
            # from .sources.database_source import DatabaseSource
            # self.register(DatabaseSource)

            self._initialized = True
            logger.info(f"Auto-discovered {len(self._sources)} IP sources")

        except ImportError as e:
            logger.warning(f"Some sources could not be imported: {e}")
        except Exception as e:
            logger.error(f"Error during auto-discovery: {e}")


# 전역 레지스트리 인스턴스
registry = SourceRegistry()
