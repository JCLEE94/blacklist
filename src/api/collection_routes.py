#!/usr/bin/env python3
"""
수집 관리 API 라우트
"""

import asyncio
import logging

from flask import Blueprint, jsonify, request

from ..core.collectors.collector_factory import get_collector_factory
from ..utils.security import input_validation, rate_limit, require_auth

logger = logging.getLogger(__name__)

# 블루프린트 생성
collection_bp = Blueprint("collection", __name__, url_prefix="/api/collection")


@collection_bp.route("/status", methods=["GET"])
@rate_limit(limit=60, window_seconds=60)  # 분당 60회
def get_collection_status():
    """수집 시스템 전체 상태 조회"""
    try:
        factory = get_collector_factory()
        status = factory.get_collector_status()

        return jsonify(
            {"success": True, "status": status, "timestamp": status.get("timestamp")}
        )

    except Exception as e:
        logger.error(f"수집 상태 조회 실패: {e}")
        return (
            jsonify({"success": False, "error": "수집 상태를 가져올 수 없습니다"}),
            500,
        )


@collection_bp.route("/collectors", methods=["GET"])
@require_auth(roles=["admin", "collector"])
def list_collectors():
    """등록된 수집기 목록 조회"""
    try:
        factory = get_collector_factory()
        manager = factory.create_collection_manager()

        collectors = manager.list_collectors()
        collector_details = []

        for name in collectors:
            collector = manager.get_collector(name)
            if collector:
                health = collector.health_check()
                collector_details.append(
                    {
                        "name": name,
                        "type": collector.source_type,
                        "enabled": collector.config.enabled,
                        "is_running": collector.is_running,
                        "health": health,
                    }
                )

        return jsonify(
            {
                "success": True,
                "collectors": collector_details,
                "total": len(collector_details),
            }
        )

    except Exception as e:
        logger.error(f"수집기 목록 조회 실패: {e}")
        return (
            jsonify({"success": False, "error": "수집기 목록을 가져올 수 없습니다"}),
            500,
        )


@collection_bp.route("/collectors/<collector_name>/enable", methods=["POST"])
@require_auth(roles=["admin"])
def enable_collector(collector_name: str):
    """특정 수집기 활성화"""
    try:
        factory = get_collector_factory()
        success = factory.enable_collector(collector_name)

        if success:
            logger.info(f"수집기 활성화 성공: {collector_name}")
            return jsonify(
                {
                    "success": True,
                    "message": "{collector_name} 수집기가 활성화되었습니다",
                }
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "{collector_name} 수집기를 찾을 수 없습니다",
                    }
                ),
                404,
            )

    except Exception as e:
        logger.error(f"수집기 활성화 실패 ({collector_name}): {e}")
        return (
            jsonify(
                {"success": False, "error": "수집기 활성화 중 오류가 발생했습니다"}
            ),
            500,
        )


@collection_bp.route("/collectors/<collector_name>/disable", methods=["POST"])
@require_auth(roles=["admin"])
def disable_collector(collector_name: str):
    """특정 수집기 비활성화"""
    try:
        factory = get_collector_factory()
        success = factory.disable_collector(collector_name)

        if success:
            logger.info(f"수집기 비활성화 성공: {collector_name}")
            return jsonify(
                {
                    "success": True,
                    "message": "{collector_name} 수집기가 비활성화되었습니다",
                }
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "{collector_name} 수집기를 찾을 수 없습니다",
                    }
                ),
                404,
            )

    except Exception as e:
        logger.error(f"수집기 비활성화 실패 ({collector_name}): {e}")
        return (
            jsonify(
                {"success": False, "error": "수집기 비활성화 중 오류가 발생했습니다"}
            ),
            500,
        )


@collection_bp.route("/collectors/<collector_name>/trigger", methods=["POST"])
@rate_limit(limit=5, window_seconds=300)  # 5분에 5회
@require_auth(roles=["admin", "collector"])
def trigger_collection(collector_name: str):
    """특정 수집기 수동 실행"""
    try:
        factory = get_collector_factory()

        # 비동기 수집 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                factory.collect_from_source(collector_name)
            )
        finally:
            loop.close()

        if result["success"]:
            logger.info(f"수집 수동 실행 성공: {collector_name}")
            return jsonify(
                {
                    "success": True,
                    "message": "{collector_name} 수집이 완료되었습니다",
                    "result": result["result"],
                }
            )
        else:
            return (
                jsonify({"success": False, "error": result.get("error", "수집 실패")}),
                400,
            )

    except Exception as e:
        logger.error(f"수집 수동 실행 실패 ({collector_name}): {e}")
        return (
            jsonify({"success": False, "error": "수집 실행 중 오류가 발생했습니다"}),
            500,
        )


@collection_bp.route("/trigger-all", methods=["POST"])
@rate_limit(limit=2, window_seconds=300)  # 5분에 2회
@require_auth(roles=["admin"])
def trigger_all_collections():
    """모든 수집기 수동 실행"""
    try:
        factory = get_collector_factory()

        # 비동기 수집 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(factory.collect_all())
        finally:
            loop.close()

        if result["success"]:
            logger.info("전체 수집 수동 실행 성공")
            return jsonify(
                {
                    "success": True,
                    "message": "모든 수집이 완료되었습니다",
                    "results": result["results"],
                }
            )
        else:
            return (
                jsonify(
                    {"success": False, "error": result.get("error", "전체 수집 실패")}
                ),
                400,
            )

    except Exception as e:
        logger.error(f"전체 수집 수동 실행 실패: {e}")
        return (
            jsonify(
                {"success": False, "error": "전체 수집 실행 중 오류가 발생했습니다"}
            ),
            500,
        )


