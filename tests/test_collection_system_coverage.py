#!/usr/bin/env python3
"""
Collection System Coverage Tests - Targeting 12% coverage components
Focus on unified_collector.py, regtech_auth.py, and collection_service.py
"""

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional

import pytest
import requests

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestUnifiedCollectorCore:
    """Test unified collector core functionality - targeting 0% coverage"""

    def test_collection_status_enum(self):
        """Test CollectionStatus enum values"""
        from src.core.collectors.unified_collector import CollectionStatus
        
        assert CollectionStatus.IDLE.value == "idle"
        assert CollectionStatus.RUNNING.value == "running"
        assert CollectionStatus.COMPLETED.value == "completed"
        assert CollectionStatus.FAILED.value == "failed"
        assert CollectionStatus.CANCELLED.value == "cancelled"

    def test_collection_result_dataclass(self):
        """Test CollectionResult data class functionality"""
        from src.core.collectors.unified_collector import CollectionResult, CollectionStatus
        
        # Test basic creation
        result = CollectionResult(
            source_name="test_source",
            status=CollectionStatus.IDLE
        )
        assert result.source_name == "test_source"
        assert result.status == CollectionStatus.IDLE
        assert result.collected_count == 0
        assert result.error_count == 0
        assert result.metadata == {}

    def test_collection_result_duration_calculation(self):
        """Test duration calculation in CollectionResult"""
        from src.core.collectors.unified_collector import CollectionResult, CollectionStatus
        
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=30)
        
        result = CollectionResult(
            source_name="test",
            status=CollectionStatus.COMPLETED,
            start_time=start_time,
            end_time=end_time
        )
        
        assert result.duration is not None
        assert abs(result.duration - 30.0) < 0.1  # Allow small float precision error

    def test_collection_result_success_rate(self):
        """Test success rate calculation in CollectionResult"""
        from src.core.collectors.unified_collector import CollectionResult, CollectionStatus
        
        # Test 100% success rate
        result = CollectionResult(
            source_name="test",
            status=CollectionStatus.COMPLETED,
            collected_count=100,
            error_count=0
        )
        assert result.success_rate == 100.0
        
        # Test 80% success rate
        result = CollectionResult(
            source_name="test",
            status=CollectionStatus.COMPLETED,
            collected_count=80,
            error_count=20
        )
        assert result.success_rate == 80.0
        
        # Test 0% when no data
        result = CollectionResult(
            source_name="test",
            status=CollectionStatus.FAILED
        )
        assert result.success_rate == 0.0

    def test_collection_result_to_dict(self):
        """Test CollectionResult.to_dict() method"""
        from src.core.collectors.unified_collector import CollectionResult, CollectionStatus
        
        start_time = datetime.now()
        result = CollectionResult(
            source_name="test_source",
            status=CollectionStatus.COMPLETED,
            collected_count=50,
            error_count=5,
            start_time=start_time,
            metadata={"test": "data"}
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["source_name"] == "test_source"
        assert result_dict["status"] == "completed"
        assert result_dict["collected_count"] == 50
        assert result_dict["error_count"] == 5
        assert result_dict["metadata"] == {"test": "data"}
        assert "start_time" in result_dict

    def test_collection_config_defaults(self):
        """Test CollectionConfig default values"""
        from src.core.collectors.unified_collector import CollectionConfig
        
        config = CollectionConfig()
        assert config.enabled is True
        assert config.interval == 3600
        assert config.max_retries == 3
        assert config.timeout == 300
        assert config.parallel_workers == 1
        assert config.settings == {}

    def test_collection_config_custom_values(self):
        """Test CollectionConfig with custom values"""
        from src.core.collectors.unified_collector import CollectionConfig
        
        config = CollectionConfig(
            enabled=False,
            interval=1800,
            max_retries=5,
            timeout=600,
            parallel_workers=2,
            settings={"custom": "value"}
        )
        
        assert config.enabled is False
        assert config.interval == 1800
        assert config.max_retries == 5
        assert config.timeout == 600
        assert config.parallel_workers == 2
        assert config.settings == {"custom": "value"}


class TestBaseCollectorImplementation:
    """Test BaseCollector abstract class functionality"""

    def test_base_collector_initialization(self):
        """Test BaseCollector initialization"""
        from src.core.collectors.unified_collector import BaseCollector, CollectionConfig
        
        # Create a concrete implementation for testing
        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"
            
            async def _collect_data(self):
                return ["test_data"]
        
        config = CollectionConfig()
        collector = TestCollector("test_collector", config)
        
        assert collector.name == "test_collector"
        assert collector.config == config
        assert collector.source_type == "TEST"
        assert collector.is_running is False
        assert collector.current_result is None

    def test_base_collector_cancel_functionality(self):
        """Test BaseCollector cancel functionality"""
        from src.core.collectors.unified_collector import BaseCollector, CollectionConfig
        
        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"
            
            async def _collect_data(self):
                return ["test_data"]
        
        config = CollectionConfig()
        collector = TestCollector("test_collector", config)
        
        assert collector._cancel_requested is False
        collector.cancel()
        assert collector._cancel_requested is True

    def test_base_collector_health_check(self):
        """Test BaseCollector health_check method"""
        from src.core.collectors.unified_collector import BaseCollector, CollectionConfig
        
        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"
            
            async def _collect_data(self):
                return ["test_data"]
        
        config = CollectionConfig()
        collector = TestCollector("test_collector", config)
        
        health = collector.health_check()
        
        assert health["name"] == "test_collector"
        assert health["type"] == "TEST"
        assert health["enabled"] is True
        assert health["is_running"] is False
        assert health["last_result"] is None

    @pytest.mark.asyncio
    async def test_base_collector_collect_disabled(self):
        """Test BaseCollector collect when disabled"""
        from src.core.collectors.unified_collector import BaseCollector, CollectionConfig, CollectionStatus
        
        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"
            
            async def _collect_data(self):
                return ["test_data"]
        
        config = CollectionConfig(enabled=False)
        collector = TestCollector("test_collector", config)
        
        result = await collector.collect()
        
        assert result.status == CollectionStatus.CANCELLED
        assert result.error_message == "수집기가 비활성화되어 있습니다."

    @pytest.mark.asyncio
    async def test_base_collector_collect_already_running(self):
        """Test BaseCollector collect when already running"""
        from src.core.collectors.unified_collector import BaseCollector, CollectionConfig, CollectionStatus
        
        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"
            
            async def _collect_data(self):
                return ["test_data"]
        
        config = CollectionConfig()
        collector = TestCollector("test_collector", config)
        
        # Simulate already running
        collector._is_running = True
        
        result = await collector.collect()
        
        assert result.status == CollectionStatus.FAILED
        assert result.error_message == "수집기가 이미 실행 중입니다."

    @pytest.mark.asyncio
    async def test_base_collector_collect_success(self):
        """Test BaseCollector successful collection"""
        from src.core.collectors.unified_collector import BaseCollector, CollectionConfig, CollectionStatus
        
        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"
            
            async def _collect_data(self):
                return ["data1", "data2", "data3"]
        
        config = CollectionConfig(timeout=5)
        collector = TestCollector("test_collector", config)
        
        result = await collector.collect()
        
        assert result.status == CollectionStatus.COMPLETED
        assert result.collected_count == 3
        assert result.error_count == 0
        assert result.start_time is not None
        assert result.end_time is not None

    @pytest.mark.asyncio
    async def test_base_collector_collect_timeout(self):
        """Test BaseCollector collection timeout"""
        from src.core.collectors.unified_collector import BaseCollector, CollectionConfig, CollectionStatus
        
        class SlowTestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "SLOW_TEST"
            
            async def _collect_data(self):
                await asyncio.sleep(2)  # Longer than timeout
                return ["data"]
        
        config = CollectionConfig(timeout=0.1, max_retries=0)  # Very short timeout
        collector = SlowTestCollector("slow_collector", config)
        
        result = await collector.collect()
        
        assert result.status == CollectionStatus.FAILED
        assert "타임아웃" in result.error_message

    @pytest.mark.asyncio
    async def test_base_collector_collect_with_retries(self):
        """Test BaseCollector collection with retries"""
        from src.core.collectors.unified_collector import BaseCollector, CollectionConfig, CollectionStatus
        
        class FailingTestCollector(BaseCollector):
            def __init__(self, name, config):
                super().__init__(name, config)
                self.attempt_count = 0
            
            @property
            def source_type(self) -> str:
                return "FAILING_TEST"
            
            async def _collect_data(self):
                self.attempt_count += 1
                if self.attempt_count < 3:
                    raise Exception("Simulated failure")
                return ["success_data"]
        
        config = CollectionConfig(max_retries=3)
        collector = FailingTestCollector("failing_collector", config)
        
        result = await collector.collect()
        
        assert result.status == CollectionStatus.COMPLETED
        assert result.collected_count == 1
        assert collector.attempt_count == 3


class TestUnifiedCollectionManager:
    """Test UnifiedCollectionManager functionality"""

    def test_unified_collection_manager_initialization(self):
        """Test UnifiedCollectionManager initialization"""
        from src.core.collectors.unified_collector import UnifiedCollectionManager
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = UnifiedCollectionManager(str(config_path))
            
            assert manager.config_path == config_path
            assert manager.collectors == {}
            assert isinstance(manager.collection_history, list)
            assert manager.max_history_size == 100

    def test_unified_collection_manager_load_default_config(self):
        """Test loading default configuration"""
        from src.core.collectors.unified_collector import UnifiedCollectionManager
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "nonexistent_config.json"
            manager = UnifiedCollectionManager(str(config_path))
            
            assert manager.global_config["global_enabled"] is True
            assert "concurrent_collections" in manager.global_config
            assert "collectors" in manager.global_config

    def test_unified_collection_manager_register_collector(self):
        """Test collector registration"""
        from src.core.collectors.unified_collector import (
            UnifiedCollectionManager, BaseCollector, CollectionConfig
        )
        
        # Create test collector
        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"
            
            async def _collect_data(self):
                return ["test_data"]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = UnifiedCollectionManager(str(config_path))
            
            config = CollectionConfig()
            collector = TestCollector("test_collector", config)
            
            manager.register_collector(collector)
            
            assert "test_collector" in manager.collectors
            assert manager.get_collector("test_collector") == collector
            assert "test_collector" in manager.list_collectors()

    def test_unified_collection_manager_unregister_collector(self):
        """Test collector unregistration"""
        from src.core.collectors.unified_collector import (
            UnifiedCollectionManager, BaseCollector, CollectionConfig
        )
        
        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"
            
            async def _collect_data(self):
                return ["test_data"]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = UnifiedCollectionManager(str(config_path))
            
            config = CollectionConfig()
            collector = TestCollector("test_collector", config)
            
            manager.register_collector(collector)
            assert "test_collector" in manager.collectors
            
            manager.unregister_collector("test_collector")
            assert "test_collector" not in manager.collectors

    def test_unified_collection_manager_get_status(self):
        """Test get_status method"""
        from src.core.collectors.unified_collector import (
            UnifiedCollectionManager, BaseCollector, CollectionConfig
        )
        
        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"
            
            async def _collect_data(self):
                return ["test_data"]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = UnifiedCollectionManager(str(config_path))
            
            config = CollectionConfig()
            collector = TestCollector("test_collector", config)
            manager.register_collector(collector)
            
            status = manager.get_status()
            
            assert "global_enabled" in status
            assert "collectors" in status
            assert "running_collectors" in status
            assert "total_collectors" in status
            assert status["total_collectors"] == 1
            assert "test_collector" in status["collectors"]

    def test_unified_collection_manager_enable_disable_global(self):
        """Test global collection enable/disable"""
        from src.core.collectors.unified_collector import UnifiedCollectionManager
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = UnifiedCollectionManager(str(config_path))
            
            # Test enable
            manager.enable_global_collection()
            assert manager.global_config["global_enabled"] is True
            
            # Test disable
            manager.disable_global_collection()
            assert manager.global_config["global_enabled"] is False

    def test_unified_collection_manager_enable_disable_collector(self):
        """Test collector enable/disable"""
        from src.core.collectors.unified_collector import (
            UnifiedCollectionManager, BaseCollector, CollectionConfig
        )
        
        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"
            
            async def _collect_data(self):
                return ["test_data"]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = UnifiedCollectionManager(str(config_path))
            
            config = CollectionConfig()
            collector = TestCollector("test_collector", config)
            manager.register_collector(collector)
            
            # Test disable
            manager.disable_collector("test_collector")
            assert collector.config.enabled is False
            
            # Test enable
            manager.enable_collector("test_collector")
            assert collector.config.enabled is True

    @pytest.mark.asyncio
    async def test_unified_collection_manager_collect_single(self):
        """Test single collector collection"""
        from src.core.collectors.unified_collector import (
            UnifiedCollectionManager, BaseCollector, CollectionConfig, CollectionStatus
        )
        
        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"
            
            async def _collect_data(self):
                return ["test_data1", "test_data2"]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = UnifiedCollectionManager(str(config_path))
            
            config = CollectionConfig()
            collector = TestCollector("test_collector", config)
            manager.register_collector(collector)
            
            result = await manager.collect_single("test_collector")
            
            assert result is not None
            assert result.status == CollectionStatus.COMPLETED
            assert result.collected_count == 2
            assert len(manager.collection_history) == 1

    @pytest.mark.asyncio
    async def test_unified_collection_manager_collect_single_nonexistent(self):
        """Test single collector collection with nonexistent collector"""
        from src.core.collectors.unified_collector import UnifiedCollectionManager
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = UnifiedCollectionManager(str(config_path))
            
            result = await manager.collect_single("nonexistent_collector")
            
            assert result is None


class TestRegtechAuthModule:
    """Test REGTECH authentication module functionality"""

    def test_regtech_auth_initialization(self):
        """Test RegtechAuth initialization"""
        from src.core.collectors.regtech_auth import RegtechAuth
        
        auth = RegtechAuth(
            base_url="https://test.example.com",
            username="test_user",
            password="test_pass",
            timeout=30
        )
        
        assert auth.base_url == "https://test.example.com"
        assert auth.username == "test_user"
        assert auth.password == "test_pass"
        assert auth.timeout == 30
        assert auth.cookie_auth_mode is False
        assert auth.cookie_string is None

    def test_regtech_auth_set_cookie_string(self):
        """Test cookie string setting"""
        from src.core.collectors.regtech_auth import RegtechAuth
        
        auth = RegtechAuth("https://test.com", "user", "pass")
        
        # Test setting valid cookie string
        auth.set_cookie_string("session=abc123; path=/")
        assert auth.cookie_auth_mode is True
        assert auth.cookie_string == "session=abc123; path=/"
        
        # Test setting empty cookie string
        auth.set_cookie_string("")
        assert auth.cookie_auth_mode is False

    def test_regtech_auth_create_session(self):
        """Test session creation"""
        from src.core.collectors.regtech_auth import RegtechAuth
        
        auth = RegtechAuth("https://test.com", "user", "pass")
        session = auth.create_session()
        
        assert isinstance(session, requests.Session)
        assert "User-Agent" in session.headers
        assert "Mozilla" in session.headers["User-Agent"]
        assert "Accept" in session.headers

    def test_regtech_auth_verify_login_success_indicators(self):
        """Test login success verification logic"""
        from src.core.collectors.regtech_auth import RegtechAuth
        
        auth = RegtechAuth("https://test.com", "user", "pass")
        
        # Mock response with success indicator
        mock_response = Mock()
        mock_response.text = "<html>Welcome to Dashboard</html>"
        mock_response.url = "https://test.com/dashboard"
        mock_response.status_code = 200
        
        result = auth._verify_login_success(mock_response)
        assert result is True

    def test_regtech_auth_verify_login_failure_indicators(self):
        """Test login failure verification logic"""
        from src.core.collectors.regtech_auth import RegtechAuth
        
        auth = RegtechAuth("https://test.com", "user", "pass")
        
        # Mock response with failure indicator
        mock_response = Mock()
        mock_response.text = "<html>로그인 실패</html>"
        mock_response.url = "https://test.com/login"
        mock_response.status_code = 200
        
        result = auth._verify_login_success(mock_response)
        assert result is False

    @patch('requests.Session.get')
    def test_regtech_auth_logout_success(self, mock_get):
        """Test successful logout"""
        from src.core.collectors.regtech_auth import RegtechAuth
        
        # Mock successful logout response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        auth = RegtechAuth("https://test.com", "user", "pass")
        auth.session = requests.Session()
        
        result = auth.logout()
        assert result is True
        assert auth.session is None

    @patch('requests.Session.get')
    def test_regtech_auth_logout_failure(self, mock_get):
        """Test logout failure handling"""
        from src.core.collectors.regtech_auth import RegtechAuth
        
        # Mock logout failure
        mock_get.side_effect = requests.exceptions.RequestException("Network error")
        
        auth = RegtechAuth("https://test.com", "user", "pass")
        auth.session = requests.Session()
        
        result = auth.logout()
        assert result is False
        assert auth.session is None  # Should still clean up session


class TestCollectionServiceMixin:
    """Test collection service mixin functionality"""

    def test_collection_service_mixin_initialization(self):
        """Test CollectionServiceMixin initialization"""
        from src.core.services.collection_service import CollectionServiceMixin
        
        mixin = CollectionServiceMixin()
        
        assert mixin.status is not None
        assert mixin.status["enabled"] is False
        assert "sources" in mixin.status
        assert "REGTECH" in mixin.status["sources"]
        assert "SECUDIUM" in mixin.status["sources"]
        assert mixin.collection_enabled is False
        assert mixin.daily_collection_enabled is False

    def test_collection_service_enable_collection(self):
        """Test enable collection functionality"""
        from src.core.services.collection_service import CollectionServiceMixin
        
        # Create a test class that includes the mixin
        class TestService(CollectionServiceMixin):
            def __init__(self):
                super().__init__()
                self.collection_manager = Mock()
                self.logger = Mock()
            
            def clear_all_database_data(self):
                return {"success": True, "cleared": 100}
            
            def add_collection_log(self, source, action, details=None):
                pass
        
        service = TestService()
        result = service.enable_collection()
        
        assert result["success"] is True
        assert service.collection_enabled is True
        assert service.daily_collection_enabled is True
        assert service.collection_manager.collection_enabled is True

    def test_collection_service_disable_collection(self):
        """Test disable collection functionality"""
        from src.core.services.collection_service import CollectionServiceMixin
        
        class TestService(CollectionServiceMixin):
            def __init__(self):
                super().__init__()
                self.collection_manager = Mock()
                self.logger = Mock()
            
            def add_collection_log(self, source, action, details=None):
                pass
        
        service = TestService()
        service.collection_enabled = True
        service.daily_collection_enabled = True
        
        result = service.disable_collection()
        
        assert result["success"] is True
        assert service.collection_enabled is False
        assert service.daily_collection_enabled is False
        assert service.collection_manager.collection_enabled is False

    def test_collection_service_get_collection_status(self):
        """Test get collection status functionality"""
        from src.core.services.collection_service import CollectionServiceMixin
        
        class TestService(CollectionServiceMixin):
            def __init__(self):
                super().__init__()
                self.collection_manager = Mock()
                self.logger = Mock()
                self._components = {"regtech": Mock(), "secudium": Mock()}
            
            def get_collection_logs(self, limit=5):
                return [{"id": 1, "message": "test log"}]
        
        service = TestService()
        status = service.get_collection_status()
        
        assert "collection_enabled" in status
        assert "daily_collection_enabled" in status
        assert "sources" in status
        assert "recent_logs" in status
        assert "timestamp" in status
        assert "regtech" in status["sources"]
        assert "secudium" in status["sources"]

    def test_collection_service_trigger_collection(self):
        """Test trigger collection functionality"""
        from src.core.services.collection_service import CollectionServiceMixin
        
        class TestService(CollectionServiceMixin):
            def __init__(self):
                super().__init__()
                self._components = {"regtech": Mock(), "secudium": Mock()}
        
        service = TestService()
        
        # Test triggering all collections
        result = service.trigger_collection("all")
        assert "전체 수집이 시작되었습니다" in result
        
        # Test triggering regtech collection
        result = service.trigger_collection("regtech")
        assert "REGTECH 수집이 시작되었습니다" in result
        
        # Test triggering secudium collection
        result = service.trigger_collection("secudium")
        assert "SECUDIUM 수집이 시작되었습니다" in result
        
        # Test unknown source
        result = service.trigger_collection("unknown")
        assert "알 수 없는 소스" in result

    def test_collection_service_search_ip(self):
        """Test IP search functionality"""
        from src.core.services.collection_service import CollectionServiceMixin
        
        class TestService(CollectionServiceMixin):
            def __init__(self):
                super().__init__()
                self.blacklist_manager = Mock()
                self.logger = Mock()
        
        service = TestService()
        
        # Mock successful search
        service.blacklist_manager.search_ip.return_value = {
            "found": True,
            "source": "REGTECH",
            "threat_level": "high"
        }
        
        result = service.search_ip("192.168.1.1")
        
        assert result["success"] is True
        assert result["ip"] == "192.168.1.1"
        assert "result" in result
        assert "timestamp" in result

    def test_collection_service_search_ip_error(self):
        """Test IP search error handling"""
        from src.core.services.collection_service import CollectionServiceMixin
        
        class TestService(CollectionServiceMixin):
            def __init__(self):
                super().__init__()
                self.blacklist_manager = Mock()
                self.logger = Mock()
        
        service = TestService()
        
        # Mock search error
        service.blacklist_manager.search_ip.side_effect = Exception("Search failed")
        
        result = service.search_ip("192.168.1.1")
        
        assert result["success"] is False
        assert result["ip"] == "192.168.1.1"
        assert "error" in result
        assert "timestamp" in result


if __name__ == "__main__":
    # Validation tests for collection system components
    import sys
    
    all_validation_failures = []
    total_tests = 0
    
    # Test 1: Core classes can be imported
    total_tests += 1
    try:
        from src.core.collectors.unified_collector import (
            CollectionStatus, CollectionResult, CollectionConfig, BaseCollector
        )
        from src.core.collectors.regtech_auth import RegtechAuth
        from src.core.services.collection_service import CollectionServiceMixin
    except ImportError as e:
        all_validation_failures.append(f"Import test failed: {e}")
    
    # Test 2: Basic functionality works
    total_tests += 1
    try:
        from src.core.collectors.unified_collector import CollectionResult, CollectionStatus
        
        result = CollectionResult("test", CollectionStatus.COMPLETED, collected_count=5)
        if result.success_rate != 100.0:
            all_validation_failures.append(f"Success rate calculation failed: expected 100.0, got {result.success_rate}")
    except Exception as e:
        all_validation_failures.append(f"Basic functionality test failed: {e}")
    
    # Test 3: Auth module works
    total_tests += 1
    try:
        from src.core.collectors.regtech_auth import RegtechAuth
        
        auth = RegtechAuth("https://test.com", "user", "pass")
        auth.set_cookie_string("test=value")
        if not auth.cookie_auth_mode:
            all_validation_failures.append("Cookie auth mode not set correctly")
    except Exception as e:
        all_validation_failures.append(f"Auth module test failed: {e}")
    
    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Collection system coverage tests are validated and ready for execution")
        sys.exit(0)