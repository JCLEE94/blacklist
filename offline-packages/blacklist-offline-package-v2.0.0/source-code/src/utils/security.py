"""
Enhanced Security Module
Provides advanced security features including authentication, authorization,
rate limiting, and security headers
"""

import hashlib
import logging
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List

import jwt

logger = logging.getLogger(__name__)


class SecurityManager:
    """Centralized security management"""

    def __init__(self, secret_key: str, jwt_secret: str = None):
        self.secret_key = secret_key
        self.jwt_secret = jwt_secret or secret_key
        self.rate_limits = defaultdict(lambda: deque(maxlen=1000))
        self.blocked_ips = set()
        self.failed_attempts = defaultdict(lambda: {"count": 0, "last_attempt": 0})

    def hash_password(self, password: str, salt: str = None) -> tuple:
        """Hash password with salt"""
        try:
            if salt is None:
                salt = secrets.token_hex(32)

            # Use PBKDF2 with SHA256
            password_hash = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                100000,  # iterations
            )

            return password_hash.hex(), salt

        except Exception as e:
            logger.error(f"Password hashing error: {e}")
            raise

    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """Verify password against hash"""
        try:
            computed_hash, _ = self.hash_password(password, salt)
            return secrets.compare_digest(password_hash, computed_hash)

        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def generate_jwt_token(
        self, user_id: str, roles: List[str] = None, expires_hours: int = 24
    ) -> str:
        """Generate JWT token"""
        try:
            payload = {
                "user_id": user_id,
                "roles": roles or [],
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(hours=expires_hours),
            }

            token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
            return token

        except Exception as e:
            logger.error(f"JWT generation error: {e}")
            raise

    def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
        except Exception as e:
            logger.error(f"JWT verification error: {e}")
            return None

    def check_rate_limit(
        self, identifier: str, limit: int, window_seconds: int = 3600
    ) -> bool:
        """Check if request is within rate limit"""
        try:
            current_time = time.time()
            requests = self.rate_limits[identifier]

            # Remove old requests outside the window
            while requests and requests[0] <= current_time - window_seconds:
                requests.popleft()

            # Check if limit exceeded
            if len(requests) >= limit:
                return False

            # Add current request
            requests.append(current_time)
            return True

        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return True  # Allow on error

    def record_failed_attempt(
        self, identifier: str, max_attempts: int = 5, lockout_minutes: int = 15
    ) -> bool:
        """Record failed authentication attempt"""
        try:
            current_time = time.time()
            attempt_data = self.failed_attempts[identifier]

            # Reset if enough time has passed
            if current_time - attempt_data["last_attempt"] > lockout_minutes * 60:
                attempt_data["count"] = 0

            attempt_data["count"] += 1
            attempt_data["last_attempt"] = current_time

            # Check if should be blocked
            if attempt_data["count"] >= max_attempts:
                self.blocked_ips.add(identifier)
                logger.warning(f"IP blocked due to failed attempts: {identifier}")
                return False

            return True

        except Exception as e:
            logger.error(f"Failed attempt recording error: {e}")
            return True

    def is_blocked(self, identifier: str) -> bool:
        """Check if identifier is blocked"""
        return identifier in self.blocked_ips

    def unblock(self, identifier: str):
        """Unblock identifier"""
        self.blocked_ips.discard(identifier)
        self.failed_attempts.pop(identifier, None)

    def generate_api_key(self, prefix: str = "ak") -> str:
        """Generate secure API key"""
        random_part = secrets.token_urlsafe(32)
        return "{prefix}_{random_part}"

    def validate_api_key_format(self, api_key: str) -> bool:
        """Validate API key format"""
        try:
            parts = api_key.split("_")
            return len(parts) == 2 and len(parts[1]) >= 32
        except Exception as e:
            return False


