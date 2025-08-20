#!/usr/bin/env python3
"""
Container Functionality Test
Tests the modified container files for proper functionality
"""

import sys
import logging
import traceback
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_container_imports():
    """Test that container modules can be imported"""
    failures = []
    
    try:
        from src.core.containers.blacklist_container import BlacklistContainer
        logger.info("✅ BlacklistContainer imported successfully")
    except Exception as e:
        failures.append(f"BlacklistContainer import failed: {e}")
        logger.error(f"❌ BlacklistContainer import failed: {e}")
    
    try:
        from src.core.containers.utils import get_container, reset_container
        logger.info("✅ Container utils imported successfully")
    except Exception as e:
        failures.append(f"Container utils import failed: {e}")
        logger.error(f"❌ Container utils import failed: {e}")
        
    return failures

def test_container_creation():
    """Test container creation and basic functionality"""
    failures = []
    
    try:
        from src.core.containers.utils import get_container, reset_container
        
        # Reset to ensure clean state
        reset_container()
        
        # Get container instance
        container = get_container()
        logger.info("✅ Container created successfully")
        
        # Test that it's a singleton
        container2 = get_container()
        if container is container2:
            logger.info("✅ Container singleton pattern works")
        else:
            failures.append("Container is not properly implementing singleton pattern")
            
    except Exception as e:
        failures.append(f"Container creation failed: {e}")
        logger.error(f"❌ Container creation failed: {e}")
        traceback.print_exc()
        
    return failures

def test_service_registration():
    """Test that services are properly registered in the container"""
    failures = []
    
    try:
        from src.core.containers.utils import get_container, reset_container
        
        # Get fresh container
        reset_container()
        container = get_container()
        
        # Test core service registration
        required_services = [
            'config',
            'cache', 
            'cache_manager',
            'auth_manager'
        ]
        
        for service_name in required_services:
            try:
                service = container.get(service_name)
                if service is not None:
                    logger.info(f"✅ Service '{service_name}' registered successfully")
                else:
                    failures.append(f"Service '{service_name}' returned None")
            except Exception as e:
                failures.append(f"Service '{service_name}' registration failed: {e}")
                logger.error(f"❌ Service '{service_name}' failed: {e}")
                
    except Exception as e:
        failures.append(f"Service registration test failed: {e}")
        logger.error(f"❌ Service registration test failed: {e}")
        traceback.print_exc()
        
    return failures

def test_container_utility_functions():
    """Test the utility functions in containers/utils.py"""
    failures = []
    
    try:
        from src.core.containers.utils import (
            get_cache_manager,
            get_auth_manager,
            resolve_service,
            reset_container
        )
        
        # Reset for clean state
        reset_container()
        
        # Test cache manager
        try:
            cache_mgr = get_cache_manager()
            if cache_mgr is not None:
                logger.info("✅ get_cache_manager() works")
            else:
                failures.append("get_cache_manager() returned None")
        except Exception as e:
            failures.append(f"get_cache_manager() failed: {e}")
            
        # Test auth manager
        try:
            auth_mgr = get_auth_manager()
            if auth_mgr is not None:
                logger.info("✅ get_auth_manager() works")
            else:
                failures.append("get_auth_manager() returned None")
        except Exception as e:
            failures.append(f"get_auth_manager() failed: {e}")
            
        # Test resolve_service
        try:
            cache_service = resolve_service('cache')
            if cache_service is not None:
                logger.info("✅ resolve_service() works")
            else:
                failures.append("resolve_service('cache') returned None")
        except Exception as e:
            failures.append(f"resolve_service() failed: {e}")
            
    except Exception as e:
        failures.append(f"Container utility functions test failed: {e}")
        logger.error(f"❌ Container utility functions test failed: {e}")
        traceback.print_exc()
        
    return failures

def test_optional_services():
    """Test optional services that may not always be available"""
    failures = []
    
    try:
        from src.core.containers.utils import (
            get_collection_manager,
            get_unified_service,
            reset_container
        )
        
        # Reset for clean state
        reset_container()
        
        # Test collection manager (may be None)
        try:
            collection_mgr = get_collection_manager()
            if collection_mgr is not None:
                logger.info("✅ get_collection_manager() returned a service")
            else:
                logger.info("ℹ️  get_collection_manager() returned None (expected if not configured)")
        except Exception as e:
            failures.append(f"get_collection_manager() failed with exception: {e}")
            
        # Test unified service (should work with fallback)
        try:
            unified_service = get_unified_service()
            if unified_service is not None:
                logger.info("✅ get_unified_service() works (either from container or factory)")
            else:
                failures.append("get_unified_service() returned None")
        except Exception as e:
            failures.append(f"get_unified_service() failed: {e}")
            
    except Exception as e:
        failures.append(f"Optional services test failed: {e}")
        logger.error(f"❌ Optional services test failed: {e}")
        traceback.print_exc()
        
    return failures

def test_container_dependency_injection():
    """Test dependency injection decorator"""
    failures = []
    
    try:
        from src.core.containers.utils import inject, reset_container
        
        # Reset for clean state
        reset_container()
        
        @inject('cache_manager')
        def test_function(cache_manager):
            return cache_manager is not None
            
        result = test_function()
        if result:
            logger.info("✅ Dependency injection decorator works")
        else:
            failures.append("Dependency injection decorator returned False")
            
    except Exception as e:
        failures.append(f"Dependency injection test failed: {e}")
        logger.error(f"❌ Dependency injection test failed: {e}")
        traceback.print_exc()
        
    return failures

def main():
    """Run all container tests"""
    logger.info("🧪 Starting Container Functionality Tests")
    logger.info("=" * 50)
    
    all_failures = []
    
    # Test 1: Import functionality
    logger.info("Test 1: Testing imports...")
    failures = test_container_imports()
    all_failures.extend(failures)
    
    # Test 2: Container creation
    logger.info("\nTest 2: Testing container creation...")
    failures = test_container_creation()
    all_failures.extend(failures)
    
    # Test 3: Service registration
    logger.info("\nTest 3: Testing service registration...")
    failures = test_service_registration()
    all_failures.extend(failures)
    
    # Test 4: Utility functions
    logger.info("\nTest 4: Testing utility functions...")
    failures = test_container_utility_functions()
    all_failures.extend(failures)
    
    # Test 5: Optional services
    logger.info("\nTest 5: Testing optional services...")
    failures = test_optional_services()
    all_failures.extend(failures)
    
    # Test 6: Dependency injection
    logger.info("\nTest 6: Testing dependency injection...")
    failures = test_container_dependency_injection()
    all_failures.extend(failures)
    
    # Report results
    logger.info("\n" + "=" * 50)
    logger.info("🔍 CONTAINER FUNCTIONALITY TEST RESULTS")
    
    if all_failures:
        logger.error(f"❌ VALIDATION FAILED - {len(all_failures)} failures found:")
        for i, failure in enumerate(all_failures, 1):
            logger.error(f"  {i}. {failure}")
        return 1
    else:
        logger.info("✅ VALIDATION PASSED - All container functionality tests successful")
        logger.info("Container modifications are working correctly")
        return 0

if __name__ == "__main__":
    sys.exit(main())