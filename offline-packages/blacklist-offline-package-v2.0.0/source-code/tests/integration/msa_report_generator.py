#!/usr/bin/env python3
"""
MSA Report Generation Logic

Extracted from msa_final_integration_report.py for better organization.
"""

import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


class MSAReportGenerator:
    """MSA 최종 리포트 생성기"""

    def __init__(self):
        self.services = {
            "API Gateway": "http://localhost:8080",
            "Collection Service": "http://localhost:8000",
            "Blacklist Service": "http://localhost:8001",
            "Analytics Service": "http://localhost:8002",
        }

        self.system_info = {}
        self.test_results = {}
        self.performance_metrics = {}

    async def collect_system_information(self):
        """시스템 정보 수집"""
        print("📊 시스템 정보 수집 중...")

        system_info = {
            "test_timestamp": datetime.now().isoformat(),
            "architecture": "Microservices Architecture (MSA)",
            "deployment_method": "Docker Compose",
            "services": {},
            "infrastructure": {
                "database": "PostgreSQL 15",
                "cache": "Redis 7",
                "api_gateway": "FastAPI + Python",
                "load_balancer": "API Gateway with Rate Limiting",
                "monitoring": "Built-in Health Checks",
            },
        }

        # 각 서비스 정보 수집
        for service_name, base_url in self.services.items():
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get("{base_url}/health")
                    if response.status_code == 200:
                        health_data = response.json()
                        system_info["services"][service_name] = {
                            "status": "healthy",
                            "url": base_url,
                            "response_time": response.elapsed.total_seconds(),
                            "details": health_data,
                        }
                    else:
                        system_info["services"][service_name] = {
                            "status": "unhealthy",
                            "url": base_url,
                            "error": "HTTP {response.status_code}",
                        }
            except Exception as e:
                system_info["services"][service_name] = {
                    "status": "error",
                    "url": base_url,
                    "error": str(e),
                }

        self.system_info = system_info

    async def run_health_checks(self):
        """Health check tests"""
        print("🏥 Health check 실행 중...")

        health_results = {}

        for service_name, base_url in self.services.items():
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get("{base_url}/health")
                    health_results[service_name] = {
                        "status": (
                            "healthy" if response.status_code == 200 else "unhealthy"
                        ),
                        "response_time": response.elapsed.total_seconds(),
                        "http_status": response.status_code,
                    }
            except Exception as e:
                health_results[service_name] = {
                    "status": "error",
                    "error": str(e),
                }

        self.test_results["health_check"] = health_results

    async def test_api_gateway_functionality(self):
        """API Gateway 기능 테스트"""
        print("🚪 API Gateway 기능 테스트 중...")

        gateway_url = self.services["API Gateway"]
        gateway_tests = {}

        routing_tests = [
            ("collection_status", "{gateway_url}/api/v1/collection/status"),
            ("blacklist_active", "{gateway_url}/api/v1/blacklist/active"),
            ("blacklist_statistics", "{gateway_url}/api/v1/blacklist/statistics"),
            ("analytics_realtime", "{gateway_url}/api/v1/analytics/realtime"),
            ("fortigate_format", "{gateway_url}/api/v1/blacklist/fortigate"),
        ]

        for test_name, url in routing_tests:
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    response = await client.get(url)
                    gateway_tests[test_name] = {
                        "status": (
                            "success" if response.status_code == 200 else "failed"
                        ),
                        "response_time": response.elapsed.total_seconds(),
                        "http_status": response.status_code,
                        "data_size": len(response.content) if response.content else 0,
                    }
            except Exception as e:
                gateway_tests[test_name] = {
                    "status": "error",
                    "error": str(e),
                }

        self.test_results["api_gateway"] = gateway_tests

    async def measure_performance_metrics(self):
        """Performance metrics measurement"""
        print("⚡ 성능 메트릭 측정 중...")

        metrics = {}

        performance_endpoints = [
            ("gateway_health", "{self.services['API Gateway']}/health"),
            (
                "blacklist_active",
                "{self.services['API Gateway']}/api/v1/blacklist/active",
            ),
            (
                "analytics_realtime",
                "{self.services['API Gateway']}/api/v1/analytics/realtime",
            ),
        ]

        for endpoint_name, url in performance_endpoints:
            response_times = []
            success_count = 0

            for _ in range(5):  # Reduced from 10 to 5 for faster execution
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        response = await client.get(url)
                        response_times.append(response.elapsed.total_seconds())
                        if response.status_code == 200:
                            success_count += 1
                except Exception as e:
                    pass

            if response_times:
                metrics[endpoint_name] = {
                    "avg_response_time": sum(response_times) / len(response_times),
                    "min_response_time": min(response_times),
                    "max_response_time": max(response_times),
                    "success_rate": (success_count / 5) * 100,
                    "total_tests": 5,
                }

        self.performance_metrics = metrics

    def calculate_overall_score(self):
        """Calculate overall system score"""
        scores = []

        # Service availability score (40%)
        if self.system_info:
            healthy_count = sum(
                1
                for s in self.system_info["services"].values()
                if s["status"] == "healthy"
            )
            total_count = len(self.system_info["services"])
            availability_score = (
                (healthy_count / total_count) * 40 if total_count > 0 else 0
            )
            scores.append(availability_score)

        # API Gateway routing score (30%)
        if "api_gateway" in self.test_results:
            successful_routes = sum(
                1
                for r in self.test_results["api_gateway"].values()
                if r["status"] == "success"
            )
            total_routes = len(self.test_results["api_gateway"])
            routing_score = (
                (successful_routes / total_routes) * 30 if total_routes > 0 else 0
            )
            scores.append(routing_score)

        # Performance score (30%)
        if self.performance_metrics:
            perf_scores = []
            for metrics in self.performance_metrics.values():
                if metrics["avg_response_time"] <= 0.1:
                    perf_scores.append(100)
                elif metrics["avg_response_time"] >= 0.5:
                    perf_scores.append(0)
                else:
                    score = 100 - ((metrics["avg_response_time"] - 0.1) / 0.4) * 100
                    perf_scores.append(max(0, score))

            if perf_scores:
                avg_perf_score = sum(perf_scores) / len(perf_scores)
                performance_score = avg_perf_score * 0.3
                scores.append(performance_score)

        return sum(scores) if scores else 0
