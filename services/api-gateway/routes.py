#!/usr/bin/env python3
"""
API Gateway Routes

Extracted from app.py for better organization.
"""

from datetime import datetime
from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .auth import verify_token
from .proxy import proxy_request

security = HTTPBearer(auto_error=False)


def register_routes(app: FastAPI):
    """라우트 등록"""

    @app.get("/health")
    async def gateway_health():
        """게이트웨이 헬스 체크"""
        from . import service_discovery

        await service_discovery.health_check()

        service_status = {}
        for service_name in service_discovery.services.keys():
            service_status[service_name] = {
                "healthy": service_discovery.is_service_healthy(service_name),
                "last_check": service_discovery.last_health_check.get(service_name),
            }

        return {
            "status": "healthy",
            "service": "api-gateway",
            "timestamp": datetime.utcnow(),
            "services": service_status,
        }

    # 수집 서비스 라우팅
    @app.get("/api/v1/collection/status")
    async def get_collection_status(
        request: Request, auth: Dict = Depends(verify_token)
    ):
        """수집 상태 조회"""
        return await proxy_request(
            "collection",
            "/api/v1/status",
            request,
            use_cache=True,
            cache_category="statistics",
        )

    @app.post("/api/v1/collection/trigger")
    async def trigger_collection(request: Request, auth: Dict = Depends(verify_token)):
        """데이터 수집 트리거"""
        if auth["user_type"] == "anonymous":
            raise HTTPException(status_code=401, detail="Authentication required")

        return await proxy_request(
            "collection", "/api/v1/collect", request, method="POST"
        )

    @app.put("/api/v1/collection/sources/{source}/enable")
    async def enable_collection_source(
        source: str, request: Request, auth: Dict = Depends(verify_token)
    ):
        """수집 소스 활성화"""
        if auth["user_type"] not in ["admin", "user"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        return await proxy_request(
            "collection", f"/api/v1/sources/{source}/enable", request, method="PUT"
        )

    # 블랙리스트 서비스 라우팅
    @app.get("/api/v1/blacklist/active")
    async def get_active_blacklist(request: Request):
        """활성 블랙리스트 조회 (공개 API)"""
        return await proxy_request(
            "blacklist", "/api/v1/active-ips", request, use_cache=True
        )

    @app.get("/api/v1/blacklist/fortigate")
    async def get_fortigate_format(request: Request):
        """FortiGate 형식 조회"""
        return await proxy_request(
            "blacklist",
            "/api/v1/fortigate",
            request,
            use_cache=True,
            cache_category="fortigate",
        )

    @app.get("/api/v1/blacklist/search/{ip}")
    async def search_ip(ip: str, request: Request):
        """IP 검색"""
        return await proxy_request("blacklist", f"/api/v1/ips/{ip}", request)

    @app.post("/api/v1/blacklist/search")
    async def search_batch(request: Request):
        """배치 IP 검색"""
        return await proxy_request(
            "blacklist", "/api/v1/search", request, method="POST"
        )

    @app.get("/api/v1/blacklist/statistics")
    async def get_blacklist_statistics(request: Request):
        """블랙리스트 통계"""
        return await proxy_request(
            "blacklist",
            "/api/v1/statistics",
            request,
            use_cache=True,
            cache_category="statistics",
        )

    # 분석 서비스 라우팅
    @app.get("/api/v1/analytics/trends")
    async def get_analytics_trends(request: Request):
        """트렌드 분석"""
        return await proxy_request(
            "analytics",
            "/api/v1/trends",
            request,
            use_cache=True,
            cache_category="trends",
        )

    @app.get("/api/v1/analytics/geographic")
    async def get_geographic_distribution(request: Request):
        """지리적 분포"""
        return await proxy_request(
            "analytics",
            "/api/v1/geographic",
            request,
            use_cache=True,
            cache_category="trends",
        )

    @app.get("/api/v1/analytics/threat-types")
    async def get_threat_types(request: Request):
        """위협 유형 분석"""
        return await proxy_request(
            "analytics",
            "/api/v1/threat-types",
            request,
            use_cache=True,
            cache_category="trends",
        )

    @app.get("/api/v1/analytics/report")
    async def get_analytics_report(request: Request):
        """종합 분석 리포트"""
        return await proxy_request(
            "analytics",
            "/api/v1/report",
            request,
            use_cache=True,
            cache_category="trends",
        )

    @app.get("/api/v1/analytics/realtime")
    async def get_realtime_metrics(request: Request):
        """실시간 메트릭"""
        return await proxy_request("analytics", "/api/v1/realtime", request)

    # 관리 API
    @app.get("/admin/services")
    async def get_services_status(auth: Dict = Depends(verify_token)):
        """서비스 상태 조회 (관리자)"""
        if auth["user_type"] != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        from . import service_discovery

        await service_discovery.health_check()

        services_info = {}
        for service_name, url in service_discovery.services.items():
            services_info[service_name] = {
                "url": url,
                "healthy": service_discovery.is_service_healthy(service_name),
                "last_check": service_discovery.last_health_check.get(service_name),
                "timeout": 30,  # Default timeout
            }

        return {"services": services_info}

    @app.post("/admin/cache/clear")
    async def clear_cache(auth: Dict = Depends(verify_token)):
        """캠시 클리어 (관리자)"""
        if auth["user_type"] != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        from . import cache_manager

        cache_manager.cache.clear()
        return {"status": "success", "message": "Cache cleared"}

    @app.get("/admin/metrics")
    async def get_gateway_metrics(auth: Dict = Depends(verify_token)):
        """게이트웨이 메트릭 (관리자)"""
        if auth["user_type"] != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        from . import cache_manager, rate_limiter, service_discovery

        return {
            "cache_size": len(cache_manager.cache),
            "rate_limiter_clients": len(rate_limiter.requests),
            "healthy_services": list(service_discovery.healthy_services),
            "uptime": "00:00:00",  # 실제로는 시작 시간부터 계산
        }
