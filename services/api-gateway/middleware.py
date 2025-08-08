#!/usr/bin/env python3
"""
API Gateway Middleware Components

Extracted from app.py for better organization.
"""

import json
import logging
import time
from collections import defaultdict
from typing import Any, Dict

from fastapi import Request, Response

logger = logging.getLogger(__name__)


class RateLimiter:
    """레이트 리미터"""

    def __init__(self):
        self.requests = defaultdict(list)
        self.limits = {
            "default": {"requests": 100, "window": 3600},
            "admin": {"requests": 1000, "window": 3600},
            "public": {"requests": 50, "window": 3600},
        }

    def is_allowed(self, client_id: str, endpoint_type: str = "default") -> bool:
        now = time.time()
        limit_config = self.limits.get(endpoint_type, self.limits["default"])

        # 현재 시간 윈도우 내의 요청만 유지
        self.requests[client_id] = [
            req_time
            for req_time in self.requests[client_id]
            if now - req_time < limit_config["window"]
        ]

        # 요청 수 확인
        if len(self.requests[client_id]) >= limit_config["requests"]:
            return False

        # 요청 추가
        self.requests[client_id].append(now)
        return True


class CacheManager:
    """캠시 매니저"""

    def __init__(self):
        self.cache = {}
        self.cache_ttl = {
            "statistics": 300,
            "trends": 600,
            "fortigate": 180,
            "health": 60,
        }

    def get_cache_key(self, request: Request) -> str:
        """캠시 키 생성"""
        import hashlib

        path = request.url.path
        query = str(request.query_params)
        return hashlib.md5(f"{path}:{query}".encode()).hexdigest()

    def get(self, key: str, category: str = "default"):
        """캠시 조회"""
        if key not in self.cache:
            return None

        data, timestamp = self.cache[key]
        ttl = self.cache_ttl.get(category, 300)

        if time.time() - timestamp > ttl:
            del self.cache[key]
            return None

        return data

    def set(self, key: str, data: Any, category: str = "default"):
        """캠시 저장"""
        self.cache[key] = (data, time.time())


async def rate_limiting_middleware(request: Request, call_next):
    """레이트 리미팅 미들웨어"""
    client_ip = request.client.host
    path = request.url.path

    # 엔드포인트 타입 결정
    endpoint_type = "default"
    if path.startswith("/admin"):
        endpoint_type = "admin"
    elif path.startswith("/api/v1/public"):
        endpoint_type = "public"

    # Global rate limiter instance
    from . import rate_limiter

    if not rate_limiter.is_allowed(client_ip, endpoint_type):
        return Response(
            content=json.dumps({"error": "Rate limit exceeded"}),
            status_code=429,
            headers={"Content-Type": "application/json"},
        )

    response = await call_next(request)
    return response


async def logging_middleware(request: Request, call_next):
    """로깅 미들웨어"""
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )

    return response
