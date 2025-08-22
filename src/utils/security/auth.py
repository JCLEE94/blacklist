#!/usr/bin/env python3
"""
Authentication Module
Provides JWT token generation, password hashing, and authentication decorators

Third-party packages:
- jwt: https://pyjwt.readthedocs.io/en/latest/
- cryptography: https://cryptography.io/en/latest/

Sample input: user credentials, password strings
Expected output: JWT tokens, password hashes, authentication status
"""

from flask import Flask, Blueprint, jsonify, request, redirect, url_for, render_template
import logging

logger = logging.getLogger(__name__)

import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

import jwt


class AuthenticationManager:
    """Handles authentication operations including JWT and password management"""

    def __init__(self, secret_key: str, jwt_secret: str = None):
        self.secret_key = secret_key
        self.jwt_secret = jwt_secret or secret_key

    def hash_password(self, password: str, salt: str = None) -> tuple:
        """Hash password with salt using PBKDF2"""
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
        """Generate JWT token with user information"""
        try:
            now = datetime.utcnow()
            payload = {
                "user_id": user_id,
                "roles": roles or [],
                "iat": now,
                "exp": now + timedelta(hours=expires_hours),
                "nonce": secrets.token_hex(8),  # Add randomness for uniqueness
            }

            token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
            return token

        except Exception as e:
            logger.error(f"JWT generation error: {e}")
            raise

    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
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

    def generate_api_key(self, prefix: str = "ak") -> str:
        """Generate secure API key"""
        # Generate URL-safe token without underscores to avoid conflicts
        random_part = secrets.token_urlsafe(32).replace("_", "")
        # If too short after removing underscores, regenerate
        while len(random_part) < 40:
            random_part += secrets.token_urlsafe(8).replace("_", "")
        return f"{prefix}_{random_part[:43]}"  # Limit to consistent length

    def validate_api_key_format(self, api_key: str) -> bool:
        """Validate API key format"""
        try:
            if not api_key or not isinstance(api_key, str):
                return False

            # Must contain exactly one underscore
            if api_key.count("_") != 1:
                return False

            parts = api_key.split("_")
            if len(parts) != 2:
                return False

            prefix, token = parts

            # Validate prefix: 2-10 chars, alphanumeric, starts with letter
            if not (
                2 <= len(prefix) <= 10
                and prefix.isalpha()  # Only letters for prefix (no numbers)
                and prefix.islower()
            ):  # Lowercase convention
                return False

            # Validate token: 40+ chars, URL-safe characters (no underscores in
            # token part)
            if not (
                len(token) >= 40 and all(c.isalnum() or c == "-" for c in token)
            ):  # No underscores in token
                return False

            return True

        except Exception as e:
            logger.error(f"API key validation error: {e}")
            return False


def require_auth(roles: List[str] = None, api_key_allowed: bool = True):
    """Decorator to require authentication"""

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Check for API key first
                api_key = request.headers.get("X-API-Key")
                if api_key and api_key_allowed:
                    # Validate API key format and existence
                    from .validation import ValidationManager

                    validator = ValidationManager()
                    if validator.validate_api_key(api_key):
                        g.user_id = "api_user"
                        g.roles = ["api"]
                        return f(*args, **kwargs)

                # Check for JWT token
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
                    auth_mgr = AuthenticationManager(
                        secret_key="placeholder",  # Will be injected by app
                        jwt_secret="placeholder",
                    )
                    payload = auth_mgr.verify_jwt_token(token)
                    if payload:
                        g.user_id = payload.get("user_id")
                        g.roles = payload.get("roles", [])

                        # Check role requirements
                        if roles:
                            user_roles = set(g.roles)
                            required_roles = set(roles)
                            if not user_roles.intersection(required_roles):
                                return (
                                    jsonify({"error": "Insufficient permissions"}),
                                    403,
                                )

                        return f(*args, **kwargs)

                return jsonify({"error": "Authentication required"}), 401

            except Exception as e:
                logger.error(f"Authentication error: {e}")
                return jsonify({"error": "Authentication failed"}), 401

        return decorated_function

    return decorator


