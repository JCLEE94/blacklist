# !/usr/bin/env python3
"""
Collection Management API Routes - Legacy compatibility wrapper
Maintains backward compatibility while using the new modular collection API

This module now acts as a compatibility layer, delegating to the new
modular collection route system
"""

import logging

from .collection.collector_routes import collector_bp
from .collection.config_routes import config_bp

# Import the new modular collection system
from .collection.main_routes import collection_bp, register_collection_routes
from .collection.status_routes import status_bp

logger = logging.getLogger(__name__)

# Re-export the main blueprint for backward compatibility
__all__ = [
    "collection_bp",
    "register_collection_routes",
    "status_bp",
    "collector_bp",
    "config_bp",
]


if __name__ == "__main__":
    # Validation test for legacy compatibility wrapper
    import sys

    print("🔄 Testing Collection Routes (Legacy Wrapper)...")

    all_validation_failures = []
    total_tests = 0

    # Test 1: Blueprint imports
    total_tests += 1
    try:
        if collection_bp is None:
            all_validation_failures.append("Collection Blueprint: Failed to import")
        else:
            print("  - Collection blueprint imported successfully")
    except Exception as e:
        all_validation_failures.append(
            f"Collection Blueprint: Exception occurred - {str(e)}"
        )

    # Test 2: Sub-blueprint imports
    total_tests += 1
    try:
        blueprints = [status_bp, collector_bp, config_bp]
        if any(bp is None for bp in blueprints):
            all_validation_failures.append(
                "Sub-blueprints: Some blueprints failed to import"
            )
        else:
            print("  - All sub-blueprints imported successfully")
    except Exception as e:
        all_validation_failures.append(f"Sub-blueprints: Exception occurred - {str(e)}")

    # Test 3: Registration function
    total_tests += 1
    try:
        if register_collection_routes is None:
            all_validation_failures.append("Registration function: Failed to import")
        else:
            print("  - Registration function available")
    except Exception as e:
        all_validation_failures.append(
            f"Registration function: Exception occurred - {str(e)}"
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
        print("Collection Routes (Legacy Wrapper) is ready for use")
        sys.exit(0)
