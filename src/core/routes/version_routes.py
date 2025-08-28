"""
버전 관리 API 엔드포인트
동적 버전 정보 제공
"""

from flask import Blueprint, jsonify
from src.core.utils.version_manager import version_manager
import logging

logger = logging.getLogger(__name__)

version_bp = Blueprint("version", __name__)


@version_bp.route("/version")
@version_bp.route("/api/version")
def get_version_api():
    """현재 버전 정보 API"""
    try:
        version_info = version_manager.get_version_info()
        return jsonify(
            {
                "success": True,
                "version": version_info["version"],
                "build_timestamp": version_info["build_timestamp"],
                "git_hash": version_info["git"]["commit_hash"],
                "git_branch": version_info["git"]["branch"],
                "build_number": version_info["build"]["build_number"],
                "environment": version_info["environment"],
            }
        )
    except Exception as e:
        logger.error(f"버전 정보 조회 실패: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "버전 정보를 가져올 수 없습니다",
                    "version": "unknown",
                }
            ),
            500,
        )


@version_bp.route("/version/full")
@version_bp.route("/api/version/full")
def get_full_version_info():
    """상세 버전 정보 API"""
    try:
        version_info = version_manager.get_version_info()
        return jsonify({"success": True, "data": version_info})
    except Exception as e:
        logger.error(f"상세 버전 정보 조회 실패: {e}")
        return (
            jsonify({"success": False, "error": "상세 버전 정보를 가져올 수 없습니다"}),
            500,
        )


@version_bp.route("/version/deployment")
@version_bp.route("/api/version/deployment")
def get_deployment_info():
    """배포 정보 API"""
    try:
        deployment_info = version_manager.get_deployment_info()
        return jsonify({"success": True, "deployment": deployment_info})
    except Exception as e:
        logger.error(f"배포 정보 조회 실패: {e}")
        return (
            jsonify({"success": False, "error": "배포 정보를 가져올 수 없습니다"}),
            500,
        )


@version_bp.route("/health")
def health_check_with_version():
    """버전 정보가 포함된 헬스체크"""
    try:
        version_info = version_manager.get_version_info()

        return jsonify(
            {
                "status": "healthy",
                "service": "blacklist-management",
                "version": version_info["version"],
                "build_number": version_info["build"]["build_number"],
                "git_hash": version_info["git"]["commit_hash"],
                "environment": version_info["environment"],
                "timestamp": version_info["build_timestamp"],
                "components": {
                    "database": "healthy",
                    "cache": "healthy",
                    "blacklist": "healthy",
                },
            }
        )
    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        return (
            jsonify(
                {
                    "status": "degraded",
                    "service": "blacklist-management",
                    "version": "unknown",
                    "error": str(e),
                }
            ),
            500,
        )
