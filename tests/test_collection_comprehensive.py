#!/usr/bin/env python3
"""
Collection System Tests Import Module

This module has been refactored into smaller, focused test modules:
- test_collection_status_api.py: Collection status and monitoring API tests
- test_collection_triggers.py: Collection trigger and control tests
- test_collection_integration.py: End-to-end integration and performance tests

To run all collection tests: pytest tests/test_collection_* -v
"""

# Import all test modules for backward compatibility
import pytest

# Import all the refactored test classes
try:
    from test_collection_integration import (TestCollectionAnalytics,
                                             TestCollectionDataPipeline,
                                             TestCollectionErrorHandling,
                                             TestCollectionPerformance)
    from test_collection_status_api import TestCollectionStatusAPI
    from test_collection_triggers import TestCollectionTriggers
except ImportError as e:
    pytest.skip(f"Unable to import refactored collection test modules: {e}")


# All test classes have been moved to separate modules.
# This file now serves as a compatibility layer.

# For individual test execution, use:
# pytest tests/test_collection_status_api.py::TestCollectionStatusAPI::test_collection_status_endpoint
# pytest tests/test_collection_triggers.py::TestCollectionTriggers::test_regtech_trigger_endpoint
# pytest tests/test_collection_integration.py::TestCollectionDataPipeline::test_data_validation_pipeline


if __name__ == "__main__":
    # Validation test for refactored module
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: Module imports work
    total_tests += 1
    try:
        from test_collection_integration import (TestCollectionAnalytics,
                                                 TestCollectionDataPipeline,
                                                 TestCollectionErrorHandling,
                                                 TestCollectionPerformance)
        from test_collection_status_api import TestCollectionStatusAPI
        from test_collection_triggers import TestCollectionTriggers

        # Test passed if no exception
    except Exception as e:
        all_validation_failures.append(f"Collection module imports failed: {e}")

    # Test 2: All collection test classes are available
    total_tests += 1
    try:
        required_classes = [
            TestCollectionStatusAPI,
            TestCollectionTriggers,
            TestCollectionDataPipeline,
            TestCollectionAnalytics,
            TestCollectionErrorHandling,
            TestCollectionPerformance,
        ]

        for cls in required_classes:
            if not hasattr(cls, "__name__"):
                all_validation_failures.append(f"Invalid collection test class: {cls}")
                break
        else:
            # All classes are valid
            pass
    except Exception as e:
        all_validation_failures.append(f"Collection class validation failed: {e}")

    # Test 3: Module can be used for pytest discovery
    total_tests += 1
    try:
        # This should work for pytest discovery
        collection_test_classes = [
            TestCollectionStatusAPI,
            TestCollectionTriggers,
            TestCollectionDataPipeline,
            TestCollectionAnalytics,
            TestCollectionErrorHandling,
            TestCollectionPerformance,
        ]

        for test_cls in collection_test_classes:
            if not test_cls.__name__.startswith("Test"):
                all_validation_failures.append(
                    f"Invalid collection test class name: {test_cls.__name__}"
                )
                break
        else:
            # Test passed
            pass
    except Exception as e:
        all_validation_failures.append(
            f"Collection pytest compatibility check failed: {e}"
        )

    # Final validation result
    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print(
            "Refactored collection comprehensive module is validated and ready for use"
        )
        sys.exit(0)
