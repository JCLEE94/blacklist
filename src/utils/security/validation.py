#!/usr/bin/env python3
"""
Input Validation and Security Headers Module
Provides input validation, CSRF protection, and security headers

Third-party packages:
- flask: https://flask.palletsprojects.com/
- re: https://docs.python.org/3/library/re.html

Sample input: user input strings, request headers
Expected output: validated/sanitized input, security headers
"""

import logging
import re
import secrets
from functools import wraps
from typing import Any, Callable, Dict

from flask import jsonify, request

logger = logging.getLogger(__name__)


class ValidationManager:
    """Handles input validation and security operations"""

    def __init__(self):
        # Common patterns for validation
        self.email_pattern = re.compile(
            r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        )
        self.ip_pattern = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")
        self.alphanumeric_pattern = re.compile(r"^[a-zA-Z0-9_-]+$")

    def sanitize_input(self, input_string: str, max_length: int = 1000) -> str:
        """Sanitize user input to prevent injection attacks"""
        try:
            if not input_string or not isinstance(input_string, str):
                return ""

            # Remove potential script tags and SQL injection patterns
            cleaned = re.sub(
                r"<script[^>]*>.*?</script>",
                "",
                input_string,
                flags=re.IGNORECASE | re.DOTALL,
            )
            cleaned = re.sub(r"<[^>]+>", "", cleaned)  # Remove HTML tags
            cleaned = re.sub(r"[;\\\\&|`$]", "", cleaned)  # Remove dangerous characters
            cleaned = cleaned.strip()[:max_length]  # Limit length

            return cleaned

        except Exception as e:
            logger.error(f"Input sanitization error: {e}")
            return ""

    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        if not email or not isinstance(email, str):
            return False
        return bool(self.email_pattern.match(email))

    def validate_ip_address(self, ip: str) -> bool:
        """Validate IP address format"""
        if not ip or not isinstance(ip, str):
            return False
        return bool(self.ip_pattern.match(ip))

    def validate_alphanumeric(
        self, value: str, allow_dash_underscore: bool = True
    ) -> bool:
        """Validate alphanumeric input"""
        if not value or not isinstance(value, str):
            return False
        if allow_dash_underscore:
            return bool(self.alphanumeric_pattern.match(value))
        return value.isalnum()

    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key format and potentially check database"""
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

            # Validate token: 40+ chars, URL-safe characters (no underscores in token part)
            if not (
                len(token) >= 40 and all(c.isalnum() or c == "-" for c in token)
            ):  # No underscores in token
                return False

            # TODO: Add database lookup for actual validation
            return True

        except Exception as e:
            logger.error(f"API key validation error: {e}")
            return False

    def validate_request_data(
        self, data: Dict[str, Any], schema: Dict[str, Any]
    ) -> Dict[str, str]:
        """Validate request data against schema"""
        errors = {}

        try:
            for field, rules in schema.items():
                value = data.get(field)

                # Check required fields
                if rules.get("required", False) and not value:
                    errors[field] = f"{field} is required"
                    continue

                if value is None:
                    continue

                # Check type
                expected_type = rules.get("type")
                if expected_type and not isinstance(value, expected_type):
                    errors[field] = f"{field} must be of type {expected_type.__name__}"
                    continue

                # Check string length
                if isinstance(value, str):
                    min_length = rules.get("min_length", 0)
                    max_length = rules.get("max_length", 1000)
                    if len(value) < min_length:
                        errors[field] = (
                            f"{field} must be at least {min_length} characters"
                        )
                    elif len(value) > max_length:
                        errors[field] = (
                            f"{field} must be at most {max_length} characters"
                        )

                # Check custom validator
                validator = rules.get("validator")
                if validator and callable(validator):
                    if not validator(value):
                        errors[field] = rules.get(
                            "error_message", f"{field} is invalid"
                        )

        except Exception as e:
            logger.error(f"Request validation error: {e}")
            errors["_general"] = "Validation error occurred"

        return errors


class SecurityHeaders:
    """Manages security headers for responses"""

    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get standard security headers"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
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
            logger.error(f"Security headers error: {e}")
            return response


def input_validation(schema: Dict[str, Any]):
    """Decorator to validate request input against schema"""

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get request data
                if request.is_json:
                    data = request.get_json() or {}
                else:
                    data = request.form.to_dict() or {}

                # Validate data
                validator = ValidationManager()
                errors = validator.validate_request_data(data, schema)

                if errors:
                    return (
                        jsonify({"error": "Validation failed", "details": errors}),
                        400,
                    )

                return f(*args, **kwargs)

            except Exception as e:
                logger.error(f"Input validation error: {e}")
                return jsonify({"error": "Validation error"}), 400

        return decorated_function

    return decorator


def generate_csrf_token() -> str:
    """Generate CSRF token"""
    return secrets.token_urlsafe(32)


def validate_csrf_token(token: str, session_token: str) -> bool:
    """Validate CSRF token"""
    try:
        if not token or not session_token:
            return False
        return secrets.compare_digest(token, session_token)
    except Exception as e:
        logger.error(f"CSRF validation error: {e}")
        return False


def security_check(f: Callable) -> Callable:
    """Comprehensive security check decorator"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get client IP
            client_ip = request.environ.get("HTTP_X_FORWARDED_FOR", request.remote_addr)
            if client_ip and "," in client_ip:
                client_ip = client_ip.split(",")[0].strip()

            # Basic security checks
            validator = ValidationManager()

            # Check for basic SQL injection patterns in query parameters
            for param_value in request.args.values():
                if any(
                    pattern in param_value.lower()
                    for pattern in ["union", "select", "drop", "insert", "delete"]
                ):
                    logger.warning(
                        f"Potential SQL injection attempt from {client_ip}: {param_value}"
                    )
                    return jsonify({"error": "Invalid request"}), 400

            return f(*args, **kwargs)

        except Exception as e:
            logger.error(f"Security check error: {e}")
            return jsonify({"error": "Security check failed"}), 500

    return decorated_function