class SecurityHeaders:
    """Security headers management"""

    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get standard security headers"""
        return {
            "X-Content-Type-Options": "nosnif",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'sel'; script-src 'sel' 'unsafe-inline'; style-src 'sel' 'unsafe-inline';",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }

    @staticmethod
    def apply_security_headers(response):
        """Apply security headers to Flask response"""
        try:
            headers = SecurityHeaders.get_security_headers()
            for header, value in headers.items():
                response.headers[header] = value
            return response
        except Exception as e:
            logger.error(f"Error applying security headers: {e}")
            return response


def require_auth(roles: List[str] = None, api_key_allowed: bool = True):
    """Decorator for requiring authentication"""

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import current_app, g, request

            try:
                security_manager = getattr(current_app, "security_manager", None)
                if not security_manager:
                    return {"error": "Security not configured"}, 500

                # Check for JWT token
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
                    payload = security_manager.verify_jwt_token(token)

                    if payload:
                        g.current_user = payload

                        # Check roles
                        if roles:
                            user_roles = payload.get("roles", [])
                            if not any(role in user_roles for role in roles):
                                return {"error": "Insufficient permissions"}, 403

                        return f(*args, **kwargs)

                # Check for API key
                if api_key_allowed:
                    api_key = request.headers.get("X-API-Key")
                    if api_key and security_manager.validate_api_key_format(api_key):
                        # 실제 API 키 검증 구현
                        from ..models.api_key import get_api_key_manager

                        api_key_manager = get_api_key_manager()
                        validated_key = api_key_manager.validate_api_key(api_key)

                        if validated_key:
                            g.current_user = {
                                "user_id": "api_user_{validated_key.key_id}",
                                "roles": validated_key.permissions,
                                "api_key_name": validated_key.name,
                            }
                            return f(*args, **kwargs)

                return {"error": "Authentication required"}, 401

            except Exception as e:
                logger.error(f"Authentication error: {e}")
                return {"error": "Authentication failed"}, 401

        return decorated_function

    return decorator


def rate_limit(limit: int = 100, window_seconds: int = 3600):
    """Decorator for rate limiting"""

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import current_app, request

            try:
                security_manager = getattr(current_app, "security_manager", None)
                if not security_manager:
                    return f(*args, **kwargs)  # Skip if not configured

                # Use IP address as identifier
                identifier = request.remote_addr

                # Check if blocked
                if security_manager.is_blocked(identifier):
                    return {"error": "IP blocked due to abuse"}, 429

                # Check rate limit
                if not security_manager.check_rate_limit(
                    identifier, limit, window_seconds
                ):
                    return {"error": "Rate limit exceeded"}, 429

                return f(*args, **kwargs)

            except Exception as e:
                logger.error(f"Rate limiting error: {e}")
                return f(*args, **kwargs)  # Allow on error

        return decorated_function

    return decorator


def input_validation(schema: Dict[str, Any]):
    """Decorator for input validation"""

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request

            try:
                if request.is_json:
                    data = request.get_json()

                    # Basic validation
                    for field, rules in schema.items():
                        if rules.get("required", False) and field not in data:
                            return {"error": "Missing required field: {field}"}, 400

                        if field in data:
                            value = data[field]

                            # Type validation
                            expected_type = rules.get("type")
                            if expected_type and not isinstance(value, expected_type):
                                return {"error": "Invalid type for {field}"}, 400

                            # Length validation for strings
                            if isinstance(value, str):
                                min_len = rules.get("min_length", 0)
                                max_len = rules.get("max_length", float("in"))
                                if not (min_len <= len(value) <= max_len):
                                    return {"error": "Invalid length for {field}"}, 400

                return f(*args, **kwargs)

            except Exception as e:
                logger.error(f"Input validation error: {e}")
                return {"error": "Validation failed"}, 400

        return decorated_function

    return decorator


def setup_security(app, secret_key: str, jwt_secret: str = None):
    """Setup security for Flask application"""
    try:
        # Initialize security manager
        app.security_manager = SecurityManager(secret_key, jwt_secret)

        # Apply security headers to all responses
        @app.after_request
        def apply_security_headers(response):
            return SecurityHeaders.apply_security_headers(response)

        logger.info("Security setup completed")
        return True

    except Exception as e:
        logger.error(f"Security setup failed: {e}")
        return False


# Utility functions
def sanitize_input(input_string: str, max_length: int = 1000) -> str:
    """Sanitize user input"""
    if not isinstance(input_string, str):
        return ""

    # Remove dangerous characters
    dangerous_chars = ["<", ">", '"', "'", "&", "\x00"]
    sanitized = input_string

    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "")

    # Limit length
    sanitized = sanitized[:max_length]

    return sanitized.strip()


def generate_csrf_token() -> str:
    """Generate CSRF token"""
    return secrets.token_urlsafe(32)


def validate_csrf_token(token: str, session_token: str) -> bool:
    """Validate CSRF token"""
    try:
        return secrets.compare_digest(token, session_token)
    except Exception as e:
        return False


# Global security manager instance
_security_manager = None


def get_security_manager(secret_key: str = None, jwt_secret: str = None):
    """Get global security manager instance"""
    global _security_manager
    if _security_manager is None and secret_key:
        _security_manager = SecurityManager(secret_key, jwt_secret)
    return _security_manager


def require_api_key(f: Callable) -> Callable:
    """Simple decorator for API key authentication"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request

        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return {"error": "API key required"}, 401

        # Simple API key validation (in real implementation, check against database)
        if not api_key.startswith("ak_") or len(api_key) < 10:
            return {"error": "Invalid API key"}, 401

        return f(*args, **kwargs)

    return decorated_function


def require_permission(permission: str):
    """Decorator for permission-based access control"""

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import g

            # Simple permission check (in real implementation, check user permissions)
            user = getattr(g, "current_user", None)
            if not user:
                return {"error": "Authentication required"}, 401

            # Basic permission logic
            user_roles = user.get("roles", [])
            if "admin" in user_roles or permission in user_roles:
                return f(*args, **kwargs)

            return {"error": "Insufficient permissions"}, 403

        return decorated_function

    return decorator


def security_check(f: Callable) -> Callable:
    """General security check decorator"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request

        # Basic security checks
        # 1. Check for common attack patterns
        user_agent = request.headers.get("User-Agent", "")
        if any(
            pattern in user_agent.lower() for pattern in ["sqlmap", "nmap", "nikto"]
        ):
            return {"error": "Request blocked"}, 403

        # 2. Basic rate limiting (simplified)
        # In a real implementation, use more sophisticated rate limiting

        return f(*args, **kwargs)

    return decorated_function
