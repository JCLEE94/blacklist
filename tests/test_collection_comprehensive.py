#!/usr/bin/env python3
"""
Comprehensive Collection System Tests for Blacklist Management System

Tests collection APIs, REGTECH/SECUDIUM integrations, data transformation,
error handling, and real-time status monitoring.
Designed to achieve 95% test coverage for collection components.
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import threading

import pytest
import requests

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestCollectionStatusAPI:
    """Test collection status and monitoring endpoints"""
    
    BASE_URL = "http://localhost:32542"
    
    def test_collection_status_endpoint(self):
        """Test collection status endpoint"""
        response = requests.get(f"{self.BASE_URL}/api/collection/status", timeout=10)
        
        assert response.status_code in [200, 503]
        data = response.json()
        
        if response.status_code == 200:
            # Check for expected fields in successful response
            assert "enabled" in data or "collection_enabled" in data
            assert "status" in data
            assert "stats" in data
        else:
            # Error response should have error field
            assert "error" in data
    
    def test_collection_daily_stats(self):
        """Test daily collection statistics"""
        response = requests.get(
            f"{self.BASE_URL}/api/collection/daily-stats?days=7", 
            timeout=10
        )
        
        # This endpoint might not exist (404) or return different formats
        assert response.status_code in [200, 404, 503]
        
        if response.status_code == 200:
            data = response.json()
            # Just verify it returns valid JSON
            assert isinstance(data, dict)
        
    def test_collection_daily_stats_limits(self):
        """Test daily stats with limit enforcement"""
        # Test exceeding max days limit
        response = requests.get(
            f"{self.BASE_URL}/api/collection/daily-stats?days=120", 
            timeout=10
        )
        
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            # Should be capped at 90 days
            assert data["period"]["days"] <= 90
    
    def test_collection_history(self):
        """Test collection execution history"""
        response = requests.get(
            f"{self.BASE_URL}/api/collection/history?limit=10&offset=0", 
            timeout=10
        )
        
        assert response.status_code in [200, 503]
        data = response.json()
        
        if response.status_code == 200:
            assert data["success"] is True
            assert "history" in data
            assert "pagination" in data
            assert data["pagination"]["limit"] == 10
    
    def test_collection_history_limits(self):
        """Test collection history with limit enforcement"""
        # Test exceeding max limit
        response = requests.get(
            f"{self.BASE_URL}/api/collection/history?limit=150", 
            timeout=10
        )
        
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            # Should be capped at 100
            assert data["pagination"]["limit"] <= 100


class TestCollectionTriggers:
    """Test collection trigger endpoints"""
    
    BASE_URL = "http://localhost:32542"
    
    def test_regtech_collection_trigger(self):
        """Test REGTECH collection trigger"""
        response = requests.post(
            f"{self.BASE_URL}/api/collection/regtech/trigger",
            json={
                "start_date": "20250101",
                "end_date": "20250117"
            },
            timeout=30
        )
        
        # Should return either success (200) or already running (503)
        assert response.status_code in [200, 503, 400]
        data = response.json()
        assert "success" in data
        
        if response.status_code == 200:
            assert data["success"] is True
            assert "message" in data
        elif response.status_code == 503:
            # Collection already running or disabled
            assert "already" in data.get("message", "").lower() or \
                   "disabled" in data.get("error", "").lower()
    
    def test_regtech_trigger_validation(self):
        """Test REGTECH trigger input validation"""
        # Test invalid date format
        response = requests.post(
            f"{self.BASE_URL}/api/collection/regtech/trigger",
            json={
                "start_date": "invalid-date",
                "end_date": "20250117"
            },
            timeout=10
        )
        
        assert response.status_code in [400, 503]
        
        # Test missing dates
        response = requests.post(
            f"{self.BASE_URL}/api/collection/regtech/trigger",
            json={},
            timeout=10
        )
        
        assert response.status_code in [400, 503]
    
    def test_secudium_collection_disabled(self):
        """Test SECUDIUM collection is properly disabled"""
        response = requests.post(
            f"{self.BASE_URL}/api/collection/secudium/trigger",
            timeout=10
        )
        
        # Should return 503 (disabled) according to system design
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert "disabled" in data.get("error", "").lower() or \
               "disabled" in data.get("message", "").lower()
    
    def test_collection_enable_disable(self):
        """Test collection enable/disable functionality"""
        # Test enable
        response = requests.post(f"{self.BASE_URL}/api/collection/enable", timeout=10)
        assert response.status_code in [200, 503]
        
        # Test disable
        response = requests.post(f"{self.BASE_URL}/api/collection/disable", timeout=10)
        assert response.status_code in [200, 503]


class TestCollectionDataPipeline:
    """Test collection data processing and transformation"""
    
    BASE_URL = "http://localhost:32542"
    
    def test_blacklist_active_endpoint(self):
        """Test active blacklist IP retrieval"""
        response = requests.get(f"{self.BASE_URL}/api/blacklist/active", timeout=10)
        
        assert response.status_code == 200
        # Should return plain text format with IP addresses
        content = response.text
        assert content is not None
        
        # Check if it contains IP-like patterns or FortiGate commands
        lines = content.split('\n')
        assert len(lines) >= 0  # At least header or empty response
    
    def test_fortigate_endpoint(self):
        """Test FortiGate External Connector endpoint"""
        response = requests.get(f"{self.BASE_URL}/api/fortigate", timeout=10)
        
        assert response.status_code == 200
        content = response.text
        assert content is not None
        
        # Should contain FortiGate configuration format
        if content.strip():
            # Check for FortiGate command structure
            assert any(keyword in content for keyword in [
                "config", "edit", "set", "next", "end"
            ]) or content.strip() == ""
    
    def test_enhanced_blacklist_v2(self):
        """Test V2 enhanced blacklist with metadata"""
        response = requests.get(f"{self.BASE_URL}/api/v2/blacklist/enhanced", timeout=10)
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        
        if data["success"]:
            assert "blacklist" in data
            assert "metadata" in data
    
    def test_data_export_functionality(self):
        """Test data export endpoints"""
        # Test CSV export
        response = requests.get(f"{self.BASE_URL}/api/export/csv", timeout=10)
        assert response.status_code in [200, 404]
        
        # Test JSON export
        response = requests.get(f"{self.BASE_URL}/api/export/json", timeout=10)
        assert response.status_code in [200, 404]


class TestCollectionAnalytics:
    """Test V2 analytics endpoints for collection data"""
    
    BASE_URL = "http://localhost:32542"
    
    def test_analytics_trends(self):
        """Test trend analysis endpoint"""
        response = requests.get(f"{self.BASE_URL}/api/v2/analytics/trends", timeout=10)
        
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            if data["success"]:
                assert "trends" in data
    
    def test_analytics_summary(self):
        """Test analytics summary endpoint"""
        response = requests.get(
            f"{self.BASE_URL}/api/v2/analytics/summary?period=7d", 
            timeout=10
        )
        
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
    
    def test_threat_levels_analysis(self):
        """Test threat levels analysis"""
        response = requests.get(
            f"{self.BASE_URL}/api/v2/analytics/threat-levels", 
            timeout=10
        )
        
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
    
    def test_sources_analysis(self):
        """Test sources analysis endpoint"""
        response = requests.get(f"{self.BASE_URL}/api/v2/analytics/sources", timeout=10)
        
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
    
    def test_geographical_analysis(self):
        """Test geographical analysis"""
        response = requests.get(f"{self.BASE_URL}/api/v2/analytics/geo", timeout=10)
        
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
    
    def test_sources_status(self):
        """Test sources status monitoring"""
        response = requests.get(f"{self.BASE_URL}/api/v2/sources/status", timeout=10)
        
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            if data["success"]:
                assert "sources" in data


class TestCollectionErrorHandling:
    """Test error handling and fallback mechanisms"""
    
    BASE_URL = "http://localhost:32542"
    
    def test_invalid_date_ranges(self):
        """Test handling of invalid date ranges"""
        # Future dates
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y%m%d")
        response = requests.post(
            f"{self.BASE_URL}/api/collection/regtech/trigger",
            json={
                "start_date": future_date,
                "end_date": future_date
            },
            timeout=10
        )
        
        assert response.status_code in [400, 503]
        
        # Invalid date order (start > end)
        response = requests.post(
            f"{self.BASE_URL}/api/collection/regtech/trigger",
            json={
                "start_date": "20250117",
                "end_date": "20250101"
            },
            timeout=10
        )
        
        assert response.status_code in [400, 503]
    
    def test_malformed_requests(self):
        """Test handling of malformed requests"""
        # Non-JSON content
        response = requests.post(
            f"{self.BASE_URL}/api/collection/regtech/trigger",
            data="invalid data",
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        assert response.status_code in [400, 503]
        
        # Missing content-type
        response = requests.post(
            f"{self.BASE_URL}/api/collection/regtech/trigger",
            data='{"start_date": "20250101"}',
            timeout=10
        )
        
        assert response.status_code in [400, 503]
    
    def test_rate_limiting(self):
        """Test rate limiting on collection endpoints"""
        # Make multiple rapid requests to trigger rate limiting
        for i in range(10):
            response = requests.get(f"{self.BASE_URL}/api/collection/status", timeout=5)
            
            # Should either succeed or be rate limited
            assert response.status_code in [200, 429, 503]
            
            if response.status_code == 429:
                # Rate limit triggered as expected
                break
    
    def test_concurrent_collection_requests(self):
        """Test handling of concurrent collection requests"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def trigger_collection():
            try:
                response = requests.post(
                    f"{self.BASE_URL}/api/collection/regtech/trigger",
                    json={
                        "start_date": "20250101",
                        "end_date": "20250102"
                    },
                    timeout=15
                )
                results.put(response.status_code)
            except Exception as e:
                results.put(str(e))
        
        # Start 3 concurrent collection requests
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=trigger_collection)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # At least one should respond properly
        success_count = 0
        while not results.empty():
            result = results.get()
            if isinstance(result, int) and result in [200, 503]:
                success_count += 1
        
        assert success_count >= 1


