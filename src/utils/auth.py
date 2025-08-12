"""
API 인증 및 보안 유틸리티

통합된 인증 시스템을 제공합니다:
- AuthManager: JWT 토큰 및 API 키 관리
- RateLimiter: Rate limiting 구현
- 데코레이터는 unified_decorators 모듈 사용
"""

import hashlib
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt

# Note: unified decorators imported when needed to avoid circular imports

logger = logging.getLogger(__name__)


class AuthManager:
    """JWT 기반 인증 관리자"""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        token_expiry: int = 3600,
    ):
        self.secret_key = secret_key or os.environ.get(
            "JWT_SECRET_KEY", "default-secret-key"
        )
        self.algorithm = algorithm
        self.token_expiry = token_expiry

        # API 키 관리 (환경 변수에서 로드)
        self.api_keys = {}
        for key, value in os.environ.items():
            if key.startswith("API_KEY_"):
                client_name = key.replace("API_KEY_", "").lower()
                self.api_keys[value] = client_name

    def generate_token(
        self,
        user_id: str,
        client_name: str = None,
        additional_claims: Dict[str, Any] = None,
    ) -> str:
        """JWT 토큰 생성"""
        payload = {
            "user_id": user_id,
            "client_name": client_name,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=self.token_expiry),
        }

        if additional_claims:
            payload.update(additional_claims)

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """JWT 토큰 검증"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid token: {e}")
            return None

    def verify_api_key(self, api_key: str) -> Optional[str]:
        """API 키 검증"""
        return self.api_keys.get(api_key)

    def hash_password(self, password: str, salt: Optional[str] = None) -> tuple:
        """비밀번호 해싱"""
        if not salt:
            salt = os.urandom(32).hex()

        pwdhash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
        ).hex()

        return pwdhash, salt

    def verify_password(self, password: str, pwdhash: str, salt: str) -> bool:
        """비밀번호 검증"""
        new_hash, _ = self.hash_password(password, salt)
        return new_hash == pwdhash


class RateLimiter:
    """Rate Limiting 구현 - DISABLED FOR STABILITY"""

    def __init__(
        self, cache_manager=None, default_limit: int = 100, window_seconds: int = 60
    ):
        self.cache = cache_manager
        self.default_limit = default_limit
        self.window_seconds = window_seconds

    def check_rate_limit(self, identifier: str, limit: Optional[int] = None) -> tuple:
        """Rate limit 확인 - ALWAYS ALLOW"""
        # Always return True to disable rate limiting completely
        limit = limit or self.default_limit
        return True, limit, limit


# Note: Deprecated functions have been removed
# Use unified_auth decorator with ip_whitelist parameter instead
