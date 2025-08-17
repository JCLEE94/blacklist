"""
API 엔드포인트 상태 및 성능 테스트

주요 API 엔드포인트의 상태와 성능을 테스트합니다.
"""

import time

from .base_test_suite import BaseUITestSuite


class APITestSuite(BaseUITestSuite):
    """API 엔드포인트 테스트 스위트"""

    async def test_api_endpoints(self):
        """API 엔드포인트 상태 테스트"""

        async def api_test():
            endpoint_results = {}

            for endpoint in self.config.API_ENDPOINTS:
                result = await self.test_single_endpoint(endpoint)
                endpoint_results[endpoint] = result

            # 성공한 엔드포인트 비율 계산
            success_rate = await self.calculate_success_rate(endpoint_results)

            if success_rate < 80:
                self.reporter.add_error(
                    f"API 엔드포인트 성공률 낮음: {success_rate:.1f}%"
                )

            return {"endpoint_results": endpoint_results, "success_rate": success_rate}

        result = await self.execute_test_with_timing("api_endpoints", api_test)
        return result

    async def test_single_endpoint(self, endpoint: str) -> dict:
        """단일 API 엔드포인트 테스트"""
        url = self.config.get_api_url(endpoint)
        api_start = time.time()

        try:
            response = await self.page.evaluate(
                f"""
                fetch('{url}').then(r => ({
                    status: r.status,
                    ok: r.ok,
                    headers: Object.fromEntries(r.headers.entries())
                }))
            """
            )

            api_duration = (time.time() - api_start) * 1000

            # API 응답 시간 임계값 확인
            if api_duration > self.config.PERFORMANCE_THRESHOLDS["api_response"]:
                self.reporter.add_warning(
                    f"API {endpoint} 응답시간 초과: {api_duration:.2f}ms"
                )

            result = {
                "status": response["status"],
                "ok": response["ok"],
                "duration": api_duration,
            }

            # 응답 상태 확인
            if response["status"] not in [200, 401, 403]:
                self.reporter.add_warning(
                    f"API {endpoint} 응답 상태 이상: {response['status']}"
                )

            return result

        except Exception as e:
            api_duration = (time.time() - api_start) * 1000
            error_result = {"error": str(e), "duration": api_duration}
            self.reporter.add_error(f"API {endpoint} 호출 실패: {str(e)}")
            return error_result

    async def calculate_success_rate(self, endpoint_results: dict) -> float:
        """성공률 계산"""
        total_endpoints = len(endpoint_results)
        if total_endpoints == 0:
            return 0.0

        successful_endpoints = sum(
            1
            for result in endpoint_results.values()
            if result.get("ok") or result.get("status") in [200, 401, 403]
        )

        return (successful_endpoints / total_endpoints) * 100

    async def test_api_performance(self):
        """전체 API 성능 테스트"""

        async def performance_test():
            performance_results = {}

            for endpoint in self.config.API_ENDPOINTS:
                # 여러 번 호출하여 평균 성능 측정
                durations = []

                for _ in range(3):  # 3번 테스트
                    result = await self.test_single_endpoint(endpoint)
                    if "duration" in result:
                        durations.append(result["duration"])

                if durations:
                    avg_duration = sum(durations) / len(durations)
                    performance_results[endpoint] = {
                        "avg_duration": avg_duration,
                        "min_duration": min(durations),
                        "max_duration": max(durations),
                    }

                    # 성능 메트릭 추가
                    self.reporter.add_performance_metric(
                        f"api_{endpoint.replace('/', '_')}",
                        avg_duration,
                        self.config.PERFORMANCE_THRESHOLDS["api_response"],
                    )

            return performance_results

        return await self.execute_test_with_timing("api_performance", performance_test)

    async def test_api_health_checks(self):
        """헬스체크 API 테스트"""
        health_endpoints = ["/health", "/api/health"]

        for endpoint in health_endpoints:
            result = await self.test_single_endpoint(endpoint)

            if result.get("status") != 200:
                self.reporter.add_error(
                    f"헬스체크 엔드포인트 {endpoint} 비정상: {result.get('status')}"
                )

    async def test_blacklist_apis(self):
        """블랙리스트 관련 API 테스트"""
        blacklist_endpoints = [
            "/api/blacklist/active",
            "/api/fortigate",
            "/api/v2/analytics/summary",
        ]

        for endpoint in blacklist_endpoints:
            result = await self.test_single_endpoint(endpoint)

            # 블랙리스트 API는 데이터를 반환해야 함
            if result.get("status") == 200:
                # 성공시 추가 검증이 가능하다면 여기에 추가
                pass
            elif result.get("status") not in [401, 403]:
                self.reporter.add_warning(
                    f"블랙리스트 API {endpoint} 비정상 상태: {result.get('status')}"
                )