def require_api_key(f: Callable) -> Callable:
    """Decorator to require API key authentication"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            api_key = request.headers.get("X-API-Key")
            if not api_key:
                return jsonify({"error": "API key required"}), 401

            from .validation import ValidationManager

            validator = ValidationManager()
            if not validator.validate_api_key(api_key):
                return jsonify({"error": "Invalid API key"}), 401

            g.user_id = "api_user"
            g.roles = ["api"]
            return f(*args, **kwargs)

        except Exception as e:
            logger.error(f"API key authentication error: {e}")
            return jsonify({"error": "Authentication failed"}), 401

    return decorated_function


def require_permission(permission: str):
    """Decorator to require specific permission"""

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                if not hasattr(g, "user_id"):
                    return jsonify({"error": "Authentication required"}), 401

                # Check if user has required permission
                user_roles = getattr(g, "roles", [])
                if permission not in user_roles and "admin" not in user_roles:
                    return jsonify({"error": f"Permission {permission} required"}), 403

                return f(*args, **kwargs)

            except Exception as e:
                logger.error(f"Permission check error: {e}")
                return jsonify({"error": "Permission check failed"}), 403

        return decorated_function

    return decorator


# Standalone utility functions for backward compatibility
def hash_password(password: str, salt: str = None) -> tuple:
    """Standalone password hashing function"""
    auth_mgr = AuthenticationManager(secret_key="default")
    return auth_mgr.hash_password(password, salt)


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Standalone password verification function"""
    auth_mgr = AuthenticationManager(secret_key="default")
    return auth_mgr.verify_password(password, password_hash, salt)


def generate_jwt_token(
    user_id: str, roles: List[str] = None, expires_hours: int = 24
) -> str:
    """Standalone JWT token generation function"""
    auth_mgr = AuthenticationManager(secret_key="default")
    return auth_mgr.generate_jwt_token(user_id, roles, expires_hours)


def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Standalone JWT token verification function"""
    auth_mgr = AuthenticationManager(secret_key="default")
    return auth_mgr.verify_jwt_token(token)


def generate_api_key(prefix: str = "ak") -> str:
    """Standalone API key generation function"""
    auth_mgr = AuthenticationManager(secret_key="default")
    return auth_mgr.generate_api_key(prefix)


if __name__ == "__main__":
    import sys

    # Test authentication functionality
    all_validation_failures = []
    total_tests = 0

    # Test 1: Password hashing and verification
    total_tests += 1
    try:
        password = "test_password_123"
        password_hash, salt = hash_password(password)
        if not verify_password(password, password_hash, salt):
            all_validation_failures.append(
                "Password hashing: Verification failed for correct password"
            )
        elif verify_password("wrong_password", password_hash, salt):
            all_validation_failures.append(
                "Password hashing: Verification succeeded for wrong password"
            )
    except Exception as e:
        all_validation_failures.append(f"Password hashing: Exception occurred - {e}")

    # Test 2: JWT token generation and verification
    total_tests += 1
    try:
        auth_mgr = AuthenticationManager("test_secret")
        token = auth_mgr.generate_jwt_token("test_user", ["user"])
        payload = auth_mgr.verify_jwt_token(token)
        if not payload or payload.get("user_id") != "test_user":
            all_validation_failures.append(
                "JWT token: Token generation or verification failed"
            )
    except Exception as e:
        all_validation_failures.append(f"JWT token: Exception occurred - {e}")

    # Test 3: API key generation and validation
    total_tests += 1
    try:
        api_key = generate_api_key("test")
        auth_mgr = AuthenticationManager("test_secret")
        if not auth_mgr.validate_api_key_format(api_key):
            all_validation_failures.append(
                "API key: Generated key failed format validation"
            )
        if auth_mgr.validate_api_key_format("invalid_key"):
            all_validation_failures.append(
                "API key: Invalid key passed format validation"
            )
    except Exception as e:
        all_validation_failures.append(f"API key: Exception occurred - {e}")

    # Final validation result
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
        print("Authentication module is validated and formal tests can now be written")
        sys.exit(0)
