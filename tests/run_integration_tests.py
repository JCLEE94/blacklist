#!/usr/bin/env python3
"""
통합 테스트 실행 스크립트
모든 주요 기능 자동 검증
"""

import requests
import time
import json
import sys
from datetime import datetime


def run_integration_tests():
    """통합 테스트 실행"""
    print("🧪 통합 테스트 시작")
    print("=" * 60)

    base_url = "http://localhost:8541"
    test_results = []

    # 1. 헬스 체크 테스트
    print("1️⃣ 헬스 체크 테스트")
    health_result = test_health_check(base_url)
    test_results.append(("Health Check", health_result))

    # 2. API 엔드포인트 테스트
    print("\n2️⃣ API 엔드포인트 테스트")
    api_result = test_api_endpoints(base_url)
    test_results.append(("API Endpoints", api_result))

    # 3. 웹 UI 테스트
    print("\n3️⃣ 웹 UI 테스트")
    ui_result = test_web_ui(base_url)
    test_results.append(("Web UI", ui_result))

    # 4. 성능 테스트
    print("\n4️⃣ 성능 테스트")
    performance_result = test_performance(base_url)
    test_results.append(("Performance", performance_result))

    # 5. 기능 테스트
    print("\n5️⃣ 기능 테스트")
    functionality_result = test_functionality(base_url)
    test_results.append(("Functionality", functionality_result))

    # 결과 출력
    print("\n" + "=" * 60)
    print("📊 통합 테스트 결과")
    print("=" * 60)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"{status} {test_name}")
        if result["passed"]:
            passed += 1
        if "details" in result:
            print(f"    {result['details']}")

    print("=" * 60)
    print(f"📈 전체 결과: {passed}/{total} 테스트 통과 ({passed/total*100:.1f}%)")

    if passed == total:
        print("🎉 모든 통합 테스트 통과!")
        return True
    else:
        print("⚠️ 일부 테스트 실패")
        return False


def test_health_check(base_url):
    """헬스 체크 테스트"""
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            healthy = data.get("status") == "healthy"
            if healthy:
                total_ips = data.get("total_ips", 0)
                return {"passed": True, "details": f"서비스 정상, IP 수: {total_ips:,}개"}
            else:
                return {"passed": False, "details": "서비스가 unhealthy 상태"}
        else:
            return {"passed": False, "details": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"passed": False, "details": f"연결 실패: {e}"}


def test_api_endpoints(base_url):
    """API 엔드포인트 테스트"""
    endpoints = [
        ("/health", 200),
        ("/api/stats", 200),
        ("/api/blacklist/active", 200),
        ("/api/search/192.168.1.1", 200),
        ("/api/fortigate", 200),
    ]

    passed_endpoints = 0
    total_endpoints = len(endpoints)

    for endpoint, expected_status in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            if response.status_code == expected_status:
                passed_endpoints += 1
                print(f"    ✅ {endpoint}")
            else:
                print(f"    ❌ {endpoint} - HTTP {response.status_code}")
        except Exception as e:
            print(f"    ❌ {endpoint} - 오류: {e}")

    passed = passed_endpoints == total_endpoints
    return {
        "passed": passed,
        "details": f"{passed_endpoints}/{total_endpoints} 엔드포인트 정상",
    }


def test_web_ui(base_url):
    """웹 UI 테스트"""
    ui_pages = [
        "/",
        "/dashboard",
        "/data-management",
        "/blacklist-search",
        "/connection-status",
        "/system-logs",
    ]

    passed_pages = 0
    total_pages = len(ui_pages)

    for page in ui_pages:
        try:
            response = requests.get(f"{base_url}{page}", timeout=10)
            if response.status_code == 200:
                passed_pages += 1
                print(f"    ✅ {page}")
            else:
                print(f"    ❌ {page} - HTTP {response.status_code}")
        except Exception as e:
            print(f"    ❌ {page} - 오류: {e}")

    passed = passed_pages == total_pages
    return {"passed": passed, "details": f"{passed_pages}/{total_pages} 페이지 정상"}


def test_performance(base_url):
    """성능 테스트"""
    test_urls = [f"{base_url}/health", f"{base_url}/api/stats", f"{base_url}/"]

    response_times = []

    for url in test_urls:
        try:
            start_time = time.time()
            response = requests.get(url, timeout=30)
            end_time = time.time()

            response_time = (end_time - start_time) * 1000  # ms
            response_times.append(response_time)

            status = "✅" if response_time < 3000 else "⚠️"
            print(f"    {status} {url.split('/')[-1] or 'home'}: {response_time:.0f}ms")

        except Exception as e:
            print(f"    ❌ {url}: 오류 - {e}")
            response_times.append(10000)  # 실패 시 큰 값

    avg_response_time = sum(response_times) / len(response_times)
    passed = avg_response_time < 3000

    return {"passed": passed, "details": f"평균 응답시간: {avg_response_time:.0f}ms"}


def test_functionality(base_url):
    """기능 테스트"""
    functional_tests = []

    # 1. IP 검색 기능
    try:
        response = requests.get(f"{base_url}/api/search/1.1.1.1", timeout=10)
        if response.status_code == 200:
            data = response.json()
            search_success = data.get("success", False)
            functional_tests.append(("IP 검색", search_success))
            print(f"    {'✅' if search_success else '❌'} IP 검색 기능")
        else:
            functional_tests.append(("IP 검색", False))
            print("    ❌ IP 검색 API 오류")
    except Exception:
        functional_tests.append(("IP 검색", False))
        print("    ❌ IP 검색 연결 실패")

    # 2. 통계 기능
    try:
        response = requests.get(f"{base_url}/api/stats", timeout=10)
        if response.status_code == 200:
            data = response.json()
            stats_success = data.get("success", False)
            functional_tests.append(("통계 조회", stats_success))
            print(f"    {'✅' if stats_success else '❌'} 통계 조회 기능")
        else:
            functional_tests.append(("통계 조회", False))
            print("    ❌ 통계 API 오류")
    except Exception:
        functional_tests.append(("통계 조회", False))
        print("    ❌ 통계 조회 연결 실패")

    # 3. 블랙리스트 조회
    try:
        response = requests.get(f"{base_url}/api/blacklist/active", timeout=10)
        if response.status_code == 200:
            content = response.text
            has_ips = len(content.strip().split("\n")) > 0
            functional_tests.append(("블랙리스트", has_ips))
            print(f"    {'✅' if has_ips else '❌'} 블랙리스트 조회")
        else:
            functional_tests.append(("블랙리스트", False))
            print("    ❌ 블랙리스트 API 오류")
    except Exception:
        functional_tests.append(("블랙리스트", False))
        print("    ❌ 블랙리스트 연결 실패")

    passed_functions = sum(1 for _, success in functional_tests if success)
    total_functions = len(functional_tests)
    passed = passed_functions == total_functions

    return {"passed": passed, "details": f"{passed_functions}/{total_functions} 기능 정상"}


def main():
    """메인 실행"""
    success = run_integration_tests()

    if success:
        print(f"\n🎉 통합 테스트 완료! 배포 성공")
        print(f"🌐 서비스 URL: http://localhost:8541")
        print(f"📊 대시보드: http://localhost:8541/dashboard")
        print(f"🔍 IP 검색: http://localhost:8541/blacklist-search")
        sys.exit(0)
    else:
        print(f"\n❌ 통합 테스트 실패! 추가 확인 필요")
        sys.exit(1)


if __name__ == "__main__":
    main()
