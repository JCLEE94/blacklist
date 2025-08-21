#!/usr/bin/env python3
"""
Unit tests for collection route endpoints
Tests collection status, triggering, and logging endpoints.

This file imports and re-exports tests from modular components for backward compatibility.
"""

from .test_collection_logs_routes import TestCollectionLogsRoutes

# Import all test classes from modular components
from .test_collection_status_routes import TestCollectionStatusRoutes
from .test_collection_trigger_routes import TestCollectionTriggerRoutes


# For backward compatibility, create a unified test class that includes all tests
class TestCollectionRoutes(
    TestCollectionStatusRoutes, TestCollectionTriggerRoutes, TestCollectionLogsRoutes
):
    """
    Unified test class for all collection route endpoints.

    This class inherits from all modular test classes to maintain
    backward compatibility while keeping the codebase organized.
    """

    pass


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
