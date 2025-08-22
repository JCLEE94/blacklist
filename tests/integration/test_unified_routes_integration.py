#!/usr/bin/env python3
"""
통합 테스트: Unified Routes API Endpoints
Rust 스타일 인라인 테스트
"""
import os
import sys

from flask import Flask

from src.core.unified_routes import unified_bp

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def test_health_endpoint_integration():
    """통합 테스트: 헬스체크 엔드포인트"""
    print("\n🧪 Testing health endpoint integration...")

    # 테스트용 앱 생성
    app = Flask(__name__)
    app.register_blueprint(unified_bp)

    with app.test_client() as client:
        # 1. 기본 헬스체크
        response = client.get("/health")
        assert response.status_code == 200, "Expected 200, got {response.status_code}"

        data = response.get_json()
        assert data["status"] in [
            "healthy",
            "degraded",
        ], "Invalid status: {data['status']}"
        assert "database" in data["components"], "Missing database component"
        assert "cache" in data["components"], "Missing cache component"

        print("✅ Health endpoint test passed")

        # 2. 상세 헬스체크
        response = client.get("/health?detailed=true")
        assert response.status_code == 200
        data = response.get_json()
        assert "response_time_ms" in data, "Missing response time"
        assert "memory_usage_mb" in data, "Missing memory usage"

        print("✅ Detailed health endpoint test passed")

    return True


def test_blacklist_api_integration():
    """통합 테스트: 블랙리스트 API 엔드포인트"""
    print("\n🧪 Testing blacklist API integration...")

    app = Flask(__name__)
    app.register_blueprint(unified_bp)

    with app.test_client() as client:
        # 1. Active IPs 텍스트 포맷
        response = client.get("/api/blacklist/active")
        assert response.status_code == 200
        assert response.content_type == "text/plain; charset=utf-8"

        # IP 형식 검증
        ips = response.data.decode("utf-8").strip().split("\n")
        if ips and ips[0]:  # IP가 있으면 검증
            for ip in ips[:5]:  # 처음 5개만 검증
                if ip:  # 빈 줄 제외
                    parts = ip.split(".")
                    assert len(parts) == 4, "Invalid IP format: {ip}"

        print(f"✅ Active IPs test passed ({len(ips)} IPs)")

        # 2. FortiGate JSON 포맷
        response = client.get("/api/fortigate")
        assert response.status_code == 200
        assert response.content_type == "application/json"

        data = response.get_json()
        assert "status" in data
        assert "blacklist" in data
        assert isinstance(data["blacklist"], list)

        print("✅ FortiGate format test passed")

        # 3. 통계 API
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.get_json()
        assert "total_ips" in data
        assert "active_ips" in data
        assert "sources" in data

        print("✅ Stats API test passed")

    return True


def test_collection_management_integration():
    """통합 테스트: 수집 관리 엔드포인트"""
    print("\n🧪 Testing collection management integration...")

    app = Flask(__name__)
    app.register_blueprint(unified_bp)

    with app.test_client() as client:
        # 1. 수집 상태 확인
        response = client.get("/api/collection/status")
        assert response.status_code == 200

        data = response.get_json()
        assert "collection_enabled" in data
        assert "sources" in data
        assert isinstance(data["sources"], dict)

        print("✅ Collection status test passed")

        # 2. 수집 로그 조회
        response = client.get("/api/collection/logs?limit=10")
        assert response.status_code == 200

        data = response.get_json()
        assert "success" in data
        assert "logs" in data
        assert isinstance(data["logs"], list)

        print("✅ Collection logs test passed")

        # 3. 실시간 로그 조회
        response = client.get("/api/collection/logs/realtime")
        assert response.status_code == 200

        data = response.get_json()
        assert "success" in data
        assert "logs" in data

        print("✅ Realtime logs test passed")

    return True


