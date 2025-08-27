# !/usr/bin/env python3
"""
인증 관련 라우트 (JWT 토큰 갱신 포함)
"""

import logging
import os
from datetime import datetime

from flask import (
    Blueprint,
    Flask,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from ..utils.security import input_validation, rate_limit

logger = logging.getLogger(__name__)

# 블루프린트 생성
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/login", methods=["POST"])
@rate_limit(limit=5, window_seconds=300)  # 5분에 5번 제한
@input_validation(
    {
        "username": {"required": True, "type": str, "min_length": 1},
        "password": {"required": True, "type": str, "min_length": 1},
    }
)
def login():
    """사용자 로그인 및 JWT 토큰 발급"""
    try:
        data = request.get_json()
        username = data["username"]
        password = data["password"]

        # 실제 구현에서는 데이터베이스에서 사용자 인증
        # 여기서는 환경 변수 기반 간단 인증
        # os imported at module level
        valid_users = {
            os.getenv("ADMIN_USERNAME", "admin"): os.getenv("ADMIN_PASSWORD", "admin"),
            os.getenv("REGTECH_USERNAME", ""): os.getenv("REGTECH_PASSWORD", ""),
            os.getenv("SECUDIUM_USERNAME", ""): os.getenv("SECUDIUM_PASSWORD", ""),
        }

        # 빈 값 제거
        valid_users = {k: v for k, v in valid_users.items() if k and v}

        if username not in valid_users or valid_users[username] != password:
            logger.warning(f"로그인 실패: {username}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "사용자명 또는 비밀번호가 올바르지 않습니다",
                    }
                ),
                401,
            )

        # 사용자 역할 결정
        roles = ["user"]
        if username == os.getenv("ADMIN_USERNAME", "admin"):
            roles = ["admin", "user"]
        elif username in [
            os.getenv("REGTECH_USERNAME"),
            os.getenv("SECUDIUM_USERNAME"),
        ]:
            roles = ["collector", "user"]

        # JWT 토큰 생성
        security_manager = getattr(current_app, "security_manager", None)
        if not security_manager:
            return (
                jsonify(
                    {"success": False, "error": "보안 시스템이 초기화되지 않았습니다"}
                ),
                500,
            )

        # Access Token (짧은 만료시간)
        access_token = security_manager.generate_jwt_token(
            user_id=username, roles=roles, expires_hours=1  # 1시간
        )

        # Refresh Token (긴 만료시간)
        refresh_token = security_manager.generate_jwt_token(
            user_id=username,
            roles=["refresh"],
            expires_hours=24 * 7,  # 갱신 전용 토큰  # 7일
        )

        logger.info(f"로그인 성공: {username}")

        return jsonify(
            {
                "success": True,
                "message": "로그인 성공",
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {"username": username, "roles": roles},
                "expires_in": 3600,  # 1시간 (초)
            }
        )

    except Exception as e:
        logger.error(f"로그인 처리 실패: {e}")
        return (
            jsonify({"success": False, "error": "로그인 처리 중 오류가 발생했습니다"}),
            500,
        )


@auth_bp.route("/refresh", methods=["POST"])
@rate_limit(limit=10, window_seconds=300)  # 5분에 10번 제한
@input_validation({"refresh_token": {"required": True, "type": str, "min_length": 10}})
def refresh_token():
    """JWT 토큰 갱신"""
    try:
        data = request.get_json()
        refresh_token = data["refresh_token"]

        security_manager = getattr(current_app, "security_manager", None)
        if not security_manager:
            return (
                jsonify(
                    {"success": False, "error": "보안 시스템이 초기화되지 않았습니다"}
                ),
                500,
            )

        # Refresh Token 검증
        payload = security_manager.verify_jwt_token(refresh_token)
        if not payload:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "유효하지 않거나 만료된 리프레시 토큰입니다",
                    }
                ),
                401,
            )

        # 리프레시 토큰인지 확인
        if "refresh" not in payload.get("roles", []):
            return (
                jsonify(
                    {"success": False, "error": "유효하지 않은 리프레시 토큰입니다"}
                ),
                401,
            )

        username = payload.get("user_id")
        if not username:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "토큰에서 사용자 정보를 찾을 수 없습니다",
                    }
                ),
                401,
            )

        # 사용자 역할 다시 가져오기 (실제로는 DB에서 조회)
        # os imported at module level
        roles = ["user"]
        if username == os.getenv("ADMIN_USERNAME", "admin"):
            roles = ["admin", "user"]
        elif username in [
            os.getenv("REGTECH_USERNAME"),
            os.getenv("SECUDIUM_USERNAME"),
        ]:
            roles = ["collector", "user"]

        # 새 Access Token 생성
        new_access_token = security_manager.generate_jwt_token(
            user_id=username, roles=roles, expires_hours=1  # 1시간
        )

        # 새 Refresh Token 생성 (선택적)
        new_refresh_token = security_manager.generate_jwt_token(
            user_id=username, roles=["refresh"], expires_hours=24 * 7  # 7일
        )

        logger.info(f"토큰 갱신 성공: {username}")

        return jsonify(
            {
                "success": True,
                "message": "토큰이 성공적으로 갱신되었습니다",
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "expires_in": 3600,  # 1시간 (초)
            }
        )

    except Exception as e:
        logger.error(f"토큰 갱신 실패: {e}")
        return (
            jsonify({"success": False, "error": "토큰 갱신 중 오류가 발생했습니다"}),
            500,
        )


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """로그아웃 (토큰 무효화)"""
    try:
        # 실제 구현에서는 토큰을 블랙리스트에 추가
        # 현재는 클라이언트에서 토큰을 삭제하도록 안내

        logger.info("로그아웃 요청")

        return jsonify(
            {
                "success": True,
                "message": "성공적으로 로그아웃되었습니다. 클라이언트에서 토큰을 삭제하세요.",
            }
        )

    except Exception as e:
        logger.error(f"로그아웃 처리 실패: {e}")
        return (
            jsonify(
                {"success": False, "error": "로그아웃 처리 중 오류가 발생했습니다"}
            ),
            500,
        )


