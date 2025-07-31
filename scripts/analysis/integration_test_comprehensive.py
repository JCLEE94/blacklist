#!/usr/bin/env python3
"""
포괄적인 통합 테스트 - 운영 서버 검증
"""
import json
import sys
import time
from datetime import datetime
from typing import Any, Dict, List

import requests

# 테스트 대상 서버
BASE_URL = "http://192.168.50.215:2541"
LOCAL_URL = "http://localhost:8541"

# 색상 코드
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_test_header(test_name: str):
    """테스트 헤더 출력"""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}테스트: {test_name}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}")


def print_result(success: bool, message: str):
    """테스트 결과 출력"""
    if success:
        print(f"{GREEN}✅ {message}{RESET}")
    else:
        print(f"{RED}❌ {message}{RESET}")


def test_health_check(base_url: str) -> bool:
    """헬스 체크 테스트"""
    print_test_header("헬스 체크")

    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        data = response.json()

        print_result(response.status_code == 200, f"HTTP 상태 코드: {response.status_code}")
        print_result(data.get("status") == "healthy", f"서비스 상태: {data.get('status')}")
        print_result("details" in data, "상세 정보 포함")

        if "details" in data:
            details = data["details"]
            print(f"  - 총 IP 수: {details.get('total_ips', 0)}")
            print(f"  - REGTECH: {details.get('regtech_count', 0)}")
            print(f"  - SECUDIUM: {details.get('secudium_count', 0)}")
            print(f"  - 캐시 상태: {details.get('cache_available', False)}")
            print(f"  - DB 연결: {details.get('database_connected', False)}")

        return response.status_code == 200 and data.get("status") == "healthy"

    except Exception as e:
        print_result(False, f"오류 발생: {e}")
        return False


def test_collection_status(base_url: str) -> bool:
    """수집 상태 테스트"""
    print_test_header("수집 상태")

    try:
        response = requests.get(f"{base_url}/api/collection/status", timeout=5)
        data = response.json()

        print_result(response.status_code == 200, f"HTTP 상태 코드: {response.status_code}")
        print_result("enabled" in data, "수집 활성화 상태 확인")
        print_result("sources" in data, "소스 정보 포함")

        print(f"  - 수집 활성화: {data.get('enabled', False)}")
        print(f"  - 마지막 수집: {data.get('last_collection', 'N/A')}")

        if "sources" in data:
            for source, info in data["sources"].items():
                print(
                    f"  - {source}: {info.get('status')} (IP: {info.get('total_ips', 0)})"
                )

        return response.status_code == 200

    except Exception as e:
        print_result(False, f"오류 발생: {e}")
        return False


def test_api_endpoints(base_url: str) -> Dict[str, bool]:
    """API 엔드포인트 테스트"""
    print_test_header("API 엔드포인트")

    endpoints = [
        ("/", "GET", "웹 대시보드"),
        ("/api/blacklist/active", "GET", "활성 블랙리스트"),
        ("/api/fortigate", "GET", "FortiGate 형식"),
        ("/api/stats", "GET", "통계"),
        ("/api/v2/blacklist/enhanced", "GET", "향상된 블랙리스트"),
        ("/api/v2/analytics/trends", "GET", "분석 트렌드"),
        ("/api/v2/sources/status", "GET", "소스 상태"),
        ("/test", "GET", "테스트 엔드포인트"),
    ]

    results = {}

    for endpoint, method, description in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{base_url}{endpoint}", timeout=5)

            success = response.status_code in [200, 201]
            results[endpoint] = success

            print_result(success, f"{description} ({endpoint}): {response.status_code}")

            # 응답 크기 확인
            if success:
                content_length = len(response.content)
                print(f"    응답 크기: {content_length:,} bytes")

        except Exception as e:
            results[endpoint] = False
            print_result(False, f"{description} ({endpoint}): {e}")

    return results


def test_collection_trigger(base_url: str) -> bool:
    """수집 트리거 테스트"""
    print_test_header("수집 트리거")

    # 현재 수집이 활성화되어 있는지 확인
    try:
        status_response = requests.get(f"{base_url}/api/collection/status", timeout=5)
        status_data = status_response.json()

        if not status_data.get("enabled", False):
            print(f"{YELLOW}⚠️  수집이 비활성화되어 있습니다. 활성화를 시도합니다.{RESET}")

            # 수집 활성화
            enable_response = requests.post(
                f"{base_url}/api/collection/enable",
                headers={"Content-Type": "application/json"},
                json={},
                timeout=10,
            )

            if enable_response.status_code == 200:
                print_result(True, "수집 활성화 성공")
            else:
                print_result(False, f"수집 활성화 실패: {enable_response.status_code}")
                return False

    except Exception as e:
        print_result(False, f"상태 확인 오류: {e}")
        return False

    # 수집 트리거 테스트는 실제 외부 서버에 부하를 줄 수 있으므로 주의
    print(f"{YELLOW}⚠️  실제 수집 트리거는 외부 서버에 부하를 줄 수 있으므로 생략합니다.{RESET}")
    return True


