#!/usr/bin/env python3
"""
Comprehensive unit tests for src/utils/security.py
테스트 커버리지 향상을 위한 보안 모듈 포괄적 테스트
"""

import hashlib
import json
import secrets
import threading
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import jwt
import pytest
from flask import Flask, g, request

from src.utils.security import (
    SecurityHeaders,
    SecurityManager,
    generate_csrf_token,
    get_security_manager,
    input_validation,
    rate_limit,
    require_api_key,
    require_auth,
    require_permission,
    sanitize_input,
    security_check,
    setup_security,
    validate_csrf_token,
)


class TestSecurityManager(unittest.TestCase):
    """SecurityManager 클래스 테스트"""

    def setUp(self):
        """테스트 셋업"""
        self.secret_key = "test-secret-key-123"
        self.jwt_secret = "test-jwt-secret-456"
        self.security_manager = SecurityManager(self.secret_key, self.jwt_secret)

    def test_initialization(self):
        """SecurityManager 초기화 테스트"""
        # 기본 초기화
        sm = SecurityManager("secret")
        self.assertEqual(sm.secret_key, "secret")
        self.assertEqual(sm.jwt_secret, "secret")  # 기본값 확인
        self.assertIsInstance(sm.rate_limits, dict)
        self.assertIsInstance(sm.blocked_ips, set)
        self.assertIsInstance(sm.failed_attempts, dict)

        # JWT secret 별도 지정
        sm_with_jwt = SecurityManager("secret", "jwt_secret")
        self.assertEqual(sm_with_jwt.jwt_secret, "jwt_secret")

    def test_password_hashing_success(self):
        """비밀번호 해시 성공 케이스"""
        password = "test_password_123"

        # 솔트 없이 해시 생성
        hash_result, salt = self.security_manager.hash_password(password)
        self.assertIsInstance(hash_result, str)
        self.assertIsInstance(salt, str)
        self.assertTrue(len(hash_result) > 0)
        self.assertTrue(len(salt) > 0)

        # 솔트 제공하여 해시 생성
        custom_salt = "custom_salt_value"
        hash_result2, salt2 = self.security_manager.hash_password(password, custom_salt)
        self.assertEqual(salt2, custom_salt)
        self.assertNotEqual(hash_result, hash_result2)  # 다른 솔트이므로 다른 해시

    def test_password_hashing_error_handling(self):
        """비밀번호 해시 에러 처리 테스트"""
        with patch('hashlib.pbkdf2_hmac', side_effect=Exception("Hash error")):
            with self.assertRaises(Exception):
                self.security_manager.hash_password("password")

    def test_password_verification_success(self):
        """비밀번호 검증 성공 케이스"""
        password = "verify_test_password"
        hash_result, salt = self.security_manager.hash_password(password)

        # 올바른 비밀번호 검증
        self.assertTrue(
            self.security_manager.verify_password(password, hash_result, salt)
        )

        # 잘못된 비밀번호 검증
        self.assertFalse(
            self.security_manager.verify_password("wrong_password", hash_result, salt)
        )

    def test_password_verification_error_handling(self):
        """비밀번호 검증 에러 처리 테스트"""
        with patch.object(self.security_manager, 'hash_password', side_effect=Exception("Verification error")):
            result = self.security_manager.verify_password("password", "hash", "salt")
            self.assertFalse(result)  # 에러 발생 시 False 반환

    def test_jwt_token_generation_success(self):
        """JWT 토큰 생성 성공 케이스"""
        user_id = "test_user_123"
        roles = ["admin", "user"]

        # 기본 생성 (24시간)
        token = self.security_manager.generate_jwt_token(user_id, roles)
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)

        # 커스텀 만료 시간
        token_custom = self.security_manager.generate_jwt_token(
            user_id, roles, expires_hours=1
        )
        self.assertIsInstance(token_custom, str)
        self.assertNotEqual(token, token_custom)

        # 역할 없이 생성
        token_no_roles = self.security_manager.generate_jwt_token(user_id)
        self.assertIsInstance(token_no_roles, str)

    def test_jwt_token_generation_error_handling(self):
        """JWT 토큰 생성 에러 처리 테스트"""
        with patch('jwt.encode', side_effect=Exception("JWT encoding error")):
            with self.assertRaises(Exception):
                self.security_manager.generate_jwt_token("user_id")

    def test_jwt_token_verification_success(self):
        """JWT 토큰 검증 성공 케이스"""
        user_id = "verify_user_123"
        roles = ["admin"]

        # 토큰 생성 및 검증
        token = self.security_manager.generate_jwt_token(user_id, roles, expires_hours=1)
        payload = self.security_manager.verify_jwt_token(token)

        self.assertIsNotNone(payload)
        self.assertEqual(payload["user_id"], user_id)
        self.assertEqual(payload["roles"], roles)
        self.assertIn("iat", payload)
        self.assertIn("exp", payload)

    def test_jwt_token_verification_expired(self):
        """만료된 JWT 토큰 검증 테스트"""
        # 이미 만료된 토큰 생성 (테스트용으로 직접 생성)
        expired_payload = {
            "user_id": "test_user",
            "roles": [],
            "iat": datetime.utcnow() - timedelta(hours=2),
            "exp": datetime.utcnow() - timedelta(hours=1),  # 1시간 전 만료
        }
        expired_token = jwt.encode(expired_payload, self.jwt_secret, algorithm="HS256")

        result = self.security_manager.verify_jwt_token(expired_token)
        self.assertIsNone(result)

    def test_jwt_token_verification_invalid(self):
        """잘못된 JWT 토큰 검증 테스트"""
        # 잘못된 토큰
        result = self.security_manager.verify_jwt_token("invalid.jwt.token")
        self.assertIsNone(result)

        # 다른 시크릿으로 서명된 토큰
        other_token = jwt.encode({"user_id": "test"}, "wrong_secret", algorithm="HS256")
        result = self.security_manager.verify_jwt_token(other_token)
        self.assertIsNone(result)

    def test_jwt_token_verification_error_handling(self):
        """JWT 토큰 검증 에러 처리 테스트"""
        with patch('jwt.decode', side_effect=Exception("JWT decode error")):
            result = self.security_manager.verify_jwt_token("token")
            self.assertIsNone(result)

    def test_rate_limit_success(self):
        """속도 제한 성공 케이스"""
        identifier = "test_ip_192.168.1.1"

        # 제한 내 요청 (5회, 1시간 윈도우)
        for i in range(5):
            self.assertTrue(
                self.security_manager.check_rate_limit(identifier, limit=5, window_seconds=3600)
            )

        # 제한 초과
        self.assertFalse(
            self.security_manager.check_rate_limit(identifier, limit=5, window_seconds=3600)
        )

    def test_rate_limit_window_expiry(self):
        """속도 제한 윈도우 만료 테스트"""
        identifier = "test_ip_window"

        # 윈도우 내에서 제한까지 요청
        for i in range(3):
            self.assertTrue(
                self.security_manager.check_rate_limit(identifier, limit=3, window_seconds=1)
            )

        # 제한 초과
        self.assertFalse(
            self.security_manager.check_rate_limit(identifier, limit=3, window_seconds=1)
        )

        # 윈도우 시간 대기 후 다시 시도
        time.sleep(1.1)
        self.assertTrue(
            self.security_manager.check_rate_limit(identifier, limit=3, window_seconds=1)
        )

    def test_rate_limit_error_handling(self):
        """속도 제한 에러 처리 테스트"""
        with patch('time.time', side_effect=Exception("Time error")):
            # 에러 발생 시 True 반환 (허용)
            result = self.security_manager.check_rate_limit("test", 5)
            self.assertTrue(result)

    def test_failed_attempt_recording_success(self):
        """실패 시도 기록 성공 케이스"""
        identifier = "test_ip_attempts"

        # 최대 시도 횟수 미만
        for i in range(4):
            result = self.security_manager.record_failed_attempt(
                identifier, max_attempts=5, lockout_minutes=15
            )
            self.assertTrue(result)

        # 최대 시도 횟수 달성
        result = self.security_manager.record_failed_attempt(
            identifier, max_attempts=5, lockout_minutes=15
        )
        self.assertFalse(result)

        # IP가 차단되었는지 확인
        self.assertTrue(self.security_manager.is_blocked(identifier))

    def test_failed_attempt_lockout_reset(self):
        """실패 시도 잠금 해제 테스트"""
        identifier = "test_ip_reset"

        # 실패 시도 기록
        self.security_manager.record_failed_attempt(
            identifier, max_attempts=2, lockout_minutes=0.01  # 0.6초
        )
        self.security_manager.record_failed_attempt(
            identifier, max_attempts=2, lockout_minutes=0.01
        )

        # 잠금 시간 대기
        time.sleep(0.7)

        # 시도 카운트 리셋되어야 함
        result = self.security_manager.record_failed_attempt(
            identifier, max_attempts=2, lockout_minutes=0.01
        )
        self.assertTrue(result)

    def test_failed_attempt_error_handling(self):
        """실패 시도 기록 에러 처리 테스트"""
        with patch('time.time', side_effect=Exception("Time error")):
            result = self.security_manager.record_failed_attempt("test")
            self.assertTrue(result)  # 에러 시 True 반환

    def test_ip_blocking_and_unblocking(self):
        """IP 차단 및 해제 테스트"""
        identifier = "test_ip_block"

        # 초기 상태: 차단되지 않음
        self.assertFalse(self.security_manager.is_blocked(identifier))

        # 차단
        self.security_manager.blocked_ips.add(identifier)
        self.assertTrue(self.security_manager.is_blocked(identifier))

        # 차단 해제
        self.security_manager.unblock(identifier)
        self.assertFalse(self.security_manager.is_blocked(identifier))

        # 실패 시도 데이터도 삭제되는지 확인
        self.security_manager.failed_attempts[identifier] = {"count": 5, "last_attempt": time.time()}
        self.security_manager.unblock(identifier)
        self.assertNotIn(identifier, self.security_manager.failed_attempts)

    def test_api_key_generation(self):
        """API 키 생성 테스트"""
        # 기본 prefix
        api_key = self.security_manager.generate_api_key()
        self.assertTrue(api_key.startswith("ak_"))
        self.assertTrue(len(api_key) > 10)

        # 커스텀 prefix
        custom_key = self.security_manager.generate_api_key("custom")
        self.assertTrue(custom_key.startswith("custom_"))

    def test_api_key_validation_success(self):
        """API 키 형식 검증 성공 케이스"""
        # 유효한 API 키
        valid_key = "ak_" + secrets.token_urlsafe(32)
        self.assertTrue(self.security_manager.validate_api_key_format(valid_key))

        # 긴 키도 유효
        long_key = "prefix_" + secrets.token_urlsafe(64)
        self.assertTrue(self.security_manager.validate_api_key_format(long_key))

    def test_api_key_validation_failure(self):
        """API 키 형식 검증 실패 케이스"""
        # 잘못된 형식들
        invalid_keys = [
            "invalid_key",  # 너무 짧음
            "no_underscore",
            "ak_short",  # 두 번째 부분이 32자 미만
            "",
            "ak_",
            "just_underscore_",
        ]

        for invalid_key in invalid_keys:
            self.assertFalse(
                self.security_manager.validate_api_key_format(invalid_key),
                f"Key should be invalid: {invalid_key}"
            )

    def test_api_key_validation_error_handling(self):
        """API 키 검증 에러 처리 테스트"""
        # None이나 잘못된 타입
        self.assertFalse(self.security_manager.validate_api_key_format(None))
        self.assertFalse(self.security_manager.validate_api_key_format(123))


