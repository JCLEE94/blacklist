#!/usr/bin/env python3
"""Web modules detailed test suite

This module serves as the main import hub for all web module tests.
Actual test implementations have been split into specialized modules for better maintainability.
"""

# Import all test classes from specialized modules
from .test_web_api_routes_detailed import TestWebApiRoutes
from .test_web_collection_routes_detailed import TestWebCollectionRoutes

# Re-export test classes for backward compatibility
__all__ = ["TestWebApiRoutes", "TestWebCollectionRoutes"]
