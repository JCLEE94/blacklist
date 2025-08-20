#!/usr/bin/env python3
"""
설정 UI 렌더링 라우트
설정 페이지 렌더링 및 관리 대시보드
"""
import logging
from datetime import datetime

from flask import Blueprint
from flask import render_template

from ..container import get_container

logger = logging.getLogger(__name__)

ui_settings_bp = Blueprint("ui_settings", __name__)


@ui_settings_bp.route("/settings")
def settings_page():
    """설정 페이지 렌더링"""
    logger.info("🔴 설정 페이지 호출됨!")
    container = get_container()

    # 데이터베이스에서 설정 가져오기 - 강제 로드 (fallback 없음)
    from src.models.settings import get_settings_manager

    settings_manager = get_settings_manager()

    # 현재 설정 값 가져오기 (기본값 없이)
    settings_dict = {
        "regtech_username": settings_manager.get_setting("regtech_username", ""),
        "regtech_password": settings_manager.get_setting("regtech_password", ""),
        "secudium_username": settings_manager.get_setting("secudium_username", ""),
        "secudium_password": settings_manager.get_setting("secudium_password", ""),
        "data_retention_days": settings_manager.get_setting("data_retention_days", 90),
        "max_ips_per_source": settings_manager.get_setting("max_ips_per_source", 50000),
    }
    logger.info(f"설정 로드됨: regtech_username={settings_dict['regtech_username']}")

    # 수집 상태 가져오기 - 기본값 False로 변경
    collection_enabled = False
    try:
        # Collection Manager에서 직접 상태 확인
        collection_manager = container.resolve("collection_manager")
        if collection_manager:
            status = collection_manager.get_status()
            collection_enabled = status.get("collection_enabled", False)
            logger.info(
                "수집 상태: {collection_enabled}, sources: {status.get('sources', {})}"
            )
    except Exception as e:
        logger.warning(f"Collection Manager에서 수집 상태 확인 실패: {e}")
        # Unified Service로 폴백
        try:
            unified_service = container.resolve("unified_service")
            if unified_service:
                collection_enabled = unified_service.collection_enabled
        except Exception as e2:
            logger.warning(f"Unified Service에서 수집 상태 확인 실패: {e2}")

    # 업데이트 주기 설정 추가
    settings_dict["update_interval"] = (
        settings_manager.get_setting("update_interval", 10800000)
        if "settings_manager" in locals()
        else 10800000
    )

    context = {
        "title": "Blacklist Manager",
        "settings": settings_dict,
        "collection_enabled": collection_enabled,
        "server_uptime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "db_size": "계산 중...",
        "cache_status": "활성",
        "active_ips": "계산 중...",
    }

    logger.info(f"🔴 Context 전달됨: settings={settings_dict}")
    logger.info("🔴 템플릿 렌더링 시작")

    return render_template("settings.html", **context)


@ui_settings_bp.route("/settings/management")
def settings_management():
    """새로운 설정 관리 대시보드"""
    return render_template("settings/dashboard.html")


@ui_settings_bp.route("/settings/regtech", methods=["GET", "POST"])
def handle_regtech_settings():
    """REGTECH 설정 조회 및 저장 API"""
    from flask import jsonify
    from flask import request

    if request.method == "GET":
        # 설정 조회
        try:
            from src.models.settings import get_settings_manager

            settings_manager = get_settings_manager()

            # REGTECH 설정 가져오기
            regtech_settings = {
                "username": settings_manager.get_setting("regtech_username", ""),
                "has_password": bool(
                    settings_manager.get_setting("regtech_password", "")
                ),
                "status": (
                    "configured"
                    if settings_manager.get_setting("regtech_username", "")
                    else "not_configured"
                ),
            }

            return jsonify(regtech_settings)

        except Exception as e:
            logger.error(f"REGTECH 설정 조회 오류: {e}")
            return jsonify({"error": str(e)}), 500

    elif request.method == "POST":
        # 설정 저장
        try:
            data = request.get_json() if request.is_json else request.form.to_dict()

            if not data:
                return jsonify({"error": "데이터가 제공되지 않았습니다"}), 400

            username = data.get("username")
            password = data.get("password")

            if not username or not password:
                return jsonify({"error": "사용자명과 비밀번호가 필요합니다"}), 400

            from src.models.settings import get_settings_manager

            settings_manager = get_settings_manager()

            # 설정 저장
            settings_manager.set_setting(
                "regtech_username", username, "string", "credentials"
            )
            settings_manager.set_setting(
                "regtech_password", password, "password", "credentials"
            )

            logger.info(f"REGTECH 설정 저장 완료: username={username}")

            # 환경변수 업데이트
            import os

            os.environ["REGTECH_USERNAME"] = username
            os.environ["REGTECH_PASSWORD"] = password

            return jsonify(
                {
                    "success": True,
                    "message": "REGTECH 설정이 저장되었습니다",
                    "username": username,
                }
            )

        except Exception as e:
            logger.error(f"REGTECH 설정 저장 오류: {e}")
            return jsonify({"error": str(e)}), 500