class TestSecurityHeaders(unittest.TestCase):
    """SecurityHeaders 클래스 테스트"""

    def test_get_security_headers(self):
        """보안 헤더 반환 테스트"""
        headers = SecurityHeaders.get_security_headers()

        # 기본 보안 헤더들이 포함되어 있는지 확인
        expected_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy",
            "Permissions-Policy",
        ]

        for header in expected_headers:
            self.assertIn(header, headers)

        # 헤더 값들 검증
        self.assertEqual(headers["X-Content-Type-Options"], "nosnif")
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertTrue(headers["X-XSS-Protection"].startswith("1"))

    def test_apply_security_headers_success(self):
        """보안 헤더 적용 성공 테스트"""
        # Mock Flask response
        mock_response = MagicMock()
        mock_response.headers = {}

        result = SecurityHeaders.apply_security_headers(mock_response)

        # 응답 객체가 반환되어야 함
        self.assertEqual(result, mock_response)

        # 헤더가 적용되었는지 확인
        self.assertGreater(len(mock_response.headers), 0)

    def test_apply_security_headers_error_handling(self):
        """보안 헤더 적용 에러 처리 테스트"""
        # 에러를 발생시키는 Mock 응답
        mock_response = MagicMock()
        mock_response.headers = MagicMock(side_effect=Exception("Header error"))

        # 에러가 발생해도 응답 객체는 반환되어야 함
        result = SecurityHeaders.apply_security_headers(mock_response)
        self.assertEqual(result, mock_response)


