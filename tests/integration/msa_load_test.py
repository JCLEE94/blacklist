#!/usr/bin/env python3
"""
MSA 아키텍처 부하 테스트
동시 접속, 처리량, 응답 시간 테스트
"""

import asyncio
import logging
import statistics
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LoadTestResult:
    endpoint: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    requests_per_second: float
    error_rate: float


class MSALoadTester:
    """MSA 부하 테스터"""

    def __init__(self):
        self.endpoints = {
            "api_gateway_health": "http://localhost:8080/health",
            "blacklist_active": "http://localhost:8080/api/v1/blacklist/active",
            "blacklist_stats": "http://localhost:8080/api/v1/blacklist/statistics",
            "collection_status": "http://localhost:8080/api/v1/collection/status",
            "analytics_realtime": "http://localhost:8080/api/v1/analytics/realtime",
            "fortigate_format": "http://localhost:8080/api/v1/blacklist/fortigate",
        }

        self.results: List[LoadTestResult] = []

    async def single_request(
        self, session: httpx.AsyncClient, url: str
    ) -> Dict[str, Any]:
        """단일 요청 실행"""
        start_time = time.time()
        try:
            response = await session.get(url, timeout=30)
            response_time = time.time() - start_time

            return {
                "success": True,
                "response_time": response_time,
                "status_code": response.status_code,
                "error": None,
            }
        except Exception as e:
            response_time = time.time() - start_time
            return {
                "success": False,
                "response_time": response_time,
                "status_code": 0,
                "error": str(e),
            }

    async def concurrent_load_test(
        self,
        endpoint_name: str,
        url: str,
        concurrent_users: int,
        requests_per_user: int,
    ) -> LoadTestResult:
        """동시 사용자 부하 테스트"""
        print(
            "🔥 {endpoint_name} 부하 테스트 - {concurrent_users}명 동시 사용자, {requests_per_user}회/사용자"
        )

        total_requests = concurrent_users * requests_per_user
        results = []

        start_time = time.time()

        async def user_session(user_id: int):
            """단일 사용자 세션"""
            user_results = []
            async with httpx.AsyncClient() as session:
                for _ in range(requests_per_user):
                    result = await self.single_request(session, url)
                    user_results.append(result)
            return user_results

        # 동시 사용자 실행
        tasks = [user_session(i) for i in range(concurrent_users)]
        user_results = await asyncio.gather(*tasks)

        # 결과 집계
        for user_result in user_results:
            results.extend(user_result)

        total_time = time.time() - start_time

        # 통계 계산
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]

        response_times = [r["response_time"] for r in successful_results]

        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
        else:
            avg_response_time = min_response_time = max_response_time = 0.0

        requests_per_second = total_requests / total_time if total_time > 0 else 0
        error_rate = (
            len(failed_results) / total_requests * 100 if total_requests > 0 else 0
        )

        result = LoadTestResult(
            endpoint=endpoint_name,
            total_requests=total_requests,
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            requests_per_second=requests_per_second,
            error_rate=error_rate,
        )

        self.results.append(result)

        # 결과 출력
        status_emoji = "✅" if error_rate < 5 else "⚠️" if error_rate < 15 else "❌"
        print(
            "   {status_emoji} 성공: {len(successful_results)}/{total_requests}, "
            "평균 응답시간: {avg_response_time:.3f}s, "
            "처리량: {requests_per_second:.1f} req/s, "
            "오류율: {error_rate:.1f}%"
        )

        return result

    async def stress_test(self):
        """스트레스 테스트 - 점진적 부하 증가"""
        print("\n💪 스트레스 테스트 - 점진적 부하 증가")
        print("=" * 60)

        stress_scenarios = [
            (5, 10),  # 5명 동시 사용자, 10회/사용자
            (10, 10),  # 10명 동시 사용자, 10회/사용자
            (20, 5),  # 20명 동시 사용자, 5회/사용자
            (50, 2),  # 50명 동시 사용자, 2회/사용자
        ]

        # 핵심 엔드포인트 테스트
        core_endpoints = [
            ("API Gateway Health", self.endpoints["api_gateway_health"]),
            ("Blacklist Active", self.endpoints["blacklist_active"]),
            ("Analytics Realtime", self.endpoints["analytics_realtime"]),
        ]

        for endpoint_name, url in core_endpoints:
            print("\n🎯 {endpoint_name} 스트레스 테스트")

            for concurrent_users, requests_per_user in stress_scenarios:
                await self.concurrent_load_test(
                    "{endpoint_name} ({concurrent_users}u/{requests_per_user}r)",
                    url,
                    concurrent_users,
                    requests_per_user,
                )

                # 서버 회복 시간
                await asyncio.sleep(1)

    async def endurance_test(self):
        """내구성 테스트 - 장시간 지속적 부하"""
        print("\n⏱️  내구성 테스트 - 30초간 지속적 부하")
        print("=" * 60)

        endpoint_name = "Gateway Health"
        url = self.endpoints["api_gateway_health"]
        duration = 30  # 30초
        concurrent_users = 10

        print("🏃 {endpoint_name} - {concurrent_users}명 동시 사용자, {duration}초간 지속")

        results = []
        start_time = time.time()
        end_time = start_time + duration

        async def continuous_user(user_id: int):
            """지속적 요청 사용자"""
            user_results = []
            async with httpx.AsyncClient() as session:
                while time.time() < end_time:
                    result = await self.single_request(session, url)
                    user_results.append(result)
                    await asyncio.sleep(0.1)  # 100ms 간격
            return user_results

        # 동시 사용자 실행
        tasks = [continuous_user(i) for i in range(concurrent_users)]
        user_results = await asyncio.gather(*tasks)

        # 결과 집계
        for user_result in user_results:
            results.extend(user_result)

        total_time = time.time() - start_time

        # 통계 계산
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]

        response_times = [r["response_time"] for r in successful_results]

        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
        else:
            avg_response_time = min_response_time = max_response_time = 0.0

        requests_per_second = len(results) / total_time if total_time > 0 else 0
        error_rate = len(failed_results) / len(results) * 100 if results else 0

        result = LoadTestResult(
            endpoint="{endpoint_name} (Endurance)",
            total_requests=len(results),
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            requests_per_second=requests_per_second,
            error_rate=error_rate,
        )

        self.results.append(result)

        status_emoji = "✅" if error_rate < 5 else "⚠️" if error_rate < 15 else "❌"
        print(
            "   {status_emoji} 총 요청: {len(results)}, "
            "성공: {len(successful_results)}, "
            "평균 응답시간: {avg_response_time:.3f}s"
        )
        print(
            "      처리량: {requests_per_second:.1f} req/s, "
            "오류율: {error_rate:.1f}%, "
            "지속시간: {total_time:.1f}s"
        )

    async def api_gateway_routing_load_test(self):
        """API Gateway 라우팅 부하 테스트"""
        print("\n🚪 API Gateway 라우팅 부하 테스트")
        print("=" * 60)

        # 모든 서비스 엔드포인트 동시 테스트
        all_endpoints = [
            ("Collection Status", self.endpoints["collection_status"]),
            ("Blacklist Active", self.endpoints["blacklist_active"]),
            ("Blacklist Stats", self.endpoints["blacklist_stats"]),
            ("Analytics Realtime", self.endpoints["analytics_realtime"]),
            ("FortiGate Format", self.endpoints["fortigate_format"]),
        ]

        concurrent_users = 5
        requests_per_user = 5

        print("🔀 모든 서비스 엔드포인트 동시 테스트 - {concurrent_users}명/{requests_per_user}회")

        for endpoint_name, url in all_endpoints:
            await self.concurrent_load_test(
                "Gateway → {endpoint_name}", url, concurrent_users, requests_per_user
            )

    def print_comprehensive_report(self):
        """종합 부하 테스트 리포트"""
        print("\n" + "=" * 80)
        print("📊 MSA 부하 테스트 종합 리포트")
        print("=" * 80)

        if not self.results:
            print("테스트 결과가 없습니다.")
            return

        # 전체 통계
        total_requests = sum(r.total_requests for r in self.results)
        total_successful = sum(r.successful_requests for r in self.results)
        total_failed = sum(r.failed_requests for r in self.results)
        overall_success_rate = (
            (total_successful / total_requests * 100) if total_requests > 0 else 0
        )

        avg_response_times = [
            r.avg_response_time for r in self.results if r.avg_response_time > 0
        ]
        overall_avg_response_time = (
            statistics.mean(avg_response_times) if avg_response_times else 0
        )

        max_throughput = max(r.requests_per_second for r in self.results)
        avg_throughput = statistics.mean([r.requests_per_second for r in self.results])

        print("📈 전체 통계:")
        print("   • 총 요청: {total_requests:,}개")
        print("   • 성공: {total_successful:,}개")
        print("   • 실패: {total_failed:,}개")
        print("   • 전체 성공률: {overall_success_rate:.1f}%")
        print("   • 평균 응답 시간: {overall_avg_response_time:.3f}초")
        print("   • 최대 처리량: {max_throughput:.1f} req/s")
        print("   • 평균 처리량: {avg_throughput:.1f} req/s")

        # 상세 결과
        print("\n📋 상세 테스트 결과:")
        for result in self.results:
            status_emoji = (
                "✅"
                if result.error_rate < 5
                else "⚠️"
                if result.error_rate < 15
                else "❌"
            )
            print("   {status_emoji} {result.endpoint}")
            print(
                "      요청: {result.total_requests}, 성공: {result.successful_requests}, 실패: {result.failed_requests}"
            )
            print(
                "      응답시간: 평균 {result.avg_response_time:.3f}s, 최소 {result.min_response_time:.3f}s, 최대 {result.max_response_time:.3f}s"
            )
            print(
                "      처리량: {result.requests_per_second:.1f} req/s, 오류율: {result.error_rate:.1f}%"
            )

        # 성능 분석
        print("\n⚡ 성능 분석:")

        # 응답 시간 분석
        fast_tests = [r for r in self.results if r.avg_response_time < 0.1]
        medium_tests = [r for r in self.results if 0.1 <= r.avg_response_time < 0.5]
        slow_tests = [r for r in self.results if r.avg_response_time >= 0.5]

        print("   • 빠른 응답 (<100ms): {len(fast_tests)}개 테스트")
        print("   • 보통 응답 (100-500ms): {len(medium_tests)}개 테스트")
        print("   • 느린 응답 (>500ms): {len(slow_tests)}개 테스트")

        # 처리량 분석
        high_throughput = [r for r in self.results if r.requests_per_second > 100]
        medium_throughput = [
            r for r in self.results if 50 <= r.requests_per_second <= 100
        ]
        low_throughput = [r for r in self.results if r.requests_per_second < 50]

        print("   • 높은 처리량 (>100 req/s): {len(high_throughput)}개 테스트")
        print("   • 보통 처리량 (50-100 req/s): {len(medium_throughput)}개 테스트")
        print("   • 낮은 처리량 (<50 req/s): {len(low_throughput)}개 테스트")

        # 권장사항
        print("\n💡 성능 개선 권장사항:")

        if slow_tests:
            print("   • 응답 시간 개선 필요한 엔드포인트: {len(slow_tests)}개")
            for test in slow_tests[:3]:  # 상위 3개만 표시
                print("     - {test.endpoint}: {test.avg_response_time:.3f}s")

        if total_failed > 0:
            error_rate = total_failed / total_requests * 100
            print("   • 전체 오류율 {error_rate:.1f}% - 안정성 개선 필요")

        if avg_throughput < 50:
            print("   • 평균 처리량 {avg_throughput:.1f} req/s - 확장성 개선 권장")

        if overall_success_rate < 95:
            print("   • 전체 성공률 {overall_success_rate:.1f}% - 시스템 안정성 점검 필요")
        else:
            print("   • 전체 성공률 {overall_success_rate:.1f}% - 우수한 안정성")

        print("\n" + "=" * 80)

        # 최종 평가
        if overall_success_rate >= 95 and overall_avg_response_time < 0.5:
            print("🎉 MSA 시스템이 부하 테스트를 성공적으로 통과했습니다!")
            print("   프로덕션 환경에서 안정적으로 운영할 수 있습니다.")
        elif overall_success_rate >= 90:
            print("⚠️  MSA 시스템이 기본적인 부하 테스트를 통과했습니다.")
            print("   일부 성능 최적화가 권장됩니다.")
        else:
            print("❌ MSA 시스템에 성능 및 안정성 문제가 있습니다.")
            print("   시스템 점검 및 개선이 필요합니다.")

        print("=" * 80)

        return overall_success_rate >= 90


async def main():
    """메인 실행 함수"""
    print("🚀 MSA 아키텍처 부하 테스트를 시작합니다...")
    print("   모든 서비스가 실행 중인지 확인하세요.")
    print()

    tester = MSALoadTester()

    try:
        # 부하 테스트 실행
        await tester.stress_test()
        await tester.endurance_test()
        await tester.api_gateway_routing_load_test()

        # 종합 리포트
        success = tester.print_comprehensive_report()

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n⏹️  부하 테스트가 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print("\n💥 부하 테스트 실행 중 오류 발생: {e}")
        logger.exception("Load test execution failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
