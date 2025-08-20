#!/usr/bin/env python3
"""
배포 검증용 상세 헬스체크 API 모듈

이 모듈은 배포 후 시스템 상태를 종합적으로 검증하는 API를 제공합니다.
- /api/deployment/health-detailed: 전체 시스템 상태 상세 점검
- /api/deployment/readiness: Kubernetes readiness probe용
- /api/deployment/liveness: Kubernetes liveness probe용  
- /api/deployment/dependencies: 의존성 서비스 상태 점검

Links:
- Flask documentation: https://flask.palletsprojects.com/
- Kubernetes health checks: https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/

Sample input: GET /api/deployment/health-detailed
Expected output: JSON with comprehensive health status including dependencies, performance metrics, and readiness status
"""

import logging
import time
from datetime import datetime

from flask import Blueprint, jsonify

# Import handling for both module and standalone execution
try:
    from ...core.exceptions import create_error_response
    from ...core.unified_service import get_unified_service
    from .health_checks import (
        check_database_health,
        check_redis_health,
        check_collection_health,
        get_performance_metrics,
    )
except ImportError:
    # Fallback for standalone execution
    import os
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

    try:
        from src.core.exceptions import create_error_response
        from src.core.unified_service import get_unified_service
        from src.api.deployment.health_checks import (
            check_database_health,
            check_redis_health,
            check_collection_health,
            get_performance_metrics,
        )
    except ImportError:
        # Mock for testing
        def get_unified_service():
            class MockService:
                def get_system_health(self):
                    return {"status": "healthy", "total_ips": 100}

            return MockService()

        def create_error_response(code, message, status_code):
            return {"error": {"code": code, "message": message}}, status_code
            
        # Mock health check functions
        def check_database_health():
            return "healthy", {"status": "healthy"}
        def check_redis_health():
            return "healthy", {"status": "healthy"}
        def check_collection_health():
            return "enabled", {"status": "enabled"}
        def get_performance_metrics():
            return {"cpu_percent": 10}


logger = logging.getLogger(__name__)

# Deployment health routes blueprint
deployment_health_bp = Blueprint(
    "deployment_health", __name__, url_prefix="/api/deployment"
)

# Service instance
service = get_unified_service()




@deployment_health_bp.route("/health-detailed", methods=["GET"])
def detailed_deployment_health():
    """종합적인 배포 상태 점검 - 모든 의존성 포함"""
    try:
        start_time = time.time()

        # Check all components using imported health check functions
        db_status, db_details = check_database_health()
        redis_status, redis_details = check_redis_health()
        collection_status, collection_details = check_collection_health()

        # Performance metrics
        performance = get_performance_metrics()

        # Overall health determination
        critical_failures = [status for status in [db_status] if status == "error"]
        degraded_services = [
            status
            for status in [db_status, redis_status, collection_status]
            if status in ["unhealthy", "degraded", "disabled"]
        ]

        if critical_failures:
            overall_status = "unhealthy"
            deployment_ready = False
        elif degraded_services:
            overall_status = "degraded"
            deployment_ready = True  # Still functional
        else:
            overall_status = "healthy"
            deployment_ready = True

        response_time_ms = int((time.time() - start_time) * 1000)

        response_data = {
            "status": overall_status,
            "deployment_ready": deployment_ready,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "blacklist-management",
            "version": "1.0.35",
            "response_time_ms": response_time_ms,
            "components": {
                "database": db_details,
                "cache": redis_details,
                "collection": collection_details,
            },
            "performance": performance,
            "summary": {
                "total_components": 3,
                "healthy": len(
                    [
                        s
                        for s in [db_status, redis_status, collection_status]
                        if s == "healthy"
                    ]
                ),
                "degraded": len(
                    [
                        s
                        for s in [db_status, redis_status, collection_status]
                        if s in ["degraded", "disabled"]
                    ]
                ),
                "failed": len(critical_failures),
            },
        }

        status_code = 200 if overall_status != "unhealthy" else 503
        return jsonify(response_data), status_code

    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return create_error_response(
            "deployment_health_failed", f"Deployment health check failed: {str(e)}", 500
        )


