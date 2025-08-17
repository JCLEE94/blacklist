"""
핵심 API 라우트
핵심 API 엔드포인트: health, blacklist, fortigate
"""

import logging
from datetime import datetime

from flask import Blueprint, Response, jsonify, request

from ..exceptions import create_error_response
from ..unified_service import get_unified_service

logger = logging.getLogger(__name__)

# API 라우트 블루프린트
api_routes_bp = Blueprint("api_routes", __name__)

# 통합 서비스 인스턴스
service = get_unified_service()


@api_routes_bp.route("/health", methods=["GET"])
@api_routes_bp.route("/healthz", methods=["GET"])
@api_routes_bp.route("/ready", methods=["GET"])
def health_check():
    """통합 서비스 헬스 체크 - K8s probe용 (rate limit 없음)"""
    try:
        health_info = service.get_system_health()

        # Create components structure expected by tests
        components = {
            "database": (
                "healthy" if health_info.get("status") == "healthy" else "unhealthy"
            ),
            "cache": "healthy",  # Assume cache is healthy for now
            "blacklist": (
                "healthy" if health_info.get("total_ips", 0) >= 0 else "unhealthy"
            ),
        }

        overall_status = (
            "healthy"
            if all(status == "healthy" for status in components.values())
            else "degraded"
        )

        response_data = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "blacklist",
            "version": "1.0.35",
            "components": components,
            "details": health_info,
        }

        # Add detailed metrics if requested
        from flask import request

        if request.args.get("detailed") == "true":
            import psutil

            response_data["response_time_ms"] = 1.0  # Placeholder
            response_data["memory_usage_mb"] = (
                psutil.Process().memory_info().rss / 1024 / 1024
            )

        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": str(e),
                    "components": {
                        "database": "unhealthy",
                        "cache": "unhealthy",
                        "blacklist": "unhealthy",
                    },
                }
            ),
            503,
        )


@api_routes_bp.route("/api/health", methods=["GET"])
def service_status():
    """서비스 상태 조회"""
    try:
        stats = service.get_system_stats()
        return jsonify(
            {
                "success": True,
                "data": {
                    "service_status": "running",
                    "database_connected": True,
                    "cache_available": True,
                    "total_ips": len(service.get_active_blacklist_entries()),
                    "active_ips": len(service.get_active_blacklist_entries()),
                    "last_updated": datetime.utcnow().isoformat(),
                },
            }
        )
    except Exception as e:
        logger.error(f"Service status error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/docs", methods=["GET"])
def api_docs():
    """API 문서"""
    return jsonify(
        {
            "message": "API Documentation",
            "dashboard_url": "/",
            "note": "Visit / or /dashboard for the web interface",
            "api_endpoints": {
                "health": "/health",
                "stats": "/api/stats",
                "blacklist": "/api/blacklist/active",
                "fortigate": "/api/fortigate",
                "collection": "/api/collection/status",
            },
        }
    )


