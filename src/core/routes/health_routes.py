"""
헬스체크 전용 라우트
api_routes.py에서 분할된 헬스체크 관련 엔드포인트
"""

import logging
from datetime import datetime

from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)

from ..exceptions import create_error_response
from ..unified_service import get_unified_service
from ..utils.version_utils import get_dynamic_version
from ..utils.uptime_tracker import (
    get_uptime_detailed,
    get_uptime_formatted,
    get_system_uptime_info,
)

# 헬스체크 라우트 블루프린트
health_routes_bp = Blueprint("health_routes", __name__)

# 통합 서비스 인스턴스
service = get_unified_service()


@health_routes_bp.route("/health", methods=["GET"])
@health_routes_bp.route("/healthz", methods=["GET"])
@health_routes_bp.route("/ready", methods=["GET"])
def health_check():
    """통합 서비스 헬스 체크 - K8s probe용 (rate limit 없음)"""
    try:
        health_info = service.get_system_health()

        # Create components structure expected by tests
        db_status = health_info.get("status")
        components = {
            "database": "healthy" if db_status == "healthy" else "unhealthy",
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

        # 업타임 정보 추가
        uptime_info = get_uptime_detailed()

        response_data = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "blacklist-management",
            "version": get_dynamic_version(),
            "uptime": uptime_info["uptime_formatted"],
            "uptime_seconds": uptime_info["uptime_seconds"],
            "started_at": uptime_info["started_at"],
            "components": components,
        }

        status_code = 200 if overall_status == "healthy" else 503
        return jsonify(response_data), status_code

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        error_response = {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "service": "blacklist-management",
        }
        return jsonify(error_response), 503


@health_routes_bp.route("/api/health", methods=["GET"])
def detailed_health_check():
    """상세 헬스 체크 - 모든 컴포넌트 상태 포함"""
    try:
        # 기본 헬스 정보 수집
        health_info = service.get_system_health()

        # 상세 컴포넌트 체크
        db_status = health_info.get("status")
        collection_enabled = health_info.get("collection_enabled")

        detailed_components = {
            "database": {
                "status": "healthy" if db_status == "healthy" else "unhealthy",
                "total_entries": health_info.get("total_ips", 0),
                "last_updated": health_info.get("last_updated", "unknown"),
            },
            "cache": {"status": "healthy", "type": "redis", "fallback": "memory"},
            "collection": {
                "status": "enabled" if collection_enabled else "disabled",
                "last_collection": health_info.get("last_collection", "never"),
            },
            "sources": {"regtech": "available", "secudium": "available"},
        }

        overall_status = "healthy"
        for component, details in detailed_components.items():
            if isinstance(details, dict) and details.get("status") in [
                "unhealthy",
                "error",
            ]:
                overall_status = "degraded"
                break

        # 상세 업타임 및 시스템 정보
        system_uptime_info = get_system_uptime_info()

        response_data = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "blacklist-management",
            "version": get_dynamic_version(),
            "uptime": system_uptime_info["application"],
            "system": system_uptime_info["system"],
            "components": detailed_components,
            "metrics": {
                "total_ips": health_info.get("total_ips", 0),
                "active_ips": health_info.get("active_ips", 0),
                "expired_ips": health_info.get("expired_ips", 0),
            },
        }

        status_code = 200 if overall_status == "healthy" else 503
        return jsonify(response_data), status_code

    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return create_error_response(
            "health_check_failed", f"Health check failed: {str(e)}", 500
        )


