#!/usr/bin/env python3
"""
Unified Control Dashboard - Legacy compatibility wrapper
Maintains backward compatibility while using the new modular route system

This module now acts as a compatibility layer, delegating to the new 
modular route handlers and templates
"""

from flask import Blueprint

from .handlers.health_handler import HealthCheckHandler
from .handlers.status_handler import UnifiedStatusHandler
from .templates.dashboard_template import get_dashboard_template
# Import the refactored modular system
from .unified_control_routes_refactored import bp as refactored_bp

# Re-export the blueprint for backward compatibility
bp = refactored_bp

# Legacy exports for any code that might import these directly
__all__ = ["bp", "UnifiedStatusHandler", "HealthCheckHandler", "get_dashboard_template"]


if __name__ == "__main__":
    # Validation test for legacy compatibility wrapper
    import sys

    print("🔄 Testing Unified Control Routes (Legacy Wrapper)...")

    all_validation_failures = []
    total_tests = 0

    # Test 1: Blueprint import
    total_tests += 1
    try:
        if bp is None:
            all_validation_failures.append("Blueprint: Failed to import blueprint")
        else:
            print("  - Blueprint imported successfully")
    except Exception as e:
        all_validation_failures.append(f"Blueprint: Exception occurred - {str(e)}")

    # Test 2: Handler imports
    total_tests += 1
    try:
        handler = UnifiedStatusHandler()
        if not handler:
            all_validation_failures.append("Status Handler: Failed to instantiate")
        else:
            print("  - Status handler instantiated successfully")
    except Exception as e:
        all_validation_failures.append(f"Status Handler: Exception occurred - {str(e)}")

    # Test 3: Template import
    total_tests += 1
    try:
        template = get_dashboard_template()
        if not template:
            all_validation_failures.append("Template: Failed to get template")
        else:
            print("  - Dashboard template retrieved successfully")
    except Exception as e:
        all_validation_failures.append(f"Template: Exception occurred - {str(e)}")

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
        print("Unified Control Routes (Legacy Wrapper) is ready for use")
        sys.exit(0)
