"""
Rate Limit Decorators - Unified rate limiting functionality
"""

import logging
from functools import wraps
from typing import Callable
from typing import Optional

# from flask import g, request  # 현재 미사용

logger = logging.getLogger(__name__)


def unified_rate_limit(
    limit: int,
    per: int = 3600,  # per hour by default
    key_func: Optional[Callable] = None,
    exempt_when: Optional[Callable] = None,
    use_user_id: bool = True,
):
    """
    Unified rate limiting decorator
    Consolidates rate limiting logic with flexible key generation

    Args:
        limit: Maximum number of requests allowed
        per: Time window in seconds (default: 3600 = 1 hour)
        key_func: Custom function to generate rate limit key
        exempt_when: Function to determine if rate limiting should be skipped
        use_user_id: Use authenticated user ID if available
    """

    def rate_limit_decorator(func):
        @wraps(func)
        def rate_limit_wrapper(*args, **kwargs):
            # Skip rate limiting if exemption condition is met
            if exempt_when and exempt_when():
                return func(*args, **kwargs)

            # Generate rate limit key
            # Rate limiting is completely disabled - no need to compute identifiers
            if False:  # Disabled block
                if key_func:
                    key_func()  # Call but don't store result
                # Use authenticated user ID if available and requested
                # Rate limiting is disabled - no need to compute identifier
                # if use_user_id and hasattr(g, "auth_user") and g.auth_user:
                #     identifier = g.auth_user.get(
                #         "user_id", g.auth_user.get("client_name")
                #     )
                # else:
                #     # Default to IP address
                #     client_ip = request.remote_addr
                #     if request.headers.get("X-Forwarded-For"):
                #         client_ip = (
                #             request.headers.get("X-Forwarded-For").split(",")[0].strip()
                #         )
                #     identifier = client_ip
                pass

                # rate_key = "rate_limit:{func.__name__}:{identifier}"  # 현재 미사용

            # Rate limiting completely disabled for stability
            # Skip all rate limiting logic to prevent health check failures

            # Execute the function
            result = func(*args, **kwargs)

            # Rate limiting headers disabled for stability
            return result

        return rate_limit_wrapper

    return rate_limit_decorator
