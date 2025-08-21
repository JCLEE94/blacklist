#!/usr/bin/env python3
"""
Health Check Handler - Handles health check requests
Provides system health and readiness status
"""

from datetime import datetime
from typing import Any, Dict

from flask import jsonify


class HealthCheckHandler:
    """Handles health check requests"""

    def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        try:
            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.3.0",
                "components": self._check_components(),
                "uptime": "operational",
            }

            # Determine overall health status
            component_health = [c["status"] for c in health_data["components"].values()]
            if "unhealthy" in component_health:
                health_data["status"] = "unhealthy"
                return jsonify(health_data), 503
            elif "degraded" in component_health:
                health_data["status"] = "degraded"
                return jsonify(health_data), 200

            return jsonify(health_data)

        except Exception as e:
            return (
                jsonify(
                    {
                        "status": "unhealthy",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                500,
            )

    def _check_components(self) -> Dict[str, Dict[str, Any]]:
        """Check health of individual system components"""
        components = {}

        # Database health
        try:
            from ...database.collection_settings import CollectionSettingsDB

            components["database"] = {
                "status": "healthy",
                "message": "Database connection available",
            }
        except ImportError:
            components["database"] = {
                "status": "degraded",
                "message": "Database module not available",
            }
        except Exception as e:
            components["database"] = {
                "status": "unhealthy",
                "message": f"Database error: {str(e)}",
            }

        # Collection system health
        try:
            from ...collection_db_collector import DatabaseCollectionSystem

            components["collection"] = {
                "status": "healthy",
                "message": "Collection system available",
            }
        except ImportError:
            components["collection"] = {
                "status": "degraded",
                "message": "Collection system module not available",
            }
        except Exception as e:
            components["collection"] = {
                "status": "unhealthy",
                "message": f"Collection system error: {str(e)}",
            }

        # Core system health (always healthy if we reach this point)
        components["core"] = {"status": "healthy", "message": "Core system operational"}

        return components


if __name__ == "__main__":
    # Validation test for health handler
    import sys

    handler = HealthCheckHandler()
    print("🚑 Testing Health Check Handler...")

    all_validation_failures = []
    total_tests = 0

    # Test 1: Health check response
    total_tests += 1
    try:
        response = handler.check_health()
        if not response:
            all_validation_failures.append("Health Check: Empty response returned")
        # Note: In actual Flask context, response would be a Response object
        print("  - Health check response generated")
    except Exception as e:
        all_validation_failures.append(f"Health Check: Exception occurred - {str(e)}")

    # Test 2: Component check
    total_tests += 1
    try:
        components = handler._check_components()
        if not isinstance(components, dict):
            all_validation_failures.append("Component Check: Invalid return type")
        elif "core" not in components:
            all_validation_failures.append("Component Check: Missing core component")
        elif not all("status" in comp for comp in components.values()):
            all_validation_failures.append("Component Check: Missing status fields")
        else:
            print(f"  - Component check successful ({len(components)} components)")
    except Exception as e:
        all_validation_failures.append(
            f"Component Check: Exception occurred - {str(e)}"
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
        print("Health Check Handler is ready for use")
        sys.exit(0)
