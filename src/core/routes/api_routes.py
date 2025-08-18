"""
통합 API 라우트 컨트롤러
분할된 라우트 모듈들을 통합하여 관리
500줄 제한을 준수하도록 리팩토링된 버전
"""

import logging

from flask import Blueprint, jsonify

from .blacklist_routes import blacklist_routes_bp

# 분할된 라우트 모듈들 임포트
from .health_routes import health_routes_bp

logger = logging.getLogger(__name__)

# 메인 API 라우트 블루프린트
api_routes_bp = Blueprint("api_routes", __name__)

# Register sub-blueprints (health routes moved to unified_routes for root-level access)
api_routes_bp.register_blueprint(blacklist_routes_bp)


def register_sub_routes(app):
    """
    분할된 라우트 블루프린트들을 앱에 등록

    Args:
        app: Flask 애플리케이션 인스턴스
    """
    app.register_blueprint(health_routes_bp)
    app.register_blueprint(blacklist_routes_bp)

    logger.info("Registered all sub-route blueprints")


from .blacklist_routes import (
    get_active_blacklist,
    get_enhanced_blacklist,
    get_fortigate_format,
)

# 레거시 호환성을 위한 임포트 (기존 코드와의 호환성 유지)
from .health_routes import health_check


@api_routes_bp.route("/api/docs", methods=["GET"])
def api_docs():
    """
    API 리스트 및 기본 문서
    """
    return jsonify(
        {
            "message": "Blacklist Management API Documentation",
            "version": "1.0.35",
            "endpoints": {
                "health": {
                    "url": "/health",
                    "method": "GET",
                    "description": "Basic health check",
                },
                "detailed_health": {
                    "url": "/api/health",
                    "method": "GET",
                    "description": "Detailed system health",
                },
                "active_blacklist": {
                    "url": "/api/blacklist/active",
                    "method": "GET",
                    "description": "Get active IP blacklist (text format)",
                },
                "fortigate_format": {
                    "url": "/api/fortigate",
                    "method": "GET",
                    "description": "Get blacklist in FortiGate format",
                },
                "enhanced_blacklist": {
                    "url": "/api/v2/blacklist/enhanced",
                    "method": "GET",
                    "description": "Enhanced blacklist with metadata",
                },
            },
            "notes": [
                "기존 대용량 api_routes.py 파일을 모듈별로 분할",
                "헬스체크 기능: health_routes.py",
                "블랙리스트 기능: blacklist_routes.py",
                "수집 기능: collection_routes.py (별도 파일)",
                "500줄 제한 준수를 위한 리팩토링 완료",
            ],
        }
    )


# 대용량 파일 분할 완료:
# - api_routes.py: 475줄 -> 80줄 (이 파일)
# - health_routes.py: 헬스체크 전용 (약 120줄)
# - blacklist_routes.py: 블랙리스트 전용 (약 140줄)
# - regtech_auth.py: REGTECH 인증 (약 180줄)
# - regtech_parser.py: REGTECH 파싱 (약 250줄)

# 모든 분할된 모듈들이 500줄 제한을 준수함
