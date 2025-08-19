#!/usr/bin/env python3
"""
Collection Auth & Service Tests - Authentication and service mixin functionality
Focus on regtech_auth.py and collection_service.py components
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
    # Validation tests for collection auth and service components
    import sys
    
    all_validation_failures = []
    total_tests = 0
    
    # Test 1: Core classes can be imported
    total_tests += 1
    try:
        from src.core.collectors.regtech_auth import RegtechAuth
        from src.core.services.collection_service import CollectionServiceMixin
    except ImportError as e:
        all_validation_failures.append(f"Import test failed: {e}")
    
    # Test 2: Auth functionality works
    total_tests += 1
    try:
        from src.core.collectors.regtech_auth import RegtechAuth
        
        auth = RegtechAuth("https://test.com", "user", "pass")
        auth.set_cookie_string("test=value")
        if not auth.cookie_auth_mode:
            all_validation_failures.append("Cookie auth mode not set correctly")
    except Exception as e:
        all_validation_failures.append(f"Auth module test failed: {e}")
    
    # Test 3: Service mixin works
    total_tests += 1
    try:
        from src.core.services.collection_service import CollectionServiceMixin
        
        mixin = CollectionServiceMixin()
        if mixin.status is None or "enabled" not in mixin.status:
            all_validation_failures.append("Service mixin status not initialized correctly")
    except Exception as e:
        all_validation_failures.append(f"Service mixin test failed: {e}")
    
    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Collection auth and service tests are validated and ready for execution")
        sys.exit(0)
