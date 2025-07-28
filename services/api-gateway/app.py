"""
API Gateway - 마이크로서비스 통합 게이트웨이
라우팅, 인증, 부하분산, 모니터링, 캐싱 등을 담당
"""

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import logging
from datetime import datetime, timedelta
import httpx
import json
import hashlib
import time
from collections import defaultdict
import os
import jwt

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Blacklist API Gateway",
    description="마이크로서비스 통합 API 게이트웨이",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 보안 설정
security = HTTPBearer(auto_error=False)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 신뢰할 수 있는 호스트 설정
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # 프로덕션에서는 구체적인 호스트 지정
)

# 서비스 설정
SERVICES = {
    "collection": {
        "url": os.getenv("COLLECTION_SERVICE_URL", "http://collection-service:8000"),
        "health_endpoint": "/health",
        "timeout": 30
    },
    "blacklist": {
        "url": os.getenv("BLACKLIST_SERVICE_URL", "http://blacklist-service:8001"),
        "health_endpoint": "/health",
        "timeout": 30
    },
    "analytics": {
        "url": os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:8002"),
        "health_endpoint": "/health",
        "timeout": 30
    }
}

# 레이트 리미터
class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.limits = {
            "default": {"requests": 100, "window": 3600},  # 1시간 100요청
            "admin": {"requests": 1000, "window": 3600},   # 관리자는 1000요청
            "public": {"requests": 50, "window": 3600}     # 공개 API는 50요청
        }
    
    def is_allowed(self, client_id: str, endpoint_type: str = "default") -> bool:
        now = time.time()
        limit_config = self.limits.get(endpoint_type, self.limits["default"])
        
        # 현재 시간 윈도우 내의 요청만 유지
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if now - req_time < limit_config["window"]
        ]
        
        # 요청 수 확인
        if len(self.requests[client_id]) >= limit_config["requests"]:
            return False
        
        # 요청 추가
        self.requests[client_id].append(now)
        return True

# 캐시 매니저
class CacheManager:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = {
            "statistics": 300,      # 통계: 5분
            "trends": 600,          # 트렌드: 10분
            "fortigate": 180,       # FortiGate: 3분
            "health": 60            # 헬스체크: 1분
        }
    
    def get_cache_key(self, request: Request) -> str:
        """캐시 키 생성"""
        path = request.url.path
        query = str(request.query_params)
        return hashlib.md5(f"{path}:{query}".encode()).hexdigest()
    
    def get(self, key: str, category: str = "default") -> Optional[Any]:
        """캐시 조회"""
        if key not in self.cache:
            return None
        
        data, timestamp = self.cache[key]
        ttl = self.cache_ttl.get(category, 300)
        
        if time.time() - timestamp > ttl:
            del self.cache[key]
            return None
        
        return data
    
    def set(self, key: str, data: Any, category: str = "default"):
        """캐시 저장"""
        self.cache[key] = (data, time.time())

