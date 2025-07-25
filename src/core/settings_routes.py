#!/usr/bin/env python3
"""
설정 관리 API 엔드포인트
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import jwt
from flask import Blueprint, jsonify, render_template, request

from src.config.settings import settings

from .container import get_container

logger = logging.getLogger(__name__)

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings")
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
                f"수집 상태: {collection_enabled}, sources: {status.get('sources', {})}"
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
    logger.info(f"🔴 템플릿 렌더링 시작")

    return render_template("settings.html", **context)


@settings_bp.route("/api/settings/regtech/auth", methods=["POST"])
def update_regtech_auth():
    """REGTECH 인증 정보 업데이트"""
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return (
                jsonify(
                    {"success": False, "error": "사용자명과 비밀번호가 필요합니다."}
                ),
                400,
            )

        # 자동 로그인 모듈 가져오기
        from .regtech_auto_login import get_regtech_auth

        auth = get_regtech_auth()

        # 인증 정보 업데이트 및 테스트
        if auth.update_credentials(username, password):
            # DB에 인증정보 저장
            try:
                from src.models.settings import get_settings_manager

                settings_manager = get_settings_manager()
                settings_manager.set_setting(
                    "regtech_username", username, "string", "credentials"
                )
                settings_manager.set_setting(
                    "regtech_password", password, "password", "credentials"
                )
                logger.info("REGTECH 인증정보가 DB에 저장되었습니다.")
            except Exception as db_error:
                logger.warning(f"DB 저장 실패: {db_error}")

            # 토큰 정보 가져오기
            token = auth._current_token

            # JWT 디코드
            jwt_token = token.replace("Bearer", "").strip()
            payload = jwt.decode(jwt_token, options={"verify_signature": False})

            # 캐시 클리어
            try:
                container = get_container()
                cache_manager = container.resolve("cache_manager")
                if cache_manager:
                    cache_manager.clear()
                    logger.info("REGTECH 인증 후 캐시가 클리어되었습니다")
            except Exception as e:
                logger.warning(f"캐시 클리어 실패: {e}")

            return jsonify(
                {
                    "success": True,
                    "token": token,
                    "expires_at": payload.get("exp", 0),
                    "username": payload.get("username", username),
                    "message": "REGTECH 인증 성공 및 DB 저장 완료",
                }
            )
        else:
            return jsonify(
                {
                    "success": False,
                    "error": "인증 실패. 사용자명과 비밀번호를 확인하세요.",
                }
            )

    except Exception as e:
        logger.error(f"REGTECH 인증 업데이트 오류: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@settings_bp.route("/api/settings/regtech/refresh-token", methods=["POST"])
def refresh_regtech_token():
    """REGTECH Bearer Token 갱신"""
    try:
        from .regtech_auto_login import get_regtech_auth

        auth = get_regtech_auth()

        # 강제로 새 토큰 발급
        auth._current_token = None  # 현재 토큰 무효화
        token = auth.get_valid_token()

        if token:
            # JWT 디코드
            jwt_token = token.replace("Bearer", "").strip()
            payload = jwt.decode(jwt_token, options={"verify_signature": False})

            return jsonify(
                {
                    "success": True,
                    "token": token,
                    "expires_at": payload.get("exp", 0),
                    "username": payload.get("username", "unknown"),
                    "message": "Bearer Token이 갱신되었습니다.",
                }
            )
        else:
            return jsonify(
                {"success": False, "error": "토큰 갱신 실패. 인증 정보를 확인하세요."}
            )

    except Exception as e:
        logger.error(f"토큰 갱신 오류: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@settings_bp.route("/api/settings/regtech/token-status")
def regtech_token_status():
    """현재 REGTECH 토큰 상태 확인"""
    try:
        from .regtech_auto_login import get_regtech_auth

        auth = get_regtech_auth()

        # 파일에서 토큰 로드
        token = auth._load_token_from_file()

        if token:
            is_valid = auth._is_token_valid(token)

            # JWT 디코드
            jwt_token = token.replace("Bearer", "").strip()
            payload = jwt.decode(jwt_token, options={"verify_signature": False})

            return jsonify(
                {
                    "has_token": True,
                    "is_valid": is_valid,
                    "token": token if is_valid else None,
                    "expires_at": payload.get("exp", 0),
                    "username": payload.get("username", "unknown"),
                }
            )
        else:
            return jsonify({"has_token": False, "is_valid": False})

    except Exception as e:
        logger.error(f"토큰 상태 확인 오류: {e}")
        return jsonify({"has_token": False, "is_valid": False, "error": str(e)})


@settings_bp.route("/api/collection/regtech/test", methods=["POST"])
def test_regtech_collection():
    """REGTECH 수집 테스트"""
    try:
        from datetime import datetime, timedelta

        import requests

        from .regtech_auto_login import get_regtech_auth

        auth = get_regtech_auth()
        token = auth.get_valid_token()

        if not token:
            return jsonify({"success": False, "error": "유효한 토큰이 없습니다."})

        # 간단한 수집 테스트
        session = requests.Session()
        session.cookies.set("regtech-va", token, domain="regtech.fsec.or.kr", path="/")
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )

        # Advisory 페이지 접근 테스트
        resp = session.get(
            "https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList", timeout=30
        )

        if resp.status_code == 200 and "login" not in resp.url:
            # 페이지에서 총 건수 추출
            import re

            match = re.search(r"총\s*<em[^>]*>([0-9,]+)</em>", resp.text)
            ip_count = match.group(1) if match else "알 수 없음"

            return jsonify(
                {
                    "success": True,
                    "ip_count": ip_count,
                    "message": f"REGTECH 접근 성공. 총 {ip_count}개 IP 확인",
                }
            )
        else:
            return jsonify({"success": False, "error": "데이터 접근 실패"})

    except Exception as e:
        logger.error(f"수집 테스트 오류: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@settings_bp.route("/api/settings/secudium/auth", methods=["POST"])
def update_secudium_auth():
    """SECUDIUM 인증 정보 업데이트"""
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return (
                jsonify(
                    {"success": False, "error": "사용자명과 비밀번호가 필요합니다."}
                ),
                400,
            )

        # 설정 업데이트 (메모리)
        settings.secudium_username = username
        settings.secudium_password = password

        # DB에 인증정보 저장
        try:
            from src.models.settings import get_settings_manager

            settings_manager = get_settings_manager()
            settings_manager.set_setting(
                "secudium_username", username, "string", "credentials"
            )
            settings_manager.set_setting(
                "secudium_password", password, "password", "credentials"
            )
            logger.info("SECUDIUM 인증정보가 DB에 저장되었습니다.")
        except Exception as db_error:
            logger.warning(f"DB 저장 실패: {db_error}")

        # 설정 파일에도 저장 (백업용)
        try:
            config_file = Path(settings.data_dir) / ".secudium_credentials.json"
            config_file.parent.mkdir(parents=True, exist_ok=True)

            config_data = {
                "username": username,
                "password": password,
                "updated_at": datetime.now().isoformat(),
            }

            with open(config_file, "w") as f:
                json.dump(config_data, f, indent=2)

            os.chmod(config_file, 0o600)
            logger.info("SECUDIUM 인증정보가 파일에도 저장되었습니다.")
        except Exception as file_error:
            logger.warning(f"파일 저장 실패: {file_error}")

        # 캐시 클리어
        try:
            container = get_container()
            cache_manager = container.resolve("cache_manager")
            if cache_manager:
                cache_manager.clear()
                logger.info("SECUDIUM 인증 정보 업데이트 후 캐시가 클리어되었습니다")
        except Exception as e:
            logger.warning(f"캐시 클리어 실패: {e}")

        return jsonify(
            {
                "success": True,
                "message": "SECUDIUM 인증 정보가 DB 및 파일에 저장되었습니다.",
            }
        )

    except Exception as e:
        logger.error(f"SECUDIUM 인증 업데이트 오류: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ========== 새로운 DB 기반 설정 API ==========


@settings_bp.route("/settings/management")
def settings_management():
    """새로운 설정 관리 대시보드"""
    return render_template("settings/dashboard.html")


@settings_bp.route("/api/settings/all", methods=["GET"])
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


@settings_bp.route("/api/settings/bulk", methods=["POST"])
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


@settings_bp.route("/api/settings/<key>", methods=["PUT"])
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


@settings_bp.route("/api/settings", methods=["POST"])
def save_settings():
    """설정 저장 API"""
    try:
        from src.models.settings import get_settings_manager

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


@settings_bp.route("/api/settings/reset", methods=["POST"])
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