# Standalone utility functions
def sanitize_input(input_string: str, max_length: int = 1000) -> str:
    """Standalone input sanitization function"""
    validator = ValidationManager()
    return validator.sanitize_input(input_string, max_length)


def validate_api_key(api_key: str) -> bool:
    """Standalone API key validation function"""
    validator = ValidationManager()
    return validator.validate_api_key(api_key)


if __name__ == "__main__":
    import sys

    # Test validation functionality
    all_validation_failures = []
    total_tests = 0

    # Test 1: Input sanitization
    total_tests += 1
    try:
        validator = ValidationManager()
        dangerous_input = "<script>alert('xss')</script>Hello World"
        sanitized = validator.sanitize_input(dangerous_input)
        if "<script>" in sanitized or "alert" in sanitized:
            all_validation_failures.append(
                "Input sanitization: Failed to remove script tags"
            )
        if "Hello World" not in sanitized:
            all_validation_failures.append(
                "Input sanitization: Removed legitimate content"
            )
    except Exception as e:
        all_validation_failures.append(f"Input sanitization: Exception occurred - {e}")

    # Test 2: Email validation
    total_tests += 1
    try:
        validator = ValidationManager()
        valid_email = "test@example.com"
        invalid_email = "invalid-email"

        if not validator.validate_email(valid_email):
            all_validation_failures.append("Email validation: Valid email rejected")
        if validator.validate_email(invalid_email):
            all_validation_failures.append("Email validation: Invalid email accepted")
    except Exception as e:
        all_validation_failures.append(f"Email validation: Exception occurred - {e}")

    # Test 3: API key format validation
    total_tests += 1
    try:
        validator = ValidationManager()
        valid_api_key = "test_" + "a" * 40  # Valid format
        invalid_api_key = "invalid_key"  # Invalid format

        if not validator.validate_api_key(valid_api_key):
            all_validation_failures.append("API key validation: Valid key rejected")
        if validator.validate_api_key(invalid_api_key):
            all_validation_failures.append("API key validation: Invalid key accepted")
    except Exception as e:
        all_validation_failures.append(f"API key validation: Exception occurred - {e}")

    # Test 4: Request data validation
    total_tests += 1
    try:
        validator = ValidationManager()
        schema = {
            "username": {
                "required": True,
                "type": str,
                "min_length": 3,
                "max_length": 20,
            },
            "email": {
                "required": True,
                "type": str,
                "validator": validator.validate_email,
            },
        }

        valid_data = {"username": "testuser", "email": "test@example.com"}
        invalid_data = {"username": "ab", "email": "invalid-email"}

        valid_errors = validator.validate_request_data(valid_data, schema)
        invalid_errors = validator.validate_request_data(invalid_data, schema)

        if valid_errors:
            all_validation_failures.append(
                f"Request validation: Valid data rejected - {valid_errors}"
            )
        if not invalid_errors:
            all_validation_failures.append("Request validation: Invalid data accepted")
    except Exception as e:
        all_validation_failures.append(f"Request validation: Exception occurred - {e}")

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
        print("Validation module is validated and formal tests can now be written")
        sys.exit(0)
