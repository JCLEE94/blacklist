"""Collection system comprehensive test suite

This module serves as the main import hub for all collection-related tests.
Actual test implementations have been split into specialized modules for better maintainability.
"""

# Import all test classes from specialized modules
from .test_collection_regtech import TestRegtechCollector
from .test_collection_secudium import TestSecudiumCollector

# Re-export test classes for backward compatibility
__all__ = ["TestRegtechCollector", "TestSecudiumCollector"]
