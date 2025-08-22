"""
Web UI dashboard routes for Blacklist Manager
Main dashboard and overview pages
"""

from .common.imports import Blueprint, flash, redirect, render_template, url_for, logger

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict



dashboard_bp = Blueprint("dashboard", __name__, url_prefix="")


def get_build_time():
    """Get build time directly from .build_info file"""
    try:
        build_info_path = Path(".build_info")
        if build_info_path.exists():
            with open(build_info_path, "r") as f:
                for line in f:
                    if line.startswith("BUILD_TIME="):
                        return line.split("=", 1)[1].strip('"')
        return "2025-06-19 17:56:00 KST"  # Fallback to current build time
    except Exception:
        return "2025-06-19 17:56:00 KST"  # Fallback to current build time


def get_build_version():
    """Get build version directly from .build_info file"""
    try:
        build_info_path = Path(".build_info")
        if build_info_path.exists():
            with open(build_info_path, "r") as f:
                for line in f:
                    if line.startswith("BUILD_VERSION="):
                        return line.split("=", 1)[1].strip('"')
        return "v2.1-202506191756"  # Fallback
    except Exception:
        return "v2.1-202506191756"  # Fallback


def get_blacklist_manager():
    """Get blacklist manager instance - simple mock for minimal functionality"""
    import time

    class MockBlacklistManager:
        def get_system_health(self):
            return {
                "database": "connected",
                "status": "healthy",
                "start_time": time.time() - 3600,  # 1 hour ago
            }

        def get_active_ips(self):
            return ([], 0)

    # Always return mock for simplicity
    return MockBlacklistManager()


def get_stats() -> Dict[str, Any]:
    """Get system statistics with proper error handling"""
    try:
        stats_path = Path("data/stats.json")
        if stats_path.exists():
            with open(stats_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            logger.warning(f"통계 파일이 존재하지 않음: {stats_path}")
    except json.JSONDecodeError as e:
        logger.error(f"통계 파일 JSON 파싱 오류: {e}")
    except IOError as e:
        logger.error(f"통계 파일 읽기 오류: {e}")
    except Exception as e:
        logger.error(f"통계 파일 처리 중 예상치 못한 오류: {e}")

    # Return default stats if file doesn't exist or has errors
    return {
        "total_ips": 0,
        "active_ips": 0,
        "sources": {},
        "last_updated": datetime.now().isoformat(),
    }


@dashboard_bp.route("/test")
def simple_test():
    """Simple test endpoint"""
    return "<h1>Test OK</h1><p>Web routes working</p>"


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard-disabled-for-debug")
def dashboard():
    """Main dashboard page - DISABLED FOR DEBUG"""
    return """
    <html>
    <head><title>Dashboard Disabled</title></head>
    <body>
        <h1>Dashboard Disabled for Debugging</h1>
        <p>Original route disabled to identify issue source</p>
        <p><a href="/unified-control">Unified Control Panel</a></p>
    </body>
    </html>
    """


@dashboard_bp.route("/data-management")
def data_management():
    """Data management page"""
    try:
        # Get current statistics
        stats = get_stats()

        return render_template(
            "data_management.html",
            stats=stats,
            current_time=datetime.now(),
        )
    except Exception as e:
        logger.error(f"Data management page error: {e}")
        flash("페이지 로드 중 오류가 발생했습니다: {str(e)}", "error")
        return redirect(url_for("dashboard.dashboard"))


@dashboard_bp.route("/statistics")
def statistics():
    """Statistics page"""
    return render_template("statistics.html")


@dashboard_bp.route("/connection-status")
def connection_status():
    """Connection status page"""
    try:
        # Test various connections
        connections = []

        # Test database connection
        try:
            blacklist_manager = get_blacklist_manager()
            health = blacklist_manager.get_system_health()
            connections.append(
                {
                    "name": "Database",
                    "status": (
                        "connected" if health["database"] == "connected" else "error"
                    ),
                    "details": "Status: {health['database']}",
                }
            )
        except Exception:
            connections.append(
                {
                    "name": "Database",
                    "status": "error",
                    "details": "Error: {str(e)}",
                }
            )

        # Test external APIs (mock)
        external_apis = [
            {"name": "REGTECH API", "url": "https://regtech.example.com"},
            {"name": "SECUDIUM API", "url": "https://secudium.example.com"},
        ]

        for api in external_apis:
            try:
                # Mock connection test
                connections.append(
                    {
                        "name": api["name"],
                        "status": "connected",  # Mock status
                        "details": "URL: {api['url']}",
                    }
                )
            except Exception:
                connections.append(
                    {
                        "name": api["name"],
                        "status": "error",
                        "details": "Error: {str(e)}",
                    }
                )

        return render_template(
            "connection_status.html",
            connections=connections,
            check_time=datetime.now(),
        )

    except Exception as e:
        logger.error(f"Connection status error: {e}")
        flash("연결 상태 확인 중 오류가 발생했습니다: {str(e)}", "error")
        return redirect(url_for("dashboard.dashboard"))


@dashboard_bp.route("/system-logs")
def system_logs():
    """System logs page"""
    try:
        # Mock log data
        logs = [
            {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "level": "INFO",
                "message": "시스템 정상 동작 중",
                "source": "system",
            },
            {
                "timestamp": (datetime.now() - timedelta(minutes=5)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "level": "INFO",
                "message": "블랙리스트 데이터 업데이트 완료",
                "source": "blacklist",
            },
            {
                "timestamp": (datetime.now() - timedelta(minutes=10)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "level": "INFO",
                "message": "데이터 수집 작업 시작",
                "source": "collection",
            },
        ]

        return render_template(
            "system_logs.html",
            logs=logs,
            current_time=datetime.now(),
        )

    except Exception as e:
        logger.error(f"System logs error: {e}")
        flash("로그 페이지 로드 중 오류가 발생했습니다: {str(e)}", "error")
        return redirect(url_for("dashboard.dashboard"))
