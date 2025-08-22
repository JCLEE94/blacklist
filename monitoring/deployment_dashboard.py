#!/usr/bin/env python3
"""
Deployment Dashboard Main Entry Point

Refactored main entry point for deployment monitoring dashboard.
Core functionality moved to dashboard_core.py for better maintainability.

Links:
- Flask documentation: https://flask.palletsprojects.com/
- Flask-SocketIO documentation: https://flask-socketio.readthedocs.io/

Sample input: python3 deployment_dashboard.py --port 8080
Expected output: Web dashboard accessible at http://localhost:8080 with real-time deployment metrics
"""

import argparse
import logging

try:
    from .dashboard_core import DeploymentDashboard
except ImportError:
    from dashboard_core import DeploymentDashboard

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Core dashboard functionality moved to dashboard_core.py
# Import the DeploymentDashboard class from the new modular structure

# HTML template moved to web_interface.py for better separation of concerns


def main():
    """Main function with CLI support"""
    parser = argparse.ArgumentParser(description="Deployment monitoring dashboard")
    parser.add_argument(
        "--api-url", default="http://localhost:32542", help="API base URL"
    )
    parser.add_argument("--port", type=int, default=8080, help="Dashboard port")
    parser.add_argument("--host", default="0.0.0.0", help="Dashboard host")
    parser.add_argument(
        "--update-interval",
        type=int,
        default=30,
        help="Metrics update interval in seconds",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()

    # Create dashboard instance
    dashboard = DeploymentDashboard(
        api_base_url=args.api_url, update_interval=args.update_interval
    )

    # Log startup event
    dashboard.log_deployment_event(
        "dashboard_started", details=f"Started on {args.host}:{args.port}"
    )

    # Run dashboard
    dashboard.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    # Validation tests for refactored dashboard
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: DeploymentDashboard import and instantiation
    total_tests += 1
    try:
        dashboard = DeploymentDashboard()
        if hasattr(dashboard, "app") and hasattr(dashboard, "api_base_url"):
            pass  # Test passed
        else:
            all_validation_failures.append(
                "DeploymentDashboard missing required attributes"
            )
    except Exception as e:
        all_validation_failures.append(f"DeploymentDashboard instantiation failed: {e}")

    # Test 2: Modular components integration
    total_tests += 1
    try:
        dashboard = DeploymentDashboard()
        if hasattr(dashboard, "metrics_collector") and hasattr(dashboard, "db_manager"):
            pass  # Test passed
        else:
            all_validation_failures.append(
                "DeploymentDashboard missing modular components"
            )
    except Exception as e:
        all_validation_failures.append(f"Modular components integration failed: {e}")

    # Test 3: Basic dashboard functionality
    total_tests += 1
    try:
        dashboard = DeploymentDashboard()
        # Test that core methods exist
        if (
            hasattr(dashboard, "collect_metrics")
            and hasattr(dashboard, "run")
            and hasattr(dashboard, "start_monitoring")
        ):
            pass  # Test passed
        else:
            all_validation_failures.append("DeploymentDashboard missing core methods")
    except Exception as e:
        all_validation_failures.append(f"Dashboard functionality test failed: {e}")

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
        print("Refactored deployment dashboard is validated and ready for use")

        # If not being imported, run main
        if len(sys.argv) > 1:
            sys.exit(main())
        else:
            sys.exit(0)