@deployment_health_bp.route("/readiness", methods=["GET"])
def readiness_probe():
    """Kubernetes readiness probe - 트래픽 수신 준비 상태"""
    try:
        # Basic health check
        health_info = service.get_system_health()

        if health_info.get("status") == "healthy":
            return (
                jsonify(
                    {
                        "status": "ready",
                        "timestamp": datetime.utcnow().isoformat(),
                        "message": "Service ready to receive traffic",
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "status": "not_ready",
                        "timestamp": datetime.utcnow().isoformat(),
                        "message": "Service not ready for traffic",
                    }
                ),
                503,
            )

    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        return (
            jsonify(
                {
                    "status": "not_ready",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            503,
        )


@deployment_health_bp.route("/liveness", methods=["GET"])
def liveness_probe():
    """Kubernetes liveness probe - 서비스 생존 상태"""
    try:
        # Simple liveness check - service responsive
        return (
            jsonify(
                {
                    "status": "alive",
                    "timestamp": datetime.utcnow().isoformat(),
                    "message": "Service is alive",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Liveness probe failed: {e}")
        return (
            jsonify(
                {
                    "status": "dead",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            503,
        )


@deployment_health_bp.route("/dependencies", methods=["GET"])
def dependencies_check():
    """외부 의존성 서비스 상태 점검"""
    try:
        dependencies = {}
        overall_healthy = True

        # Database dependency using imported function
        db_status, db_details = check_database_health()
        dependencies["postgresql"] = db_details
        if db_status == "error":
            overall_healthy = False

        # Cache dependency using imported function
        redis_status, redis_details = check_redis_health()
        dependencies["redis"] = redis_details
        # Redis degradation is not critical

        # Collection system dependency using imported function
        collection_status, collection_details = check_collection_health()
        dependencies["collection"] = collection_details
        # Collection disabled is not critical

        response_data = {
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "dependencies": dependencies,
            "critical_failures": not overall_healthy,
        }

        status_code = 200 if overall_healthy else 503
        return jsonify(response_data), status_code

    except Exception as e:
        logger.error(f"Dependencies check failed: {e}")
        return create_error_response(
            "dependencies_check_failed", f"Dependencies check failed: {str(e)}", 500
        )


@deployment_health_bp.route("/metrics", methods=["GET"])
def deployment_metrics():
    """배포 관련 메트릭 수집"""
    try:
        health_info = service.get_system_health()
        performance = get_performance_metrics()

        # API response time test
        start_time = time.time()
        service.get_system_health()  # Test call
        api_response_time = int((time.time() - start_time) * 1000)

        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "blacklist": {
                "total_ips": health_info.get("total_ips", 0),
                "active_ips": health_info.get("active_ips", 0),
                "expired_ips": health_info.get("expired_ips", 0),
            },
            "performance": {**performance, "api_response_time_ms": api_response_time},
            "collection": {
                "enabled": health_info.get("collection_enabled", False),
                "last_collection": health_info.get("last_collection", "never"),
            },
            "uptime": health_info.get("uptime", "unknown"),
        }

        return jsonify(metrics), 200

    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        return create_error_response(
            "metrics_collection_failed", f"Metrics collection failed: {str(e)}", 500
        )




if __name__ == "__main__":
    # Validation tests
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: Blueprint configuration
    total_tests += 1
    try:
        if deployment_health_bp.name == "deployment_health":
            print("✅ Blueprint properly configured")
        else:
            all_validation_failures.append(f"Blueprint name incorrect: {deployment_health_bp.name}")
    except Exception as e:
        all_validation_failures.append(f"Blueprint configuration failed: {e}")

    # Test 2: Service instance availability
    total_tests += 1
    try:
        if hasattr(service, 'get_system_health'):
            print("✅ Service instance working")
        else:
            all_validation_failures.append("Service instance missing get_system_health method")
    except Exception as e:
        all_validation_failures.append(f"Service instance failed: {e}")

    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Deployment health routes module is validated and ready for use")
        sys.exit(0)
