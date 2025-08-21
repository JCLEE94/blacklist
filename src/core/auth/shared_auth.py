#!/usr/bin/env python3
"""
공통 인증 헬퍼 모듈
여러 컬렉터에서 사용하는 공통 인증 로직을 통합
"""

import logging
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)


class SharedAuthHelper:
    """
    공통 인증 기능을 제공하는 헬퍼 클래스
    """

    @staticmethod
    def create_session_with_headers(
        headers: Optional[Dict[str, str]] = None
    ) -> requests.Session:
        """공통 헤더를 포함한 세션 생성"""
        session = requests.Session()

        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        if headers:
            default_headers.update(headers)

        session.headers.update(default_headers)
        return session

    @staticmethod
    def validate_login_response(response: requests.Response) -> bool:
        """로그인 응답 검증"""
        if response.status_code == 200:
            # 로그인 성공 시 일반적인 패턴들 확인
            success_indicators = [
                "dashboard",
                "main",
                "home",
                "welcome",
                "logout",
                "profile",
                "menu",
            ]

            fail_indicators = [
                "login",
                "error",
                "fail",
                "invalid",
                "incorrect",
                "denied",
                "unauthorized",
            ]

            response_text = response.text.lower()

            # 실패 지표가 있으면 실패
            for indicator in fail_indicators:
                if indicator in response_text:
                    return False

            # 성공 지표가 있으면 성공
            for indicator in success_indicators:
                if indicator in response_text:
                    return True

            # 쿠키 기반 판단
            if response.cookies:
                return True

        elif response.status_code == 302:
            # 리다이렉트 기반 판단
            location = response.headers.get("Location", "").lower()
            if "login" not in location and "error" not in location:
                return True

        return False

    @staticmethod
    def extract_csrf_token(response: requests.Response) -> Optional[str]:
        """CSRF 토큰 추출"""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(response.text, "html.parser")

            # 일반적인 CSRF 토큰 패턴들
            csrf_patterns = [
                ("input", {"name": "csrf_token"}),
                ("input", {"name": "_token"}),
                ("input", {"name": "authenticity_token"}),
                ("meta", {"name": "csrf-token"}),
                ("meta", {"name": "_token"}),
            ]

            for tag, attrs in csrf_patterns:
                element = soup.find(tag, attrs)
                if element:
                    value = element.get("value") or element.get("content")
                    if value:
                        return value

        except Exception as e:
            logger.debug(f"CSRF token extraction failed: {e}")

        return None

    @staticmethod
    def build_login_payload(
        username: str,
        password: str,
        csrf_token: Optional[str] = None,
        additional_fields: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """로그인 페이로드 구성"""
        payload = {
            "username": username,
            "password": password,
        }

        # 다양한 username 필드명 시도
        username_fields = ["username", "user", "userid", "email", "login", "id"]
        password_fields = ["password", "passwd", "pwd", "pass"]

        # CSRF 토큰 추가
        if csrf_token:
            payload["csrf_token"] = csrf_token
            payload["_token"] = csrf_token
            payload["authenticity_token"] = csrf_token

        # 추가 필드
        if additional_fields:
            payload.update(additional_fields)

        return payload

    @staticmethod
    def perform_login(
        session: requests.Session,
        login_url: str,
        username: str,
        password: str,
        additional_payload: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> bool:
        """표준 로그인 수행"""
        try:
            # 1. 로그인 페이지 접근하여 CSRF 토큰 추출
            response = session.get(login_url, timeout=timeout)
            csrf_token = SharedAuthHelper.extract_csrf_token(response)

            # 2. 로그인 페이로드 구성
            payload = SharedAuthHelper.build_login_payload(
                username, password, csrf_token, additional_payload
            )

            # 3. 로그인 요청
            response = session.post(
                login_url, data=payload, timeout=timeout, allow_redirects=True
            )

            # 4. 로그인 결과 검증
            return SharedAuthHelper.validate_login_response(response)

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    @staticmethod
    def check_session_validity(session: requests.Session, test_url: str) -> bool:
        """세션 유효성 확인"""
        try:
            response = session.get(test_url, timeout=10)

            # 로그인 페이지로 리다이렉트되면 세션 만료
            if "login" in response.url.lower():
                return False

            # 401, 403 응답이면 세션 만료
            if response.status_code in [401, 403]:
                return False

            return response.status_code == 200

        except Exception:
            return False
