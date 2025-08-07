#!/usr/bin/env python3
"""
API Gateway Proxy Functions

Extracted from app.py for better organization.
"""

import logging
from typing import Dict, Any

from fastapi import HTTPException, Request
import httpx

logger = logging.getLogger(__name__)


async def proxy_request(
    service_name: str,
    path: str,
    request: Request,
    method: str = "GET",
    use_cache: bool = False,
    cache_category: str = "default",
) -> Dict[str, Any]:
    """서비스로 요청 프록시"""
    from . import service_discovery, cache_manager, SERVICES

    # 서비스 상태 확인
    if not service_discovery.is_service_healthy(service_name):
        raise HTTPException(
            status_code=503, detail=f"Service {service_name} is unavailable"
        )

    # 캠시 확인
    if use_cache and method == "GET":
        cache_key = cache_manager.get_cache_key(request)
        cached_data = cache_manager.get(cache_key, cache_category)
        if cached_data:
            return cached_data

    # 서비스 URL 구성
    service_url = service_discovery.get_service_url(service_name)
    target_url = f"{service_url}{path}"

    # 쿼리 파라미터 추가
    if request.query_params:
        target_url += f"?{request.query_params}"

    try:
        async with httpx.AsyncClient(
            timeout=SERVICES.get(service_name, {}).get("timeout", 30)
        ) as client:
            if method == "GET":
                response = await client.get(target_url)
            elif method == "POST":
                body = await request.body()
                response = await client.post(
                    target_url,
                    content=body,
                    headers={
                        "Content-Type": request.headers.get(
                            "content-type", "application/json"
                        )
                    },
                )
            elif method == "PUT":
                body = await request.body()
                response = await client.put(
                    target_url,
                    content=body,
                    headers={
                        "Content-Type": request.headers.get(
                            "content-type", "application/json"
                        )
                    },
                )
            elif method == "DELETE":
                response = await client.delete(target_url)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")

            response.raise_for_status()
            result = response.json()

            # 캠시 저장
            if use_cache and method == "GET":
                cache_key = cache_manager.get_cache_key(request)
                cache_manager.set(cache_key, result, cache_category)

            return result

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Service timeout")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Proxy error for {service_name}: {e}")
        raise HTTPException(status_code=502, detail="Service error")
