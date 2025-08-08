#!/usr/bin/env python3
"""
MSA Test Configuration and Data Classes

Extracted from msa_comprehensive_integration_test.py for better organization.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ServiceConfig:
    """서비스 설정"""

    name: str
    url: str
    port: int
    health_endpoint: str
    timeout: int = 30


@dataclass
class TestResult:
    """테스트 결과"""

    name: str
    passed: bool
    response_time: float
    error_message: Optional[str] = None
    status_code: Optional[int] = None
    response_data: Optional[Dict] = None


class MSAServiceConfigs:
    """MSA 서비스 설정 관리"""

    @staticmethod
    def get_default_services():
        """기본 서비스 설정 반환"""
        return {
            "api_gateway": ServiceConfig(
                name="API Gateway",
                url="http://localhost:8080",
                port=8080,
                health_endpoint="/health",
            ),
            "collection_service": ServiceConfig(
                name="Collection Service",
                url="http://localhost:8000",
                port=8000,
                health_endpoint="/health",
            ),
            "blacklist_service": ServiceConfig(
                name="Blacklist Service",
                url="http://localhost:8001",
                port=8001,
                health_endpoint="/health",
            ),
            "analytics_service": ServiceConfig(
                name="Analytics Service",
                url="http://localhost:8002",
                port=8002,
                health_endpoint="/health",
            ),
        }

    @staticmethod
    def get_test_routes():
        """테스트 라우트 설정 반환"""
        return [
            {
                "name": "Gateway Health Check",
                "url": "/health",
                "expected_status": 200,
                "description": "API Gateway 자체 헬스체크",
            },
            {
                "name": "Collection Service via Gateway",
                "url": "/api/v1/collection/status",
                "expected_status": [200, 503],
                "description": "Gateway를 통한 Collection Service 라우팅",
            },
            {
                "name": "Blacklist Service via Gateway",
                "url": "/api/v1/blacklist/statistics",
                "expected_status": [200, 503],
                "description": "Gateway를 통한 Blacklist Service 라우팅",
            },
            {
                "name": "Analytics Service via Gateway",
                "url": "/api/v1/analytics/realtime",
                "expected_status": [200, 503],
                "description": "Gateway를 통한 Analytics Service 라우팅",
            },
        ]

    @staticmethod
    def get_performance_tests():
        """성능 테스트 설정 반환"""
        return [
            {
                "name": "Gateway Response Time",
                "endpoint": "/health",
                "target_time": 0.5,
                "requests": 10,
            },
            {
                "name": "Blacklist Query Performance",
                "endpoint": "/api/v1/blacklist/active",
                "target_time": 2.0,
                "requests": 5,
            },
            {
                "name": "Analytics Performance",
                "endpoint": "/api/v1/analytics/realtime",
                "target_time": 3.0,
                "requests": 3,
            },
        ]