# 서비스 디스커버리
class ServiceDiscovery:
    def __init__(self):
        self.healthy_services = set()
        self.last_health_check = {}
    
    async def health_check(self):
        """모든 서비스 헬스 체크 - 성능 최적화 버전"""
        # 캐시에서 최근 헬스체크 결과 확인 (30초 TTL)
        cache_key = "service_health_check_v2"
        cached_health = cache_manager.get(cache_key)
        if cached_health:
            self.healthy_services = cached_health.get("healthy_services", set())
            self.last_health_check = cached_health.get("last_health_check", {})
            logger.debug("Service health check returned from cache")
            return

        # 동시 헬스체크 (병렬 처리)
        import asyncio
        
        async def check_single_service(service_name: str, config: dict):
            """단일 서비스 헬스체크"""
            try:
                async with httpx.AsyncClient(timeout=3) as client:  # 타임아웃 단축
                    response = await client.get(f"{config['url']}{config['health_endpoint']}")
                    if response.status_code == 200:
                        return service_name, True
                    else:
                        logger.warning(f"Health check failed for {service_name}: status {response.status_code}")
                        return service_name, False
            except asyncio.TimeoutError:
                logger.warning(f"Health check timeout for {service_name}")
                return service_name, False
            except Exception as e:
                logger.warning(f"Health check failed for {service_name}: {e}")
                return service_name, False

        # 모든 서비스를 병렬로 체크
        tasks = [
            check_single_service(service_name, config) 
            for service_name, config in SERVICES.items()
        ]
        
        try:
            # 모든 헬스체크를 병렬 실행
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            current_time = datetime.utcnow()
            new_healthy_services = set()
            new_last_health_check = {}
            
            for result in results:
                if isinstance(result, tuple):
                    service_name, is_healthy = result
                    if is_healthy:
                        new_healthy_services.add(service_name)
                    new_last_health_check[service_name] = current_time
                else:
                    logger.error(f"Health check exception: {result}")
            
            self.healthy_services = new_healthy_services
            self.last_health_check = new_last_health_check
            
            # 결과를 캐시에 저장
            health_data = {
                "healthy_services": self.healthy_services,
                "last_health_check": self.last_health_check
            }
            cache_manager.set(cache_key, health_data, ttl=30)
            
            logger.info(f"Health check completed: {len(new_healthy_services)}/{len(SERVICES)} services healthy")
            
        except Exception as e:
            logger.error(f"Health check batch failed: {e}")
            # 이전 상태 유지
    
    def is_service_healthy(self, service_name: str) -> bool:
        """서비스 상태 확인"""
        return service_name in self.healthy_services
    
    def get_service_url(self, service_name: str) -> str:
        """서비스 URL 조회"""
        if service_name not in SERVICES:
            raise ValueError(f"Unknown service: {service_name}")
        return SERVICES[service_name]["url"]

# 전역 인스턴스
rate_limiter = RateLimiter()
cache_manager = CacheManager()
service_discovery = ServiceDiscovery()

# 인증 관리
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
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
            "permissions": payload.get("permissions", [])
        }
    except jwt.InvalidTokenError:
        return {"user_type": "anonymous", "client_id": "anonymous"}

# 미들웨어
@app.middleware("http")
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
    
    if not rate_limiter.is_allowed(client_ip, endpoint_type):
        return Response(
            content=json.dumps({"error": "Rate limit exceeded"}),
            status_code=429,
            headers={"Content-Type": "application/json"}
        )
    
    response = await call_next(request)
    return response

@app.middleware("http")
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

# 프록시 함수
async def proxy_request(
    service_name: str,
    path: str,
    request: Request,
    method: str = "GET",
    use_cache: bool = False,
    cache_category: str = "default"
) -> Dict[str, Any]:
    """서비스로 요청 프록시"""
    
    # 서비스 상태 확인
    if not service_discovery.is_service_healthy(service_name):
        raise HTTPException(
            status_code=503,
            detail=f"Service {service_name} is unavailable"
        )
    
    # 캐시 확인
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
        async with httpx.AsyncClient(timeout=SERVICES[service_name]["timeout"]) as client:
            if method == "GET":
                response = await client.get(target_url)
            elif method == "POST":
                body = await request.body()
                response = await client.post(
                    target_url,
                    content=body,
                    headers={"Content-Type": request.headers.get("content-type", "application/json")}
                )
            elif method == "PUT":
                body = await request.body()
                response = await client.put(
                    target_url,
                    content=body,
                    headers={"Content-Type": request.headers.get("content-type", "application/json")}
                )
            elif method == "DELETE":
                response = await client.delete(target_url)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
            
            response.raise_for_status()
            result = response.json()
            
            # 캐시 저장
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

# API 엔드포인트
@app.get("/health")
async def gateway_health():
    """게이트웨이 헬스 체크"""
    await service_discovery.health_check()
    
    service_status = {}
    for service_name in SERVICES.keys():
        service_status[service_name] = {
            "healthy": service_discovery.is_service_healthy(service_name),
            "last_check": service_discovery.last_health_check.get(service_name)
        }
    
    return {
        "status": "healthy",
        "service": "api-gateway",
        "timestamp": datetime.utcnow(),
        "services": service_status
    }

# 수집 서비스 라우팅
@app.get("/api/v1/collection/status")
async def get_collection_status(request: Request, auth: Dict = Depends(verify_token)):
    """수집 상태 조회"""
    return await proxy_request("collection", "/api/v1/status", request, use_cache=True, cache_category="statistics")

@app.post("/api/v1/collection/trigger")
async def trigger_collection(request: Request, auth: Dict = Depends(verify_token)):
    """데이터 수집 트리거"""
    if auth["user_type"] == "anonymous":
        raise HTTPException(status_code=401, detail="Authentication required")
    
    return await proxy_request("collection", "/api/v1/collect", request, method="POST")

