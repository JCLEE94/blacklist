#!/usr/bin/env python3
"""
REGTECH 인증 모듈
regtech_collector.py에서 분리된 인증 관련 기능
"""

import logging
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class RegtechAuth:
    """
    REGTECH 인증 처리 전담 클래스
    """

    def __init__(self, base_url: str, username: str, password: str, timeout: int = 30):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session = None
        self.cookie_auth_mode = False  # Track if using cookie-based auth
        self.cookie_string = None  # Store cookie string for authentication

    def set_cookie_string(self, cookie_string: str) -> None:
        """Set cookie string for authentication"""
        if cookie_string:
            self.cookie_string = cookie_string
            self.cookie_auth_mode = True
            logger.info("✅ Cookie string set for authentication")
        else:
            self.cookie_auth_mode = False
            logger.warning("⚠️ Empty cookie string provided, cookie auth disabled")

    def create_session(self) -> requests.Session:
        """새로운 세션 생성"""
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/91.0.4472.124 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;"
                    "q=0.9,image/webp,*/*;q=0.8"
                ),
                "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        return session

    def login(self) -> Optional[requests.Session]:
        """
        REGTECH 로그인 수행

        Returns:
            requests.Session: 로그인된 세션 또는 None
        """
        try:
            # 새 세션 생성
            self.session = self.create_session()

            # 로그인 페이지 접근
            login_url = f"{self.base_url}/login/loginForm"
            logger.info(f"Accessing login page: {login_url}")

            response = self.session.get(login_url, timeout=self.timeout)
            response.raise_for_status()

            # 로그인 폼 처리
            soup = BeautifulSoup(response.text, "html.parser")
            login_form = soup.find("form")

            if not login_form:
                logger.error("Login form not found")
                return None

            # 로그인 데이터 준비
            login_data = {"username": self.username, "password": self.password}

            # CSRF 토큰 처리 (있는 경우)
            csrf_input = soup.find("input", {"name": re.compile(r"csrf|token", re.I)})
            if csrf_input and csrf_input.get("value"):
                login_data[csrf_input["name"]] = csrf_input["value"]

            # 로그인 요청 전송
            login_submit_url = login_form.get("action", login_url)
            if not login_submit_url.startswith("http"):
                login_submit_url = f"{self.base_url}{login_submit_url}"

            logger.info(f"Submitting login to: {login_submit_url}")

            response = self.session.post(
                login_submit_url,
                data=login_data,
                timeout=self.timeout,
                allow_redirects=True,
            )
            response.raise_for_status()

            # 로그인 성공 확인
            if self._verify_login_success(response):
                logger.info("REGTECH login successful")
                return self.session
            else:
                logger.error("REGTECH login failed")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during REGTECH login: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during REGTECH login: {e}")
            return None

    def _verify_login_success(self, response: requests.Response) -> bool:
        """로그인 성공 여부 확인"""
        # 로그인 실패 지표들 확인
        failure_indicators = [
            "로그인 실패",
            "login failed",
            "잘못된 사용자",
            "invalid credentials",
            "비밀번호가 올바르지 않습니다",
        ]

        response_text = response.text.lower()

        for indicator in failure_indicators:
            if indicator.lower() in response_text:
                return False

        # 로그인 성공 지표들 확인
        success_indicators = [
            "대시보드",
            "dashboard",
            "메인 페이지",
            "로그아웃",
            "logout",
        ]

        for indicator in success_indicators:
            if indicator.lower() in response_text:
                return True

        # URL 기반 확인 (로그인 후 리다이렉트)
        if "/login" not in response.url and response.status_code == 200:
            return True

        return False

    def robust_login(self, session: requests.Session) -> bool:
        """
        강화된 로그인 로직 - 새로운 2단계 프로세스 (2025년 업데이트)
        브라우저 분석으로 검증된 성공한 인증 방식 적용

        Args:
            session: 사용할 세션 객체

        Returns:
            bool: 로그인 성공 여부
        """
        try:
            # 1. 로그인 페이지 접속 (세션 쿠키 획득)
            logger.info("🔐 Getting session cookie...")
            session.get(f"{self.base_url}/login/loginForm", timeout=self.timeout)

            # 2. 사용자 확인 API 호출 (첫 번째 단계)
            logger.info(f"👤 Verifying user: {self.username}")
            verify_data = {"memberId": self.username, "memberPw": self.password}

            # AJAX 헤더 설정
            session.headers.update(
                {
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": self.base_url,
                    "Referer": f"{self.base_url}/login/loginForm",
                }
            )

            verify_resp = session.post(
                f"{self.base_url}/member/findOneMember",
                data=verify_data,
                timeout=self.timeout,
            )

            if verify_resp.status_code != 200:
                logger.error(f"❌ User verification failed: {verify_resp.status_code}")
                return False

            logger.info("✅ User verified successfully")

            # 3. 실제 로그인 (두 번째 단계)
            logger.info("🔑 Performing actual login...")
            login_form_data = {
                "username": self.username,  # 브라우저 분석으로 확인된 필드명
                "password": self.password,  # 브라우저 분석으로 확인된 필드명
                "login_error": "",
                "txId": "",
                "token": "",
                "memberId": "",
                "smsTimeExcess": "N",
            }

            login_resp = session.post(
                f"{self.base_url}/login/addLogin",  # 브라우저 분석으로 확인된 엔드포인트
                data=login_form_data,
                timeout=self.timeout,
                allow_redirects=True,
            )

            # 로그인 성공 확인
            if login_resp.status_code == 200 and "main" in login_resp.url:
                if "logout" in login_resp.text.lower() or "로그아웃" in login_resp.text:
                    logger.info("✅ REGTECH login successful!")
                    self.session = session
                    return True

            logger.error("❌ REGTECH login failed - redirect or content check failed")
            logger.debug(f"Response URL: {login_resp.url}")
            logger.debug(f"Response status: {login_resp.status_code}")
            return False

        except Exception as e:
            logger.error(f"❌ REGTECH login error: {e}")
            return False

    def create_authenticated_session(self) -> requests.Session:
        """
        인증된 세션 생성 (쿠키 기반)

        Returns:
            requests.Session: 쿠키가 설정된 세션
        """
        session = self.create_session()

        if self.cookie_auth_mode and self.cookie_string:
            # 쿠키 문자열 파싱 및 설정
            cookies = {}
            for cookie_pair in self.cookie_string.split("; "):
                if "=" in cookie_pair:
                    key, value = cookie_pair.split("=", 1)
                    cookies[key] = value

            # 세션에 쿠키 설정
            for key, value in cookies.items():
                session.cookies.set(key, value)

            logger.info(f"✅ Created authenticated session with {len(cookies)} cookies")

        return session

    def logout(self) -> bool:
        """로그아웃 수행"""
        if not self.session:
            return True

        try:
            logout_url = f"{self.base_url}/logout"
            response = self.session.get(logout_url, timeout=self.timeout)
            response.raise_for_status()

            logger.info("REGTECH logout successful")
            return True

        except Exception as e:
            logger.warning(f"Logout failed (non-critical): {e}")
            return False
        finally:
            if self.session:
                self.session.close()
                self.session = None