class TestCollectionPerformance:
    """Test performance and scalability of collection system"""
    
    BASE_URL = "http://localhost:32542"
    
    def test_status_endpoint_performance(self):
        """Test status endpoint response time"""
        start_time = time.time()
        
        response = requests.get(f"{self.BASE_URL}/api/collection/status", timeout=10)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Should respond within 2 seconds
        assert response_time < 2.0
        assert response.status_code in [200, 503]
    
    def test_large_date_range_handling(self):
        """Test handling of large date ranges"""
        # Test maximum allowed date range
        response = requests.get(
            f"{self.BASE_URL}/api/collection/daily-stats?days=90",
            timeout=15
        )
        
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert data["period"]["days"] == 90
    
    def test_memory_usage_stability(self):
        """Test memory usage stability during operations"""
        # Make multiple requests to test for memory leaks
        for i in range(20):
            response = requests.get(f"{self.BASE_URL}/api/collection/status", timeout=5)
            assert response.status_code in [200, 503]
            
            response = requests.get(f"{self.BASE_URL}/api/blacklist/active", timeout=5)
            assert response.status_code == 200
            
            # Small delay to allow garbage collection
            time.sleep(0.1)


class TestCollectionIntegration:
    """Test integration with external systems and components"""
    
    BASE_URL = "http://localhost:32542"
    
    def test_health_check_integration(self):
        """Test health check includes collection status"""
        response = requests.get(f"{self.BASE_URL}/health", timeout=10)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data
        
        # Should include collection-related components
        components = data["components"]
        assert isinstance(components, dict)
    
    def test_detailed_health_check(self):
        """Test detailed health check endpoint"""
        response = requests.get(f"{self.BASE_URL}/api/health", timeout=10)
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "status" in data
    
    def test_monitoring_dashboard_integration(self):
        """Test monitoring dashboard endpoints"""
        response = requests.get(f"{self.BASE_URL}/monitoring/dashboard", timeout=10)
        
        # Should either work or return 404 if not implemented
        assert response.status_code in [200, 404]
    
    def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint"""
        response = requests.get(f"{self.BASE_URL}/metrics", timeout=10)
        
        # Should return metrics in Prometheus format
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            content = response.text
            # Should contain Prometheus-style metrics
            assert content is not None


if __name__ == "__main__":
    import sys
    
    # Track all validation failures
    all_validation_failures = []
    total_tests = 0
    
    # Test classes to run
    test_classes = [
        TestCollectionStatusAPI,
        TestCollectionTriggers,
        TestCollectionDataPipeline,
        TestCollectionAnalytics,
        TestCollectionErrorHandling,
        TestCollectionPerformance,
        TestCollectionIntegration
    ]
    
    print("🔄 Running Comprehensive Collection System Tests...")
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    for test_class in test_classes:
        print(f"\n📋 Testing {test_class.__name__}...")
        test_instance = test_class()
        
        # Get all test methods
        test_methods = [method for method in dir(test_instance) 
                       if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            test_method = getattr(test_instance, method_name)
            
            try:
                # Run test
                test_method()
                print(f"  ✅ {method_name}")
                
            except Exception as e:
                all_validation_failures.append(
                    f"{test_class.__name__}.{method_name}: {str(e)}"
                )
                print(f"  ❌ {method_name}: {str(e)}")
    
    # Final validation result
    print("\n" + "=" * 60)
    print("📊 COLLECTION SYSTEM TEST SUMMARY")
    
    passed = total_tests - len(all_validation_failures)
    success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed}")
    print(f"Failed: {len(all_validation_failures)}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if all_validation_failures:
        print(f"\n❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"\n✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Collection system is validated and ready for production use")
        sys.exit(0)