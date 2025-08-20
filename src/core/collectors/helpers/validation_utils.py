#!/usr/bin/env python3
"""
REGTECH 유효성 검증 모듈
IP 유효성 및 로그인 검증 기능을 제공
"""

import logging
from typing import Any, Dict

import requests

logger = logging.getLogger(__name__)


class RegtechValidationUtils:
    """
    REGTECH 유효성 검증 전담 클래스
    """

    def __init__(self):
        # IP 유틸리티는 호출자에서 주입
        self.ip_utils = None

    def set_ip_utils(self, ip_utils):
        """
        IP 유틸리티 설정"""
        self.ip_utils = ip_utils

    def is_valid_ip(self, ip: str) -> bool:
        """
        IP 유효성 검사 (통합 유틸리티 사용)"""
        if not self.ip_utils:
            # Fallback: 기본 유효성 검사
            import ipaddress

            try:
                ipaddress.ip_address(ip)
                return True
            except ValueError:
                return False

        return self.ip_utils.validate_ip(ip) and not self.ip_utils.is_private_ip(ip)

    def verify_login_success(self, response: requests.Response) -> bool:
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
            logger.error(f"로그인 검증 중 오류: {e}")
            return False

    def should_cancel(self, cancel_event=None) -> bool:
        """취소 요청 확인"""
        if cancel_event and hasattr(cancel_event, "is_set"):
            return cancel_event.is_set()
        return False