class TestUtilityFunctions(unittest.TestCase):
    """유틸리티 함수 테스트"""

    def test_sanitize_input_success(self):
        """입력 값 정화 성공 케이스"""
        # 정상 입력
        clean_input = sanitize_input("normal text input")
        self.assertEqual(clean_input, "normal text input")

        # 위험한 문자 제거
        dangerous_input = '<script>alert("xss")</script>'
        sanitized = sanitize_input(dangerous_input)
        self.assertNotIn("<", sanitized)
        self.assertNotIn(">", sanitized)
        self.assertNotIn('"', sanitized)

        # 길이 제한
        long_input = "a" * 2000
        limited = sanitize_input(long_input, max_length=100)
        self.assertEqual(len(limited), 100)

        # 공백 제거
        whitespace_input = "  test input  "
        trimmed = sanitize_input(whitespace_input)
        self.assertEqual(trimmed, "test input")

    def test_sanitize_input_edge_cases(self):
        """입력 값 정화 엣지 케이스"""
        # 잘못된 타입
        self.assertEqual(sanitize_input(123), "")
        self.assertEqual(sanitize_input(None), "")
        self.assertEqual(sanitize_input([]), "")

        # 빈 문자열
        self.assertEqual(sanitize_input(""), "")

        # null 바이트
        null_input = "test\x00input"
        sanitized = sanitize_input(null_input)
        self.assertNotIn("\x00", sanitized)

    def test_csrf_token_generation(self):
        """CSRF 토큰 생성 테스트"""
        token1 = generate_csrf_token()
        token2 = generate_csrf_token()

        # 토큰이 문자열이고 충분한 길이인지 확인
        self.assertIsInstance(token1, str)
        self.assertIsInstance(token2, str)
        self.assertGreater(len(token1), 20)

        # 매번 다른 토큰이 생성되는지 확인
        self.assertNotEqual(token1, token2)

    def test_csrf_token_validation_success(self):
        """CSRF 토큰 검증 성공 케이스"""
        token = generate_csrf_token()

        # 같은 토큰
        self.assertTrue(validate_csrf_token(token, token))

        # 다른 토큰
        other_token = generate_csrf_token()
        self.assertFalse(validate_csrf_token(token, other_token))

    def test_csrf_token_validation_error_handling(self):
        """CSRF 토큰 검증 에러 처리 테스트"""
        # 잘못된 입력
        self.assertFalse(validate_csrf_token(None, "token"))
        self.assertFalse(validate_csrf_token("token", None))
        self.assertFalse(validate_csrf_token(123, "token"))


