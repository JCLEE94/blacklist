#!/usr/bin/env python3
"""
Security Module
Provides a unified interface for all security-related functionality

This module consolidates authentication, rate limiting, and validation
into a single, easy-to-use interface while maintaining modularity.
"""

from .auth import (
    AuthenticationManager,
    generate_api_key,
    generate_jwt_token,
    hash_password,
    require_api_key,
    require_auth,
    require_permission,
    verify_jwt_token,
    verify_password,
)
from .rate_limiting import RateLimitManager, get_rate_limit_manager, rate_limit
from .validation import (
    SecurityHeaders,
    ValidationManager,
    generate_csrf_token,
    input_validation,
    sanitize_input,
    security_check,
    validate_api_key,
    validate_csrf_token,
)


# For backward compatibility - preserve the original SecurityManager interface
class SecurityManager:
    """Centralized security management - backward compatibility wrapper"""

    def __init__(self, secret_key: str, jwt_secret: str = None):
        self.auth_manager = AuthenticationManager(secret_key, jwt_secret)
        self.rate_manager = get_rate_limit_manager()
        self.validator = ValidationManager()
        self.secret_key = secret_key
        self.jwt_secret = jwt_secret or secret_key

    # Authentication methods
    def hash_password(self, password: str, salt: str = None) -> tuple:
        return self.auth_manager.hash_password(password, salt)

    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        return self.auth_manager.verify_password(password, password_hash, salt)

    def generate_jwt_token(
        self, user_id: str, roles=None, expires_hours: int = 24
    ) -> str:
        return self.auth_manager.generate_jwt_token(user_id, roles, expires_hours)

    def verify_jwt_token(self, token: str):
        return self.auth_manager.verify_jwt_token(token)

    def generate_api_key(self, prefix: str = "ak") -> str:
        return self.auth_manager.generate_api_key(prefix)

    def validate_api_key_format(self, api_key: str) -> bool:
        return self.auth_manager.validate_api_key_format(api_key)

    # Rate limiting methods
    def check_rate_limit(
        self, identifier: str, limit: int, window_seconds: int = 3600
    ) -> bool:
        return self.rate_manager.check_rate_limit(identifier, limit, window_seconds)

    def record_failed_attempt(
        self, identifier: str, max_attempts: int = 5, lockout_minutes: int = 15
    ) -> bool:
        return self.rate_manager.record_failed_attempt(
            identifier, max_attempts, lockout_minutes
        )

    def is_blocked(self, identifier: str) -> bool:
        return self.rate_manager.is_blocked(identifier)

    def unblock(self, identifier: str):
        return self.rate_manager.unblock(identifier)

    # Properties for backward compatibility
    @property
    def rate_limits(self):
        return self.rate_manager.rate_limits

    @property
    def blocked_ips(self):
        return self.rate_manager.blocked_ips

    @property
    def failed_attempts(self):
        return self.rate_manager.failed_attempts


def setup_security(app, secret_key: str, jwt_secret: str = None):
    """Setup security for Flask application"""
    try:
        # Initialize security manager
        security_manager = SecurityManager(secret_key, jwt_secret)

        # Store in app config
        app.config["SECURITY_MANAGER"] = security_manager

        # Apply security headers to all responses
        @app.after_request
        def apply_security_headers(response):
            return SecurityHeaders.apply_security_headers(response)

        return security_manager

    except Exception as e:
        app.logger.error(f"Security setup error: {e}")
        raise


def get_security_manager(secret_key: str = None, jwt_secret: str = None):
    """Get or create security manager instance"""
    # For compatibility with existing code
    if secret_key:
        return SecurityManager(secret_key, jwt_secret)

    # Try to get from Flask app context
    try:
        from flask import current_app

        return current_app.config.get("SECURITY_MANAGER")
    except BaseException:
        # Fallback to default
        return SecurityManager("default_secret", "default_jwt_secret")


__all__ = [
    "SecurityManager",
    "AuthenticationManager",
    "RateLimitManager",
    "ValidationManager",
    "SecurityHeaders",
    "setup_security",
    "get_security_manager",
    "require_auth",
    "require_api_key",
    "require_permission",
    "rate_limit",
    "input_validation",
    "security_check",
    "hash_password",
    "verify_password",
    "generate_jwt_token",
    "verify_jwt_token",
    "generate_api_key",
    "sanitize_input",
    "validate_api_key",
    "generate_csrf_token",
    "validate_csrf_token",
]
