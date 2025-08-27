#!/usr/bin/env python3
"""
Core Dashboard Management Module

Provides the main DeploymentDashboard class with metrics collection and database management.
Separated from web interface for better maintainability.

Links:
- Flask documentation: https://flask.palletsprojects.com/
- SQLite documentation: https://docs.python.org/3/library/sqlite3.html

Sample input: DeploymentDashboard(api_base_url="http://localhost:32542")
Expected output: Dashboard instance with monitoring capabilities
"""

import logging
import threading
import time
from typing import Dict, List, Any

from flask import Flask
from flask_socketio import SocketIO

try:
    from .dashboard_metrics import DashboardMetricsCollector
    from .database_manager import DatabaseManager
except ImportError:
    # Fallback for direct execution
    from dashboard_metrics import DashboardMetricsCollector
    from database_manager import DatabaseManager

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DeploymentDashboard:
    """Core deployment monitoring dashboard"""

    def __init__(
        self, api_base_url: str = "http://localhost:32542", update_interval: int = 30
    ):
        self.api_base_url = api_base_url
        self.update_interval = update_interval
        self.db_path = "deployment_monitoring.db"

        # Initialize Flask app
        self.app = Flask(__name__)
        self.app.config["SECRET_KEY"] = "deployment-dashboard-secret"
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")

        # Initialize components
        self.metrics_collector = DashboardMetricsCollector(api_base_url)
        self.db_manager = DatabaseManager(self.db_path)

        # Monitoring data
        self.current_metrics = {}
        self.deployment_history = []
        self.monitoring_active = False

        # Setup database
        self.db_manager.init_database()

    def collect_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        return self.metrics_collector.collect_metrics()

    def store_metrics(self, metrics: Dict[str, Any]):
        """Store metrics in database"""
        self.db_manager.store_metrics(metrics)

    def get_deployment_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent deployment history"""
        return self.db_manager.get_deployment_history(limit)

    def get_metrics_history(
        self, metric_type: str, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get metrics history for specified time period"""
        return self.db_manager.get_metrics_history(metric_type, hours)

    def log_deployment_event(
        self,
        event_type: str,
        version: str = None,
        status: str = None,
        details: str = None,
        duration_seconds: int = None,
    ):
        """Log deployment event"""
        self.db_manager.log_deployment_event(
            event_type, version, status, details, duration_seconds
        )

    def monitoring_loop(self):
        """Background monitoring loop"""
        logger.info("Starting monitoring loop")
        self.monitoring_active = True

        while self.monitoring_active:
            try:
                # Collect metrics
                metrics = self.collect_metrics()
                self.current_metrics = metrics

                # Store in database
                self.store_metrics(metrics)

                # Emit to connected clients
                self.socketio.emit("metrics_update", metrics)

                # Sleep until next collection
                time.sleep(self.update_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Brief pause on error

    def start_monitoring(self):
        """Start background monitoring"""
        if not self.monitoring_active:
            monitoring_thread = threading.Thread(
                target=self.monitoring_loop, daemon=True
            )
            monitoring_thread.start()
            logger.info("Monitoring started")

    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        logger.info("Monitoring stopped")

    def run(self, host: str = "0.0.0.0", port: int = 8080, debug: bool = False):
        """Run the dashboard with web routes"""
        # Import and setup routes
        try:
            from .web_interface import setup_routes, setup_socketio_events
        except ImportError:
            from web_interface import setup_routes, setup_socketio_events
        setup_routes(self)
        setup_socketio_events(self)

        self.start_monitoring()

        logger.info(f"Starting deployment dashboard on http://{host}:{port}")

        try:
            self.socketio.run(self.app, host=host, port=port, debug=debug)
        except KeyboardInterrupt:
            logger.info("Shutting down dashboard...")
        finally:
            self.stop_monitoring()


if __name__ == "__main__":
    # Validation tests
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: DeploymentDashboard instantiation
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

    # Test 2: Database initialization through db_manager
    total_tests += 1
    try:
        dashboard = DeploymentDashboard()
        dashboard.db_path = ":memory:"  # Use in-memory database for testing
        dashboard.db_manager.db_path = ":memory:"
        dashboard.db_manager.init_database()
        # Test passed if no exception
    except Exception as e:
        all_validation_failures.append(f"Database initialization failed: {e}")

    # Test 3: Metrics collection function
    total_tests += 1
    try:
        dashboard = DeploymentDashboard()
        metrics = dashboard.collect_metrics()
        if (
            isinstance(metrics, dict)
            and "timestamp" in metrics
            and "services" in metrics
        ):
            pass  # Test passed
        else:
            all_validation_failures.append(
                f"Metrics collection returned invalid format: {type(metrics)}"
            )
    except Exception as e:
        all_validation_failures.append(f"Metrics collection failed: {e}")

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
        print("Dashboard core module is validated and ready for use")
        sys.exit(0)