@auth_bp.route("/verify", methods=["POST"])
@input_validation({"token": {"required": True, "type": str, "min_length": 10}})
def verify_token():
    """JWT 토큰 검증"""
    try:
        data = request.get_json()
        token = data["token"]

        security_manager = getattr(current_app, "security_manager", None)
        if not security_manager:
            return (
                jsonify(
                    {"success": False, "error": "보안 시스템이 초기화되지 않았습니다"}
                ),
                500,
            )

        # 토큰 검증
        payload = security_manager.verify_jwt_token(token)

        if payload:
            return jsonify(
                {
                    "success": True,
                    "valid": True,
                    "payload": {
                        "user_id": payload.get("user_id"),
                        "roles": payload.get("roles"),
                        "exp": payload.get("exp"),
                        "iat": payload.get("iat"),
                    },
                }
            )
        else:
            return jsonify(
                {
                    "success": True,
                    "valid": False,
                    "message": "토큰이 유효하지 않거나 만료되었습니다",
                }
            )

    except Exception as e:
        logger.error(f"토큰 검증 실패: {e}")
        return (
            jsonify({"success": False, "error": "토큰 검증 중 오류가 발생했습니다"}),
            500,
        )


@auth_bp.route("/change-password", methods=["POST"])
@input_validation(
    {
        "current_password": {"required": True, "type": str},
        "new_password": {"required": True, "type": str, "min_length": 8},
    }
)
def change_password():
    """비밀번호 변경"""
    try:
        # 현재는 환경 변수 기반이므로 구현하지 않음
        # 실제 데이터베이스 구현 시 활성화

        return (
            jsonify(
                {
                    "success": False,
                    "error": "현재 환경에서는 비밀번호 변경이 지원되지 않습니다",
                }
            ),
            501,
        )

    except Exception as e:
        logger.error(f"비밀번호 변경 실패: {e}")
        return (
            jsonify(
                {"success": False, "error": "비밀번호 변경 중 오류가 발생했습니다"}
            ),
            500,
        )


@auth_bp.route("/profile", methods=["GET"])
def get_profile():
    """현재 사용자 프로필 조회"""
    try:
        # Authorization 헤더에서 토큰 추출
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "error": "인증 토큰이 필요합니다"}), 401

        token = auth_header.split(" ")[1]

        security_manager = getattr(current_app, "security_manager", None)
        if not security_manager:
            return (
                jsonify(
                    {"success": False, "error": "보안 시스템이 초기화되지 않았습니다"}
                ),
                500,
            )

        # 토큰 검증
        payload = security_manager.verify_jwt_token(token)
        if not payload:
            return jsonify({"success": False, "error": "유효하지 않은 토큰입니다"}), 401

        return jsonify(
            {
                "success": True,
                "profile": {
                    "user_id": payload.get("user_id"),
                    "roles": payload.get("roles"),
                    "token_issued_at": datetime.fromtimestamp(
                        payload.get("iat", 0)
                    ).isoformat(),
                    "token_expires_at": datetime.fromtimestamp(
                        payload.get("exp", 0)
                    ).isoformat(),
                },
            }
        )

    except Exception as e:
        logger.error(f"프로필 조회 실패: {e}")
        return (
            jsonify({"success": False, "error": "프로필 조회 중 오류가 발생했습니다"}),
            500,
        )


# 에러 핸들러
@auth_bp.errorhandler(400)
def bad_request(error):
    return jsonify({"success": False, "error": "Invalid request data"}), 400


@auth_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({"success": False, "error": "Authentication required"}), 401


@auth_bp.errorhandler(429)
def rate_limit_exceeded(error):
    return (
        jsonify(
            {"success": False, "error": "Rate limit exceeded. Please try again later."}
        ),
        429,
    )


@auth_bp.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "Internal server error"}), 500
