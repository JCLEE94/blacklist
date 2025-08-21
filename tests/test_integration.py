#!/usr/bin/env python3
"""
통합 테스트 스위트
모든 주요 기능을 테스트
"""
import sys
import time
from datetime import datetime

import requests


class IntegrationTest:
    def __init__(self, base_url="http://localhost:2541"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def test(self, name, func):
        """테스트 실행 및 결과 기록"""
        print(f"\n{'='*60}")
        print(f"테스트: {name}")
        print(f"{'='*60}")

        try:
            result = func()
            if result:
                self.log("✅ {name} - PASSED", "SUCCESS")
                self.test_results.append((name, "PASSED", None))
                return True
            else:
                self.log("❌ {name} - FAILED", "ERROR")
                self.test_results.append((name, "FAILED", "Test returned False"))
                return False
        except Exception as e:
            self.log("❌ {name} - ERROR: {str(e)}", "ERROR")
            self.test_results.append((name, "ERROR", str(e)))
            return False

    def test_health_check(self):
        """헬스 체크 테스트"""
        response = self.session.get("{self.base_url}/health")
        self.log("Status: {response.status_code}")
        self.log("Response: {response.text[:200]}")
        return response.status_code == 200

    def test_stats_api(self):
        """통계 API 테스트"""
        response = self.session.get("{self.base_url}/api/stats")
        self.log("Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            self.log("Total IPs: {data.get('data', {}).get('total_ips', 0)}")
            self.log("Status: {data.get('data', {}).get('status', 'unknown')}")
        return response.status_code == 200

    def test_collection_status(self):
        """수집 상태 확인"""
        response = self.session.get("{self.base_url}/api/collection/status")
        self.log("Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            self.log("Collection enabled: {data.get('enabled', False)}")
            self.log("Status: {data.get('status', 'unknown')}")
        return response.status_code == 200

    def test_collection_enable(self):
        """수집 활성화 테스트"""
        response = self.session.post(
            "{self.base_url}/api/collection/enable",
            headers={"Content-Type": "application/json"},
        )
        self.log("Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            self.log("Success: {data.get('success', False)}")
            self.log("Message: {data.get('message', '')}")
        return response.status_code == 200

    def test_regtech_trigger(self):
        """REGTECH 수집 트리거 테스트"""
        response = self.session.post(
            "{self.base_url}/api/collection/regtech/trigger",
            headers={"Content-Type": "application/json"},
            json={},
        )
        self.log("Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            self.log("Success: {data.get('success', False)}")
            self.log("Task ID: {data.get('task_id', '')}")
        else:
            self.log("Error response: {response.text}")
        return response.status_code == 200

    def test_secudium_trigger(self):
        """SECUDIUM 수집 트리거 테스트 - 비활성화됨"""
        self.log("SECUDIUM 수집이 비활성화되었습니다 (사용자 요청)")
        return True

    def test_fortigate_api(self):
        """FortiGate API 테스트"""
        response = self.session.get("{self.base_url}/api/fortigate")
        self.log("Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            self.log("FortiGate format validated")
        return response.status_code == 200

    def test_search_api(self):
        """검색 API 테스트"""
        test_ip = "1.2.1.1"
        response = self.session.get("{self.base_url}/api/search/{test_ip}")
        self.log("Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            self.log("Search for {test_ip}: found={data.get('found', False)}")
        return response.status_code == 200

    def test_database_clear(self):
        """데이터베이스 클리어 테스트"""
        response = self.session.post(
            "{self.base_url}/api/database/clear",
            headers={"Content-Type": "application/json"},
            json={"confirm": True},
        )
        self.log("Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            self.log("Success: {data.get('success', False)}")
        return response.status_code == 200

    def test_dashboard_pages(self):
        """대시보드 페이지 테스트"""
        pages = [
            "/",
            "/dashboard",
            "/unified-control",
            "/statistics",
            "/raw-data",
            "/search",
            "/settings/management",
        ]

        all_passed = True
        for page in pages:
            response = self.session.get("{self.base_url}{page}")
            self.log("{page}: {response.status_code}")
            if response.status_code != 200:
                all_passed = False

        return all_passed

    def test_export_endpoints(self):
        """내보내기 엔드포인트 테스트"""
        endpoints = [
            "/api/blacklist/active-simple",
            "/api/fortigate-simple",
            "/api/export/json",
            "/api/export/txt",
        ]

        all_passed = True
        for endpoint in endpoints:
            response = self.session.get("{self.base_url}{endpoint}")
            self.log("{endpoint}: {response.status_code}")
            if response.status_code != 200:
                all_passed = False

        return all_passed

    def run_all_tests(self):
        """모든 테스트 실행"""
        print("\n" + "=" * 80)
        print("🧪 블랙리스트 시스템 통합 테스트 시작")
        print("=" * 80)
        print(f"Target: {self.base_url}")
        print(f"Time: {datetime.now()}")

        # 기본 기능 테스트
        self.test("1. Health Check", self.test_health_check)
        self.test("2. Stats API", self.test_stats_api)
        self.test("3. Collection Status", self.test_collection_status)

        # 수집 기능 테스트
        self.test("4. Collection Enable", self.test_collection_enable)
        time.sleep(2)  # 활성화 대기

        self.test("5. REGTECH Trigger", self.test_regtech_trigger)
        self.test("6. SECUDIUM Trigger", self.test_secudium_trigger)

        # API 엔드포인트 테스트
        self.test("7. FortiGate API", self.test_fortigate_api)
        self.test("8. Search API", self.test_search_api)
        self.test("9. Export Endpoints", self.test_export_endpoints)

        # 웹 페이지 테스트
        self.test("10. Dashboard Pages", self.test_dashboard_pages)

        # 클린업 테스트
        self.test("11. Database Clear", self.test_database_clear)

        # 결과 요약
        print("\n" + "=" * 80)
        print("📊 테스트 결과 요약")
        print("=" * 80)

        passed = sum(1 for _, status, _ in self.test_results if status == "PASSED")
        failed = sum(1 for _, status, _ in self.test_results if status == "FAILED")
        errors = sum(1 for _, status, _ in self.test_results if status == "ERROR")
        total = len(self.test_results)

        print(f"총 테스트: {total}")
        print(f"✅ 성공: {passed}")
        print(f"❌ 실패: {failed}")
        print(f"⚠️  에러: {errors}")
        print(f"성공률: {(passed/total*100):.1f}%")

        # 실패한 테스트 상세
        if failed + errors > 0:
            print("\n" + "=" * 80)
            print("❌ 실패한 테스트")
            print("=" * 80)
            for name, status, error in self.test_results:
                if status != "PASSED":
                    print(f"- {name}: {status}")
                    if error:
                        print(f"  Error: {error}")

        return passed == total


if __name__ == "__main__":
    # 환경에 따른 URL 설정
    import os

    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    elif os.getenv("KUBERNETES_SERVICE_HOST"):
        # K8s 환경
        base_url = "http://blacklist:2541"
    else:
        # 로컬/Docker 환경
        base_url = "http://localhost:2541"

    tester = IntegrationTest(base_url)
    success = tester.run_all_tests()

    # 종료 코드 설정
    sys.exit(0 if success else 1)
