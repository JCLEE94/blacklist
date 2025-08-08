# \!/usr/bin/env python3
"""
API Gateway - Simplified and Modularized

Refactored from original 600-line app.py for better organization.
Core functionality moved to specialized modules.
"""

import asyncio
import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Blacklist API Gateway",
    description="마이크로서비스 통합 API 게이트웨이",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Service configuration
SERVICES = {
    "collection": {
        "url": os.getenv("COLLECTION_SERVICE_URL", "http://collection-service:8000"),
        "health_endpoint": "/health",
        "timeout": 30,
    },
    "blacklist": {
        "url": os.getenv("BLACKLIST_SERVICE_URL", "http://blacklist-service:8001"),
        "health_endpoint": "/health",
        "timeout": 30,
    },
    "analytics": {
        "url": os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:8002"),
        "health_endpoint": "/health",
        "timeout": 30,
    },
}

# Initialize core components
try:
    from .middleware import CacheManager, RateLimiter
    from .service_discovery import ServiceDiscovery

    rate_limiter = RateLimiter()
    cache_manager = CacheManager()
    service_discovery = ServiceDiscovery(
        {name: config["url"] for name, config in SERVICES.items()}
    )

    # Import and register routes after initializing components
    from .routes import register_routes

    register_routes(app)

except ImportError as e:
    logger.warning(f"Could not import modular components: {e}")
    logger.info("Falling back to basic health check only")

    from datetime import datetime

    @app.get("/health")
    async def basic_health():
        """Basic health check fallback"""
        return {
            "status": "healthy",
            "service": "api-gateway",
            "timestamp": datetime.utcnow(),
            "mode": "fallback",
        }


# Background tasks
@app.on_event("startup")
async def startup_event():
    """시작 시 초기화"""
    logger.info("API Gateway starting up...")

    try:
        await service_discovery.health_check()
        # 주기적 헬스 체크 시작
        asyncio.create_task(periodic_health_check())
    except Exception as e:
        logger.error(f"Startup failed: {e}")


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
