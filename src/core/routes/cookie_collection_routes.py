#!/usr/bin/env python3
"""
쿠키 기반 수집을 위한 API 라우트
"""

from flask import Flask, Blueprint, jsonify, request, redirect, url_for, render_template
import logging
logger = logging.getLogger(__name__)

import os
from datetime import datetime



# Blueprint 생성
cookie_collection_bp = Blueprint(
    "cookie_collection", __name__, url_prefix="/api/collection/cookie"
)


@cookie_collection_bp.route("/regtech/set", methods=["POST"])
def set_regtech_cookies():
    """REGTECH 쿠키 설정"""
    try:
        data = request.get_json() or {}
        cookie_string = data.get("cookies", "")

        if not cookie_string:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "쿠키 문자열이 필요합니다",
                        "example": "JSESSIONID=ABC123; regtech-front=XYZ789",
                    }
                ),
                400,
            )

        # 환경 변수에 쿠키 설정
        os.environ["REGTECH_COOKIES"] = cookie_string

        # 수집 서비스에 쿠키 설정
        try:
            from ..services.unified_service_factory import get_unified_service

            service = get_unified_service()

            # REGTECH 컴포넌트가 있으면 쿠키 설정
            if "regtech" in service._components:
                service._components["regtech"].set_cookie_string(cookie_string)
                logger.info("REGTECH 쿠키 설정 완료")

        except Exception as e:
            logger.warning(f"서비스에 쿠키 설정 실패: {e}")

        return jsonify(
            {
                "success": True,
                "message": "REGTECH 쿠키가 설정되었습니다",
                "cookie_count": len(cookie_string.split(";")),
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"쿠키 설정 실패: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@cookie_collection_bp.route("/regtech/collect", methods=["POST"])
def collect_with_cookies():
    """쿠키를 사용한 REGTECH 수집"""
    try:
        data = request.get_json() or {}

        # 쿠키 확인
        cookie_string = data.get("cookies") or os.getenv("REGTECH_COOKIES", "")

        if not cookie_string:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "쿠키가 설정되지 않았습니다. /api/collection/cookie/regtech/set 를 먼저 호출하세요",
                    }
                ),
                400,
            )

        # 수집 서비스 가져오기
        from ..services.unified_service_factory import get_unified_service

        service = get_unified_service()

        # REGTECH 컴포넌트 확인
        if "regtech" not in service._components:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "REGTECH 컴포넌트를 사용할 수 없습니다",
                    }
                ),
                500,
            )

        # 쿠키 설정 (요청에 쿠키가 포함된 경우)
        if data.get("cookies"):
            service._components["regtech"].set_cookie_string(data["cookies"])

        # 수집 실행
        import asyncio

        async def run_collection():
            collector = service._components["regtech"]
            return await collector._collect_data()

        # 비동기 수집 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        collected_data = loop.run_until_complete(run_collection())
        loop.close()

        if collected_data:
            # 데이터베이스 저장
            save_count = 0
            try:
                from ..managers.blacklist_manager import UnifiedBlacklistManager

                blacklist_manager = UnifiedBlacklistManager()

                for ip_data in collected_data:
                    try:
                        blacklist_manager.add_ip(
                            ip=ip_data.get("ip"),
                            source=ip_data.get("source", "REGTECH"),
                            threat_level=ip_data.get("threat_level", "medium"),
                            description=ip_data.get(
                                "description", "Cookie-based collection"
                            ),
                            detection_date=ip_data.get("detection_date"),
                        )
                        save_count += 1
                    except Exception as e:
                        logger.warning(f"IP 저장 실패 ({ip_data.get('ip')}): {e}")

            except Exception as e:
                logger.warning(f"데이터베이스 저장 실패: {e}")

            # 로그 추가
            service.add_collection_log(
                source="regtech",
                action="cookie_collection",
                details={
                    "collected_count": len(collected_data),
                    "saved_count": save_count,
                    "method": "cookie_based",
                },
            )

            return jsonify(
                {
                    "success": True,
                    "message": f"쿠키 기반 수집 완료",
                    "collected_count": len(collected_data),
                    "saved_count": save_count,
                    "sample_ips": [ip_data.get("ip") for ip_data in collected_data[:5]],
                    "timestamp": datetime.now().isoformat(),
                }
            )
        else:
            return jsonify(
                {
                    "success": False,
                    "message": "수집된 데이터가 없습니다. 쿠키가 만료되었거나 접근 권한이 없을 수 있습니다",
                    "collected_count": 0,
                }
            )

    except Exception as e:
        logger.error(f"쿠키 기반 수집 실패: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@cookie_collection_bp.route("/regtech/status", methods=["GET"])
def get_cookie_status():
    """쿠키 설정 상태 확인"""
    try:
        cookie_string = os.getenv("REGTECH_COOKIES", "")

        status = {
            "cookies_set": bool(cookie_string),
            "cookie_count": len(cookie_string.split(";")) if cookie_string else 0,
            "component_available": False,
            "cookie_mode": False,
        }

        # 수집 서비스 상태 확인
        try:
            from ..services.unified_service_factory import get_unified_service

            service = get_unified_service()

            if "regtech" in service._components:
                status["component_available"] = True
                collector = service._components["regtech"]
                status["cookie_mode"] = getattr(collector, "cookie_auth_mode", False)
                status["session_cookies"] = len(
                    getattr(collector, "session_cookies", {})
                )

        except Exception as e:
            logger.warning(f"서비스 상태 확인 실패: {e}")

        return jsonify(
            {"success": True, "status": status, "timestamp": datetime.now().isoformat()}
        )

    except Exception as e:
        logger.error(f"상태 확인 실패: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@cookie_collection_bp.route("/guide", methods=["GET"])
def get_cookie_guide():
    """쿠키 설정 가이드"""
    guide = {
        "title": "REGTECH 쿠키 기반 수집 가이드",
        "steps": [
            {
                "step": 1,
                "title": "브라우저에서 REGTECH 로그인",
                "description": "https://regtech.fsec.or.kr/login/loginForm 에서 로그인",
                "credentials": {"username": "nextrade", "password": "Sprtmxm1@3"},
            },
            {
                "step": 2,
                "title": "개발자 도구에서 쿠키 복사",
                "description": "F12 → Application → Cookies → regtech.fsec.or.kr",
                "important_cookies": ["JSESSIONID", "regtech-front"],
            },
            {
                "step": 3,
                "title": "쿠키 설정 API 호출",
                "method": "POST",
                "url": "/api/collection/cookie/regtech/set",
                "body": {
                    "cookies": "JSESSIONID=your_session_id; regtech-front=your_front_id"
                },
            },
            {
                "step": 4,
                "title": "수집 실행",
                "method": "POST",
                "url": "/api/collection/cookie/regtech/collect",
                "description": "쿠키 기반 자동 수집 실행",
            },
        ],
        "api_endpoints": {
            "set_cookies": "/api/collection/cookie/regtech/set",
            "collect": "/api/collection/cookie/regtech/collect",
            "status": "/api/collection/cookie/regtech/status",
            "guide": "/api/collection/cookie/guide",
        },
    }

    return jsonify(guide)
