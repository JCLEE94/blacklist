#!/usr/bin/env python3
"""
MSA 아키텍처 최종 통합 테스트 리포트 생성기
모든 테스트 결과를 종합하여 최종 평가 리포트 생성
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from typing import Any, Dict, List

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MSAFinalReportGenerator:
    """MSA 최종 리포트 생성기"""

    def __init__(self):
        self.services = {
            "API Gateway": "http://localhost:8080",
            "Collection Service": "http://localhost:8000",
            "Blacklist Service": "http://localhost:8001",
            "Analytics Service": "http://localhost:8002",
        }

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
                    response = await client.get(f"{base_url}/health")
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
                            "error": f"HTTP {response.status_code}",
                        }
            except Exception as e:
                system_info["services"][service_name] = {
                    "status": "error",
                    "url": base_url,
                    "error": str(e),
                }

        self.system_info = system_info

    async def run_quick_health_check(self):
        """빠른 헬스체크 실행"""
        print("🏥 빠른 헬스체크 실행 중...")

        health_results = {}

        for service_name, base_url in self.services.items():
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(f"{base_url}/health")
                    response_time = time.time() - start_time

                    health_results[service_name] = {
                        "status": "healthy"
                        if response.status_code == 200
                        else "unhealthy",
                        "response_time": response_time,
                        "http_status": response.status_code,
                    }
            except Exception as e:
                response_time = time.time() - start_time
                health_results[service_name] = {
                    "status": "error",
                    "response_time": response_time,
                    "error": str(e),
                }

        self.test_results["health_check"] = health_results

    async def test_api_gateway_functionality(self):
        """API Gateway 기능 테스트"""
        print("🚪 API Gateway 기능 테스트 중...")

        gateway_url = self.services["API Gateway"]
        gateway_tests = {}

        # 핵심 라우팅 테스트
        routing_tests = [
            ("collection_status", f"{gateway_url}/api/v1/collection/status"),
            ("blacklist_active", f"{gateway_url}/api/v1/blacklist/active"),
            ("blacklist_statistics", f"{gateway_url}/api/v1/blacklist/statistics"),
            ("analytics_realtime", f"{gateway_url}/api/v1/analytics/realtime"),
            ("fortigate_format", f"{gateway_url}/api/v1/blacklist/fortigate"),
        ]

        for test_name, url in routing_tests:
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    response = await client.get(url)
                    response_time = time.time() - start_time

                    gateway_tests[test_name] = {
                        "status": "success"
                        if response.status_code == 200
                        else "failed",
                        "response_time": response_time,
                        "http_status": response.status_code,
                        "data_size": len(response.content) if response.content else 0,
                    }
            except Exception as e:
                response_time = time.time() - start_time
                gateway_tests[test_name] = {
                    "status": "error",
                    "response_time": response_time,
                    "error": str(e),
                }

        self.test_results["api_gateway"] = gateway_tests

    async def test_service_integration(self):
        """서비스 간 통합 테스트"""
        print("🔗 서비스 간 통합 테스트 중...")

        integration_tests = {}

        # 데이터 흐름 테스트
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                # 1. Collection Status 확인
                collection_response = await client.get(
                    f"{self.services['API Gateway']}/api/v1/collection/status"
                )

                # 2. Blacklist Statistics 확인
                blacklist_response = await client.get(
                    f"{self.services['API Gateway']}/api/v1/blacklist/statistics"
                )

                # 3. Analytics 확인
                analytics_response = await client.get(
                    f"{self.services['API Gateway']}/api/v1/analytics/realtime"
                )

                integration_tests["data_flow"] = {
                    "collection_status": collection_response.status_code,
                    "blacklist_stats": blacklist_response.status_code,
                    "analytics_realtime": analytics_response.status_code,
                    "overall_success": all(
                        r.status_code == 200
                        for r in [
                            collection_response,
                            blacklist_response,
                            analytics_response,
                        ]
                    ),
                }

        except Exception as e:
            integration_tests["data_flow"] = {"overall_success": False, "error": str(e)}

        self.test_results["integration"] = integration_tests

    async def measure_performance_metrics(self):
        """성능 메트릭 측정"""
        print("⚡ 성능 메트릭 측정 중...")

        metrics = {}

        # 주요 엔드포인트 성능 테스트
        performance_endpoints = [
            ("gateway_health", f"{self.services['API Gateway']}/health"),
            (
                "blacklist_active",
                f"{self.services['API Gateway']}/api/v1/blacklist/active",
            ),
            (
                "analytics_realtime",
                f"{self.services['API Gateway']}/api/v1/analytics/realtime",
            ),
        ]

        for endpoint_name, url in performance_endpoints:
            response_times = []
            success_count = 0

            # 10회 테스트
            for _ in range(10):
                start_time = time.time()
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        response = await client.get(url)
                        response_time = time.time() - start_time
                        response_times.append(response_time)

                        if response.status_code == 200:
                            success_count += 1

                except Exception:
                    response_time = time.time() - start_time
                    response_times.append(response_time)

            if response_times:
                metrics[endpoint_name] = {
                    "avg_response_time": sum(response_times) / len(response_times),
                    "min_response_time": min(response_times),
                    "max_response_time": max(response_times),
                    "success_rate": (success_count / 10) * 100,
                    "total_tests": 10,
                }

        self.performance_metrics = metrics

    def generate_final_report(self):
        """최종 리포트 생성"""
        print("\n" + "=" * 100)
        print("🏗️  MSA 아키텍처 최종 통합 테스트 리포트")
        print("=" * 100)

        # 시스템 개요
        print(f"\n📋 시스템 개요:")
        print(f"   • 테스트 일시: {self.system_info['test_timestamp']}")
        print(f"   • 아키텍처: {self.system_info['architecture']}")
        print(f"   • 배포 방식: {self.system_info['deployment_method']}")
        print(f"   • 서비스 수: {len(self.services)}개")

        # 인프라 정보
        print(f"\n🏗️  인프라 구성:")
        for component, version in self.system_info["infrastructure"].items():
            print(f"   • {component.replace('_', ' ').title()}: {version}")

        # 서비스 상태
        print(f"\n🏥 서비스 상태 요약:")
        healthy_services = 0
        total_services = len(self.services)

        for service_name, service_info in self.system_info["services"].items():
            status_emoji = "✅" if service_info["status"] == "healthy" else "❌"
            print(f"   {status_emoji} {service_name}: {service_info['status']}")

            if service_info["status"] == "healthy":
                healthy_services += 1
                print(f"      URL: {service_info['url']}")
                print(f"      응답시간: {service_info['response_time']:.3f}초")

        system_health_rate = (healthy_services / total_services) * 100
        print(
            f"\n   📊 전체 서비스 가용성: {system_health_rate:.1f}% ({healthy_services}/{total_services})"
        )

        # API Gateway 테스트 결과
        if "api_gateway" in self.test_results:
            print(f"\n🚪 API Gateway 테스트 결과:")
            gateway_results = self.test_results["api_gateway"]
            successful_routes = sum(
                1
                for result in gateway_results.values()
                if result["status"] == "success"
            )
            total_routes = len(gateway_results)

            print(f"   • 라우팅 테스트: {successful_routes}/{total_routes} 성공")

            for test_name, result in gateway_results.items():
                status_emoji = "✅" if result["status"] == "success" else "❌"
                print(
                    f"   {status_emoji} {test_name.replace('_', ' ').title()}: {result['response_time']:.3f}초"
                )

        # 성능 메트릭
        if self.performance_metrics:
            print(f"\n⚡ 성능 메트릭:")

            avg_response_times = []
            for endpoint_name, metrics in self.performance_metrics.items():
                avg_response_times.append(metrics["avg_response_time"])
                print(f"   • {endpoint_name.replace('_', ' ').title()}:")
                print(f"     - 평균 응답시간: {metrics['avg_response_time']:.3f}초")
                print(
                    f"     - 최소/최대: {metrics['min_response_time']:.3f}s / {metrics['max_response_time']:.3f}s"
                )
                print(f"     - 성공률: {metrics['success_rate']:.1f}%")

            if avg_response_times:
                overall_avg = sum(avg_response_times) / len(avg_response_times)
                print(f"\n   📈 전체 평균 응답시간: {overall_avg:.3f}초")

        # 통합 테스트 결과
        if "integration" in self.test_results:
            print(f"\n🔗 서비스 간 통합 테스트:")
            integration_result = self.test_results["integration"]["data_flow"]

            if integration_result.get("overall_success", False):
                print(f"   ✅ 전체 데이터 흐름 테스트 성공")
                print(
                    f"   • Collection Service: HTTP {integration_result.get('collection_status', 'N/A')}"
                )
                print(
                    f"   • Blacklist Service: HTTP {integration_result.get('blacklist_stats', 'N/A')}"
                )
                print(
                    f"   • Analytics Service: HTTP {integration_result.get('analytics_realtime', 'N/A')}"
                )
            else:
                print(f"   ❌ 통합 테스트 실패")
                if "error" in integration_result:
                    print(f"      오류: {integration_result['error']}")

        # 최종 평가
        print(f"\n" + "=" * 100)
        print("🎯 최종 평가 및 권장사항")
        print("=" * 100)

        # 종합 점수 계산
        scores = []

        # 서비스 가용성 점수 (40%)
        availability_score = system_health_rate * 0.4
        scores.append(availability_score)

        # API Gateway 라우팅 점수 (30%)
        if "api_gateway" in self.test_results:
            gateway_success_rate = (successful_routes / total_routes) * 100
            routing_score = gateway_success_rate * 0.3
            scores.append(routing_score)

        # 성능 점수 (30%)
        if self.performance_metrics:
            # 100ms 이하면 만점, 500ms 이상이면 0점
            performance_scores = []
            for metrics in self.performance_metrics.values():
                if metrics["avg_response_time"] <= 0.1:
                    performance_scores.append(100)
                elif metrics["avg_response_time"] >= 0.5:
                    performance_scores.append(0)
                else:
                    # 선형 보간
                    score = 100 - ((metrics["avg_response_time"] - 0.1) / 0.4) * 100
                    performance_scores.append(max(0, score))

            if performance_scores:
                avg_performance_score = sum(performance_scores) / len(
                    performance_scores
                )
                performance_weight_score = avg_performance_score * 0.3
                scores.append(performance_weight_score)

        overall_score = sum(scores) if scores else 0

        print(f"📊 종합 점수: {overall_score:.1f}/100")

        # 등급 판정
        if overall_score >= 90:
            grade = "A (우수)"
            grade_emoji = "🌟"
            status_message = "MSA 아키텍처가 프로덕션 환경에서 안정적으로 운영될 준비가 완료되었습니다."
        elif overall_score >= 80:
            grade = "B (양호)"
            grade_emoji = "✅"
            status_message = "MSA 아키텍처가 기본 요구사항을 충족하며, 일부 최적화로 더 나은 성능을 얻을 수 있습니다."
        elif overall_score >= 70:
            grade = "C (보통)"
            grade_emoji = "⚠️"
            status_message = "MSA 아키텍처가 기본적으로 작동하지만, 몇 가지 개선사항이 필요합니다."
        else:
            grade = "D (개선 필요)"
            grade_emoji = "❌"
            status_message = "MSA 아키텍처에 중요한 문제가 있어 개선이 필요합니다."

        print(f"🏆 시스템 등급: {grade_emoji} {grade}")
        print(f"\n💡 상태: {status_message}")

        # 구체적 권장사항
        print(f"\n📋 권장사항:")

        recommendations = []

        if system_health_rate < 100:
            recommendations.append("• 일부 서비스의 헬스체크 실패 - 서비스 상태 점검 필요")

        if self.performance_metrics:
            slow_endpoints = [
                name
                for name, metrics in self.performance_metrics.items()
                if metrics["avg_response_time"] > 0.2
            ]
            if slow_endpoints:
                recommendations.append(f"• 응답 시간 개선 필요: {', '.join(slow_endpoints)}")

        if "api_gateway" in self.test_results:
            failed_routes = [
                name
                for name, result in self.test_results["api_gateway"].items()
                if result["status"] != "success"
            ]
            if failed_routes:
                recommendations.append(
                    f"• API Gateway 라우팅 문제: {', '.join(failed_routes)}"
                )

        if not recommendations:
            recommendations = [
                "• 모든 시스템이 정상 작동 중입니다",
                "• 정기적인 모니터링 및 백업 수행 권장",
                "• 부하 증가에 대비한 스케일링 계획 수립",
                "• 보안 강화를 위한 정기적인 업데이트",
            ]

        for recommendation in recommendations:
            print(f"   {recommendation}")

        # MSA 특화 권장사항
        print(f"\n🏗️  MSA 운영 권장사항:")
        print(f"   • 서비스 메시 (Istio/Envoy) 도입으로 고급 트래픽 관리")
        print(f"   • 분산 트레이싱 (Jaeger/Zipkin) 구성으로 서비스 간 호출 추적")
        print(f"   • 중앙집중식 로깅 (ELK Stack) 구성")
        print(f"   • 서비스별 독립적인 CI/CD 파이프라인 구축")
        print(f"   • 카나리 배포 및 블루-그린 배포 전략 수립")
        print(f"   • 서비스별 SLA 및 모니터링 대시보드 구성")

        print(f"\n" + "=" * 100)
        print(f"✨ MSA 통합 테스트 완료 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   테스트된 서비스: {len(self.services)}개")
        print(f"   전체 가용성: {system_health_rate:.1f}%")
        print(f"   종합 점수: {overall_score:.1f}/100 ({grade})")
        print("=" * 100)

        return overall_score >= 70  # 70점 이상이면 성공


async def main():
    """메인 실행 함수"""
    print("🚀 MSA 아키텍처 최종 통합 테스트 리포트를 생성합니다...")
    print("   모든 MSA 서비스가 실행 중인지 확인하세요.")
    print()

    generator = MSAFinalReportGenerator()

    try:
        # 시스템 정보 수집
        await generator.collect_system_information()

        # 헬스체크 실행
        await generator.run_quick_health_check()

        # API Gateway 기능 테스트
        await generator.test_api_gateway_functionality()

        # 서비스 간 통합 테스트
        await generator.test_service_integration()

        # 성능 메트릭 측정
        await generator.measure_performance_metrics()

        # 최종 리포트 생성
        success = generator.generate_final_report()

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n⏹️  테스트가 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 리포트 생성 중 오류 발생: {e}")
        logger.exception("Report generation failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
