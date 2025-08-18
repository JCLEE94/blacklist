#!/usr/bin/env python3
"""
향상된 REGTECH 수집기 - BaseCollector 상속 및 강화된 에러 핸들링
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup

from ..common.ip_utils import IPUtils
from .helpers.data_transform import RegtechDataTransform
from .helpers.request_utils import RegtechRequestUtils
from .helpers.validation_utils import RegtechValidationUtils
from .unified_collector import BaseCollector, CollectionConfig

logger = logging.getLogger(__name__)


class RegtechCollector(BaseCollector):
    """
    BaseCollector를 상속받은 REGTECH 수집기
    강화된 에러 핸들링과 복구 메커니즘 포함
    """

    def __init__(self, config: CollectionConfig):
        super().__init__("REGTECH", config)

        # DB에서 설정 로드
        try:
            from ..database.collection_settings import CollectionSettingsDB
            self.db = CollectionSettingsDB()
            
            # DB에서 REGTECH 설정 가져오기
            source_config = self.db.get_source_config("regtech")
            credentials = self.db.get_credentials("regtech")
            
            if source_config:
                self.base_url = source_config["base_url"]
                self.config_data = source_config["config"]
            else:
                # 기본값 사용
                self.base_url = "https://regtech.fsec.or.kr"
                self.config_data = {}
            
            if credentials:
                self.username = credentials["username"]
                self.password = credentials["password"]
            else:
                # 환경변수 fallback
                self.username = os.getenv("REGTECH_USERNAME")
                self.password = os.getenv("REGTECH_PASSWORD")
                
        except ImportError:
            # DB 없으면 기본값/환경변수 사용
            self.base_url = "https://regtech.fsec.or.kr"
            self.username = os.getenv("REGTECH_USERNAME")
            self.password = os.getenv("REGTECH_PASSWORD")
            self.config_data = {}

        # 에러 핸들링 설정
        self.max_page_errors = 5  # 연속 페이지 에러 허용 횟수
        self.session_retry_limit = 3  # 세션 재시도 횟수
        self.request_timeout = 30  # 요청 타임아웃 (초)
        self.page_delay = 1  # 페이지 간 지연 (초)

        # 상태 추적
        self.current_session = None
        self.page_error_count = 0
        self.total_collected = 0

        # Helper 객체들 초기화
        self.request_utils = RegtechRequestUtils(self.base_url, self.request_timeout)
        self.data_transform = RegtechDataTransform()
        self.validation_utils = RegtechValidationUtils()
        self.validation_utils.set_ip_utils(IPUtils)

        if not self.username or not self.password:
            raise ValueError(
                "REGTECH_USERNAME and REGTECH_PASSWORD environment variables must be set"
            )

    @property
    def source_type(self) -> str:
        return "REGTECH"

    async def _collect_data(self) -> List[Any]:
        """
        메인 데이터 수집 메서드
        강화된 에러 핸들링과 재시도 로직 포함
        """
        collected_ips = []
        session_retry_count = 0

        while session_retry_count < self.session_retry_limit:
            try:
                # 세션 초기화
                session = self.request_utils.create_session()
                self.current_session = session

                # 로그인 시도
                if not await self._robust_login(session):
                    raise Exception("로그인 실패 후 재시도 한계 도달")

                # 데이터 수집
                start_date, end_date = self.data_transform.get_date_range(self.config)
                collected_ips = await self._robust_collect_ips(
                    session, start_date, end_date
                )

                # 성공적으로 수집 완료
                self.logger.info(f"REGTECH 수집 완료: {len(collected_ips)}개 IP")
                break

            except requests.exceptions.ConnectionError as e:
                session_retry_count += 1
                self.logger.warning(
                    f"연결 오류 (재시도 {session_retry_count}/{self.session_retry_limit}): {e}"
                )
                if session_retry_count < self.session_retry_limit:
                    await asyncio.sleep(5 * session_retry_count)  # 지수적 백오프

            except requests.exceptions.Timeout as e:
                session_retry_count += 1
                self.logger.warning(
                    f"타임아웃 오류 (재시도 {session_retry_count}/{self.session_retry_limit}): {e}"
                )
                if session_retry_count < self.session_retry_limit:
                    await asyncio.sleep(3 * session_retry_count)

            except Exception as e:
                self.logger.error(f"예상치 못한 오류: {e}")
                session_retry_count += 1
                if session_retry_count < self.session_retry_limit:
                    await asyncio.sleep(2 * session_retry_count)

            finally:
                if hasattr(self, "current_session") and self.current_session:
                    self.current_session.close()
                    self.current_session = None

        if session_retry_count >= self.session_retry_limit:
            raise Exception(f"최대 재시도 횟수 ({self.session_retry_limit}) 초과")

        return collected_ips

    async def _robust_login(self, session: requests.Session) -> bool:
        """강화된 로그인 로직"""
        login_attempts = 0
        max_login_attempts = 3

        while login_attempts < max_login_attempts:
            try:
                self.logger.info(
                    f"로그인 시도 {login_attempts + 1}/{max_login_attempts}"
                )

                # 로그인 페이지 접근
                login_page_url = f"{self.base_url}/login/loginForm"
                response = session.get(login_page_url)

                if response.status_code != 200:
                    raise Exception(f"로그인 페이지 접근 실패: {response.status_code}")

                # CSRF 토큰이나 숨겨진 필드 추출 시도
                soup = BeautifulSoup(response.text, "html.parser")
                hidden_inputs = soup.find_all("input", type="hidden")
                login_data = {
                    "username": self.username,
                    "password": self.password,
                    "login_error": "",
                    "txId": "",
                    "token": "",
                    "memberId": "",
                    "smsTimeExcess": "N",
                }

                # 숨겨진 필드들 추가
                for hidden_input in hidden_inputs:
                    name = hidden_input.get("name")
                    value = hidden_input.get("value", "")
                    if name:
                        login_data[name] = value

                # 로그인 요청
                login_url = f"{self.base_url}/login/addLogin"
                login_response = session.post(
                    login_url,
                    data=login_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    allow_redirects=True,
                )

                # 로그인 성공 확인
                if self.validation_utils.verify_login_success(login_response):
                    self.logger.info("로그인 성공")
                    return True
                else:
                    login_attempts += 1
                    if login_attempts < max_login_attempts:
                        self.logger.warning(f"로그인 실패, {2} 초 후 재시도")
                        await asyncio.sleep(2)

            except Exception as e:
                login_attempts += 1
                self.logger.error(f"로그인 중 오류: {e}")
                if login_attempts < max_login_attempts:
                    await asyncio.sleep(3)

        self.logger.error("로그인 최대 시도 횟수 초과")
        return False

    async def _robust_collect_ips(
        self, session: requests.Session, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """강화된 IP 수집 로직"""
        all_ips = []
        page = 0
        consecutive_errors = 0
        max_pages = 100  # 안전장치

        self.logger.info(f"IP 수집 시작: {start_date} ~ {end_date}")

        while page < max_pages and consecutive_errors < self.max_page_errors:
            try:
                # 취소 요청 확인
                if self.validation_utils.should_cancel(
                    getattr(self, "_cancel_event", None)
                ):
                    self.logger.info("사용자 취소 요청으로 수집 중단")
                    break

                # 페이지 지연
                if page > 0:
                    await asyncio.sleep(self.page_delay)

                # 페이지 데이터 수집
                page_ips = await self.request_utils.collect_single_page(
                    session, page, start_date, end_date
                )

                # IP 유효성 검사 적용
                valid_page_ips = []
                for ip_data in page_ips:
                    if self.validation_utils.is_valid_ip(ip_data.get("ip", "")):
                        valid_page_ips.append(ip_data)
                page_ips = valid_page_ips

                if not page_ips:
                    self.logger.info(
                        f"페이지 {page + 1}에서 더 이상 데이터 없음, 수집 종료"
                    )
                    break

                all_ips.extend(page_ips)
                consecutive_errors = 0  # 성공 시 에러 카운트 리셋

                self.logger.info(
                    f"페이지 {page + 1}: {len(page_ips)}개 수집 (총 {len(all_ips)}개)"
                )
                page += 1

            except requests.exceptions.RequestException as e:
                consecutive_errors += 1
                self.logger.warning(
                    f"페이지 {page + 1} 수집 실패 (연속 에러: {consecutive_errors}/{self.max_page_errors}): {e}"
                )

                if consecutive_errors < self.max_page_errors:
                    await asyncio.sleep(2 * consecutive_errors)  # 점진적 지연

            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"페이지 {page + 1} 처리 중 예상치 못한 오류: {e}")

                if consecutive_errors < self.max_page_errors:
                    await asyncio.sleep(1)

        if consecutive_errors >= self.max_page_errors:
            self.logger.error(f"연속 페이지 에러 한계 도달 ({self.max_page_errors})")

        # 중복 제거
        unique_ips = self.data_transform.remove_duplicates(all_ips)
        self.logger.info(f"중복 제거 후 최종 수집: {len(unique_ips)}개 IP")

        return unique_ips

    def _transform_data(self, raw_data: dict) -> dict:
        """데이터 변환 - 헬퍼 모듈 위임"""
        return self.data_transform.transform_data(raw_data)

    def collect_from_web(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        웹 수집 인터페이스 메서드 (동기 래퍼)
        collection_service.py에서 호출하는 인터페이스
        """
        import asyncio
        
        try:
            # 날짜 범위 설정
            if not start_date or not end_date:
                from datetime import datetime, timedelta
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            # 비동기 수집 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                collected_data = loop.run_until_complete(self._collect_data())
                return {
                    "success": True,
                    "data": collected_data,
                    "count": len(collected_data),
                    "message": f"REGTECH에서 {len(collected_data)}개 IP 수집 완료"
                }
            finally:
                loop.close()
                
        except Exception as e:
            self.logger.error(f"REGTECH 웹 수집 실패: {e}")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "error": str(e),
                "message": f"REGTECH 수집 중 오류: {e}"
            }