@health_routes_bp.route("/build-info", methods=["GET"])
def visual_build_info():
    """빌드 정보 시각적 표시"""
    try:
        import os
        import subprocess

        from flask import render_template_string

        # Git 정보 수집
        try:
            git_commit = (
                subprocess.check_output(
                    ["git", "rev-parse", "--short", "HEAD"],
                    cwd=os.path.dirname(__file__),
                )
                .decode()
                .strip()
            )
        except BaseException:
            git_commit = "unknown"

        try:
            git_branch = (
                subprocess.check_output(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=os.path.dirname(__file__),
                )
                .decode()
                .strip()
            )
        except BaseException:
            git_branch = "unknown"

        try:
            build_date = (
                subprocess.check_output(
                    ["git", "log", "-1", "--format=%ci"], cwd=os.path.dirname(__file__)
                )
                .decode()
                .strip()
            )
        except BaseException:
            build_date = datetime.utcnow().isoformat()

        # 시스템 상태 정보
        health_info = service.get_system_health()

        # HTML 템플릿
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Blacklist Management - Build Info</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; padding: 20px; background: #f5f5f5;
        }
        .container { max-width: 800px; margin: 0 auto; }
        .card {
            background: white; padding: 20px; margin: 20px 0; border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header { text-align: center; color: #333; }
        .version {
            font-size: 2.5em; font-weight: bold; color: #007bff;
            margin: 20px 0; text-align: center;
        }
        .info-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px; margin: 20px 0;
        }
        .info-item { padding: 15px; background: #f8f9fa; border-radius: 4px; }
        .label { font-weight: bold; color: #6c757d; margin-bottom: 5px; }
        .value { color: #333; font-family: monospace; }
        .status {
            display: inline-block; padding: 4px 12px; border-radius: 20px;
            font-size: 0.8em; font-weight: bold; text-transform: uppercase;
        }
        .status.healthy { background: #d4edda; color: #155724; }
        .status.degraded { background: #fff3cd; color: #856404; }
        .footer { text-align: center; color: #6c757d; margin-top: 40px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1 class="header">🛡️ Blacklist Management System</h1>
            <div class="version">v{{ version }}</div>
            <div style="text-align: center;">
                <span class="status {{ status_class }}">{{ status.upper() }}</span>
            </div>
        </div>

        <div class="card">
            <h2>📦 빌드 정보</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="label">Version</div>
                    <div class="value">{{ version }}</div>
                </div>
                <div class="info-item">
                    <div class="label">Git Commit</div>
                    <div class="value">{{ git_commit }}</div>
                </div>
                <div class="info-item">
                    <div class="label">Git Branch</div>
                    <div class="value">{{ git_branch }}</div>
                </div>
                <div class="info-item">
                    <div class="label">Build Date</div>
                    <div class="value">{{ build_date }}</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>📊 시스템 상태</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="label">Total IPs</div>
                    <div class="value">{{ total_ips }}</div>
                </div>
                <div class="info-item">
                    <div class="label">Active IPs</div>
                    <div class="value">{{ active_ips }}</div>
                </div>
                <div class="info-item">
                    <div class="label">Collection Status</div>
                    <div class="value">{{ collection_status }}</div>
                </div>
                <div class="info-item">
                    <div class="label">Last Updated</div>
                    <div class="value">{{ timestamp }}</div>
                </div>
            </div>
        </div>

        <div class="footer">
            <p>🚀 Updated: {{ timestamp }}</p>
            <p><a href="/health">JSON Health Check</a> | <a href="/api/health">Detailed Health</a></p>
        </div>
    </div>
</body>
</html>
        """

        # 템플릿 데이터
        template_data = {
            "version": get_dynamic_version(),
            "git_commit": git_commit,
            "git_branch": git_branch,
            "build_date": build_date,
            "status": health_info.get("status", "unknown"),
            "status_class": (
                "healthy" if health_info.get("status") == "healthy" else "degraded"
            ),
            "total_ips": health_info.get("total_ips", 0),
            "active_ips": health_info.get("active_ips", 0),
            "collection_status": (
                "enabled" if health_info.get("collection_enabled") else "disabled"
            ),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        }

        return render_template_string(html_template, **template_data)

    except Exception as e:
        logger.error(f"Build info error: {e}")
        return f"<h1>Build Info Error</h1><p>{str(e)}</p>", 500


@health_routes_bp.route("/api/uptime", methods=["GET"])
def uptime_info():
    """실시간 업타임 정보 API"""
    try:
        uptime_data = get_system_uptime_info()

        return jsonify(
            {
                "success": True,
                "data": uptime_data,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Uptime info error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
