#!/usr/bin/env python3
"""
MSA Report Formatting and Output

Extracted from msa_final_integration_report.py for better organization.
"""

from datetime import datetime
from typing import Dict


class MSAReportFormatter:
    """MSA 리포트 포맷터"""

    @staticmethod
    def format_final_report(
        system_info: Dict,
        test_results: Dict,
        performance_metrics: Dict,
        overall_score: float,
    ) -> bool:
        """최종 리포트 생성 및 출력"""
        print("\n" + "=" * 100)
        print("🏗️  MSA 아키텍처 최종 통합 테스트 리포트")
        print("=" * 100)

        # 시스템 개요
        print("\n📋 시스템 개요:")
        print(f"   • 테스트 일시: {system_info.get('test_timestamp', 'N/A')}")
        print(f"   • 아키텍처: {system_info.get('architecture', 'N/A')}")
        print(f"   • 배포 방식: {system_info.get('deployment_method', 'N/A')}")
        print(f"   • 서비스 수: {len(system_info.get('services', {}))}개")

        # 인프라 정보
        if "infrastructure" in system_info:
            print("\n🏗️  인프라 구성:")
            for component, version in system_info["infrastructure"].items():
                print(f"   • {component.replace('_', ' ').title()}: {version}")

        # 서비스 상태
        MSAReportFormatter._format_service_status(system_info)

        # API Gateway 테스트 결과
        MSAReportFormatter._format_api_gateway_results(test_results)

        # 성능 메트릭
        MSAReportFormatter._format_performance_metrics(performance_metrics)

        # 최종 평가
        return MSAReportFormatter._format_final_evaluation(overall_score, system_info)

    @staticmethod
    def _format_service_status(system_info: Dict):
        """서비스 상태 포맷팅"""
        services = system_info.get("services", {})
        if not services:
            return

        print("\n🏥 서비스 상태 요약:")
        healthy_services = 0
        total_services = len(services)

        for service_name, service_info in services.items():
            status_emoji = "✅" if service_info["status"] == "healthy" else "❌"
            print(f"   {status_emoji} {service_name}: {service_info['status']}")

            if service_info["status"] == "healthy":
                healthy_services += 1
                print(f"      URL: {service_info['url']}")
                print(f"      응답시간: {service_info['response_time']:.3f}초")

        system_health_rate = (healthy_services / total_services) * 100
        print(
            "\n   📊 전체 서비스 가용성: {system_health_rate:.1f}% ({healthy_services}/{total_services})"
        )

    @staticmethod
    def _format_api_gateway_results(test_results: Dict):
        """API Gateway 테스트 결과 포맷팅"""
        if "api_gateway" not in test_results:
            return

        print("\n🚪 API Gateway 테스트 결과:")
        gateway_results = test_results["api_gateway"]
        successful_routes = sum(
            1 for result in gateway_results.values() if result["status"] == "success"
        )
        total_routes = len(gateway_results)

        print(f"   • 라우팅 테스트: {successful_routes}/{total_routes} 성공")

        for test_name, result in gateway_results.items():
            status_emoji = "✅" if result["status"] == "success" else "❌"
            print(
                "   {status_emoji} {test_name.replace('_', ' ').title()}: {result['response_time']:.3f}초"
            )

    @staticmethod
    def _format_performance_metrics(performance_metrics: Dict):
        """성능 메트릭 포맷팅"""
        if not performance_metrics:
            return

        print("\n⚡ 성능 메트릭:")

        avg_response_times = []
        for endpoint_name, metrics in performance_metrics.items():
            avg_response_times.append(metrics["avg_response_time"])
            print(f"   • {endpoint_name.replace('_', ' ').title()}:")
            print(f"     - 평균 응답시간: {metrics['avg_response_time']:.3f}초")
            print(
                "     - 최소/최대: {metrics['min_response_time']:.3f}s / {metrics['max_response_time']:.3f}s"
            )
            print(f"     - 성공률: {metrics['success_rate']:.1f}%")

        if avg_response_times:
            overall_avg = sum(avg_response_times) / len(avg_response_times)
            print(f"\n   📈 전체 평균 응답시간: {overall_avg:.3f}초")

    @staticmethod
    def _format_final_evaluation(overall_score: float, system_info: Dict) -> bool:
        """최종 평가 포맷팅"""
        print("\n" + "=" * 100)
        print("🎯 최종 평가 및 권장사항")
        print("=" * 100)

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
            status_message = (
                "MSA 아키텍처가 기본적으로 작동하지만, 몇 가지 개선사항이 필요합니다."
            )
        else:
            grade = "D (개선 필요)"
            grade_emoji = "❌"
            status_message = "MSA 아키텍처에 중요한 문제가 있어 개선이 필요합니다."

        print(f"🏆 시스템 등급: {grade_emoji} {grade}")
        print(f"\n💡 상태: {status_message}")

        # 권장사항
        MSAReportFormatter._format_recommendations(overall_score)

        # MSA 특화 권장사항
        MSAReportFormatter._format_msa_recommendations()

        # 요약
        MSAReportFormatter._format_summary(overall_score, grade, system_info)

        return overall_score >= 70

    @staticmethod
    def _format_recommendations(overall_score: float):
        """권장사항 포맷팅"""
        print("\n📋 권장사항:")

        recommendations = []

        if overall_score < 80:
            recommendations.extend(
                [
                    "• 서비스 헬스체크 개선 필요",
                    "• 응답 시간 최적화 검토",
                    "• API Gateway 라우팅 안정성 강화",
                ]
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

    @staticmethod
    def _format_msa_recommendations():
        """MSA 특화 권장사항 포맷팅"""
        print("\n🏗️  MSA 운영 권장사항:")
        print("   • 서비스 메시 (Istio/Envoy) 도입으로 고급 트래픽 관리")
        print("   • 분산 트레이싱 (Jaeger/Zipkin) 구성으로 서비스 간 호출 추적")
        print("   • 중앙집중식 로깅 (ELK Stack) 구성")
        print("   • 서비스별 독립적인 CI/CD 파이프라인 구축")
        print("   • 카나리 배포 및 블루-그린 배포 전략 수립")
        print("   • 서비스별 SLA 및 모니터링 대시보드 구성")

    @staticmethod
    def _format_summary(overall_score: float, grade: str, system_info: Dict):
        """요약 포맷팅"""
        services = system_info.get("services", {})
        healthy_count = sum(1 for s in services.values() if s["status"] == "healthy")
        total_count = len(services)
        system_health_rate = (
            (healthy_count / total_count) * 100 if total_count > 0 else 0
        )

        print("\n" + "=" * 100)
        print(
            f"✨ MSA 통합 테스트 완료 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(f"   테스트된 서비스: {total_count}개")
        print(f"   전체 가용성: {system_health_rate:.1f}%")
        print(f"   종합 점수: {overall_score:.1f}/100 ({grade})")
        print("=" * 100)
