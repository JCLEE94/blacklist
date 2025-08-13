#!/usr/bin/env python3
"""
통합 테스트: End-to-End (E2E)
전체 시스템 플로우 테스트
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


from src.core.app_compact import create_compact_app
from src.core.container import get_container


def test_complete_data_flow():
    """E2E 테스트: 전체 데이터 플로우"""
    print("\n🧪 Testing complete data flow (E2E)...")

    with tempfile.TemporaryDirectory() as tmpdir:
        # 환경 설정
        os.environ["FLASK_ENV"] = "testing"
        os.environ["DATABASE_URL"] = "sqlite:///{tmpdir}/test.db"
        os.environ["COLLECTION_ENABLED"] = "false"

        try:
            # 1. 애플리케이션 초기화
            print("\n1️⃣ Initializing application...")
            app = create_compact_app("testing")

            with app.test_client() as client:
                # 2. 헬스체크
                print("2️⃣ Health check...")
                response = client.get("/health")
                assert response.status_code == 200
                health_data = response.get_json()
                assert health_data["status"] in ["healthy", "degraded"]
                print("✅ Application is healthy")

                # 3. 초기 상태 확인
                print("\n3️⃣ Checking initial state...")
                response = client.get("/api/stats")
                assert response.status_code == 200
                stats = response.get_json()
                initial_count = stats.get("total_ips", 0)
                print(f"✅ Initial IP count: {initial_count}")

                # 4. 수집 활성화
                print("\n4️⃣ Enabling collection...")
                response = client.post("/api/collection/enable")
                assert response.status_code in [200, 202]
                result = response.get_json()
                assert result.get("success") or result.get("action") == "enabled"
                print("✅ Collection enabled")

                # 5. Mock 데이터 삽입 (실제 수집 대신)
                print("\n5️⃣ Simulating data collection...")
                container = get_container()
                blacklist_manager = container.resolve("blacklist_manager")

                if blacklist_manager:
                    # Mock IPs 추가
                    mock_ips = [
                        {
                            "ip": "192.168.1.100",
                            "source": "REGTECH",
                            "threat_type": "C&C",
                        },
                        {
                            "ip": "10.0.0.50",
                            "source": "REGTECH",
                            "threat_type": "Malware",
                        },
                        {
                            "ip": "172.16.0.10",
                            "source": "PUBLIC",
                            "threat_type": "Phishing",
                        },
                    ]

                    for ip_data in mock_ips:
                        blacklist_manager.add_ip(
                            ip=ip_data["ip"],
                            source=ip_data["source"],
                            metadata={"threat_type": ip_data["threat_type"]},
                        )

                    print(f"✅ Added {len(mock_ips)} test IPs")

                # 6. 데이터 검증
                print("\n6️⃣ Verifying data...")

                # Active IPs 확인
                response = client.get("/api/blacklist/active")
                assert response.status_code == 200
                active_ips = response.data.decode("utf-8").strip().split("\n")
                active_ips = [ip for ip in active_ips if ip]  # 빈 줄 제거
                print(f"✅ Active IPs: {len(active_ips)}")

                # FortiGate 형식 확인
                response = client.get("/api/fortigate")
                assert response.status_code == 200
                fortigate_data = response.get_json()
                assert "blacklist" in fortigate_data
                assert (
                    len(fortigate_data["blacklist"]) >= len(mock_ips)
                    if blacklist_manager
                    else True
                )
                print("✅ FortiGate format verified")

                # 7. 검색 기능 테스트
                print("\n7️⃣ Testing search functionality...")
                if len(active_ips) > 0:
                    test_ip = active_ips[0]
                    response = client.get("/api/search/{test_ip}")
                    assert response.status_code == 200
                    search_result = response.get_json()
                    assert search_result["found"] == True
                    print(f"✅ Search found IP: {test_ip}")

                # 8. 통계 업데이트 확인
                print("\n8️⃣ Checking statistics update...")
                response = client.get("/api/stats")
                assert response.status_code == 200
                final_stats = response.get_json()
                final_count = final_stats.get("total_ips", 0)
                print(f"✅ Final IP count: {final_count}")

                # 9. 수집 비활성화
                print("\n9️⃣ Disabling collection...")
                response = client.post("/api/collection/disable")
                assert response.status_code == 200
                print("✅ Collection disabled")

                print("\n✅ Complete data flow test passed!")

        finally:
            # 환경 정리
            for key in ["FLASK_ENV", "DATABASE_URL", "COLLECTION_ENABLED"]:
                if key in os.environ:
                    del os.environ[key]

    return True


def test_deployment_pipeline_simulation():
    """E2E 테스트: 배포 파이프라인 시뮬레이션"""
    print("\n🧪 Testing deployment pipeline simulation (E2E)...")

    # 1. 코드 변경 시뮬레이션
    print("\n1️⃣ Simulating code change...")
    version_file = Path("src/core/__init__.py")
    if version_file.exists():
        content = version_file.read_text()
        if "__version__" in content:
            print("✅ Version file found")

    # 2. CI/CD 워크플로우 검증
    print("\n2️⃣ Validating CI/CD workflow...")
    workflow_file = Path(".github/workflows/simple-cicd.yml")
    assert workflow_file.exists(), "CI/CD workflow not found"
    print("✅ CI/CD workflow exists")

    # 3. Docker 빌드 시뮬레이션
    print("\n3️⃣ Simulating Docker build...")
    dockerfile = Path("deployment/Dockerfile")
    assert dockerfile.exists(), "Dockerfile not found"

    # Dockerfile 내용 검증
    with open(dockerfile, "r") as f:
        dockerfile_content = f.read()
        assert "FROM python:" in dockerfile_content
        assert "COPY requirements.txt" in dockerfile_content
        assert "CMD" in dockerfile_content or "ENTRYPOINT" in dockerfile_content
    print("✅ Dockerfile validated")

    # 4. Kubernetes 매니페스트 검증
    print("\n4️⃣ Validating Kubernetes manifests...")
    k8s_base = Path("k8s-gitops/base")
    assert k8s_base.exists(), "K8s base directory not found"

    required_manifests = ["deployment.yaml", "service.yaml", "kustomization.yaml"]
    for manifest in required_manifests:
        assert (k8s_base / manifest).exists(), "{manifest} not found"
    print("✅ All K8s manifests present")

    # 5. ArgoCD 설정 검증
    print("\n5️⃣ Validating ArgoCD configuration...")
    argocd_app = Path("k8s-gitops/argocd/blacklist-app-https.yaml")
    assert argocd_app.exists(), "ArgoCD application not found"
    print("✅ ArgoCD application configured")

    # 6. 배포 스크립트 검증
    print("\n6️⃣ Validating deployment scripts...")
    deploy_scripts = ["scripts/k8s-management.sh", "scripts/check-deployment-status.sh"]

    for script in deploy_scripts:
        script_path = Path(script)
        if script_path.exists():
            print(f"✅ {script} found")

    print("\n✅ Deployment pipeline simulation passed!")
    return True


def test_error_recovery_flow():
    """E2E 테스트: 에러 복구 플로우"""
    print("\n🧪 Testing error recovery flow (E2E)...")

    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["FLASK_ENV"] = "testing"

        try:
            app = create_compact_app("testing")

            with app.test_client() as client:
                # 1. 잘못된 요청 처리
                print("\n1️⃣ Testing invalid request handling...")
                response = client.get("/api/search/invalid-ip-format")
                assert response.status_code == 400
                error_data = response.get_json()
                assert "error" in error_data
                print("✅ Invalid IP handled correctly")

                # 2. 존재하지 않는 엔드포인트
                print("\n2️⃣ Testing non-existent endpoint...")
                response = client.get("/api/nonexistent")
                assert response.status_code == 404
                print("✅ 404 error handled correctly")

                # 3. 잘못된 메소드
                print("\n3️⃣ Testing wrong HTTP method...")
                response = client.delete("/api/blacklist/active")
                assert response.status_code == 405
                print("✅ Method not allowed handled correctly")

                # 4. 빈 POST 요청
                print("\n4️⃣ Testing empty POST request...")
                response = client.post(
                    "/api/search", data="", content_type="application/json"
                )
                assert response.status_code in [400, 422]
                print("✅ Empty request handled correctly")

                # 5. 대용량 요청 시뮬레이션
                print("\n5️⃣ Testing large batch request...")
                large_batch = {"ips": ["192.168.1." + str(i) for i in range(1000)]}
                response = client.post(
                    "/api/search", json=large_batch, content_type="application/json"
                )
                # 요청은 성공해야 함
                assert response.status_code == 200
                print("✅ Large batch handled successfully")

                print("\n✅ Error recovery flow test passed!")

        finally:
            if "FLASK_ENV" in os.environ:
                del os.environ["FLASK_ENV"]

    return True


def test_performance_under_load():
    """E2E 테스트: 부하 상황에서의 성능"""
    print("\n🧪 Testing performance under load (E2E)...")

    import concurrent.futures
    import time

    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["FLASK_ENV"] = "testing"

        try:
            app = create_compact_app("testing")

            with app.test_client() as client:
                # 1. 단일 요청 응답 시간
                print("\n1️⃣ Testing single request performance...")
                start = time.time()
                response = client.get("/health")
                elapsed = (time.time() - start) * 1000

                assert response.status_code == 200
                assert elapsed < 100, "Health check too slow: {elapsed:.2f}ms"
                print(f"✅ Single request: {elapsed:.2f}ms")

                # 2. 동시 요청 테스트
                print("\n2️⃣ Testing concurrent requests...")

                def make_request(endpoint):
                    start = time.time()
                    resp = client.get(endpoint)
                    elapsed = (time.time() - start) * 1000
                    return resp.status_code, elapsed

                # 10개 동시 요청
                endpoints = ["/health", "/api/stats"] * 5

                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(make_request, ep) for ep in endpoints]
                    results = [f.result() for f in futures]

                # 모든 요청 성공 확인
                statuses = [r[0] for r in results]
                assert all(
                    s == 200 for s in statuses
                ), "Some concurrent requests failed"

                # 평균 응답 시간
                avg_time = sum(r[1] for r in results) / len(results)
                print(f"✅ Concurrent requests avg: {avg_time:.2f}ms")

                # 3. 지속적인 부하 테스트
                print("\n3️⃣ Testing sustained load...")
                sustained_times = []

                for i in range(20):
                    start = time.time()
                    response = client.get("/api/blacklist/active")
                    elapsed = (time.time() - start) * 1000
                    sustained_times.append(elapsed)

                    assert response.status_code == 200

                avg_sustained = sum(sustained_times) / len(sustained_times)
                max_sustained = max(sustained_times)

                print(
                    "✅ Sustained load - Avg: {avg_sustained:.2f}ms, Max: {max_sustained:.2f}ms"
                )

                # 성능 기준
                assert (
                    avg_sustained < 50
                ), "Average response time too high: {avg_sustained:.2f}ms"
                assert (
                    max_sustained < 200
                ), "Max response time too high: {max_sustained:.2f}ms"

                print("\n✅ Performance under load test passed!")

        finally:
            if "FLASK_ENV" in os.environ:
                del os.environ["FLASK_ENV"]

    return True


def test_multi_source_integration():
    """E2E 테스트: 다중 소스 통합"""
    print("\n🧪 Testing multi-source integration (E2E)...")

    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["FLASK_ENV"] = "testing"
        os.environ["DATABASE_URL"] = "sqlite:///{tmpdir}/test.db"

        try:
            # Mock 수집기 설정
            with patch(
                "src.core.regtech_simple_collector.RegtechSimpleCollector"
            ) as mock_regtech:
                # Mock 수집 데이터
                mock_regtech_instance = Mock()
                mock_regtech_instance.collect_ips.return_value = [
                    {"ip": "192.168.1.1", "source": "REGTECH", "threat_type": "C&C"},
                    {
                        "ip": "192.168.1.2",
                        "source": "REGTECH",
                        "threat_type": "Malware",
                    },
                ]
                mock_regtech.return_value = mock_regtech_instance

                app = create_compact_app("testing")

                with app.test_client() as client:
                    # 1. 수집 상태 확인
                    print("\n1️⃣ Checking collection status...")
                    response = client.get("/api/collection/status")
                    assert response.status_code == 200
                    status = response.get_json()
                    print(
                        "✅ Collection enabled: {status.get('collection_enabled', False)}"
                    )

                    # 2. V2 소스 상태 확인
                    print("\n2️⃣ Checking source status...")
                    response = client.get("/api/v2/sources/status")
                    assert response.status_code == 200
                    sources = response.get_json()
                    assert "sources" in sources
                    print(f"✅ Sources configured: {list(sources['sources'].keys())}")

                    # 3. 통계 확인
                    print("\n3️⃣ Checking statistics by source...")
                    response = client.get("/api/stats")
                    assert response.status_code == 200
                    stats = response.get_json()

                    if "sources" in stats:
                        for source, count in stats["sources"].items():
                            print(f"  {source}: {count} IPs")

                    print("\n✅ Multi-source integration test passed!")

        finally:
            for key in ["FLASK_ENV", "DATABASE_URL"]:
                if key in os.environ:
                    del os.environ[key]

    return True


def run_all_e2e_integration_tests():
    """모든 E2E 통합 테스트 실행"""
    print("\n" + "=" * 60)
    print("🚀 Running End-to-End Integration Tests")
    print("=" * 60)

    tests = [
        ("Complete Data Flow", test_complete_data_flow),
        ("Deployment Pipeline Simulation", test_deployment_pipeline_simulation),
        ("Error Recovery Flow", test_error_recovery_flow),
        ("Performance Under Load", test_performance_under_load),
        ("Multi-Source Integration", test_multi_source_integration),
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


if __name__ == "__main__":
    success = run_all_e2e_integration_tests()
    sys.exit(0 if success else 1)
