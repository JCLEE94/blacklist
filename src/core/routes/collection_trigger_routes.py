"""
수집 트리거 라우트
REGTECH, SECUDIUM 데이터 수집 트리거 API
"""

import logging
import os
from datetime import datetime

from flask import Blueprint
from flask import jsonify
from flask import request

from ..container import get_container
from ..unified_service import get_unified_service

logger = logging.getLogger(__name__)

# 수집 트리거 라우트 블루프린트
collection_trigger_bp = Blueprint("collection_trigger", __name__)

# 통합 서비스 인스턴스
service = get_unified_service()


@collection_trigger_bp.route("/api/collection/regtech/trigger", methods=["POST"])
def trigger_regtech_collection():
    """REGTECH 수집 트리거"""
    try:
        # 컴테이너에서 progress_tracker 가져오기
        container = get_container()
        progress_tracker = container.get("progress_tracker")

        # 진행 상황 추적 시작
        if progress_tracker:
            progress_tracker.start_collection("regtech")

        # 로그 추가
        service.add_collection_log(
            "regtech",
            "collection_triggered",
            {"triggered_by": "manual", "timestamp": datetime.now().isoformat()},
        )

        # POST 데이터에서 날짜 파라미터 추출
        data = {}
        try:
            if request.is_json:
                data = request.get_json() or {}
            else:
                data = request.form.to_dict() or {}
        except Exception as e:
            data = {}

        start_date = data.get("start_date")
        end_date = data.get("end_date")
        cookies = data.get("cookies")  # 쿠키 파라미터 추가

        # 쿠키가 제공된 경우 환경 변수에 설정
        if cookies:
            os.environ["REGTECH_COOKIES"] = cookies
            logger.info("REGTECH cookies provided via API - set in environment")

        # REGTECH 수집 실행
        logger.info("About to call service.trigger_regtech_collection")
        result = service.trigger_regtech_collection(
            start_date=start_date, end_date=end_date
        )
        logger.info(f"trigger_regtech_collection returned: {type(result)}")

        # 진행 상황 정보 추가
        progress_info = None
        if progress_tracker:
            try:
                progress = progress_tracker.get_progress("regtech")
                if progress and isinstance(progress, dict):
                    progress_info = {
                        "status": progress.get("status", "unknown"),
                        "current": progress.get("current_item", 0),
                        "total": progress.get("total_items", 0),
                        "percentage": progress.get("percentage", 0.0),
                        "message": progress.get("message", ""),
                    }
            except Exception as pe:
                logger.error(f"Progress info error: {pe}")
                progress_info = None

        if result.get("success"):
            return jsonify(
                {
                    "success": True,
                    "message": "REGTECH 수집이 트리거되었습니다.",
                    "source": "regtech",
                    "data": result,
                    "progress": progress_info,
                }
            )
        else:
            if progress_tracker:
                progress_tracker.fail_collection(
                    "regtech", result.get("message", "REGTECH 수집 트리거 실패")
                )
            return (
                jsonify(
                    {
                        "success": False,
                        "message": result.get("message", "REGTECH 수집 트리거 실패"),
                        "error": result.get("error"),
                        "progress": progress_info,
                    }
                ),
                500,
            )

    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        logger.error(f"REGTECH trigger error: {e}")
        logger.error(f"Traceback: {tb}")

        # 진행 상황 실패 처리
        if "progress_tracker" in locals() and progress_tracker:
            try:
                progress_tracker.fail_collection("regtech", str(e))
            except Exception as fail_error:
                logger.error(f"Error in fail_collection: {fail_error}")

        service.add_collection_log(
            "regtech", "collection_failed", {"error": str(e), "triggered_by": "manual"}
        )
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "message": "REGTECH 수집 트리거 중 오류가 발생했습니다.",
                }
            ),
            500,
        )


@collection_trigger_bp.route("/api/collection/secudium/trigger", methods=["POST"])
def trigger_secudium_collection():
    """SECUDIUM 수집 트리거 (현재 비활성화됨)"""
    try:
        # 컴테이너에서 progress_tracker 가져오기
        container = get_container()
        progress_tracker = container.get("progress_tracker")

        # SECUDIUM은 현재 계정 문제로 비활성화됨
        if progress_tracker:
            progress_tracker.fail_collection(
                "secudium", "SECUDIUM 수집은 현재 비활성화되어 있습니다."
            )

        return (
            jsonify(
                {
                    "success": False,
                    "message": "SECUDIUM 수집은 현재 비활성화되어 있습니다.",
                    "reason": "계정 문제로 인해 일시적으로 사용할 수 없습니다.",
                    "source": "secudium",
                    "disabled": True,
                }
            ),
            503,
        )  # Service Unavailable
    except Exception as e:
        logger.error(f"SECUDIUM trigger error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "message": "SECUDIUM 수집 트리거 중 오류가 발생했습니다.",
                }
            ),
            500,
        )


@collection_trigger_bp.route("/api/collection/progress/<source>", methods=["GET"])
def get_collection_progress(source):
    """특정 소스의 수집 진행 상황 조회"""
    try:
        container = get_container()
        progress_tracker = container.get("progress_tracker")

        if not progress_tracker:
            return (
                jsonify(
                    {"success": False, "message": "Progress tracker not available"}
                ),
                503,
            )

        progress = progress_tracker.get_progress(source)
        if progress:
            return jsonify(
                {
                    "success": True,
                    "source": source,
                    "progress": {
                        "status": progress["status"],
                        "current": progress["current_item"],
                        "total": progress["total_items"],
                        "percentage": progress["percentage"],
                        "message": progress["message"],
                        "started_at": progress["started_at"],
                        "updated_at": progress.get("updated_at"),
                    },
                }
            )
        else:
            return jsonify(
                {
                    "success": True,
                    "source": source,
                    "progress": None,
                    "message": "No active collection for {source}",
                }
            )
    except Exception as e:
        logger.error(f"Progress check error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
