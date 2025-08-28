import logging

from flask import Blueprint, jsonify, redirect

logger = logging.getLogger(__name__)

"""루트 경로 라우트 추가"""


root_bp = Blueprint("root", __name__)


@root_bp.route("/")
def index():
    """루트 경로 - 대시보드로 리다이렉트"""
    return redirect("/dashboard")


@root_bp.route("/api/system")
def system_status():
    """시스템 상태 API"""
    return jsonify(
        {
            "message": "🛡️ Blacklist Management System",
            "version": "3.0.2",
            "status": "running",
            "dashboard": "/dashboard",
            "endpoints": {
                "dashboard": "/dashboard",
                "health": "/health",
                "stats": "/api/stats",
                "blacklist": "/api/blacklist/active",
                "fortigate": "/api/fortigate",
                "collection": "/api/collection/status",
            },
        }
    )


def calculate_source_distribution(stats):
    """실제 데이터를 기반으로 소스별 분포 계산"""
    try:
        sources = stats.get("sources", {})
        total = sum(source.get("total_ips", 0) for source in sources.values())

        if total == 0:
            # 데이터가 없을 때 기본값
            return {
                "regtech": {"count": 0, "percentage": 0},
                "secudium": {"count": 0, "percentage": 0},
                "public": {"count": 0, "percentage": 0},
            }

        regtech_count = sources.get("regtech", {}).get("total_ips", 0)
        secudium_count = sources.get("secudium", {}).get("total_ips", 0)
        public_count = total - regtech_count - secudium_count

        return {
            "regtech": {
                "count": regtech_count,
                "percentage": (
                    round((regtech_count / total) * 100, 1) if total > 0 else 0
                ),
            },
            "secudium": {
                "count": secudium_count,
                "percentage": (
                    round((secudium_count / total) * 100, 1) if total > 0 else 0
                ),
            },
            "public": {
                "count": max(0, public_count),
                "percentage": (
                    round((max(0, public_count) / total) * 100, 1) if total > 0 else 0
                ),
            },
        }
    except Exception as e:
        logger.error(f"소스별 분포 계산 실패: {e}")
        # 오류 시 기본값 반환
        return {
            "regtech": {"count": 0, "percentage": 0},
            "secudium": {"count": 0, "percentage": 0},
            "public": {"count": 0, "percentage": 0},
        }


@root_bp.route("/dashboard")
def dashboard():
    """대시보드 - 메인 대시보드 표시"""
    from flask import render_template

    try:
        # 우리가 만든 dashboard.html 표시
        return render_template("dashboard.html")
    except Exception as e:
        logger.error(f"대시보드 로드 실패: {e}")
        # 실패시 기본 HTML 반환
        return (
            f"""
        <html>
        <head><title>Dashboard Error</title></head>
        <body>
            <h1>Dashboard temporarily unavailable</h1>
            <p>Error: {str(e)}</p>
            <p><a href="/health">Health Check</a></p>
        </body>
        </html>
        """,
            500,
        )


@root_bp.route("/api")
def api_root():
    """API 루트 - 사용 가능한 엔드포인트 목록"""
    return jsonify(
        {
            "message": "Blacklist Management API",
            "version": "1.0.0",
            "endpoints": {
                "health": "/health",
                "api_docs": "/api/docs",
                "blacklist": "/api/blacklist/active",
                "fortigate": "/api/fortigate",
                "stats": "/api/stats",
                "collection_status": "/api/collection/status",
            },
        }
    )
