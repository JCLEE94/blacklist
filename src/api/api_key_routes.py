# !/usr/bin/env python3
"""
API 키 관리 라우트
"""


from ..models.api_key import get_api_key_manager
from ..utils.security import input_validation, rate_limit, require_auth
from flask import Flask, Blueprint, jsonify, request, redirect, url_for, render_template
import logging
logger = logging.getLogger(__name__)

# 블루프린트 생성
api_key_bp = Blueprint("api_keys", __name__, url_prefix="/api/keys")


@api_key_bp.route("/create", methods=["POST"])
@rate_limit(limit=10, window_seconds=3600)  # 시간당 10개 생성 제한
@require_auth(roles=["admin"])  # 관리자만 생성 가능
@input_validation(
    {
        "name": {"required": True, "type": str, "min_length": 1, "max_length": 100},
        "description": {"required": False, "type": str, "max_length": 500},
        "permissions": {"required": False, "type": list},
        "expires_in_days": {"required": False, "type": int},
    }
)
def create_api_key():
    """새 API 키 생성"""
    try:
        data = request.get_json()

        api_key_manager = get_api_key_manager()

        # API 키 생성
        raw_key, api_key_obj = api_key_manager.create_api_key(
            name=data["name"],
            description=data.get("description", ""),
            permissions=data.get("permissions", ["read"]),
            expires_in_days=data.get("expires_in_days"),
        )

        logger.info(f"새 API 키 생성: {api_key_obj.name} (ID: {api_key_obj.key_id})")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "API 키가 성공적으로 생성되었습니다",
                    "api_key": raw_key,  # 한 번만 반환
                    "key_info": api_key_obj.to_dict(),
                    "warning": "이 키는 다시 표시되지 않으니 안전한 곳에 보관하세요",
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"API 키 생성 실패: {e}")
        return jsonify({"success": False, "error": "API 키 생성에 실패했습니다"}), 500


@api_key_bp.route("/list", methods=["GET"])
@require_auth(roles=["admin"])
def list_api_keys():
    """API 키 목록 조회"""
    try:
        include_inactive = (
            request.args.get("include_inactive", "false").lower() == "true"
        )

        api_key_manager = get_api_key_manager()
        api_keys = api_key_manager.list_api_keys(include_inactive=include_inactive)

        return jsonify(
            {
                "success": True,
                "api_keys": [key.to_dict() for key in api_keys],
                "total": len(api_keys),
            }
        )

    except Exception as e:
        logger.error(f"API 키 목록 조회 실패: {e}")
        return (
            jsonify({"success": False, "error": "API 키 목록을 가져올 수 없습니다"}),
            500,
        )


@api_key_bp.route("/<key_id>", methods=["GET"])
@require_auth(roles=["admin"])
def get_api_key(key_id: str):
    """특정 API 키 상세 조회"""
    try:
        api_key_manager = get_api_key_manager()
        api_key = api_key_manager.get_api_key(key_id)

        if not api_key:
            return (
                jsonify({"success": False, "error": "API 키를 찾을 수 없습니다"}),
                404,
            )

        return jsonify({"success": True, "api_key": api_key.to_dict()})

    except Exception as e:
        logger.error(f"API 키 조회 실패: {e}")
        return (
            jsonify({"success": False, "error": "API 키 정보를 가져올 수 없습니다"}),
            500,
        )


@api_key_bp.route("/<key_id>/revoke", methods=["POST"])
@require_auth(roles=["admin"])
def revoke_api_key(key_id: str):
    """API 키 비활성화"""
    try:
        api_key_manager = get_api_key_manager()

        # 키 존재 확인
        api_key = api_key_manager.get_api_key(key_id)
        if not api_key:
            return (
                jsonify({"success": False, "error": "API 키를 찾을 수 없습니다"}),
                404,
            )

        # 비활성화
        success = api_key_manager.revoke_api_key(key_id)

        if success:
            logger.info(f"API 키 비활성화: {api_key.name} (ID: {key_id})")
            return jsonify(
                {"success": True, "message": "API 키가 성공적으로 비활성화되었습니다"}
            )
        else:
            return (
                jsonify({"success": False, "error": "API 키 비활성화에 실패했습니다"}),
                500,
            )

    except Exception as e:
        logger.error(f"API 키 비활성화 실패: {e}")
        return (
            jsonify(
                {"success": False, "error": "API 키 비활성화 중 오류가 발생했습니다"}
            ),
            500,
        )


