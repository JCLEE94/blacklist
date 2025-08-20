#!/usr/bin/env python3
"""
REGTECH 수집기 - 모듈화된 구조
BaseCollector 상속 및 강화된 에러 핸들링
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

import requests

from ..common.ip_utils import IPUtils
from .helpers.data_transform import RegtechDataTransform
from .helpers.request_utils import RegtechRequestUtils
from .helpers.validation_utils import RegtechValidationUtils
from .regtech_auth import RegtechAuth
from .regtech_browser import RegtechBrowserAutomation
from .regtech_data_processor import RegtechDataProcessor
from .unified_collector import BaseCollector, CollectionConfig

logger = logging.getLogger(__name__)


class RegtechCollector(BaseCollector):
    """
    BaseCollector를 상속받은 REGTECH 수집기
    모듈화된 구조로 강화된 에러 핸들링과 복구 메커니즘 포함
    """

    def __init__(self, config: CollectionConfig):
        super().__init__("REGTECH", config)

        # 기본 설정
        self.base_url = "https://regtech.fsec.or.kr"
        self.config_data = {}

        # 환경 변수에서 설정 로드
        self.username = os.getenv("REGTECH_USERNAME")
        self.password = os.getenv("REGTECH_PASSWORD")

        # DB에서 설정 로드 (선택적)
        self._load_db_config()

        # 에러 핸들링 설정
        self.max_page_errors = 5
        self.session_retry_limit = 3
        self.request_timeout = 30
        self.page_delay = 1

        # 상태 추적
        self.current_session = None
        self.page_error_count = 0
        self.total_collected = 0

        # 모듈화된 컴포넌트들 초기화
        self.auth = RegtechAuth(self.base_url, self.username, self.password)
        self.browser_automation = RegtechBrowserAutomation(
            self.base_url, self.username, self.password
        )
        self.data_processor = RegtechDataProcessor()

        # Helper 객체들 초기화
        self.request_utils = RegtechRequestUtils(self.base_url, self.request_timeout)
        self.data_transform = RegtechDataTransform()
        self.validation_utils = RegtechValidationUtils()
        self.validation_utils.set_ip_utils(IPUtils)

        # 데이터 프로세서에 검증 유틸리티 설정
        self.data_processor.validation_utils = self.validation_utils

        logger.info("REGTECH collector initialized with modular components")

    def _load_db_config(self):
        """DB에서 설정 로드 (선택적)"""
        try:
            from ..database.collection_settings import CollectionSettingsDB

            self.db = CollectionSettingsDB()

            # DB에서 REGTECH 설정 가져오기
            source_config = self.db.get_source_config("regtech")
            credentials = self.db.get_credentials("regtech")

            if source_config:
                self.base_url = source_config.get("base_url", self.base_url)
                self.config_data = source_config.get("config", {})

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

    def set_cookie_string(self, cookie_string: str):
        """외부에서 쿠키 문자열 설정"""
        self.auth.set_cookie_string(cookie_string)
        logger.info("Cookie string updated through auth module")

    @property
    def source_type(self) -> str:
        return "REGTECH"

    async def _collect_data(self) -> List[Any]:
        """
        메인 데이터 수집 메서드 - 자동 쿠키 관리 포함
        """
        # 1. 쿠키가 없으면 자동 추출 시도
        if not self.auth.cookie_auth_mode:
            logger.info("🔄 No cookies available - attempting automatic extraction...")
            cookie_string = self.browser_automation.auto_extract_cookies()
            if cookie_string:
                self.auth.set_cookie_string(cookie_string)
                logger.info("✅ Automatic cookie extraction successful")
            else:
                logger.warning(
                    "❌ Automatic cookie extraction failed - falling back to login mode"
                )
                return await self._collect_with_login()

        # 2. 쿠키 기반 수집 시도
        if self.auth.cookie_auth_mode:
            collected_data = await self._collect_with_cookies()

            # 3. 수집 결과가 없거나 쿠키 만료 의심 시 재추출 시도
            if not collected_data:
                logger.warning(
                    "🔄 No data collected - cookies might be expired, attempting re-extraction..."
                )
                cookie_string = self.browser_automation.auto_extract_cookies()
                if cookie_string:
                    self.auth.set_cookie_string(cookie_string)
                    logger.info(
                        "✅ Cookie re-extraction successful - retrying collection..."
                    )
                    collected_data = await self._collect_with_cookies()
                else:
                    logger.error(
                        "❌ Cookie re-extraction failed - falling back to login mode"
                    )
                    return await self._collect_with_login()

            return collected_data
        else:
            return await self._collect_with_login()

    async def _collect_with_cookies(self) -> List[Any]:
        """쿠키 기반 데이터 수집"""
        collected_ips = []

        try:
            # 인증된 세션 생성
            session = self.auth.create_authenticated_session()

            logger.info("Starting cookie-based data collection")

            # 실제 REGTECH 사이트 구조에 맞는 블랙리스트 페이지들
            blacklist_urls = [
                "/board/11/boardList",  # 공지사항 게시판 (위협 정보 포함 가능)
                "/fcti/securityAdvisory/advisoryList",  # 보안 권고 목록
                "/fcti/securityAdvisory/blacklistDownload",  # 블랙리스트 다운로드
                "/fcti/threat/threatList",  # 위협 정보 목록
                "/fcti/threat/ipBlacklist",  # IP 블랙리스트
                "/fcti/report/threatReport",  # 위협 리포트
                "/board/boardList?menuCode=FCTI",  # FCTI 관련 게시판
                "/threat/intelligence/ipList",  # 위협 인텔리전스 IP 목록
            ]

            for path in blacklist_urls:
                try:
                    url = f"{self.base_url}{path}"
                    logger.info(f"Trying URL: {url}")

                    response = session.get(
                        url, verify=False, timeout=self.request_timeout
                    )

                    # 쿠키 만료 확인
                    if self.auth._is_cookie_expired(response):
                        logger.warning(
                            f"Cookies expired at {url} - will trigger re-extraction"
                        )
                        return []  # 빈 결과 반환하여 상위에서 재추출 트리거

                    if response.status_code == 200:
                        content_type = response.headers.get("content-type", "").lower()

                        # 데이터 프로세서로 위임
                        if "excel" in content_type or "spreadsheet" in content_type:
                            ips = await self.data_processor.process_excel_response(
                                response
                            )
                            if ips:
                                collected_ips.extend(ips)
                                logger.info(
                                    f"Collected {len(ips)} IPs from Excel download"
                                )
                                break

                        elif "text/html" in content_type:
                            ips = await self.data_processor.process_html_response(
                                response
                            )
                            if ips:
                                collected_ips.extend(ips)
                                logger.info(f"Collected {len(ips)} IPs from HTML page")
                                if len(ips) > 10:  # 충분한 데이터가 있으면 중단
                                    break

                        elif "application/json" in content_type:
                            ips = await self.data_processor.process_json_response(
                                response
                            )
                            if ips:
                                collected_ips.extend(ips)
                                logger.info(f"Collected {len(ips)} IPs from JSON API")
                                break

                    elif (
                        response.status_code == 302
                        and "login" in response.headers.get("Location", "")
                    ):
                        logger.warning("Redirected to login - cookies may be expired")
                        break

                except Exception as e:
                    logger.error(f"Error accessing {path}: {e}")
                    continue

            # 수집된 데이터 검증 및 변환
            if collected_ips:
                validated_ips = self.data_processor.validate_and_transform_data(
                    collected_ips
                )
                logger.info(
                    f"Validated {len(validated_ips)} out of {len(collected_ips)} collected IPs"
                )
                return validated_ips
            else:
                logger.warning("No IPs collected - check cookies or access permissions")
                return []

        except Exception as e:
            logger.error(f"Cookie-based collection failed: {e}")
            return []

    async def _collect_with_login(self) -> List[Any]:
        """기존 로그인 기반 데이터 수집"""
        collected_ips = []
        session_retry_count = 0

        while session_retry_count < self.session_retry_limit:
            try:
                # 세션 초기화
                session = self.request_utils.create_session()
                self.current_session = session

                # 로그인 시도
                if not self._robust_login(session):
                    raise Exception("로그인 실패 후 재시도 한계 도달")

                # 데이터 수집
                start_date, end_date = self.data_transform.get_date_range(self.config)
                collected_ips = await self._robust_collect_ips(
                    session, start_date, end_date
                )

                # 성공적으로 수집 완료
                logger.info(f"REGTECH 수집 완료: {len(collected_ips)}개 IP")
                break

            except requests.exceptions.ConnectionError as e:
                session_retry_count += 1
                logger.warning(
                    f"연결 오류 (재시도 {session_retry_count}/{self.session_retry_limit}): {e}"
                )
                if session_retry_count < self.session_retry_limit:
                    await asyncio.sleep(5 * session_retry_count)  # 지수적 백오프

            except requests.exceptions.Timeout as e:
                session_retry_count += 1
                logger.warning(
                    f"타임아웃 오류 (재시도 {session_retry_count}/{self.session_retry_limit}): {e}"
                )
                if session_retry_count < self.session_retry_limit:
                    await asyncio.sleep(3 * session_retry_count)

            except Exception as e:
                logger.error(f"예상치 못한 오류: {e}")
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

    def _robust_login(self, session: requests.Session) -> bool:
        """강화된 로그인 로직 - 인증 모듈로 위임"""
        return self.auth.robust_login(session)

    async def _robust_collect_ips(
        self, session: requests.Session, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """강화된 IP 수집 로직"""
        all_ips = []
        page = 0
        consecutive_errors = 0
        max_pages = 100  # 안전장치

        logger.info(f"IP 수집 시작: {start_date} ~ {end_date}")

        while page < max_pages and consecutive_errors < self.max_page_errors:
            try:
                # 취소 요청 확인
                if self.validation_utils.should_cancel(
                    getattr(self, "_cancel_event", None)
                ):
                    logger.info("사용자 취소 요청으로 수집 중단")
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
                    logger.info(f"페이지 {page + 1}에서 더 이상 데이터 없음, 수집 종료")
                    break

                all_ips.extend(page_ips)
                consecutive_errors = 0  # 성공 시 에러 카운트 리셋

                logger.info(
                    f"페이지 {page + 1}: {len(page_ips)}개 수집 (총 {len(all_ips)}개)"
                )
                page += 1

            except requests.exceptions.RequestException as e:
                consecutive_errors += 1
                logger.warning(
                    f"페이지 {page + 1} 수집 실패 (연속 에러: {consecutive_errors}/{self.max_page_errors}): {e}"
                )

                if consecutive_errors < self.max_page_errors:
                    await asyncio.sleep(2 * consecutive_errors)  # 점진적 지연

            except Exception as e:
                consecutive_errors += 1
                logger.error(f"페이지 {page + 1} 처리 중 예상치 못한 오류: {e}")

                if consecutive_errors < self.max_page_errors:
                    await asyncio.sleep(1)

        if consecutive_errors >= self.max_page_errors:
            logger.error(f"연속 페이지 에러 한계 도달 ({self.max_page_errors})")

        # 중복 제거
        unique_ips = self.data_processor.remove_duplicates(all_ips)
        logger.info(f"중복 제거 후 최종 수집: {len(unique_ips)}개 IP")

        return unique_ips

    def _transform_data(self, raw_data: dict) -> dict:
        """데이터 변환 - 헬퍼 모듈 위임"""
        return self.data_transform.transform_data(raw_data)

    def collect_from_web(
        self, start_date: str = None, end_date: str = None
    ) -> Dict[str, Any]:
        """
        웹 수집 인터페이스 메서드 (동기 래퍼)
        collection_service.py에서 호출하는 인터페이스
        """
        import asyncio

        try:
            # 날짜 범위 설정
            if not start_date or not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

            # 비동기 수집 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                collected_data = loop.run_until_complete(self._collect_data())
                return {
                    "success": True,
                    "data": collected_data,
                    "count": len(collected_data),
                    "message": f"REGTECH에서 {len(collected_data)}개 IP 수집 완료",
                }
            finally:
                loop.close()

        except Exception as e:
            logger.error(f"REGTECH 웹 수집 실패: {e}")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "error": str(e),
                "message": f"REGTECH 수집 중 오류: {e}",
            }


if __name__ == "__main__":
    # 모듈화된 REGTECH 컴렉터 테스트
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: 기본 컴렉터 생성
    total_tests += 1
    try:
        from .unified_collector import CollectionConfig

        config = CollectionConfig()
        collector = RegtechCollector(config)
        if not hasattr(collector, "auth") or not hasattr(collector, "data_processor"):
            all_validation_failures.append("필수 컴포넌트 누락")
    except Exception as e:
        all_validation_failures.append(f"컴렉터 생성 실패: {e}")

    # Test 2: 메서드 존재 확인
    total_tests += 1
    try:
        from .unified_collector import CollectionConfig

        config = CollectionConfig()
        collector = RegtechCollector(config)
        required_methods = [
            "_collect_data",
            "_collect_with_cookies",
            "collect_from_web",
        ]
        for method_name in required_methods:
            if not hasattr(collector, method_name):
                all_validation_failures.append(f"필수 메서드 누락: {method_name}")
    except Exception as e:
        all_validation_failures.append(f"메서드 확인 테스트 실패: {e}")

    # Test 3: 쿠키 설정 테스트
    total_tests += 1
    try:
        from .unified_collector import CollectionConfig

        config = CollectionConfig()
        collector = RegtechCollector(config)
        collector.set_cookie_string("test_cookie=test_value")
        # 에러 없이 실행되면 성공
    except Exception as e:
        all_validation_failures.append(f"쿠키 설정 테스트 실패: {e}")

    # 최종 검증 결과
    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("Modularized RegtechCollector is validated and ready for use")
        sys.exit(0)
