"""
Auth Decorators - Unified authentication functionality
"""

import logging
from functools import wraps
from typing import List, Optional

from flask import g, jsonify, request

from .registry import get_registry

logger = logging.getLogger(__name__)


def unified_auth(
    required: bool = True,
    roles: Optional[List[str]] = None,
    permissions: Optional[List[str]] = None,
    allow_api_key: bool = True,
    require_admin: bool = False,
    ip_whitelist: Optional[List[str]] = None,
):
    """
    Unified authentication decorator
    Consolidates all authentication logic with flexible options

    Args:
        required: Whether authentication is required
        roles: List of required roles
        permissions: List of required permissions
        allow_api_key: Whether to allow API key authentication
        require_admin: Whether to require admin privileges
        ip_whitelist: List of allowed IP addresses
    """

    def auth_decorator(func):
        @wraps(func)
        def auth_wrapper(*args, **kwargs):
            # Check IP whitelist if specified
            if ip_whitelist:
                client_ip = request.remote_addr
                # X-Forwarded-For 헤더 확인 (프록시 환경)
                if request.headers.get("X-Forwarded-For"):
                    client_ip = (
                        request.headers.get("X-Forwarded-For").split(",")[0].strip()
                    )

                if client_ip not in ip_whitelist:
                    return jsonify({"error": "Access denied from this IP"}), 403

            registry = get_registry()
            if not registry.auth_manager:
                if required:
                    return jsonify({"error": "Authentication not configured"}), 503
                return func(*args, **kwargs)

            # Extract authentication credentials
            auth_header = request.headers.get("Authorization", "")
            api_key = request.headers.get("X-API-Key", "")

            user_context = None

            # Try Bearer token authentication (JWT)
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                try:
                    user_context = registry.auth_manager.verify_token(token)
                except Exception as e:
                    logger.warning("Token verification failed: {e}")
                    if required:
                        return jsonify({"error": "Invalid or expired token"}), 401

            # Try ApiKey authentication (custom format)
            elif auth_header.lower().startswith("apikey "):
                api_key = auth_header.split(" ")[1]
                try:
                    client_name = registry.auth_manager.verify_api_key(api_key)
                    if client_name:
                        user_context = {"client_name": client_name, "api_key": True}
                except Exception as e:
                    logger.warning("API key verification failed: {e}")
                    if required:
                        return jsonify({"error": "Invalid API key"}), 401

            # Try X-API-Key header authentication
            elif api_key and allow_api_key:
                try:
                    client_name = registry.auth_manager.verify_api_key(api_key)
                    if client_name:
                        user_context = {
                            "user_id": client_name,
                            "client_name": client_name,
                            "api_key": True,
                        }
                except Exception as e:
                    logger.warning("API key verification failed: {e}")
                    if required:
                        return jsonify({"error": "Invalid API key"}), 401

            # Check if authentication is required
            if required and not user_context:
                return (
                    jsonify(
                        {
                            "error": "Authentication required",
                            "message": "Please provide valid credentials",
                        }
                    ),
                    401,
                )

            # Check admin requirement
            if require_admin and (not user_context or not user_context.get("is_admin")):
                return jsonify({"error": "Admin access required"}), 403

            # Check roles if specified
            if user_context and roles:
                user_roles = user_context.get("roles", [])
                if not any(role in user_roles for role in roles):
                    return jsonify({"error": "Insufficient privileges"}), 403

            # Check permissions if specified
            if user_context and permissions:
                user_permissions = user_context.get("permissions", [])
                if not any(perm in user_permissions for perm in permissions):
                    return jsonify({"error": "Insufficient permissions"}), 403

            # Set user context in Flask g
            if user_context:
                g.auth_user = user_context  # For compatibility with existing code
                g.user_id = user_context.get("user_id")
                g.client_name = user_context.get("client_name")
                g.user_roles = user_context.get("roles", [])
                g.user_permissions = user_context.get("permissions", [])
                g.is_admin = user_context.get("is_admin", False)

            return func(*args, **kwargs)

        return auth_wrapper

    return auth_decorator