@api_key_bp.route("/<key_id>", methods=["DELETE"])
@require_auth(roles=["admin"])
def delete_api_key(key_id: str):
    """API 키 완전 삭제"""
    try:
        api_key_manager = get_api_key_manager()

        # 키 존재 확인
        api_key = api_key_manager.get_api_key(key_id)
        if not api_key:
            return (
                jsonify({"success": False, "error": "API 키를 찾을 수 없습니다"}),
                404,
            )

        # 삭제
        success = api_key_manager.delete_api_key(key_id)

        if success:
            logger.info(f"API 키 삭제: {api_key.name} (ID: {key_id})")
            return jsonify(
                {"success": True, "message": "API 키가 성공적으로 삭제되었습니다"}
            )
        else:
            return (
                jsonify({"success": False, "error": "API 키 삭제에 실패했습니다"}),
                500,
            )

    except Exception as e:
        logger.error(f"API 키 삭제 실패: {e}")
        return (
            jsonify({"success": False, "error": "API 키 삭제 중 오류가 발생했습니다"}),
            500,
        )


@api_key_bp.route("/validate", methods=["POST"])
@input_validation({"api_key": {"required": True, "type": str, "min_length": 10}})
def validate_api_key():
    """API 키 유효성 검증 (테스트용)"""
    try:
        data = request.get_json()
        api_key = data["api_key"]

        api_key_manager = get_api_key_manager()
        validated_key = api_key_manager.validate_api_key(api_key)

        if validated_key:
            return jsonify(
                {
                    "success": True,
                    "valid": True,
                    "key_info": {
                        "name": validated_key.name,
                        "permissions": validated_key.permissions,
                        "expires_at": (
                            validated_key.expires_at.isoformat()
                            if validated_key.expires_at
                            else None
                        ),
                        "usage_count": validated_key.usage_count,
                    },
                }
            )
        else:
            return jsonify(
                {
                    "success": True,
                    "valid": False,
                    "message": "API 키가 유효하지 않거나 만료되었습니다",
                }
            )

    except Exception as e:
        logger.error(f"API 키 검증 실패: {e}")
        return (
            jsonify({"success": False, "error": "API 키 검증 중 오류가 발생했습니다"}),
            500,
        )


@api_key_bp.route("/stats", methods=["GET"])
@require_auth(roles=["admin"])
def get_api_key_stats():
    """API 키 통계 조회"""
    try:
        api_key_manager = get_api_key_manager()
        all_keys = api_key_manager.list_api_keys(include_inactive=True)

        stats = {
            "total_keys": len(all_keys),
            "active_keys": len([k for k in all_keys if k.is_active]),
            "inactive_keys": len([k for k in all_keys if not k.is_active]),
            "expired_keys": len([k for k in all_keys if k.is_expired()]),
            "total_usage": sum(k.usage_count for k in all_keys),
            "permissions_breakdown": {},
        }

        # 권한별 분류
        for key in all_keys:
            for perm in key.permissions:
                stats["permissions_breakdown"][perm] = (
                    stats["permissions_breakdown"].get(perm, 0) + 1
                )

        return jsonify({"success": True, "stats": stats})

    except Exception as e:
        logger.error(f"API 키 통계 조회 실패: {e}")
        return jsonify({"success": False, "error": "통계를 가져올 수 없습니다"}), 500


# 에러 핸들러
@api_key_bp.errorhandler(400)
def bad_request(error):
    return jsonify({"success": False, "error": "Invalid request data"}), 400


@api_key_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({"success": False, "error": "Authentication required"}), 401


@api_key_bp.errorhandler(403)
def forbidden(error):
    return jsonify({"success": False, "error": "Insufficient permissions"}), 403


@api_key_bp.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "Resource not found"}), 404


@api_key_bp.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "Internal server error"}), 500