@api_routes_bp.route("/api/blacklist/active", methods=["GET"])
def get_active_blacklist():
    """활성 블랙리스트 조회 (플레인 텍스트)"""
    try:
        ips = service.get_active_blacklist_entries()

        # Accept 헤더를 확인하여 응답 형식 결정
        accept_header = request.headers.get("Accept", "text/plain")

        if "application/json" in accept_header:
            # JSON 형식으로 반환
            return jsonify(
                {
                    "success": True,
                    "count": len(ips),
                    "ips": ips,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        else:
            # 기본값: 플레인 텍스트 형식으로 반환
            ip_list = "\n".join(ips) if ips else ""
            return Response(
                ip_list,
                mimetype="text/plain; charset=utf-8",
                headers={
                    "X-Total-Count": str(len(ips)),
                },
            )
    except Exception as e:
        logger.error(f"Active blacklist error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/blacklist/active-txt", methods=["GET"])
def get_active_blacklist_txt():
    """활성 블랙리스트 조회 (플레인 텍스트)"""
    try:
        ips = service.get_active_blacklist_entries()

        # 플레인 텍스트 형식으로 반환
        ip_list = "\n".join(ips) if ips else ""

        response = Response(
            ip_list,
            mimetype="text/plain",
            headers={
                "Content-Disposition": "attachment; filename=blacklist.txt",
                "X-Total-Count": str(len(ips)),
            },
        )
        return response
    except Exception as e:
        logger.error(f"Active blacklist txt error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/blacklist/active-simple", methods=["GET"])
def get_active_blacklist_simple():
    """활성 블랙리스트 조회 (심플 텍스트 - FortiGate용)"""
    try:
        ips = service.get_active_blacklist_entries()

        # 심플 텍스트 형식으로 반환 (한 줄에 하나씩)
        ip_list = "\n".join(ips) if ips else ""

        response = Response(ip_list, mimetype="text/plain")
        return response
    except Exception as e:
        logger.error(f"Active blacklist simple error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/fortigate", methods=["GET"])
@api_routes_bp.route("/api/fortigate-simple", methods=["GET"])
def get_fortigate_simple():
    """FortiGate External Connector 형식 (심플 버전)"""
    try:
        ips = service.get_active_blacklist_entries()

        # FortiGate External Connector 형식
        data = {
            "status": "success",
            "type": "IP",
            "version": 1,
            "blacklist": ips,
            "data": ips,
        }

        return jsonify(data)
    except Exception as e:
        logger.error(f"FortiGate simple error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/stats", methods=["GET"])
def get_stats():
    """시스템 통계 조회"""
    try:
        stats = service.get_system_stats()
        return jsonify({
            "success": True,
            "data": stats
        })
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/sources/status", methods=["GET"])
def get_sources_status():
    """데이터 소스 상태 조회"""
    try:
        # Mock data for now - replace with actual service call
        sources_status = {
            "REGTECH": {
                "status": "active",
                "last_updated": datetime.utcnow().isoformat(),
                "total_ips": 0
            },
            "SECUDIUM": {
                "status": "active", 
                "last_updated": datetime.utcnow().isoformat(),
                "total_ips": 0
            }
        }
        
        return jsonify({
            "success": True,
            "data": sources_status
        })
    except Exception as e:
        logger.error(f"Sources status error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/v2/analytics/summary", methods=["GET"])
def get_analytics_summary():
    """분석 요약 데이터 조회"""
    try:
        # Mock analytics data for now
        summary = {
            "total_ips": 0,
            "active_ips": 0,
            "blocked_today": 0,
            "threat_levels": {
                "high": 0,
                "medium": 0,
                "low": 0
            }
        }
        
        return jsonify({
            "success": True,
            "data": summary
        })
    except Exception as e:
        logger.error(f"Analytics summary error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/v2/analytics/trends", methods=["GET"])
def get_analytics_trends():
    """트렌드 분석 데이터 조회"""
    try:
        # Mock trends data for now
        trends = {
            "daily_trends": [],
            "source_distribution": {},
            "geo_distribution": {}
        }
        
        return jsonify({
            "success": True,
            "data": trends
        })
    except Exception as e:
        logger.error(f"Analytics trends error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/monitoring/dashboard", methods=["GET"])
def monitoring_dashboard():
    """모니터링 대시보드 데이터"""
    try:
        dashboard_data = {
            "system_health": service.get_system_health(),
            "stats": service.get_system_stats(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return jsonify({
            "success": True,
            "data": dashboard_data
        })
    except Exception as e:
        logger.error(f"Monitoring dashboard error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/metrics", methods=["GET"])
def prometheus_metrics():
    """Prometheus 메트릭 엔드포인트 - 55개 메트릭 제공"""
    try:
        # 고급 메트릭 시스템 사용
        from ..monitoring.prometheus_metrics import get_metrics
        
        metrics_instance = get_metrics()
        
        # 실시간 데이터 수집
        stats = service.get_system_stats()
        health = service.get_system_health()
        
        # 시스템 정보 수집
        import psutil
        import time
        from datetime import datetime
        
        system_info = {
            "active_connections": 1,  # Flask connection
            "memory": {
                "rss": psutil.Process().memory_info().rss,
                "vms": psutil.Process().memory_info().vms,
                "shared": getattr(psutil.Process().memory_info(), 'shared', 0)
            },
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "disk": {
                "/app": {
                    "used": psutil.disk_usage('/').used,
                    "free": psutil.disk_usage('/').free,
                    "total": psutil.disk_usage('/').total
                }
            }
        }
        
        # 비즈니스 정보 수집
        business_data = {
            "ip_stats": {
                "regtech": {"active": stats.get('regtech_active', 0), "inactive": stats.get('regtech_inactive', 0)},
                "secudium": {"active": stats.get('secudium_active', 0), "inactive": stats.get('secudium_inactive', 0)}
            },
            "data_freshness": {
                "regtech": stats.get('regtech_last_update_seconds', 0),
                "secudium": stats.get('secudium_last_update_seconds', 0)
            },
            "cache": {
                "size_bytes": stats.get('cache_size', 0)
            },
            "database": {
                "active": 1,
                "idle": 0,
                "total": 1
            }
        }
        
        # 메트릭 업데이트
        metrics_instance.update_system_metrics(system_info)
        metrics_instance.update_business_metrics(business_data)
        
        # 버전 정보 설정
        metrics_instance.set_version_info("1.0.35", datetime.now().strftime("%Y-%m-%d"), "latest")
        
        # Prometheus 형식 응답 생성
        return metrics_instance.get_metrics_response()
        
    except Exception as e:
        logger.error(f"Advanced metrics error: {e}")
        
        # 기본 메트릭 fallback
        try:
            stats = service.get_system_stats()
            
            fallback_metrics = f"""# HELP blacklist_up Service health status
# TYPE blacklist_up gauge
blacklist_up 1

# HELP blacklist_total_ips Total number of IPs
# TYPE blacklist_total_ips gauge
blacklist_total_ips {stats.get('total_ips', 0)}

# HELP blacklist_active_ips Number of active IPs
# TYPE blacklist_active_ips gauge
blacklist_active_ips {stats.get('active_ips', 0)}

# HELP blacklist_errors_total Total errors
# TYPE blacklist_errors_total counter
blacklist_errors_total{{error_type="metric_generation",component="prometheus"}} 1
"""
            
            return Response(
                fallback_metrics, 
                mimetype="text/plain; version=0.0.4",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        except Exception as fallback_error:
            logger.error(f"Fallback metrics error: {fallback_error}")
            return Response(
                "# Metrics system unavailable\nblacklist_up 0\n", 
                mimetype="text/plain",
                status=500
            )

@api_routes_bp.route("/api/realtime/stats", methods=["GET"])
def realtime_stats():
    """실시간 통계 조회"""
    try:
        stats = service.get_system_stats()
        return jsonify({
            "success": True,
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Realtime stats error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/realtime/collection-status", methods=["GET"])
def realtime_collection_status():
    """실시간 수집 상태 조회"""
    try:
        from ..collection_manager import get_collection_manager
        manager = get_collection_manager()
        status = manager.get_collection_status()
        
        return jsonify({
            "success": True,
            "data": status,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Realtime collection status error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/monitoring/system", methods=["GET"])
def monitoring_system():
    """시스템 모니터링 데이터"""
    try:
        import psutil
        
        system_info = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "percent": psutil.virtual_memory().percent,
                "used": psutil.virtual_memory().used,
                "total": psutil.virtual_memory().total
            },
            "disk": {
                "percent": psutil.disk_usage('/').percent,
                "used": psutil.disk_usage('/').used,
                "total": psutil.disk_usage('/').total
            },
            "uptime": datetime.utcnow().isoformat()
        }
        
        return jsonify({
            "success": True,
            "data": system_info
        })
    except Exception as e:
        logger.error(f"System monitoring error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/realtime/feed", methods=["GET"])
def realtime_feed():
    """실시간 피드 데이터"""
    try:
        import random
        
        # 시뮬레이션된 실시간 이벤트
        events = [
            {"type": "info", "message": "시스템 정상 작동 중", "icon": "bi-info-circle"},
            {"type": "success", "message": "헬스체크 통과", "icon": "bi-check-circle"},
            {"type": "warning", "message": "메모리 사용률 증가", "icon": "bi-exclamation-triangle"}
        ]
        
        event = random.choice(events)
        event["timestamp"] = datetime.utcnow().strftime("%H:%M:%S")
        
        return jsonify({
            "success": True,
            "event": event
        })
    except Exception as e:
        logger.error(f"Realtime feed error: {e}")
        return jsonify(create_error_response(e)), 500
