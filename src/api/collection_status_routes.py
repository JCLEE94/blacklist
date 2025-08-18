#!/usr/bin/env python3
"""
수집 상태 및 데이터 조회 API 라우트
"""

import logging

from flask import Blueprint, jsonify, request

from ..core.collectors.collector_factory import get_collector_factory
from ..utils.security import rate_limit, require_auth

logger = logging.getLogger(__name__)

# 블루프린트 생성
collection_status_bp = Blueprint("collection_status", __name__, url_prefix="/api/collection")


@collection_status_bp.route("/status", methods=["GET"])
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


@collection_status_bp.route("/daily-stats", methods=["GET"])
@rate_limit(limit=30, window_seconds=60)  # 분당 30회
def get_daily_collection_stats():
    """날짜별 수집 통계 조회 (시각화용)"""
    try:
        days = request.args.get("days", 30, type=int)  # 기본 30일
        
        factory = get_collector_factory()
        manager = factory.create_collection_manager()
        
        # 날짜별 수집 데이터 조회
        daily_stats = manager.get_daily_collection_stats(days)
        
        # 시각화를 위한 데이터 변환
        visualization_data = {
            "labels": [stat["date"] for stat in daily_stats],
            "datasets": [
                {
                    "label": "REGTECH",
                    "data": [stat.get("regtech_count", 0) for stat in daily_stats],
                    "backgroundColor": "rgba(54, 162, 235, 0.2)",
                    "borderColor": "rgba(54, 162, 235, 1)",
                    "borderWidth": 2
                },
                {
                    "label": "SECUDIUM", 
                    "data": [stat.get("secudium_count", 0) for stat in daily_stats],
                    "backgroundColor": "rgba(255, 99, 132, 0.2)",
                    "borderColor": "rgba(255, 99, 132, 1)", 
                    "borderWidth": 2
                },
                {
                    "label": "중복 제거됨",
                    "data": [stat.get("duplicates_removed", 0) for stat in daily_stats],
                    "backgroundColor": "rgba(255, 206, 86, 0.2)",
                    "borderColor": "rgba(255, 206, 86, 1)",
                    "borderWidth": 2
                }
            ],
            "totals": {
                "total_collected": sum([stat.get("total_count", 0) for stat in daily_stats]),
                "total_duplicates": sum([stat.get("duplicates_removed", 0) for stat in daily_stats]),
                "regtech_total": sum([stat.get("regtech_count", 0) for stat in daily_stats]),
                "secudium_total": sum([stat.get("secudium_count", 0) for stat in daily_stats])
            }
        }

        return jsonify({
            "success": True,
            "data": daily_stats,
            "visualization": visualization_data,
            "period": f"{days}일",
            "summary": {
                "total_days": len(daily_stats),
                "collection_days": len([s for s in daily_stats if s.get("total_count", 0) > 0])
            }
        })

    except Exception as e:
        logger.error(f"일별 수집 통계 조회 실패: {e}")
        return (
            jsonify({"success": False, "error": "일별 통계를 가져올 수 없습니다"}),
            500,
        )


@collection_status_bp.route("/collectors", methods=["GET"])
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


@collection_status_bp.route("/history", methods=["GET"])
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