# !/usr/bin/env python3
"""
Collection Status Routes - Status and statistics endpoints
Handles collection system status, daily stats, and history
"""

import logging
from datetime import datetime, timedelta

from flask import Blueprint, Flask, jsonify, request

logger = logging.getLogger(__name__)

try:
    from ...core.collectors.collector_factory import get_collector_factory
    from ...utils.security import rate_limit

    COLLECTOR_AVAILABLE = True
except ImportError:
    COLLECTOR_AVAILABLE = False


status_bp = Blueprint("collection_status", __name__, url_prefix="/api/collection")


@status_bp.route("/status", methods=["GET"])
@rate_limit(limit=60, window_seconds=60)  # 60 requests per minute
def get_collection_status():
    """Get overall collection system status"""
    if not COLLECTOR_AVAILABLE:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Collection system not available",
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            503,
        )

    try:
        factory = get_collector_factory()
        status = factory.get_collector_status()

        return jsonify(
            {
                "success": True,
                "status": status,
                "timestamp": status.get("timestamp", datetime.now().isoformat()),
            }
        )

    except Exception as e:
        logger.error(f"Failed to get collection status: {e}")
        return (
            jsonify(
                {"success": False, "error": "Unable to retrieve collection status"}
            ),
            500,
        )


@status_bp.route("/daily-stats", methods=["GET"])
@rate_limit(limit=30, window_seconds=60)  # 30 requests per minute
def get_daily_collection_stats():
    """Get daily collection statistics for visualization"""
    if not COLLECTOR_AVAILABLE:
        return (
            jsonify({"success": False, "error": "Collection system not available"}),
            503,
        )

    try:
        days = request.args.get("days", 30, type=int)  # Default 30 days
        if days > 90:  # Limit to 90 days
            days = 90

        factory = get_collector_factory()
        manager = factory.create_collection_manager()

        # Get daily collection data
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        stats = (
            manager.get_daily_stats(start_date, end_date)
            if hasattr(manager, "get_daily_stats")
            else []
        )

        return jsonify(
            {
                "success": True,
                "stats": stats,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days,
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to get daily stats: {e}")
        return (
            jsonify({"success": False, "error": "Unable to retrieve daily statistics"}),
            500,
        )


@status_bp.route("/history", methods=["GET"])
@rate_limit(limit=20, window_seconds=60)  # 20 requests per minute
def get_collection_history():
    """Get collection execution history"""
    if not COLLECTOR_AVAILABLE:
        return (
            jsonify({"success": False, "error": "Collection system not available"}),
            503,
        )

    try:
        limit = request.args.get("limit", 50, type=int)
        offset = request.args.get("offset", 0, type=int)

        if limit > 100:  # Limit to 100 records
            limit = 100

        factory = get_collector_factory()
        manager = factory.create_collection_manager()

        # Get collection history
        history = (
            manager.get_history(limit, offset)
            if hasattr(manager, "get_history")
            else []
        )

        return jsonify(
            {
                "success": True,
                "history": history,
                "pagination": {"limit": limit, "offset": offset, "total": len(history)},
            }
        )

    except Exception as e:
        logger.error(f"Failed to get collection history: {e}")
        return (
            jsonify(
                {"success": False, "error": "Unable to retrieve collection history"}
            ),
            500,
        )


if __name__ == "__main__":
    # Validation test for status routes
    import sys

    app = Flask(__name__)
    app.register_blueprint(status_bp)

    all_validation_failures = []
    total_tests = 0

    print("📊 Testing Collection Status Routes...")

    with app.test_client() as client:
        # Test 1: Status endpoint
        total_tests += 1
        try:
            response = client.get("/api/collection/status")
            if response.status_code not in [200, 503]:
                all_validation_failures.append(
                    f"Status route: Unexpected status code {response.status_code}"
                )
            else:
                print("  - Status endpoint responds correctly")
        except Exception as e:
            all_validation_failures.append(
                f"Status route: Exception occurred - {str(e)}"
            )

        # Test 2: Daily stats endpoint
        total_tests += 1
        try:
            response = client.get("/api/collection/daily-stats?days=7")
            if response.status_code not in [200, 503]:
                all_validation_failures.append(
                    f"Daily stats route: Unexpected status code {response.status_code}"
                )
            else:
                print("  - Daily stats endpoint responds correctly")
        except Exception as e:
            all_validation_failures.append(
                f"Daily stats route: Exception occurred - {str(e)}"
            )

        # Test 3: History endpoint
        total_tests += 1
        try:
            response = client.get("/api/collection/history?limit=10")
            if response.status_code not in [200, 503]:
                all_validation_failures.append(
                    f"History route: Unexpected status code {response.status_code}"
                )
            else:
                print("  - History endpoint responds correctly")
        except Exception as e:
            all_validation_failures.append(
                f"History route: Exception occurred - {str(e)}"
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
        print("Collection Status Routes are ready for use")
        sys.exit(0)
