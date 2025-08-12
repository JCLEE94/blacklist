"""
SECUDIUM 수집기 더미 구현
실제 SECUDIUM 계정 문제로 비활성화 상태
"""

import logging
import os
from typing import Any, Dict, List

import requests

from .collectors.unified_collector import BaseCollector, CollectionConfig

logger = logging.getLogger(__name__)


class SecudiumCollector(BaseCollector):
    """SECUDIUM 수집기 - BaseCollector 상속 (현재 계정 이슈로 비활성화)"""

    def __init__(self, config: CollectionConfig):
        super().__init__("SECUDIUM", config)

        # SECUDIUM 특화 설정
        self.base_url = "https://secudium.com"  # 실제 URL로 수정 필요
        self.username = os.getenv("SECUDIUM_USERNAME")
        self.password = os.getenv("SECUDIUM_PASSWORD")

        # 현재 계정 이슈로 비활성화
        self.config.enabled = False

        self.logger.warning(
            "SECUDIUM Collector initialized but disabled due to account issues"
        )

    @property
    def source_type(self) -> str:
        return "SECUDIUM"

    async def _collect_data(self) -> List[Any]:
        """
        SECUDIUM 데이터 수집 (현재 비활성화)
        실제 계정 문제 해결 시 구현 필요
        """
        if not self.config.enabled:
            self.logger.warning("SECUDIUM collection is disabled due to account issues")
            return []

        # 실제 구현 시 아래 로직 활성화
        """
        try:
            # 로그인 및 데이터 수집 로직
            session = self._create_session()

            # 로그인
            if not await self._login(session):
                raise Exception("SECUDIUM 로그인 실패")

            # 데이터 수집
            collected_data = await self._collect_bulletin_data(session)

            self.logger.info("SECUDIUM 수집 완료: {len(collected_data)}개")
            return collected_data

        except Exception as e:
            self.logger.error("SECUDIUM 수집 실패: {e}")
            raise
        """

        return []

    def _create_session(self) -> requests.Session:
        """SECUDIUM용 세션 생성"""
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            }
        )
        return session

    async def _login(self, session: requests.Session) -> bool:
        """SECUDIUM 로그인 (구현 대기)"""
        # 실제 구현 시 활성화
        return False

    async def _collect_bulletin_data(
        self, session: requests.Session
    ) -> List[Dict[str, Any]]:
        """게시판 데이터 수집 (구현 대기)"""
        # 실제 구현 시 활성화
        return []
