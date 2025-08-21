#!/usr/bin/env python3
"""
SECUDIUM 수집기 - BaseCollector 상속 및 강화된 에러 핸들링
SECUDIUM 보안 위협 정보 수집 시스템
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

from ..common.ip_utils import IPUtils
from .unified_collector import BaseCollector, CollectionConfig

logger = logging.getLogger(__name__)


class SecudiumCollector(BaseCollector):
    """
    BaseCollector를 상속받은 SECUDIUM 수집기
    ISAP (Information Sharing and Analysis Platform) API 통합
    """

    def __init__(self, config: Optional[CollectionConfig] = None):
        if config is None:
            config = CollectionConfig()
        super().__init__("SECUDIUM", config)

        # DB에서 설정 로드
        try:
            from ..database.collection_settings import CollectionSettingsDB

            self.db = CollectionSettingsDB()

            # DB에서 SECUDIUM 설정 가져오기
            source_config = self.db.get_source_config("secudium")
            credentials = self.db.get_credentials("secudium")

            if source_config:
                self.base_url = source_config["base_url"]
                self.config_data = source_config["config"]
            else:
                # 기본값 사용
                self.base_url = "https://www.secudium.kr"
                self.config_data = {}

            if credentials:
                self.username = credentials["username"]
                self.password = credentials["password"]
            else:
                # Auth manager에서 설정 로드
                from ..auth_manager import get_auth_manager
                auth_manager = get_auth_manager()
                ui_credentials = auth_manager.get_credentials("secudium")
                
                if ui_credentials:
                    self.username = ui_credentials["username"]
                    self.password = ui_credentials["password"]
                else:
                    # 환경변수 fallback
                    self.username = os.getenv("SECUDIUM_USERNAME")
                    self.password = os.getenv("SECUDIUM_PASSWORD")

        except ImportError:
            # DB 없으면 기본값/환경변수 사용
            self.base_url = "https://www.secudium.kr"
            self.username = os.getenv("SECUDIUM_USERNAME")
            self.password = os.getenv("SECUDIUM_PASSWORD")
            self.config_data = {}

        # API 엔드포인트
        self.login_url = f"{self.base_url}/isap-api/loginProcess"
        self.board_url = f"{self.base_url}/isap-api/board"
        self.download_url = f"{self.base_url}/isap-api/board/download"

        # 에러 핸들링 설정
        self.max_retry_attempts = 3
        self.request_timeout = 30
        self.session_token = None
        self.session = None

        # 상태 추적
        self.total_collected = 0
        self.error_count = 0

    @property
    def source_type(self) -> str:
        return "SECUDIUM"

    async def _collect_data(self) -> List[Any]:
        """
        메인 데이터 수집 메서드
        ISAP API를 통한 보안 위협 정보 수집
        """
        if not self.config.enabled:
            logger.info("SECUDIUM collector is disabled")
            return []

        if not self.username or not self.password:
            logger.error("SECUDIUM credentials not configured")
            raise ValueError("SECUDIUM_USERNAME and SECUDIUM_PASSWORD must be set")

        collected_ips = []

        try:
            # 세션 생성 및 로그인
            if not await self._create_session():
                logger.error("Failed to create SECUDIUM session")
                return []

            # 최신 위협 정보 조회
            board_data = await self._get_board_list()
            if not board_data:
                logger.warning("No board data available")
                return []

            # 각 게시물에서 IP 정보 추출
            for item in board_data[:10]:  # 최신 10개만 처리
                try:
                    ips = await self._extract_ips_from_item(item)
                    collected_ips.extend(ips)
                except Exception as e:
                    logger.error(f"Error processing item {item.get('id')}: {e}")
                    self.error_count += 1
                    continue

            self.total_collected = len(collected_ips)
            logger.info(f"Collected {self.total_collected} IPs from SECUDIUM")

            return collected_ips

        except Exception as e:
            logger.error(f"SECUDIUM collection failed: {e}")
            raise
        finally:
            await self._close_session()

    async def _create_session(self) -> bool:
        """세션 생성 및 로그인"""
        try:
            self.session = requests.Session()

            # 로그인 요청
            login_data = {
                "user_id": self.username,
                "user_pw": self.password,
                "is_expire": "Y",  # Force new login
            }

            response = self.session.post(
                self.login_url, json=login_data, timeout=self.request_timeout
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.session_token = result.get("token")
                    # Set authorization header
                    self.session.headers.update(
                        {"Authorization": f"Bearer {self.session_token}"}
                    )
                    logger.info("SECUDIUM session created successfully")
                    return True
                else:
                    logger.error(f"Login failed: {result.get('message')}")
            else:
                logger.error(f"Login request failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Session creation failed: {e}")

        return False

    async def _get_board_list(self) -> List[Dict]:
        """게시판 목록 조회"""
        try:
            params = {"board_type": "threat", "page": 1, "limit": 20}

            response = self.session.get(
                self.board_url, params=params, timeout=self.request_timeout
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("items", [])
            else:
                logger.error(f"Board list request failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Failed to get board list: {e}")

        return []

    async def _extract_ips_from_item(self, item: Dict) -> List[Dict]:
        """게시물에서 IP 정보 추출"""
        extracted_ips = []

        try:
            # Excel 파일 다운로드 시도
            if item.get("has_attachment"):
                file_url = f"{self.download_url}/{item['id']}"
                response = self.session.get(file_url, timeout=self.request_timeout)

                if response.status_code == 200:
                    # Excel 파일 파싱
                    df = pd.read_excel(response.content, engine="openpyxl")

                    # IP 컬럼 찾기
                    ip_columns = [col for col in df.columns if "ip" in col.lower()]

                    for col in ip_columns:
                        for ip_value in df[col].dropna():
                            ip_str = str(ip_value).strip()
                            if IPUtils.is_valid_ip(ip_str):
                                extracted_ips.append(
                                    {
                                        "ip": ip_str,
                                        "source": "SECUDIUM",
                                        "category": item.get("category", "malicious"),
                                        "detection_date": item.get(
                                            "created_at", datetime.now().isoformat()
                                        ),
                                        "threat_level": item.get(
                                            "threat_level", "high"
                                        ),
                                        "description": item.get("title", ""),
                                    }
                                )

            # HTML 콘텐츠에서 IP 추출
            if item.get("content"):
                soup = BeautifulSoup(item["content"], "html.parser")
                text_content = soup.get_text()

                # IP 패턴 매칭
                import re

                ip_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
                matches = re.findall(ip_pattern, text_content)

                for ip_str in matches:
                    if IPUtils.is_valid_ip(ip_str) and not IPUtils.is_private_ip(
                        ip_str
                    ):
                        extracted_ips.append(
                            {
                                "ip": ip_str,
                                "source": "SECUDIUM",
                                "category": "suspicious",
                                "detection_date": item.get(
                                    "created_at", datetime.now().isoformat()
                                ),
                                "threat_level": "medium",
                                "description": item.get("title", ""),
                            }
                        )

        except Exception as e:
            logger.error(f"Failed to extract IPs from item: {e}")

        return extracted_ips

    async def _close_session(self):
        """세션 정리"""
        try:
            if self.session:
                self.session.close()
                self.session = None
                self.session_token = None
                logger.info("SECUDIUM session closed")
        except Exception as e:
            logger.error(f"Error closing session: {e}")

    async def validate_credentials(self) -> bool:
        """자격증명 유효성 검증"""
        try:
            success = await self._create_session()
            if success:
                await self._close_session()
            return success
        except Exception:
            return False

    def get_status(self) -> Dict[str, Any]:
        """현재 수집기 상태 반환"""
        return {
            "source": self.source_type,
            "enabled": self.config.enabled,
            "last_collection": getattr(self, "last_collection_time", None),
            "total_collected": self.total_collected,
            "error_count": self.error_count,
            "session_active": self.session is not None,
        }

    # Test compatibility methods
    def get_config(self) -> Dict[str, Any]:
        """Get configuration for test compatibility"""
        return {
            "base_url": self.base_url,
            "username": self.username,
            "enabled": self.config.enabled,
            **self.config_data,
        }

    def set_config(self, config: Dict[str, Any]):
        """Set configuration for test compatibility"""
        self.config_data.update(config)

    def _create_session(self) -> requests.Session:
        """Create session for test compatibility"""
        if self.session is None:
            self.session = requests.Session()
        return self.session

    def _process_data(self, raw_data: bytes) -> List[Dict[str, Any]]:
        """Process data for test compatibility"""
        try:
            # Try to decode as text
            text_data = raw_data.decode("utf-8")
            # Simple parsing - split by lines and assume each line is an IP
            ips = []
            for line in text_data.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("IP"):  # Skip headers
                    ips.append(
                        {
                            "ip": line,
                            "source": "SECUDIUM",
                            "date": datetime.now().strftime("%Y-%m-%d"),
                        }
                    )
            return ips
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            return []


# 테스트용 메인 실행
if __name__ == "__main__":

    async def test_collector():
        config = CollectionConfig()
        config.enabled = True

        collector = SecudiumCollector(config)

        # 자격증명 검증
        if await collector.validate_credentials():
            print("✅ Credentials valid")

            # 데이터 수집 테스트
            result = await collector.collect()
            print(f"Collection result: {result.status}")
            print(f"Collected: {result.collected_count} IPs")
        else:
            print("❌ Invalid credentials")

    asyncio.run(test_collector())
