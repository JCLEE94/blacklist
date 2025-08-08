#!/usr/bin/env python3
"""
API Gateway Service Discovery

Extracted from app.py for better organization.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Set

import httpx

logger = logging.getLogger(__name__)


class ServiceDiscovery:
    """서비스 디스커버리"""

    def __init__(self, services: Dict[str, str]):
        self.services = services
        self.healthy_services: Set[str] = set()
        self.last_health_check = {}

    async def health_check(self):
        """모든 서비스 헬스 체크 - 성능 최적화 버전"""
        # 캠시에서 최근 헬스체크 결과 확인 (30초 TTL)
        from . import cache_manager

        cache_key = "service_health_check_v2"
        cached_health = cache_manager.get(cache_key)
        if cached_health:
            self.healthy_services = cached_health.get("healthy_services", set())
            self.last_health_check = cached_health.get("last_health_check", {})
            logger.debug("Service health check returned from cache")
            return

        # 동시 헬스체크 (병렬 처리)
        async def check_single_service(service_name: str, base_url: str):
            """단일 서비스 헬스체크"""
            try:
                async with httpx.AsyncClient(timeout=3) as client:
                    response = await client.get(f"{base_url}/health")
                    if response.status_code == 200:
                        return service_name, True
                    else:
                        logger.warning(
                            f"Health check failed for {service_name}: status {response.status_code}"
                        )
                        return service_name, False
            except asyncio.TimeoutError:
                logger.warning(f"Health check timeout for {service_name}")
                return service_name, False
            except Exception as e:
                logger.warning(f"Health check failed for {service_name}: {e}")
                return service_name, False

        # 모든 서비스를 병렬로 체크
        tasks = [
            check_single_service(service_name, base_url)
            for service_name, base_url in self.services.items()
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

            # 결과를 캠시에 저장
            health_data = {
                "healthy_services": self.healthy_services,
                "last_health_check": self.last_health_check,
            }
            cache_manager.set(cache_key, health_data, "health")

            logger.info(
                f"Health check completed: {len(new_healthy_services)}/{len(self.services)} services healthy"
            )

        except Exception as e:
            logger.error(f"Health check batch failed: {e}")

    def is_service_healthy(self, service_name: str) -> bool:
        """서비스 상태 확인"""
        return service_name in self.healthy_services

    def get_service_url(self, service_name: str) -> str:
        """서비스 URL 조회"""
        if service_name not in self.services:
            raise ValueError(f"Unknown service: {service_name}")
        return self.services[service_name]
