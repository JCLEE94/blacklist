#!/usr/bin/env python3
"""
API Gateway Authentication

Extracted from app.py for better organization.
"""

import os
from typing import Dict, Any

import jwt
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)


def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """JWT 토큰 검증"""
    if not credentials:
        return {"user_type": "anonymous", "client_id": "anonymous"}

    try:
        # 실제 구현에서는 JWT 시크릿 키 사용
        secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key")
        payload = jwt.decode(credentials.credentials, secret_key, algorithms=["HS256"])
        return {
            "user_type": payload.get("user_type", "user"),
            "client_id": payload.get("client_id", "unknown"),
            "permissions": payload.get("permissions", []),
        }
    except jwt.InvalidTokenError:
        return {"user_type": "anonymous", "client_id": "anonymous"}
