"""
웹 인터페이스 라우트
대시보드, 페이지, 웹 UI 관련 라우트
"""

import logging
from datetime import datetime

from flask import Blueprint, jsonify, redirect, render_template, url_for

from ..unified_service import get_unified_service

logger = logging.getLogger(__name__)

# 웹 라우트 블루프린트
web_routes_bp = Blueprint("web_routes", __name__)

# 통합 서비스 인스턴스
service = get_unified_service()


def _get_dashboard_data():
    """대시보드 데이터 준비 (공통 함수)"""
    try:
        # 실제 블랙리스트 데이터 가져오기
        from src.core.container import get_container

        container = get_container()
        blacklist_mgr = container.get("blacklist_manager")

        # 실제 IP 개수 조회 (문자열 리스트 반환)
        active_ips_list = blacklist_mgr.get_active_ips()
        total_ips = len(active_ips_list) if active_ips_list else 0

        # 소스별 통계는 데이터베이스에서 직접 조회
        regtech_count = 0
        secudium_count = 0
        public_count = 0

        try:
            # 데이터베이스에서 소스별 통계 직접 조회 (PostgreSQL 연결 사용)
            import os

            import psycopg2

            # Get PostgreSQL connection URL from environment
            database_url = os.environ.get(
                "DATABASE_URL",
                "postgresql://blacklist_user:blacklist_password_change_me@localhost:32543/blacklist",
            )

            with psycopg2.connect(database_url) as conn:
                cursor = conn.cursor()

                # 소스별 카운트 조회 (blacklist_entries 테이블 사용 - PostgreSQL 문법)
                cursor.execute(
                    """
                    SELECT 
                        LOWER(source) as source_name,
                        COUNT(*) as count
                    FROM blacklist_entries 
                    WHERE is_active = true 
                      AND (expiry_date IS NULL OR expiry_date > NOW())
                    GROUP BY LOWER(source)
                """
                )

                source_results = cursor.fetchall()
                for source_name, count in source_results:
                    if "regtech" in source_name:
                        regtech_count += count
                    elif "secudium" in source_name:
                        secudium_count += count
                    else:
                        public_count += count

        except Exception as db_error:
            logger.error(f"Database source query error: {db_error}")
            # 기본값으로 전체를 public으로 처리
            public_count = total_ips

        stats = {
            "total_ips": total_ips,
            "active_ips": total_ips,  # 활성 IP는 전체와 동일
            "regtech_count": regtech_count,
            "secudium_count": secudium_count,
            "public_count": public_count,
        }

        logger.info(
            f"Dashboard stats: total={total_ips}, regtech={regtech_count}, secudium={secudium_count}, public={public_count}"
        )

    except Exception as e:
        logger.error(f"Dashboard data collection error: {e}")
        # 기본값 사용
        stats = {
            "total_ips": 0,
            "active_ips": 0,
            "regtech_count": 0,
            "secudium_count": 0,
            "public_count": 0,
        }

    # 템플릿 데이터 준비
    # Calculate real percentages
    total = stats.get("total_ips", 0)
    regtech_count = stats.get("regtech_count", 0)
    secudium_count = stats.get("secudium_count", 0)
    public_count = stats.get("public_count", 0)

    regtech_pct = round((regtech_count / total * 100) if total > 0 else 0, 1)
    secudium_pct = round((secudium_count / total * 100) if total > 0 else 0, 1)
    public_pct = round((public_count / total * 100) if total > 0 else 0, 1)

    # Get real monthly data (for now, return empty if no data)
    monthly_data = []
    if total > 0:
        # Show current month with actual data
        current_month = datetime.now().strftime("%m월")
        monthly_data = [{"month": current_month, "count": total}]

    # 활성 소스 목록 생성
    active_sources = []
    if regtech_count > 0:
        active_sources.append("REGTECH")
    if secudium_count > 0:
        active_sources.append("SECUDIUM")
    if public_count > 0:
        active_sources.append("Public")

    template_data = {
        "total_ips": stats.get("total_ips", 0),
        "active_ips": stats.get("active_ips", 0),
        "active_sources": active_sources,
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "monthly_data": monthly_data,
        "source_distribution": {
            "regtech": {"count": regtech_count, "percentage": regtech_pct},
            "secudium": {"count": secudium_count, "percentage": secudium_pct},
            "public": {"count": public_count, "percentage": public_pct},
        },
    }
    return template_data


