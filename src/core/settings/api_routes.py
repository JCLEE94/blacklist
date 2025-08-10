#!/usr/bin/env python3
"""
DB 기반 설정 관리 API 엔드포인트
대량 설정 업데이트, 개별 설정 관리, 설정 리셋 기능
"""
import logging

from flask import Blueprint
from flask import jsonify
from flask import request

logger = logging.getLogger(__name__)

api_settings_bp = Blueprint("api_settings", __name__)


@api_settings_bp.route("/api/settings/all", methods=["GET"])
def get_all_settings_api():
    """모든 설정 조회 (카테고리별 그룹화)"""
    # try 블록 제거하고 직접 반환
    settings = {
        "general": {
            "app_name": "Blacklist Management System",
            "timezone": "Asia/Seoul",
            "items_per_page": 50,
        },
        "collection": {
            "collection_enabled": True,
            "collection_interval_hours": 6,
            "regtech_enabled": True,
            "secudium_enabled": True,
        },
        "credentials": {
            "regtech_username": "nextrade",
            "regtech_password": "***",
            "secudium_username": "nextrade",
            "secudium_password": "***",
        },
        "security": {"session_timeout_minutes": 60, "api_rate_limit": 1000},
        "notification": {
            "email_notifications": False,
            "admin_email": "admin@example.com",
        },
        "performance": {"cache_ttl_seconds": 300, "max_concurrent_collections": 2},
    }

    # 카테고리 메타데이터 추가
    categories_info = {
        "general": {
            "name": "일반 설정",
            "description": "애플리케이션의 기본 설정",
            "icon": "bi-gear",
        },
        "collection": {
            "name": "수집 설정",
            "description": "REGTECH/SECUDIUM 데이터 수집 관련 설정",
            "icon": "bi-download",
        },
        "security": {
            "name": "보안 설정",
            "description": "보안 및 접근 제어 설정",
            "icon": "bi-shield-lock",
        },
        "notification": {
            "name": "알림 설정",
            "description": "이메일 및 알림 관련 설정",
            "icon": "bi-bell",
        },
        "performance": {
            "name": "성능 설정",
            "description": "캐시 및 성능 최적화 설정",
            "icon": "bi-speedometer2",
        },
        "integration": {
            "name": "연동 설정",
            "description": "외부 시스템 연동 설정",
            "icon": "bi-link-45deg",
        },
        "credentials": {
            "name": "인증 정보",
            "description": "REGTECH/SECUDIUM 로그인 인증 정보",
            "icon": "bi-key",
        },
    }

    return jsonify(
        {"success": True, "data": {"settings": settings, "categories": categories_info}}
    )


@api_settings_bp.route("/api/settings/bulk", methods=["POST"])
def update_settings_bulk():
    """설정값 일괄 업데이트"""
    try:
        from src.models.settings import get_settings_manager

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        settings_manager = get_settings_manager()
        updated_count = 0

        for key, setting_data in data.items():
            try:
                # 설정 데이터 구조 검증
                if isinstance(setting_data, dict) and "value" in setting_data:
                    value = setting_data["value"]
                    setting_type = setting_data.get("type", "string")
                    category = setting_data.get("category", "general")
                else:
                    # 단순 값인 경우
                    value = setting_data
                    setting_type = "string"
                    category = "general"

                settings_manager.set_setting(key, value, setting_type, category)
                updated_count += 1

            except Exception as e:
                logger.warning(f"Failed to update setting {key}: {e}")

        return jsonify(
            {
                "success": True,
                "message": f"{updated_count} settings updated successfully",
            }
        )
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_settings_bp.route("/api/settings/<key>", methods=["PUT"])
def update_individual_setting(key: str):
    """개별 설정값 업데이트"""
    try:
        from src.models.settings import get_settings_manager

        data = request.get_json()
        if not data or "value" not in data:
            return jsonify({"success": False, "error": "No value provided"}), 400

        value = data["value"]
        setting_type = data.get("type", "string")
        category = data.get("category", "general")

        settings_manager = get_settings_manager()
        settings_manager.set_setting(key, value, setting_type, category)

        return jsonify(
            {"success": True, "message": f"Setting {key} updated successfully"}
        )
    except Exception as e:
        logger.error(f"Failed to update setting {key}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_settings_bp.route("/api/settings", methods=["POST"])
def save_settings():
    """설정 저장 API"""
    try:
        from src.models.settings import get_settings_manager

        from ..container import get_container

        settings_manager = get_settings_manager()

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400

        # 각 설정값 저장
        for key, value in data.items():
            if value is not None and value != "":
                try:
                    # 패스워드 필드는 특별 처리
                    if "password" in key:
                        # 마스킹된 값이면 무시
                        if value == "********":
                            continue
                        setting_type = "password"
                        category = "credentials"
                    elif key in [
                        "data_retention_days",
                        "max_ips_per_source",
                        "update_interval",
                    ]:
                        setting_type = "integer"
                        category = "general"
                        value = int(value)
                    else:
                        setting_type = "string"
                        category = "credentials" if "username" in key else "general"

                    settings_manager.set_setting(key, value, setting_type, category)
                    logger.info(
                        f"설정 저장됨: {key} = {'***' if 'password' in key else value}"
                    )

                except Exception as e:
                    logger.warning(f"설정 저장 실패 {key}: {e}")

        # 캐시 클리어 - 설정 변경 후 즉시 반영되도록
        try:
            container = get_container()
            cache_manager = container.resolve("cache_manager")
            if cache_manager:
                cache_manager.clear()
                logger.info("설정 변경 후 캐시가 클리어되었습니다")
        except Exception as cache_error:
            logger.warning(f"캐시 클리어 실패: {cache_error}")

        return jsonify(
            {"success": True, "message": "설정이 성공적으로 저장되었습니다."}
        )

    except Exception as e:
        logger.error(f"설정 저장 오류: {e}")
        return jsonify({"success": False, "message": f"설정 저장 실패: {str(e)}"}), 500


@api_settings_bp.route("/api/settings/reset", methods=["POST"])
def reset_all_settings():
    """모든 설정을 기본값으로 리셋"""
    try:
        from src.models.settings import get_settings_manager

        confirm = (
            request.get_json().get("confirm", False)
            if request.is_json
            else request.form.get("confirm", "false").lower() == "true"
        )

        if not confirm:
            return (
                jsonify({"success": False, "error": "Reset confirmation required"}),
                400,
            )

        settings_manager = get_settings_manager()
        settings_manager.reset_to_defaults()

        return jsonify(
            {"success": True, "message": "All settings reset to defaults successfully"}
        )
    except Exception as e:
        logger.error(f"Failed to reset settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
