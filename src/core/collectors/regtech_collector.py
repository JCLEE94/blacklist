#!/usr/bin/env python3
"""
향상된 REGTECH 수집기 - BaseCollector 상속 및 강화된 에러 핸들링
"""

import asyncio
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup

from .unified_collector import BaseCollector, CollectionConfig
from ..common.ip_utils import IPUtils

logger = logging.getLogger(__name__)


class RegtechCollector(BaseCollector):
    """
    BaseCollector를 상속받은 REGTECH 수집기
    강화된 에러 핸들링과 복구 메커니즘 포함
    """

    def __init__(self, config: CollectionConfig):
        super().__init__("REGTECH", config)

        # REGTECH 특화 설정
        self.base_url = "https://regtech.fsec.or.kr"
        self.username = os.getenv("REGTECH_USERNAME")
        self.password = os.getenv("REGTECH_PASSWORD")

        # 에러 핸들링 설정
        self.max_page_errors = 5  # 연속 페이지 에러 허용 횟수
        self.session_retry_limit = 3  # 세션 재시도 횟수
        self.request_timeout = 30  # 요청 타임아웃 (초)
        self.page_delay = 1  # 페이지 간 지연 (초)

        # 상태 추적
        self.current_session = None
        self.page_error_count = 0
        self.total_collected = 0

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
                session = self._create_session()
                self.current_session = session

                # 로그인 시도
                if not await self._robust_login(session):
                    raise Exception("로그인 실패 후 재시도 한계 도달")

                # 데이터 수집
                start_date, end_date = self._get_date_range()
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

    def _create_session(self) -> requests.Session:
        """강화된 세션 생성"""
        session = requests.Session()

        # 강화된 헤더 설정
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

        # 타임아웃 설정
        session.timeout = self.request_timeout

        # SSL 검증 설정
        session.verify = True

        return session

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
                if self._verify_login_success(login_response):
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

    def _verify_login_success(self, response: requests.Response) -> bool:
        """로그인 성공 여부 확인"""
        try:
            # 상태 코드 확인
            if response.status_code != 200:
                return False

            # URL 확인 (에러 페이지로 리다이렉트되지 않았는지)
            if "error" in response.url.lower() or "login" in response.url.lower():
                return False

            # 응답 내용 확인
            response_text = response.text.lower()

            # 로그인 실패 지표
            failure_indicators = ["login", "error", "incorrect", "invalid", "failed"]
            if any(
                indicator in response_text[:1000] for indicator in failure_indicators
            ):
                return False

            # 로그인 성공 지표
            success_indicators = ["dashboard", "main", "home", "welcome"]
            if any(
                indicator in response_text[:1000] for indicator in success_indicators
            ):
                return True

            # 기본적으로 성공으로 간주 (보수적 접근)
            return True

        except Exception as e:
            self.logger.error(f"로그인 검증 중 오류: {e}")
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
                if self._should_cancel():
                    self.logger.info("사용자 취소 요청으로 수집 중단")
                    break

                # 페이지 지연
                if page > 0:
                    await asyncio.sleep(self.page_delay)

                # 페이지 데이터 수집
                page_ips = await self._collect_single_page(
                    session, page, start_date, end_date
                )

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
        unique_ips = self._remove_duplicates(all_ips)
        self.logger.info(f"중복 제거 후 최종 수집: {len(unique_ips)}개 IP")

        return unique_ips

    async def _collect_single_page(
        self, session: requests.Session, page: int, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """단일 페이지 데이터 수집"""
        try:
            # 요청 데이터 준비
            data = {
                "page": str(page),
                "tabSort": "blacklist",
                "startDate": start_date,
                "endDate": end_date,
                "findCondition": "all",
                "findKeyword": "",
                "size": "100",  # 페이지당 적절한 크기
                "rows": "100",
                "excelDownload": "",
                "cveId": "",
                "ipId": "",
                "estId": "",
            }

            # 요청 전송
            url = f"{self.base_url}/fcti/securityAdvisory/advisoryList"
            response = session.post(
                url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self.request_timeout,
            )

            if response.status_code != 200:
                raise requests.exceptions.RequestException(
                    f"HTTP {response.status_code}"
                )

            # HTML 파싱
            soup = BeautifulSoup(response.text, "html.parser")

            # 로그인 페이지로 리다이렉트 확인
            if "login" in response.text.lower()[:500]:
                raise Exception("세션 만료 - 로그인 페이지로 리다이렉트됨")

            # IP 데이터 추출
            return self._extract_ips_from_soup(soup, page)

        except asyncio.TimeoutError:
            raise requests.exceptions.Timeout(f"페이지 {page + 1} 요청 타임아웃")
        except Exception as e:
            raise Exception(f"페이지 {page + 1} 처리 실패: {e}")

    def _extract_ips_from_soup(
        self, soup: BeautifulSoup, page: int
    ) -> List[Dict[str, Any]]:
        """BeautifulSoup 객체에서 IP 데이터 추출"""
        page_ips = []

        try:
            # 테이블 찾기
            tables = soup.find_all("table")

            for table in tables:
                caption = table.find("caption")
                if caption and "요주의 IP" in caption.text:
                    tbody = table.find("tbody")
                    if not tbody:
                        continue

                    rows = tbody.find_all("tr")

                    for row_idx, row in enumerate(rows):
                        try:
                            cells = row.find_all("td")
                            if len(cells) >= 4:
                                ip = cells[0].text.strip()
                                country = cells[1].text.strip()
                                reason = cells[2].text.strip()
                                date = cells[3].text.strip()

                                # IP 유효성 검사
                                if self._is_valid_ip(ip):
                                    ip_data = {
                                        "ip": ip,
                                        "country": country,
                                        "reason": reason,
                                        "date": date,
                                        "source": "REGTECH",
                                        "page": page + 1,
                                        "row": row_idx + 1,
                                        "collected_at": datetime.now().isoformat(),
                                    }
                                    page_ips.append(ip_data)

                        except Exception as e:
                            self.logger.warning(
                                "행 처리 중 오류 (페이지 {page + 1}, 행 {row_idx + 1}): {e}"
                            )
                            continue

                    break  # 요주의 IP 테이블을 찾았으므로 중단

            return page_ips

        except Exception as e:
            self.logger.error(f"IP 추출 중 오류 (페이지 {page + 1}): {e}")
            return []

    def _transform_data(self, raw_data: dict) -> dict:
        """
        원시 데이터를 표준 형식으로 변환 (탐지일 기준 3개월 만료)
        
        Args:
            raw_data: 원시 수집 데이터
            
        Returns:
            변환된 데이터 딕셔너리 (expires_at 포함)
        """
        try:
            # 탐지일 파싱
            detection_date_str = raw_data.get('date', datetime.now().strftime('%Y-%m-%d'))
            
            # 다양한 날짜 형식 처리
            detection_date = None
            try:
                if len(detection_date_str.replace('-', '').replace('.', '')) == 8:
                    # YYYYMMDD, YYYY-MM-DD, YYYY.MM.DD 형식
                    clean_date = detection_date_str.replace('-', '').replace('.', '')
                    detection_date = datetime.strptime(clean_date, '%Y%m%d')
                else:
                    # 기본적으로 ISO 형식 시도
                    detection_date = datetime.fromisoformat(detection_date_str)
            except:
                # 파싱 실패 시 현재 날짜 사용
                detection_date = datetime.now()
                self.logger.warning(f"날짜 파싱 실패, 현재 날짜 사용: {detection_date_str}")
            
            # 수집일 기준 3개월 후 만료 설정 (탐지일 아님)
            collection_date = datetime.now()  # 실제 수집한 날짜
            expires_at = collection_date + timedelta(days=90)  # 수집일 + 3개월 = 90일
            
            # 기본 변환
            transformed = {
                'ip': raw_data.get('ip', ''),
                'country': raw_data.get('country', 'Unknown'),
                'reason': raw_data.get('reason', 'Unknown threat'),
                'source': 'REGTECH',
                'detection_date': detection_date.strftime('%Y-%m-%d'),  # 실제 탐지일 유지
                'collection_date': collection_date.strftime('%Y-%m-%d'),  # 수집일 추가
                'expires_at': expires_at.isoformat(),  # 수집일 기준 만료
                'threat_level': raw_data.get('threat_level', 'medium'),
                'category': raw_data.get('category', 'malware'),
                'confidence': raw_data.get('confidence', 0.8)
            }
            
            # 추가 필드 처리
            if 'additional_info' in raw_data:
                transformed['additional_info'] = raw_data['additional_info']
                
            # IP 유효성 검증
            if not self._is_valid_ip(transformed['ip']):
                self.logger.warning(f"Invalid IP in transformed data: {transformed['ip']}")
                
            return transformed
            
        except Exception as e:
            self.logger.error(f"Data transformation error: {e}")
            # 최소한의 데이터 반환 (수집일 기준 3개월 만료)
            fallback_collection = datetime.now()
            fallback_expires = fallback_collection + timedelta(days=90)
            return {
                'ip': raw_data.get('ip', '0.0.0.0'),
                'source': 'REGTECH',
                'country': 'Unknown',
                'reason': 'Transform error',
                'detection_date': fallback_collection.strftime('%Y-%m-%d'),  # 에러 시 수집일로 설정
                'collection_date': fallback_collection.strftime('%Y-%m-%d'),  # 수집일
                'expires_at': fallback_expires.isoformat()  # 수집일 기준 만료
            }

    def _is_valid_ip(self, ip: str) -> bool:
        """IP 유효성 검사 (통합 유틸리티 사용)"""
        return IPUtils.validate_ip(ip) and not IPUtils.is_private_ip(ip)

    def _get_date_range(self) -> tuple[str, str]:
        """수집 날짜 범위 계산"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)  # 기본 30일

        # 설정에서 날짜 범위 override 가능
        if hasattr(self.config, "settings"):
            days = self.config.settings.get("collection_days", 30)
            start_date = end_date - timedelta(days=days)

        return start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")

    def _remove_duplicates(self, ips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중복 IP 제거 (최신 데이터 우선)"""
        seen = {}
        unique_ips = []

        # 역순으로 순회하여 최신 데이터를 우선 보존
        for ip_data in reversed(ips):
            ip_addr = ip_data.get("ip")
            if ip_addr and ip_addr not in seen:
                seen[ip_addr] = True
                unique_ips.append(ip_data)

        # 원래 순서로 복원
        unique_ips.reverse()
        return unique_ips