@collection_bp.route("/collectors/<collector_name>/cancel", methods=["POST"])
@require_auth(roles=["admin"])
def cancel_collection(collector_name: str):
    """실행 중인 수집 취소"""
    try:
        factory = get_collector_factory()
        manager = factory.create_collection_manager()

        collector = manager.get_collector(collector_name)
        if not collector:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "{collector_name} 수집기를 찾을 수 없습니다",
                    }
                ),
                404,
            )

        if not collector.is_running:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "{collector_name} 수집기가 실행 중이 아닙니다",
                    }
                ),
                400,
            )

        collector.cancel()
        logger.info(f"수집 취소 요청: {collector_name}")

        return jsonify(
            {"success": True, "message": "{collector_name} 수집 취소가 요청되었습니다"}
        )

    except Exception as e:
        logger.error(f"수집 취소 실패 ({collector_name}): {e}")
        return (
            jsonify({"success": False, "error": "수집 취소 중 오류가 발생했습니다"}),
            500,
        )


@collection_bp.route("/cancel-all", methods=["POST"])
@require_auth(roles=["admin"])
def cancel_all_collections():
    """모든 실행 중인 수집 취소"""
    try:
        factory = get_collector_factory()
        manager = factory.create_collection_manager()

        manager.cancel_all_collections()
        logger.info("모든 수집 취소 요청")

        return jsonify({"success": True, "message": "모든 수집 취소가 요청되었습니다"})

    except Exception as e:
        logger.error(f"전체 수집 취소 실패: {e}")
        return (
            jsonify(
                {"success": False, "error": "전체 수집 취소 중 오류가 발생했습니다"}
            ),
            500,
        )


@collection_bp.route("/history", methods=["GET"])
@require_auth(roles=["admin", "collector"])
def get_collection_history():
    """수집 히스토리 조회"""
    try:
        factory = get_collector_factory()
        manager = factory.create_collection_manager()

        # 최근 히스토리 가져오기
        status = manager.get_status()
        recent_results = status.get("recent_results", [])

        # 쿼리 파라미터 처리
        limit = min(int(request.args.get("limit", 50)), 100)  # 최대 100개
        source = request.args.get("source")

        # 필터링
        filtered_results = recent_results
        if source:
            filtered_results = [
                result
                for result in filtered_results
                if result.get("source_name", "").upper() == source.upper()
            ]

        # 제한
        filtered_results = filtered_results[:limit]

        return jsonify(
            {
                "success": True,
                "history": filtered_results,
                "total": len(filtered_results),
                "limit": limit,
            }
        )

    except Exception as e:
        logger.error(f"수집 히스토리 조회 실패: {e}")
        return (
            jsonify({"success": False, "error": "수집 히스토리를 가져올 수 없습니다"}),
            500,
        )


@collection_bp.route("/config", methods=["GET"])
@require_auth(roles=["admin"])
def get_collection_config():
    """수집 설정 조회"""
    try:
        factory = get_collector_factory()
        manager = factory.create_collection_manager()

        config_info = {
            "global_enabled": manager.global_config.get("global_enabled", True),
            "concurrent_collections": manager.global_config.get(
                "concurrent_collections", 3
            ),
            "retry_delay": manager.global_config.get("retry_delay", 5),
            "max_history_size": manager.max_history_size,
        }

        return jsonify({"success": True, "config": config_info})

    except Exception as e:
        logger.error(f"수집 설정 조회 실패: {e}")
        return (
            jsonify({"success": False, "error": "수집 설정을 가져올 수 없습니다"}),
            500,
        )


@collection_bp.route("/config", methods=["PUT"])
@require_auth(roles=["admin"])
@input_validation(
    {
        "concurrent_collections": {"required": False, "type": int},
        "retry_delay": {"required": False, "type": int},
    }
)
def update_collection_config():
    """수집 설정 업데이트"""
    try:
        data = request.get_json()
        factory = get_collector_factory()
        manager = factory.create_collection_manager()

        # 설정 업데이트
        if "concurrent_collections" in data:
            concurrent = max(1, min(data["concurrent_collections"], 10))  # 1-10 범위
            manager.global_config["concurrent_collections"] = concurrent

        if "retry_delay" in data:
            delay = max(1, min(data["retry_delay"], 60))  # 1-60초 범위
            manager.global_config["retry_delay"] = delay

        # 설정 저장
        manager._save_config(manager.global_config)

        logger.info("수집 설정 업데이트 완료")

        return jsonify(
            {
                "success": True,
                "message": "수집 설정이 업데이트되었습니다",
                "config": {
                    "concurrent_collections": manager.global_config.get(
                        "concurrent_collections"
                    ),
                    "retry_delay": manager.global_config.get("retry_delay"),
                },
            }
        )

    except Exception as e:
        logger.error(f"수집 설정 업데이트 실패: {e}")
        return (
            jsonify(
                {"success": False, "error": "수집 설정 업데이트 중 오류가 발생했습니다"}
            ),
            500,
        )


# 에러 핸들러
@collection_bp.errorhandler(400)
def bad_request(error):
    return jsonify({"success": False, "error": "Invalid request data"}), 400


@collection_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({"success": False, "error": "Authentication required"}), 401


@collection_bp.errorhandler(403)
def forbidden(error):
    return jsonify({"success": False, "error": "Insufficient permissions"}), 403


@collection_bp.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "Resource not found"}), 404


@collection_bp.errorhandler(429)
def rate_limit_exceeded(error):
    return (
        jsonify(
            {"success": False, "error": "Rate limit exceeded. Please try again later."}
        ),
        429,
    )


@collection_bp.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "Internal server error"}), 500
