"""
Integration tests for service layer interactions - Modular Entry Point

This module imports and re-exports all modular integration tests
for backward compatibility and centralized test execution.
"""
# Import all modular test classes
from .test_service_core import TestServiceCore
from .test_collection_integration import TestCollectionIntegration
from .test_cache_database_integration import TestCacheDatabaseIntegration
from .test_error_recovery import TestServiceErrorRecovery

# Re-export for backward compatibility
TestServiceLayerIntegration = TestServiceCore

# Import shared fixtures
from .fixtures import IntegrationTestFixtures

# Make all test classes available at module level
__all__ = [
    "TestServiceCore",
    "TestCollectionIntegration", 
    "TestCacheDatabaseIntegration",
    "TestServiceErrorRecovery",
    "TestServiceLayerIntegration",  # Backward compatibility alias
    "IntegrationTestFixtures"
]

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
