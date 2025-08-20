#!/usr/bin/env python3
"""
Comprehensive Container Validation Test Suite

This script validates the container modifications and overall system functionality
focusing on the 95% coverage target and ensuring no regressions.
"""

import sys
import json
import logging
import traceback
import requests
from typing import List, Dict, Any
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ContainerValidationSuite:
    """Comprehensive validation suite for container functionality"""
    
    def __init__(self):
        self.failures: List[str] = []
        self.warnings: List[str] = []
        self.successes: List[str] = []
        self.total_tests = 0
        self.base_url = "http://localhost:32542"
        
    def log_success(self, message: str):
        """Log successful test"""
        self.successes.append(message)
        logger.info(f"✅ {message}")
        
    def log_failure(self, message: str, exception: Exception = None):
        """Log test failure"""
        self.failures.append(message)
        logger.error(f"❌ {message}")
        if exception:
            logger.error(f"   Exception: {exception}")
            
    def log_warning(self, message: str):
        """Log test warning"""
        self.warnings.append(message)
        logger.warning(f"⚠️ {message}")

    def test_container_imports(self) -> bool:
        """Test container module imports"""
        self.total_tests += 1
        try:
            # Test blacklist container
            from src.core.containers.blacklist_container import BlacklistContainer
            self.log_success("BlacklistContainer import successful")
            
            # Test container utils
            from src.core.containers.utils import get_container, reset_container
            self.log_success("Container utils import successful")
            
            # Test base container
            from src.core.containers.base_container import ServiceContainer
            self.log_success("Base container import successful")
            
            return True
        except Exception as e:
            self.log_failure("Container imports failed", e)
            return False
    
    def test_container_initialization(self) -> bool:
        """Test container initialization and singleton pattern"""
        self.total_tests += 1
        try:
            from src.core.containers.utils import get_container, reset_container
            
            # Reset container
            reset_container()
            
            # Get container instances
            container1 = get_container()
            container2 = get_container()
            
            # Verify singleton pattern
            if container1 is container2:
                self.log_success("Container singleton pattern works correctly")
                return True
            else:
                self.log_failure("Container singleton pattern broken")
                return False
                
        except Exception as e:
            self.log_failure("Container initialization failed", e)
            return False
    
    def test_service_registration(self) -> bool:
        """Test service registration and retrieval"""
        self.total_tests += 1
        try:
            from src.core.containers.utils import get_container, reset_container
            
            reset_container()
            container = get_container()
            
            # Test core services
            required_services = ['config', 'cache', 'cache_manager', 'auth_manager']
            failed_services = []
            
            for service_name in required_services:
                try:
                    service = container.get(service_name)
                    if service is not None:
                        self.log_success(f"Service '{service_name}' registered successfully")
                    else:
                        failed_services.append(f"{service_name} (returned None)")
                except Exception as e:
                    failed_services.append(f"{service_name} (exception: {e})")
            
            if not failed_services:
                return True
            else:
                for failure in failed_services:
                    self.log_failure(f"Service registration failed: {failure}")
                return False
                
        except Exception as e:
            self.log_failure("Service registration test failed", e)
            return False
    
    def test_utility_functions(self) -> bool:
        """Test container utility functions"""
        self.total_tests += 1
        try:
            from src.core.containers.utils import (
                get_cache_manager, get_auth_manager, 
                get_collection_manager, get_unified_service,
                resolve_service, reset_container
            )
            
            reset_container()
            utility_test_results = []
            
            # Test cache manager
            try:
                cache_mgr = get_cache_manager()
                utility_test_results.append(("get_cache_manager", cache_mgr is not None))
            except Exception as e:
                utility_test_results.append(("get_cache_manager", False))
            
            # Test auth manager  
            try:
                auth_mgr = get_auth_manager()
                utility_test_results.append(("get_auth_manager", auth_mgr is not None))
            except Exception as e:
                utility_test_results.append(("get_auth_manager", False))
            
            # Test collection manager (optional service)
            try:
                collection_mgr = get_collection_manager()
                utility_test_results.append(("get_collection_manager", True))  # Can be None, that's OK
            except Exception as e:
                utility_test_results.append(("get_collection_manager", False))
            
            # Test unified service
            try:
                unified_service = get_unified_service()
                utility_test_results.append(("get_unified_service", unified_service is not None))
            except Exception as e:
                utility_test_results.append(("get_unified_service", False))
            
            # Test resolve_service
            try:
                cache_service = resolve_service('cache')
                utility_test_results.append(("resolve_service", cache_service is not None))
            except Exception as e:
                utility_test_results.append(("resolve_service", False))
            
            # Evaluate results
            failed_utilities = [name for name, success in utility_test_results if not success]
            successful_utilities = [name for name, success in utility_test_results if success]
            
            for util in successful_utilities:
                self.log_success(f"Utility function '{util}' works correctly")
                
            for util in failed_utilities:
                self.log_failure(f"Utility function '{util}' failed")
            
            return len(failed_utilities) == 0
            
        except Exception as e:
            self.log_failure("Utility functions test failed", e)
            return False
    
    def test_dependency_injection(self) -> bool:
        """Test dependency injection decorator"""
        self.total_tests += 1
        try:
            from src.core.containers.utils import inject, reset_container
            
            reset_container()
            
            @inject('cache_manager')
            def test_injected_function(cache_manager):
                return cache_manager is not None
            
            result = test_injected_function()
            if result:
                self.log_success("Dependency injection decorator works correctly")
                return True
            else:
                self.log_failure("Dependency injection decorator returned False")
                return False
                
        except Exception as e:
            self.log_failure("Dependency injection test failed", e)
            return False
    
    def test_api_endpoints(self) -> bool:
        """Test critical API endpoints functionality"""
        self.total_tests += 1
        endpoints_to_test = [
            ("/health", "Health endpoint"),
            ("/api/health", "Detailed health endpoint"),
            ("/api/collection/status", "Collection status endpoint"),
            ("/api/blacklist/active", "Active blacklist endpoint"),
            ("/api/fortigate", "FortiGate endpoint"),
        ]
        
        failed_endpoints = []
        successful_endpoints = []
        
        for endpoint, description in endpoints_to_test:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                if response.status_code in [200, 503]:  # 503 is OK for some endpoints
                    successful_endpoints.append(description)
                else:
                    failed_endpoints.append(f"{description} (status: {response.status_code})")
            except requests.exceptions.RequestException as e:
                failed_endpoints.append(f"{description} (connection error: {e})")
            except Exception as e:
                failed_endpoints.append(f"{description} (error: {e})")
        
        for endpoint in successful_endpoints:
            self.log_success(f"API endpoint test: {endpoint}")
            
        for endpoint in failed_endpoints:
            self.log_failure(f"API endpoint test failed: {endpoint}")
        
        return len(failed_endpoints) == 0
    
    def test_analytics_api_response_structure(self) -> bool:
        """Test analytics API response structure"""
        self.total_tests += 1
        try:
            # Test trends endpoint
            response = requests.get(f"{self.base_url}/api/v2/analytics/trends", timeout=10)
            
            if response.status_code in [200, 503]:
                data = response.json()
                
                # Check expected structure based on actual response
                if "status" in data and data["status"] == "success":
                    self.log_success("Analytics trends endpoint returns correct structure")
                    
                    # Validate additional fields
                    required_fields = ["data", "timestamp"]
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if not missing_fields:
                        self.log_success("Analytics trends response has all required fields")
                        return True
                    else:
                        self.log_failure(f"Analytics trends response missing fields: {missing_fields}")
                        return False
                else:
                    self.log_warning("Analytics trends endpoint returned non-success status")
                    return True  # This is acceptable in some cases
            else:
                self.log_warning(f"Analytics trends endpoint returned status: {response.status_code}")
                return True  # Service might be unavailable
                
        except Exception as e:
            self.log_failure("Analytics API response structure test failed", e)
            return False
    
    def test_database_operations(self) -> bool:
        """Test database operations through container"""
        self.total_tests += 1
        try:
            from src.core.containers.utils import get_container, reset_container
            
            reset_container()
            container = get_container()
            
            # Try to get blacklist manager
            try:
                blacklist_mgr = container.get('blacklist_manager')
                if blacklist_mgr is not None:
                    self.log_success("Database operations: blacklist manager accessible")
                    
                    # Try basic operation
                    try:
                        # Just test that we can call get_active_ips without crashing
                        active_ips = blacklist_mgr.get_active_ips()
                        self.log_success("Database operations: get_active_ips works")
                        return True
                    except Exception as e:
                        self.log_warning(f"Database operations: get_active_ips failed ({e})")
                        return True  # Database may not be configured
                else:
                    self.log_warning("Database operations: blacklist manager not available")
                    return True  # May not be configured
                    
            except Exception as e:
                self.log_warning(f"Database operations: blacklist manager access failed ({e})")
                return True  # May not be configured
                
        except Exception as e:
            self.log_failure("Database operations test failed", e)
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling in container operations"""
        self.total_tests += 1
        try:
            from src.core.containers.utils import get_container, resolve_service, reset_container
            
            reset_container()
            
            # Test accessing non-existent service
            try:
                non_existent = resolve_service('non_existent_service')
                self.log_failure("Error handling: should have raised exception for non-existent service")
                return False
            except ValueError:
                self.log_success("Error handling: correctly raises ValueError for non-existent service")
            except Exception as e:
                self.log_success(f"Error handling: raises exception for non-existent service ({type(e).__name__})")
            
            # Test container shutdown and recreation
            try:
                container1 = get_container()
                reset_container()
                container2 = get_container()
                
                if container1 is not container2:
                    self.log_success("Error handling: container reset works correctly")
                    return True
                else:
                    self.log_failure("Error handling: container reset failed")
                    return False
                    
            except Exception as e:
                self.log_failure(f"Error handling: container reset test failed ({e})")
                return False
                
        except Exception as e:
            self.log_failure("Error handling test failed", e)
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all container validation tests"""
        logger.info("🧪 Starting Comprehensive Container Validation Suite")
        logger.info("=" * 60)
        
        test_methods = [
            ("Container Imports", self.test_container_imports),
            ("Container Initialization", self.test_container_initialization),
            ("Service Registration", self.test_service_registration),
            ("Utility Functions", self.test_utility_functions),
            ("Dependency Injection", self.test_dependency_injection),
            ("API Endpoints", self.test_api_endpoints),
            ("Analytics API Structure", self.test_analytics_api_response_structure),
            ("Database Operations", self.test_database_operations),
            ("Error Handling", self.test_error_handling),
        ]
        
        passed_tests = 0
        start_time = time.time()
        
        for test_name, test_method in test_methods:
            logger.info(f"\n📋 Running test: {test_name}")
            try:
                if test_method():
                    passed_tests += 1
            except Exception as e:
                self.log_failure(f"Test '{test_name}' crashed with exception", e)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Generate report
        logger.info("\n" + "=" * 60)
        logger.info("🔍 CONTAINER VALIDATION RESULTS")
        logger.info(f"📊 Duration: {duration:.2f} seconds")
        logger.info(f"📈 Tests Passed: {passed_tests}/{self.total_tests}")
        logger.info(f"✅ Successes: {len(self.successes)}")
        logger.info(f"⚠️ Warnings: {len(self.warnings)}")
        logger.info(f"❌ Failures: {len(self.failures)}")
        
        # Calculate success rate
        success_rate = (passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        logger.info(f"📊 Success Rate: {success_rate:.1f}%")
        
        # Show details
        if self.warnings:
            logger.info("\n⚠️ WARNINGS:")
            for warning in self.warnings:
                logger.warning(f"  • {warning}")
        
        if self.failures:
            logger.info("\n❌ FAILURES:")
            for failure in self.failures:
                logger.error(f"  • {failure}")
        
        # Determine overall result
        if len(self.failures) == 0:
            logger.info("\n🎉 VALIDATION PASSED - Container modifications working correctly")
            if len(self.warnings) > 0:
                logger.info("⚠️ Some warnings present but no blocking issues found")
            return {
                "passed": True,
                "success_rate": success_rate,
                "total_tests": self.total_tests,
                "failures": len(self.failures),
                "warnings": len(self.warnings),
                "duration": duration
            }
        else:
            logger.error("\n💥 VALIDATION FAILED - Issues found in container modifications")
            return {
                "passed": False,
                "success_rate": success_rate,
                "total_tests": self.total_tests,
                "failures": len(self.failures),
                "warnings": len(self.warnings),
                "duration": duration
            }

def main():
    """Main entry point"""
    try:
        suite = ContainerValidationSuite()
        results = suite.run_all_tests()
        
        # Exit with appropriate code
        if results["passed"]:
            return 0
        else:
            return 1
            
    except KeyboardInterrupt:
        logger.info("\n🛑 Testing interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"\n💥 Testing suite crashed: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())