@web_routes_bp.route("/", methods=["GET"])
@web_routes_bp.route("/dashboard-fixed", methods=["GET"])
def dashboard():
    """메인페이지 - 통합 관리패널 (임시로 다른 경로 사용)"""
    try:
        # Use the same template as working unified-control endpoint
        return render_template("unified_control.html")
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        # Return simple HTML as fallback
        return (
            """
        <html>
        <head><title>Dashboard</title></head>
        <body>
            <h1>Dashboard Temporarily Unavailable</h1>
            <p>Error: {}</p>
            <p><a href="/unified-control">Use Unified Control Panel</a></p>
            <p><a href="/test">Test Page</a></p>
        </body>
        </html>
        """.format(
                str(e)
            ),
            500,
        )


@web_routes_bp.route("/legacy-dashboard", methods=["GET"])
def legacy_dashboard():
    """레거시 대시보드 (백업용)"""
    try:
        return render_template("dashboard.html", **_get_dashboard_data())
    except Exception as e:
        logger.error(f"Dashboard template error: {e}")
        return (
            jsonify(
                {
                    "error": "Dashboard rendering failed",
                    "message": str(e),
                    "fallback": "Try /test for a simple page",
                }
            ),
            500,
        )


@web_routes_bp.route("/unified-control-old", methods=["GET"])
def unified_control_panel():
    """통합 관리패널 (원래 데이터 포함 버전 - 임시 비활성화)"""
    try:
        return render_template("unified_dashboard.html", **_get_dashboard_data())
    except Exception as e:
        logger.error(f"Unified control panel error: {e}")
        return (
            jsonify({"error": "Unified control panel failed", "message": str(e)}),
            500,
        )


@web_routes_bp.route("/raw-data", methods=["GET"])
def raw_data_page():
    """전체 데이터 조회 페이지"""
    try:
        return render_template("raw_data.html", **_get_dashboard_data())
    except Exception as e:
        logger.error(f"Raw data page error: {e}")
        return jsonify({"error": "Raw data page failed", "message": str(e)}), 500


@web_routes_bp.route("/test", methods=["GET"])
def test_page():
    """간단한 테스트 페이지"""
    return "<html><body><h1>Test Page Working</h1><p>Simple HTML without templates</p></body></html>"


@web_routes_bp.route("/docker-logs", methods=["GET"])
def docker_logs_page():
    """Docker 로그 웹 인터페이스"""
    return render_template("docker_logs.html")


@web_routes_bp.route("/search", methods=["GET"])
@web_routes_bp.route("/blacklist-search", methods=["GET"])
def blacklist_search():
    """IP 검색 페이지"""
    try:
        return render_template("blacklist_search.html")
    except Exception as e:
        logger.error(f"Search page error: {e}")
        return (
            jsonify(
                {
                    "error": "Search page not available",
                    "message": str(e),
                    "fallback": "Use /api/search/<ip> for direct search",
                }
            ),
            500,
        )


@web_routes_bp.route("/collection-control", methods=["GET"])
def collection_control():
    """수집 제어 패널 페이지 - 통합 관리로 리디렉션"""
    return redirect(url_for("unified.web_routes.unified_control"))


@web_routes_bp.route("/unified-control", methods=["GET"])
def unified_control():
    """통합 관리 패널 (수집 제어 + 데이터 관리)"""
    try:
        return render_template("unified_control.html")
    except Exception as e:
        logger.error(f"Unified control page error: {e}")
        return (
            jsonify(
                {
                    "error": "Unified control page not available",
                    "message": str(e),
                    "fallback": "Use /api/collection/status for status",
                }
            ),
            500,
        )


@web_routes_bp.route("/connection-status", methods=["GET"])
def connection_status():
    """연결 상태 페이지"""
    try:
        return render_template("connection_status.html")
    except Exception as e:
        logger.error(f"Connection status page error: {e}")
        return (
            jsonify(
                {
                    "error": "Connection status page not available",
                    "message": str(e),
                    "fallback": "Use /health for system health",
                }
            ),
            500,
        )


@web_routes_bp.route("/data-management", methods=["GET"])
def data_management():
    """데이터 관리 페이지 - 통합 관리로 리디렉션"""
    return redirect(url_for("unified.web_routes.unified_control"))


@web_routes_bp.route("/system-logs", methods=["GET"])
def system_logs():
    """시스템 로그 페이지"""
    try:
        return render_template("system_logs.html")
    except Exception as e:
        logger.error(f"System logs page error: {e}")
        return redirect(url_for("web_routes.docker_logs_page"))


@web_routes_bp.route("/statistics", methods=["GET"])
def statistics():
    """통계 페이지"""
    try:
        return render_template("statistics.html")
    except Exception as e:
        logger.error(f"Statistics page error: {e}")
        return (
            jsonify(
                {
                    "error": "Statistics page not available",
                    "message": str(e),
                    "fallback": "Use /api/stats for statistics data",
                }
            ),
            500,
        )