class TestGlobalFunctions(unittest.TestCase):
    """전역 함수 테스트"""

    def test_get_security_manager_singleton(self):
        """전역 보안 매니저 싱글톤 테스트"""
        # 초기에는 None
        manager1 = get_security_manager()
        self.assertIsNone(manager1)

        # secret_key 제공하여 생성
        manager2 = get_security_manager("test_secret")
        self.assertIsNotNone(manager2)
        self.assertIsInstance(manager2, SecurityManager)

        # 같은 인스턴스 반환 확인
        manager3 = get_security_manager()
        self.assertEqual(manager2, manager3)

    def test_setup_security_success(self):
        """Flask 앱 보안 설정 성공 테스트"""
        app = Flask(__name__)

        result = setup_security(app, "test_secret", "jwt_secret")

        self.assertTrue(result)
        self.assertTrue(hasattr(app, "security_manager"))
        self.assertIsInstance(app.security_manager, SecurityManager)

    def test_setup_security_error_handling(self):
        """Flask 앱 보안 설정 에러 처리 테스트"""
        # None 앱 전달
        result = setup_security(None, "secret")
        self.assertFalse(result)


class TestDecorators(unittest.TestCase):
    """데코레이터 테스트"""

    def setUp(self):
        """테스트 앱 설정"""
        self.app = Flask(__name__)
        self.app.testing = True
        setup_security(self.app, "test_secret", "jwt_secret")

    def test_require_api_key_success(self):
        """API 키 요구 데코레이터 성공 케이스"""
        @require_api_key
        def test_endpoint():
            return {"status": "success"}

        with self.app.test_request_context(headers={"X-API-Key": "ak_" + "a" * 32}):
            result = test_endpoint()
            self.assertEqual(result["status"], "success")

    def test_require_api_key_missing(self):
        """API 키 누락 테스트"""
        @require_api_key
        def test_endpoint():
            return {"status": "success"}

        with self.app.test_request_context():
            result, status_code = test_endpoint()
            self.assertEqual(status_code, 401)
            self.assertIn("error", result)

    def test_require_api_key_invalid(self):
        """잘못된 API 키 테스트"""
        @require_api_key
        def test_endpoint():
            return {"status": "success"}

        with self.app.test_request_context(headers={"X-API-Key": "invalid_key"}):
            result, status_code = test_endpoint()
            self.assertEqual(status_code, 401)

    def test_security_check_success(self):
        """보안 체크 데코레이터 성공 케이스"""
        @security_check
        def test_endpoint():
            return {"status": "success"}

        with self.app.test_request_context(headers={"User-Agent": "Mozilla/5.0"}):
            result = test_endpoint()
            self.assertEqual(result["status"], "success")

    def test_security_check_blocked_user_agent(self):
        """보안 체크 데코레이터 차단 케이스"""
        @security_check
        def test_endpoint():
            return {"status": "success"}

        # 악성 User-Agent
        with self.app.test_request_context(headers={"User-Agent": "sqlmap"}):
            result, status_code = test_endpoint()
            self.assertEqual(status_code, 403)

        with self.app.test_request_context(headers={"User-Agent": "nmap"}):
            result, status_code = test_endpoint()
            self.assertEqual(status_code, 403)


if __name__ == "__main__":
    # 테스트 실행
    unittest.main(verbosity=2)