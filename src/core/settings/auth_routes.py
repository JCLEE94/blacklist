#!/usr/bin/env python3
"""
인증 관련 설정 API 엔드포인트
REGTECH 및 SECUDIUM 인증 정보 관리
"""
import logging

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

import json
import os
from datetime import datetime
from pathlib import Path

import jwt

from src.config.settings import settings

from ..container import get_container

auth_settings_bp = Blueprint("auth_settings", __name__)


@auth_settings_bp.route("/api/auth-config", methods=["GET"])
def get_auth_config():
    """인증 설정 정보 조회"""
    try:
        from src.models.settings import get_settings_manager

        settings_manager = get_settings_manager()

        # 현재 저장된 인증 정보 조회 (비밀번호는 마스킹)
        regtech_username = settings_manager.get_setting("regtech_username", "")
        secudium_username = settings_manager.get_setting("secudium_username", "")

        # 인증 상태 확인
        regtech_configured = bool(
            regtech_username and settings_manager.get_setting("regtech_password")
        )
        secudium_configured = bool(
            secudium_username and settings_manager.get_setting("secudium_password")
        )

        return jsonify(
            {
                "success": True,
                "data": {
                    "regtech": {
                        "username": regtech_username,
                        "password": "********" if regtech_configured else "",
                        "configured": regtech_configured,
                    },
                    "secudium": {
                        "username": secudium_username,
                        "password": "********" if secudium_configured else "",
                        "configured": secudium_configured,
                    },
                },
            }
        )
    except Exception as e:
        logger.error(f"인증 설정 조회 오류: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "data": {
                        "regtech": {
                            "username": "",
                            "password": "",
                            "configured": False,
                        },
                        "secudium": {
                            "username": "",
                            "password": "",
                            "configured": False,
                        },
                    },
                }
            ),
            500,
        )


@auth_settings_bp.route("/api/auth-config", methods=["POST"])
def save_auth_config():
    """인증 설정 정보 저장"""
    try:
        data = request.get_json() or {}

        # 요청 데이터 검증
        if not data:
            return (
                jsonify({"success": False, "error": "데이터가 제공되지 않았습니다."}),
                400,
            )

        results = {"regtech": None, "secudium": None}

        # REGTECH 인증 정보 처리
        if "regtech" in data:
            regtech_data = data["regtech"]
            if regtech_data.get("username") and regtech_data.get("password"):
                try:
                    from src.models.settings import get_settings_manager

                    settings_manager = get_settings_manager()

                    # 마스킹된 비밀번호가 아닌 경우만 저장
                    if regtech_data["password"] != "********":
                        settings_manager.set_setting(
                            "regtech_username",
                            regtech_data["username"],
                            "string",
                            "credentials",
                        )
                        settings_manager.set_setting(
                            "regtech_password",
                            regtech_data["password"],
                            "password",
                            "credentials",
                        )
                    else:
                        # 사용자명만 업데이트
                        settings_manager.set_setting(
                            "regtech_username",
                            regtech_data["username"],
                            "string",
                            "credentials",
                        )

                    results["regtech"] = {
                        "success": True,
                        "message": "REGTECH 인증 정보 저장됨",
                    }
                    logger.info("REGTECH 인증 정보 저장 성공")

                except Exception as e:
                    results["regtech"] = {"success": False, "error": str(e)}
                    logger.error(f"REGTECH 인증 정보 저장 실패: {e}")

        # SECUDIUM 인증 정보 처리
        if "secudium" in data:
            secudium_data = data["secudium"]
            if secudium_data.get("username") and secudium_data.get("password"):
                try:
                    from src.models.settings import get_settings_manager

                    settings_manager = get_settings_manager()

                    # 마스킹된 비밀번호가 아닌 경우만 저장
                    if secudium_data["password"] != "********":
                        settings_manager.set_setting(
                            "secudium_username",
                            secudium_data["username"],
                            "string",
                            "credentials",
                        )
                        settings_manager.set_setting(
                            "secudium_password",
                            secudium_data["password"],
                            "password",
                            "credentials",
                        )
                    else:
                        # 사용자명만 업데이트
                        settings_manager.set_setting(
                            "secudium_username",
                            secudium_data["username"],
                            "string",
                            "credentials",
                        )

                    results["secudium"] = {
                        "success": True,
                        "message": "SECUDIUM 인증 정보 저장됨",
                    }
                    logger.info("SECUDIUM 인증 정보 저장 성공")

                except Exception as e:
                    results["secudium"] = {"success": False, "error": str(e)}
                    logger.error(f"SECUDIUM 인증 정보 저장 실패: {e}")

        # 캐시 클리어
        try:
            container = get_container()
            cache_manager = container.resolve("cache_manager")
            if cache_manager:
                cache_manager.clear()
                logger.info("인증 설정 변경 후 캐시 클리어됨")
        except Exception as e:
            logger.warning(f"캐시 클리어 실패: {e}")

        # 전체 성공 여부 판단
        overall_success = any(
            result and result.get("success")
            for result in results.values()
            if result is not None
        )

        return jsonify(
            {
                "success": overall_success,
                "message": (
                    "인증 설정이 저장되었습니다."
                    if overall_success
                    else "인증 설정 저장에 실패했습니다."
                ),
                "results": results,
            }
        )

    except Exception as e:
        logger.error(f"인증 설정 저장 오류: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@auth_settings_bp.route("/api/settings/regtech/auth", methods=["POST"])
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
        from ..regtech_auto_login import get_regtech_auth

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


@auth_settings_bp.route("/api/settings/regtech/refresh-token", methods=["POST"])
def refresh_regtech_token():
    """REGTECH Bearer Token 갱신"""
    try:
        from ..regtech_auto_login import get_regtech_auth

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


@auth_settings_bp.route("/api/settings/regtech/token-status")
def regtech_token_status():
    """현재 REGTECH 토큰 상태 확인"""
    try:
        from ..regtech_auto_login import get_regtech_auth

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


@auth_settings_bp.route("/api/collection/regtech/test", methods=["POST"])
def test_regtech_collection():
    """REGTECH 수집 테스트"""
    try:
        import re

        import requests

        from ..regtech_auto_login import get_regtech_auth

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
            match = re.search(r"총\s*<em[^>]*>([0-9,]+)</em>", resp.text)
            ip_count = match.group(1) if match else "알 수 없음"

            return jsonify(
                {
                    "success": True,
                    "ip_count": ip_count,
                    "message": "REGTECH 접근 성공. 총 {ip_count}개 IP 확인",
                }
            )
        else:
            return jsonify({"success": False, "error": "데이터 접근 실패"})

    except Exception as e:
        logger.error(f"수집 테스트 오류: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@auth_settings_bp.route("/api/settings/secudium/auth", methods=["POST"])
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
