#!/usr/bin/env python3
"""
통합 테스트: Collection System
수집 관리자와 REGTECH 수집기 통합 테스트
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.core.collection_manager import CollectionManager
from src.core.regtech_simple_collector import RegtechSimpleCollector
from src.core.unified_service import UnifiedBlacklistService


def test_collection_manager_initialization():
    """통합 테스트: CollectionManager 초기화"""
    print("\n🧪 Testing CollectionManager initialization...")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        config_path = os.path.join(tmpdir, "config.json")

        # 1. 첫 번째 초기화 - 기본값 확인
        manager = CollectionManager(db_path=db_path, config_path=config_path)

        assert (
            manager.collection_enabled == False
        ), "Collection should be disabled by default"
        assert os.path.exists(config_path), "Config file should be created"

        print("✅ Initial state test passed")

        # 2. 환경변수 우선순위 테스트
        os.environ["COLLECTION_ENABLED"] = "true"
        manager2 = CollectionManager(db_path=db_path, config_path=config_path)

        assert (
            manager2.collection_enabled == True
        ), "Environment variable should override"

        del os.environ["COLLECTION_ENABLED"]
        print("✅ Environment variable priority test passed")

        # 3. 설정 지속성 테스트
        manager.enable_collection()
        manager3 = CollectionManager(db_path=db_path, config_path=config_path)

        assert manager3.collection_enabled == True, "Setting should persist"

        print("✅ Settings persistence test passed")

    return True


def test_collection_enable_disable_cycle():
    """통합 테스트: 수집 활성화/비활성화 사이클"""
    print("\n🧪 Testing collection enable/disable cycle...")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        config_path = os.path.join(tmpdir, "config.json")

        manager = CollectionManager(db_path=db_path, config_path=config_path)

        # 1. 수집 활성화
        result = manager.enable_collection()
        assert result["success"] == True
        assert manager.collection_enabled == True
        assert result["action"] == "enabled"

        print("✅ Enable collection test passed")

        # 2. 중복 활성화 시도
        result = manager.enable_collection()
        assert result["success"] == True
        assert result["message"] == "Collection already enabled"

        print("✅ Duplicate enable test passed")

        # 3. 수집 비활성화
        result = manager.disable_collection()
        assert result["success"] == True
        assert manager.collection_enabled == False
        assert result["action"] == "disabled"

        print("✅ Disable collection test passed")

        # 4. 소스별 활성화/비활성화
        manager.enable_source("regtech")
        assert manager.sources["regtech"]["enabled"] == True

        manager.disable_source("regtech")
        assert manager.sources["regtech"]["enabled"] == False

        print("✅ Source-specific control test passed")

    return True


def test_regtech_collector_mock_integration():
    """통합 테스트: REGTECH 수집기 (Mock 사용)"""
    print("\n🧪 Testing REGTECH collector integration (mocked)...")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")

        # Mock responses
        mock_response_login = Mock()
        mock_response_login.status_code = 200
        mock_response_login.text = "success"
        mock_response_login.url = "https://example.com/success"

        mock_response_data = Mock()
        mock_response_data.status_code = 200
        mock_response_data.json.return_value = {
            "result": {
                "data": [
                    {
                        "type": "C&C",
                        "ip": "192.168.1.1",
                        "port": "443",
                        "url": "malware.com",
                        "create_time": "2024-01-15",
                    },
                    {
                        "type": "Malware",
                        "ip": "10.0.0.1",
                        "port": "80",
                        "url": "phishing.com",
                        "create_time": "2024-01-16",
                    },
                ]
            }
        }

        with patch("requests.Session") as mock_session:
            session_instance = Mock()
            mock_session.return_value = session_instance

            # Configure mock session
            session_instance.get.side_effect = [
                mock_response_login,  # login page
                mock_response_data,  # data fetch
            ]
            session_instance.post.return_value = mock_response_login

            # Create collector
            collector = RegtechSimpleCollector(
                username="test_user", password="test_pass", db_path=db_path
            )

            # Collect data
            ips = collector.collect_ips()

            assert len(ips) == 2, "Expected 2 IPs, got {len(ips)}"
            assert ips[0]["ip"] == "192.168.1.1"
            assert ips[0]["source"] == "REGTECH"
            assert ips[1]["ip"] == "10.0.0.1"

            print(f"✅ Mock data collection test passed ({len(ips)} IPs)")

            # Verify session was used correctly
            assert session_instance.get.called
            assert session_instance.post.called

            print("✅ Session interaction test passed")

    return True


def test_data_lifecycle_integration():
    """통합 테스트: 데이터 생명주기"""
    print("\n🧪 Testing data lifecycle integration...")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        config_path = os.path.join(tmpdir, "config.json")

        # Create manager
        manager = CollectionManager(db_path=db_path, config_path=config_path)

        # Initialize database
        import sqlite3

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create tables
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS blacklist_ip (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL,
                source TEXT,
                detection_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """
        )

        # 1. Insert test data with different ages
        now = datetime.now()
        test_data = [
            ("192.168.1.1", "REGTECH", now - timedelta(days=10)),  # Recent
            ("10.0.0.1", "REGTECH", now - timedelta(days=89)),  # Almost expired
            ("172.16.0.1", "REGTECH", now - timedelta(days=91)),  # Expired
        ]

        for ip, source, detection_date in test_data:
            expires_at = detection_date + timedelta(days=90)
            cursor.execute(
                """
                INSERT INTO blacklist_ip (
                    ip,
                    source,
                    detection_date,
                    expires_at,
                    is_active
                )
                VALUES (?, ?, ?, ?, ?)
            """,
                (ip, source, detection_date, expires_at, 1),
            )

        conn.commit()

        # 2. Test data retrieval
        cursor.execute("SELECT COUNT(*) FROM blacklist_ip")
        total_count = cursor.fetchone()[0]
        assert total_count == 3, "Expected 3 IPs, got {total_count}"

        print("✅ Data insertion test passed")

        # 3. Test cleanup (simulated)
        # Update expired records
        cursor.execute(
            """
            UPDATE blacklist_ip
            SET is_active = 0
            WHERE expires_at < ?
        """,
            (now,),
        )

        cursor.execute("SELECT COUNT(*) FROM blacklist_ip WHERE is_active = 1")
        active_count = cursor.fetchone()[0]
        assert active_count == 2, "Expected 2 active IPs, got {active_count}"

        print("✅ Expiration handling test passed")

        # 4. Test statistics
        stats = manager.get_collection_status()
        assert "sources" in stats
        assert "regtech" in stats["sources"]

        print("✅ Statistics calculation test passed")

        conn.close()

    return True