def test_performance(base_url: str) -> bool:
    """성능 테스트"""
    print_test_header("성능 테스트")

    endpoints = ["/health", "/api/stats", "/api/blacklist/active", "/api/fortigate"]

    total_time = 0
    test_count = 0

    for endpoint in endpoints:
        try:
            start_time = time.time()
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            end_time = time.time()

            response_time = (end_time - start_time) * 1000  # ms
            total_time += response_time
            test_count += 1

            success = response_time < 500  # 500ms 이하
            print_result(success, f"{endpoint}: {response_time:.0f}ms")

        except Exception as e:
            print_result(False, f"{endpoint}: 오류 - {e}")

    if test_count > 0:
        avg_time = total_time / test_count
        print(f"\n평균 응답 시간: {avg_time:.0f}ms")
        return avg_time < 500

    return False


def test_docker_logs(base_url: str) -> bool:
    """Docker 로그 엔드포인트 테스트"""
    print_test_header("Docker 로그 API")

    try:
        # Docker 컨테이너 목록
        response = requests.get(f"{base_url}/api/docker/containers", timeout=5)

        if response.status_code == 200:
            print_result(True, "Docker 컨테이너 목록 조회 성공")
            containers = response.json()

            if isinstance(containers, list) and len(containers) > 0:
                print(f"  발견된 컨테이너: {len(containers)}개")
                for container in containers[:3]:  # 처음 3개만 표시
                    print(
                        f"    - {container.get('name', 'Unknown')}: {container.get('status', 'Unknown')}"
                    )

            return True
        else:
            print_result(False, f"Docker API 응답 오류: {response.status_code}")
            return False

    except Exception as e:
        print_result(False, f"Docker API 오류: {e}")
        return False


def test_collection_logs_persistence(base_url: str) -> bool:
    """수집 로그 영속성 테스트"""
    print_test_header("수집 로그 영속성")

    try:
        # 첫 번째 요청
        response1 = requests.get(f"{base_url}/api/collection/status", timeout=5)
        data1 = response1.json()

        logs1 = data1.get("logs", [])
        print(f"현재 로그 수: {len(logs1)}")

        # 최신 로그 몇 개 표시
        if logs1:
            print("최신 로그:")
            for log in logs1[:3]:
                print(
                    f"  - {log.get('timestamp', 'N/A')}: {log.get('source', 'N/A')} - {log.get('action', 'N/A')}"
                )

        # 잠시 대기
        time.sleep(2)

        # 두 번째 요청
        response2 = requests.get(f"{base_url}/api/collection/status", timeout=5)
        data2 = response2.json()

        logs2 = data2.get("logs", [])

        # 로그가 유지되는지 확인
        logs_maintained = len(logs2) >= len(logs1)
        print_result(logs_maintained, f"로그 유지 여부: {len(logs1)} → {len(logs2)}")

        return logs_maintained

    except Exception as e:
        print_result(False, f"로그 영속성 테스트 오류: {e}")
        return False


def run_all_tests(base_url: str):
    """모든 테스트 실행"""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}블랙리스트 시스템 통합 테스트{RESET}")
    print(f"{BLUE}대상 서버: {base_url}{RESET}")
    print(f"{BLUE}실행 시간: {datetime.now()}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}")

    results = {
        "헬스 체크": test_health_check(base_url),
        "수집 상태": test_collection_status(base_url),
        "API 엔드포인트": all(test_api_endpoints(base_url).values()),
        "수집 트리거": test_collection_trigger(base_url),
        "성능": test_performance(base_url),
        "Docker 로그": test_docker_logs(base_url),
        "로그 영속성": test_collection_logs_persistence(base_url),
    }

    # 결과 요약
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}테스트 결과 요약{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}")

    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)

    for test_name, result in results.items():
        status = f"{GREEN}✅ PASS{RESET}" if result else f"{RED}❌ FAIL{RESET}"
        print(f"{test_name}: {status}")

    print(f"\n전체 결과: {passed_tests}/{total_tests} 테스트 통과")

    if passed_tests == total_tests:
        print(f"\n{GREEN}🎉 모든 테스트가 성공적으로 통과했습니다!{RESET}")
        return 0
    else:
        print(f"\n{RED}⚠️  일부 테스트가 실패했습니다.{RESET}")
        return 1


if __name__ == "__main__":
    # 기본적으로 운영 서버 테스트
    test_url = BASE_URL

    # 명령줄 인자로 로컬 테스트 지정 가능
    if len(sys.argv) > 1 and sys.argv[1] == "local":
        test_url = LOCAL_URL
        print(f"{YELLOW}로컬 서버를 대상으로 테스트를 실행합니다.{RESET}")

    exit_code = run_all_tests(test_url)
    sys.exit(exit_code)