def test_search_functionality_integration():
    """통합 테스트: 검색 기능"""
    print("\n🧪 Testing search functionality integration...")

    app = Flask(__name__)
    app.register_blueprint(unified_bp)

    with app.test_client() as client:
        # 1. 단일 IP 검색
        test_ip = "192.168.1.1"
        response = client.get("/api/search/{test_ip}")
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.get_json()
            assert "ip" in data
            assert "found" in data
            print(f"✅ Single IP search test passed - {test_ip}")
        else:
            print(f"✅ Single IP search test passed - {test_ip} not found")

        # 2. 배치 검색
        batch_data = {"ips": ["192.168.1.1", "10.0.0.1", "172.16.0.1"]}
        response = client.post(
            "/api/search", json=batch_data, content_type="application/json"
        )
        assert response.status_code == 200

        data = response.get_json()
        assert "results" in data
        assert len(data["results"]) == len(batch_data["ips"])

        print("✅ Batch search test passed")

        # 3. 잘못된 IP 형식
        response = client.get("/api/search/invalid-ip")
        assert response.status_code == 400

        print("✅ Invalid IP error handling test passed")

    return True


def test_error_handling_integration():
    """통합 테스트: 에러 처리"""
    print("\n🧪 Testing error handling integration...")

    app = Flask(__name__)
    app.register_blueprint(unified_bp)

    with app.test_client() as client:
        # 1. 잘못된 엔드포인트
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

        print("✅ 404 error handling test passed")

        # 2. 잘못된 메소드
        response = client.delete("/api/blacklist/active")
        assert response.status_code == 405

        print("✅ Method not allowed error handling test passed")

        # 3. 잘못된 Content-Type
        response = client.post("/api/search", data="invalid", content_type="text/plain")
        assert response.status_code in [400, 415]

        print("✅ Invalid content type error handling test passed")

    return True


def test_v2_api_endpoints_integration():
    """통합 테스트: V2 API 엔드포인트"""
    print("\n🧪 Testing V2 API endpoints integration...")

    app = Flask(__name__)
    app.register_blueprint(unified_bp)

    with app.test_client() as client:
        # 1. Enhanced blacklist
        response = client.get("/api/v2/blacklist/enhanced")
        assert response.status_code == 200

        data = response.get_json()
        assert "success" in data
        assert "data" in data

        print("✅ V2 enhanced blacklist test passed")

        # 2. Analytics trends
        response = client.get("/api/v2/analytics/trends")
        assert response.status_code == 200

        data = response.get_json()
        assert "success" in data

        print("✅ V2 analytics trends test passed")

        # 3. Sources status
        response = client.get("/api/v2/sources/status")
        assert response.status_code == 200

        data = response.get_json()
        assert "sources" in data

        print("✅ V2 sources status test passed")

    return True


def test_performance_integration():
    """통합 테스트: 성능 테스트"""
    print("\n🧪 Testing API performance...")

    import time

    app = Flask(__name__)
    app.register_blueprint(unified_bp)

    with app.test_client() as client:
        # 1. Health endpoint 응답 시간
        start = time.time()
        response = client.get("/health")
        elapsed = (time.time() - start) * 1000  # ms

        assert response.status_code == 200
        assert elapsed < 100, "Health endpoint too slow: {elapsed:.2f}ms"

        print(f"✅ Health endpoint performance: {elapsed:.2f}ms")

        # 2. Blacklist API 응답 시간
        start = time.time()
        response = client.get("/api/blacklist/active")
        elapsed = (time.time() - start) * 1000

        assert response.status_code == 200
        assert elapsed < 500, "Blacklist API too slow: {elapsed:.2f}ms"

        print(f"✅ Blacklist API performance: {elapsed:.2f}ms")

        # 3. 동시 요청 테스트
        import concurrent.futures

        def make_request():
            resp = client.get("/api/stats")
            return resp.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in futures]

        assert all(r == 200 for r in results), "Concurrent requests failed"

        print("✅ Concurrent requests test passed")

    return True


def run_all_integration_tests():
    """모든 통합 테스트 실행"""
    print("\n" + "=" * 60)
    print("🚀 Running Unified Routes Integration Tests")
    print("=" * 60)

    tests = [
        ("Health Endpoint", test_health_endpoint_integration),
        ("Blacklist API", test_blacklist_api_integration),
        ("Collection Management", test_collection_management_integration),
        ("Search Functionality", test_search_functionality_integration),
        ("Error Handling", test_error_handling_integration),
        ("V2 API Endpoints", test_v2_api_endpoints_integration),
        ("Performance", test_performance_integration),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"❌ {test_name} test failed")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} test failed with error: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


# 메인 실행
if __name__ == "__main__":
    success = run_all_integration_tests()
    sys.exit(0 if success else 1)