def test_collection_error_handling():
    """통합 테스트: 수집 에러 처리"""
    print("\n🧪 Testing collection error handling...")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")

        # Test invalid credentials
        with patch("requests.Session") as mock_session:
            session_instance = Mock()
            mock_session.return_value = session_instance

            # Simulate login failure
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "error"
            mock_response.url = "https://example.com/login?error=true"

            session_instance.get.return_value = mock_response
            session_instance.post.return_value = mock_response

            collector = RegtechSimpleCollector(
                username="invalid", password="invalid", db_path=db_path
            )

            # Should handle error gracefully
            ips = collector.collect_ips()
            assert len(ips) == 0, "Should return empty list on auth failure"

            print("✅ Auth failure handling test passed")

        # Test network error
        with patch("requests.Session") as mock_session:
            session_instance = Mock()
            mock_session.return_value = session_instance

            # Simulate network error
            session_instance.get.side_effect = Exception("Network error")

            collector = RegtechSimpleCollector(
                username="test", password="test", db_path=db_path
            )

            ips = collector.collect_ips()
            assert len(ips) == 0, "Should return empty list on network error"

            print("✅ Network error handling test passed")

    return True


def test_unified_service_integration():
    """통합 테스트: UnifiedBlacklistService"""
    print("\n🧪 Testing UnifiedBlacklistService integration...")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock environment
        os.environ["BLACKLIST_DB_PATH"] = os.path.join(tmpdir, "test.db")

        try:
            # Create service
            service = UnifiedBlacklistService()

            # 1. Test service initialization
            assert service._running == True, "Service should be running"
            assert hasattr(
                service, "blacklist_manager"
            ), "Should have blacklist_manager"
            assert hasattr(
                service, "collection_manager"
            ), "Should have collection_manager"

            print("✅ Service initialization test passed")

            # 2. Test health check
            health = service.get_system_health()
            assert "total_ips" in health
            assert "active_ips" in health
            assert "collection_enabled" in health

            print("✅ Health check test passed")

            # 3. Test collection control
            result = service.toggle_collection(enable=True)
            assert "success" in result

            result = service.toggle_collection(enable=False)
            assert "success" in result

            print("✅ Collection control test passed")

            # 4. Test logging
            service.add_collection_log("test", "test_action", {"test": "data"})
            logs = service.get_collection_logs(10)
            assert isinstance(logs, list)

            print("✅ Logging system test passed")

        finally:
            if "BLACKLIST_DB_PATH" in os.environ:
                del os.environ["BLACKLIST_DB_PATH"]

    return True


def run_all_collection_integration_tests():
    """모든 수집 시스템 통합 테스트 실행"""
    print("\n" + "=" * 60)
    print("🚀 Running Collection System Integration Tests")
    print("=" * 60)

    tests = [
        ("CollectionManager Initialization", test_collection_manager_initialization),
        ("Collection Enable/Disable Cycle", test_collection_enable_disable_cycle),
        ("REGTECH Collector Mock", test_regtech_collector_mock_integration),
        ("Data Lifecycle", test_data_lifecycle_integration),
        ("Error Handling", test_collection_error_handling),
        ("UnifiedService Integration", test_unified_service_integration),
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
    success = run_all_collection_integration_tests()
    sys.exit(0 if success else 1)
