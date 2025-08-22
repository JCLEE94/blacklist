#!/usr/bin/env python3
"""
Rate Limiting Module
Provides rate limiting functionality with configurable windows and limits

Third-party packages:
- collections: https://docs.python.org/3/library/collections.html

Sample input: request identifiers, rate limits
Expected output: rate limit status, blocked IPs
"""

from flask import Flask, Blueprint, jsonify, request, redirect, url_for, render_template
import logging

logger = logging.getLogger(__name__)

import time
from collections import defaultdict, deque
from functools import wraps
from typing import Callable, Dict


class RateLimitManager:
    """Manages rate limiting for requests and authentication attempts"""

    def __init__(self):
        self.rate_limits = defaultdict(lambda: deque(maxlen=1000))
        self.blocked_ips = set()
        self.failed_attempts = defaultdict(lambda: {"count": 0, "last_attempt": 0})

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

    def get_failed_attempts(self, identifier: str) -> int:
        """Get number of failed attempts for identifier"""
        return self.failed_attempts.get(identifier, {}).get("count", 0)

    def get_rate_limit_status(self, identifier: str) -> Dict:
        """Get current rate limit status for identifier"""
        requests = self.rate_limits[identifier]
        return {
            "identifier": identifier,
            "current_requests": len(requests),
            "is_blocked": self.is_blocked(identifier),
            "failed_attempts": self.get_failed_attempts(identifier),
        }


# Global rate limit manager instance
_rate_limit_manager = None


def get_rate_limit_manager() -> RateLimitManager:
    """Get global rate limit manager instance"""
    global _rate_limit_manager
    if _rate_limit_manager is None:
        _rate_limit_manager = RateLimitManager()
    return _rate_limit_manager


def rate_limit(limit: int = 100, window_seconds: int = 3600):
    """Decorator to apply rate limiting to routes"""

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get client identifier (IP address)
                client_ip = request.environ.get(
                    "HTTP_X_FORWARDED_FOR", request.remote_addr
                )
                if client_ip and "," in client_ip:
                    client_ip = client_ip.split(",")[0].strip()

                rate_limiter = get_rate_limit_manager()

                # Check if IP is blocked
                if rate_limiter.is_blocked(client_ip):
                    return (
                        jsonify(
                            {
                                "error": "IP address blocked due to too many failed attempts"
                            }
                        ),
                        429,
                    )

                # Check rate limit
                if not rate_limiter.check_rate_limit(client_ip, limit, window_seconds):
                    return (
                        jsonify(
                            {
                                "error": "Rate limit exceeded",
                                "limit": limit,
                                "window_seconds": window_seconds,
                            }
                        ),
                        429,
                    )

                return f(*args, **kwargs)

            except Exception as e:
                logger.error(f"Rate limiting error: {e}")
                # Allow request on error to avoid blocking legitimate traffic
                return f(*args, **kwargs)

        return decorated_function

    return decorator


def create_rate_limiter(limit: int = 100, window_seconds: int = 3600):
    """Create a rate limiter with specific configuration"""

    def rate_limiter(identifier: str) -> bool:
        """Check if request should be allowed"""
        manager = get_rate_limit_manager()
        return manager.check_rate_limit(identifier, limit, window_seconds)

    return rate_limiter


def record_failed_login(identifier: str) -> bool:
    """Record a failed login attempt"""
    manager = get_rate_limit_manager()
    return manager.record_failed_attempt(identifier)


def is_ip_blocked(identifier: str) -> bool:
    """Check if IP is currently blocked"""
    manager = get_rate_limit_manager()
    return manager.is_blocked(identifier)


def unblock_ip(identifier: str):
    """Unblock an IP address"""
    manager = get_rate_limit_manager()
    manager.unblock(identifier)


if __name__ == "__main__":
    import sys

    # Test rate limiting functionality
    all_validation_failures = []
    total_tests = 0

    # Test 1: Rate limit enforcement
    total_tests += 1
    try:
        manager = RateLimitManager()
        test_ip = "192.168.1.100"

        # Should allow first 3 requests (limit=3 for test)
        for i in range(3):
            if not manager.check_rate_limit(test_ip, 3, 60):
                all_validation_failures.append(
                    f"Rate limit: Request {i+1} was denied when it should be allowed"
                )
                break

        # 4th request should be denied
        if manager.check_rate_limit(test_ip, 3, 60):
            all_validation_failures.append(
                "Rate limit: 4th request was allowed when it should be denied"
            )

    except Exception as e:
        all_validation_failures.append(f"Rate limit: Exception occurred - {e}")

    # Test 2: Failed attempt tracking
    total_tests += 1
    try:
        manager = RateLimitManager()
        test_ip = "192.168.1.101"

        # Record 4 failed attempts (max_attempts=5 for test)
        for i in range(4):
            if not manager.record_failed_attempt(test_ip, 5, 15):
                all_validation_failures.append(
                    f"Failed attempts: Attempt {i+1} blocked prematurely"
                )
                break

        # 5th attempt should block the IP
        if manager.record_failed_attempt(test_ip, 5, 15):
            all_validation_failures.append(
                "Failed attempts: 5th attempt was allowed when IP should be blocked"
            )

        # IP should now be blocked
        if not manager.is_blocked(test_ip):
            all_validation_failures.append(
                "Failed attempts: IP not blocked after max attempts"
            )

    except Exception as e:
        all_validation_failures.append(f"Failed attempts: Exception occurred - {e}")

    # Test 3: Unblocking functionality
    total_tests += 1
    try:
        manager = RateLimitManager()
        test_ip = "192.168.1.102"

        # Block IP by recording max failed attempts
        for i in range(5):
            manager.record_failed_attempt(test_ip, 5, 15)

        if not manager.is_blocked(test_ip):
            all_validation_failures.append(
                "Unblocking: IP not blocked before unblock test"
            )
        else:
            # Unblock IP
            manager.unblock(test_ip)
            if manager.is_blocked(test_ip):
                all_validation_failures.append(
                    "Unblocking: IP still blocked after unblock"
                )

    except Exception as e:
        all_validation_failures.append(f"Unblocking: Exception occurred - {e}")

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
        print("Rate limiting module is validated and formal tests can now be written")
        sys.exit(0)