@app.put("/api/v1/collection/sources/{source}/enable")
async def enable_collection_source(source: str, request: Request, auth: Dict = Depends(verify_token)):
    """수집 소스 활성화"""
    if auth["user_type"] not in ["admin", "user"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return await proxy_request("collection", f"/api/v1/sources/{source}/enable", request, method="PUT")

# 블랙리스트 서비스 라우팅
@app.get("/api/v1/blacklist/active")
async def get_active_blacklist(request: Request):
    """활성 블랙리스트 조회 (공개 API)"""
    return await proxy_request("blacklist", "/api/v1/active-ips", request, use_cache=True)

@app.get("/api/v1/blacklist/fortigate")
async def get_fortigate_format(request: Request):
    """FortiGate 형식 조회"""
    return await proxy_request("blacklist", "/api/v1/fortigate", request, use_cache=True, cache_category="fortigate")

@app.get("/api/v1/blacklist/search/{ip}")
async def search_ip(ip: str, request: Request):
    """IP 검색"""
    return await proxy_request("blacklist", f"/api/v1/ips/{ip}", request)

@app.post("/api/v1/blacklist/search")
async def search_batch(request: Request):
    """배치 IP 검색"""
    return await proxy_request("blacklist", "/api/v1/search", request, method="POST")

@app.get("/api/v1/blacklist/statistics")
async def get_blacklist_statistics(request: Request):
    """블랙리스트 통계"""
    return await proxy_request("blacklist", "/api/v1/statistics", request, use_cache=True, cache_category="statistics")

# 분석 서비스 라우팅
@app.get("/api/v1/analytics/trends")
async def get_analytics_trends(request: Request):
    """트렌드 분석"""
    return await proxy_request("analytics", "/api/v1/trends", request, use_cache=True, cache_category="trends")

@app.get("/api/v1/analytics/geographic")
async def get_geographic_distribution(request: Request):
    """지리적 분포"""
    return await proxy_request("analytics", "/api/v1/geographic", request, use_cache=True, cache_category="trends")

@app.get("/api/v1/analytics/threat-types")
async def get_threat_types(request: Request):
    """위협 유형 분석"""
    return await proxy_request("analytics", "/api/v1/threat-types", request, use_cache=True, cache_category="trends")

@app.get("/api/v1/analytics/report")
async def get_analytics_report(request: Request):
    """종합 분석 리포트"""
    return await proxy_request("analytics", "/api/v1/report", request, use_cache=True, cache_category="trends")

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
    
    await service_discovery.health_check()
    
    services_info = {}
    for service_name, config in SERVICES.items():
        services_info[service_name] = {
            "url": config["url"],
            "healthy": service_discovery.is_service_healthy(service_name),
            "last_check": service_discovery.last_health_check.get(service_name),
            "timeout": config["timeout"]
        }
    
    return {"services": services_info}

@app.post("/admin/cache/clear")
async def clear_cache(auth: Dict = Depends(verify_token)):
    """캐시 클리어 (관리자)"""
    if auth["user_type"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    cache_manager.cache.clear()
    return {"status": "success", "message": "Cache cleared"}

@app.get("/admin/metrics")
async def get_gateway_metrics(auth: Dict = Depends(verify_token)):
    """게이트웨이 메트릭 (관리자)"""
    if auth["user_type"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {
        "cache_size": len(cache_manager.cache),
        "rate_limiter_clients": len(rate_limiter.requests),
        "healthy_services": list(service_discovery.healthy_services),
        "uptime": "00:00:00"  # 실제로는 시작 시간부터 계산
    }

# 백그라운드 태스크
@app.on_event("startup")
async def startup_event():
    """시작 시 초기화"""
    logger.info("API Gateway starting up...")
    await service_discovery.health_check()
    
    # 주기적 헬스 체크 시작
    asyncio.create_task(periodic_health_check())

async def periodic_health_check():
    """주기적 헬스 체크"""
    while True:
        try:
            await service_discovery.health_check()
            await asyncio.sleep(30)  # 30초마다 체크
        except Exception as e:
            logger.error(f"Health check error: {e}")
            await asyncio.sleep(30)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)