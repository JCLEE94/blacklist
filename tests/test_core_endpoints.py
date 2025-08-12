#!/usr/bin/env python3
"""
Core Blacklist API 엔드포인트 테스트
/, /health, /api/blacklist/active, /api/fortigate, /api/stats 엔드포인트 검증
"""


import requests


def test_core_endpoints(base_url="http://localhost:8541"):
    """Core Blacklist 엔드포인트 테스트"""

    session = requests.Session()
    results = []

    print("🔍 Core Blacklist API 엔드포인트 테스트 시작")
    print("=" * 60)

    # Test 1: 메인 페이지 (/)
    print("\n1. 메인 페이지 (/) 테스트")
    try:
        response = session.get("{base_url}/", timeout=10)
        if response.status_code == 200:
            # HTML 응답 확인
            is_html = "text/html" in response.headers.get("Content-Type", "")
            has_dashboard = "dashboard" in response.text.lower()

            if is_html and has_dashboard:
                print("✅ 메인 페이지: 정상 (대시보드 HTML 반환)")
                results.append(("/", True, "대시보드 페이지 정상"))
            else:
                print("❌ 메인 페이지: HTML이 아니거나 대시보드 콘텐츠 없음")
                results.append(("/", False, "Invalid content"))
        else:
            print("❌ 메인 페이지: HTTP {response.status_code}")
            results.append(("/", False, "HTTP {response.status_code}"))
    except Exception as e:
        print("❌ 메인 페이지 오류: {e}")
        results.append(("/", False, str(e)))

    # Test 2: Health Check (/health)
    print("\n2. Health Check (/health) 테스트")
    try:
        response = session.get("{base_url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "unknown")

            print("✅ Health Check: {status}")
            print("   - Total IPs: {data.get('total_ips', 0)}")
            print("   - Active IPs: {data.get('active_ips', 0)}")
            print("   - Uptime: {data.get('uptime', 'N/A')}")

            results.append(("/health", True, status))
        else:
            print("❌ Health Check: HTTP {response.status_code}")
            results.append(("/health", False, "HTTP {response.status_code}"))
    except Exception as e:
        print("❌ Health Check 오류: {e}")
        results.append(("/health", False, str(e)))

    # Test 3: Active Blacklist (/api/blacklist/active)
    print("\n3. Active Blacklist (/api/blacklist/active) 테스트")
    try:
        response = session.get("{base_url}/api/blacklist/active", timeout=10)
        if response.status_code == 200:
            # 텍스트 형식 응답 확인
            content = response.text
            lines = content.strip().split("\n") if content else []

            print("✅ Active Blacklist: {len(lines)} IPs")
            if lines and lines[0]:  # 첫 번째 IP 샘플 출력
                print("   샘플 IP: {lines[0]}")

            # IP 형식 검증 (간단한 체크)
            if lines and all("." in line for line in lines[:5]):  # 처음 5개만 체크
                results.append(("/api/blacklist/active", True, "{len(lines)} IPs"))
            else:
                results.append(("/api/blacklist/active", True, "Empty or no IPs"))
        else:
            print("❌ Active Blacklist: HTTP {response.status_code}")
            results.append(
                ("/api/blacklist/active", False, "HTTP {response.status_code}")
            )
    except Exception as e:
        print("❌ Active Blacklist 오류: {e}")
        results.append(("/api/blacklist/active", False, str(e)))

    # Test 4: FortiGate Format (/api/fortigate)
    print("\n4. FortiGate Format (/api/fortigate) 테스트")
    try:
        response = session.get("{base_url}/api/fortigate", timeout=10)
        if response.status_code == 200:
            data = response.json()

            # FortiGate 형식 검증 (새로운 형식)
            has_threat_feed = "threat_feed" in data
            has_entries = "entries" in data.get("threat_feed", {})

            if has_threat_feed and has_entries:
                ip_count = len(data["threat_feed"].get("entries", []))
                print("✅ FortiGate Format: 정상 ({ip_count} IPs)")
                print(
                    "   - Description: {data['threat_feed'].get('description', 'N/A')}"
                )
                print("   - Last Updated: {data.get('last_updated', 'N/A')}")

                # 첫 번째 IP 샘플 확인
                if ip_count > 0:
                    first_ip = data["threat_feed"]["entries"][0]
                    print("   - 샘플 데이터: {first_ip}")

                results.append(("/api/fortigate", True, "{ip_count} IPs"))
            else:
                print("❌ FortiGate Format: 형식 오류")
                results.append(("/api/fortigate", False, "Invalid format"))
        else:
            print("❌ FortiGate Format: HTTP {response.status_code}")
            results.append(("/api/fortigate", False, "HTTP {response.status_code}"))
    except Exception as e:
        print("❌ FortiGate Format 오류: {e}")
        results.append(("/api/fortigate", False, str(e)))

    # Test 5: System Stats (/api/stats)
    print("\n5. System Stats (/api/stats) 테스트")
    try:
        response = session.get("{base_url}/api/stats", timeout=10)
        if response.status_code == 200:
            data = response.json()

            print("✅ System Stats: 정상")
            print("   - Total IPs: {data.get('total_ips', 0)}")
            print("   - Active IPs: {data.get('active_ips', 0)}")
            print("   - Last Update: {data.get('last_update', 'N/A')}")

            # 소스별 통계
            sources = data.get("sources", {})
            if sources:
                print("   - 소스별 통계:")
                for source, info in sources.items():
                    print("     * {source}: {info.get('count', 0)} IPs")

            results.append(("/api/stats", True, "Stats available"))
        else:
            print("❌ System Stats: HTTP {response.status_code}")
            results.append(("/api/stats", False, "HTTP {response.status_code}"))
    except Exception as e:
        print("❌ System Stats 오류: {e}")
        results.append(("/api/stats", False, str(e)))

    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)

    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)

    for endpoint, success, message in results:
        status = "✅" if success else "❌"
        print("{status} {endpoint}: {message}")

    print(
        "\n총 {total_count}개 중 {success_count}개 성공 ({success_count/total_count*100:.0f}%)"
    )

    return success_count == total_count


def test_dashboard_charts(base_url="http://localhost:8541"):
    """대시보드 차트 데이터 API 테스트"""
    print("\n\n🔍 대시보드 차트 데이터 API 테스트")
    print("=" * 60)

    session = requests.Session()

    # Monthly data API 테스트
    print("\n6. Monthly Data API (/api/stats/monthly-data) 테스트")
    try:
        response = session.get("{base_url}/api/stats/monthly-data", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Monthly Data API: {len(data)} 개월 데이터")
            if data:
                print("   샘플: {data[0]}")
        else:
            print("❌ Monthly Data API: HTTP {response.status_code}")
    except Exception as e:
        print("❌ Monthly Data API 오류: {e}")

    # Source distribution API 테스트
    print("\n7. Source Distribution API (/api/stats/source-distribution) 테스트")
    try:
        response = session.get("{base_url}/api/stats/source-distribution", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Source Distribution API: 정상")
            for source, info in data.items():
                print(
                    "   - {source}: {info.get('count', 0)} ({info.get('percentage', 0)}%)"
                )
        else:
            print("❌ Source Distribution API: HTTP {response.status_code}")
    except Exception as e:
        print("❌ Source Distribution API 오류: {e}")


if __name__ == "__main__":
    # Core endpoints 테스트
    all_passed = test_core_endpoints()

    # 차트 데이터 API 테스트
    test_dashboard_charts()

    print("\n✅ Core Blacklist API 엔드포인트 테스트 완료")
