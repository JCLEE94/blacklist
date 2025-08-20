#!/usr/bin/env python3
"""
REGTECH 요청 유틸리티 모듈
세션 관리, 요청 처리 등의 기능을 제공
"""

import asyncio
import logging
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class RegtechRequestUtils:
    """
    REGTECH 요청 처리 전담 클래스
    """

    def __init__(self, base_url: str, request_timeout: int = 30):
        self.base_url = base_url
        self.request_timeout = request_timeout

    def create_session(self) -> requests.Session:
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

    async def collect_single_page(
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

            # 보안 권고 목록 페이지로 요청 전송
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
            return self.extract_ips_from_soup(soup, page)

        except asyncio.TimeoutError:
            raise requests.exceptions.Timeout(f"페이지 {page + 1} 요청 타임아웃")
        except Exception as e:
            raise Exception(f"페이지 {page + 1} 처리 실패: {e}")

    def extract_ips_from_soup(
        self, soup: BeautifulSoup, page: int
    ) -> List[Dict[str, Any]]:
        """
        BeautifulSoup 객체에서 IP 데이터 추출"""
        from datetime import datetime

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

                                # IP 유효성 검사는 호출자에서 처리
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
                            logger.warning(
                                f"행 처리 중 오류 (페이지 {page + 1}, 행 {row_idx + 1}): {e}"
                            )
                            continue

                    break  # 요주의 IP 테이블을 찾았으므로 중단

            return page_ips

        except Exception as e:
            logger.error(f"IP 추출 중 오류 (페이지 {page + 1}): {e}")
            return []
