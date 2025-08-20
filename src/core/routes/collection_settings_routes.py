#!/usr/bin/env python3
"""
수집 설정 관리 라우트
UI에서 수집 소스 설정 및 자격증명을 저장/조회
"""

from pathlib import Path

from flask import Blueprint
from flask import jsonify
from flask import render_template_string
from flask import request

try:
    from ..database.collection_settings import CollectionSettingsDB

    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

bp = Blueprint("collection_settings", __name__, url_prefix="/api/collection/settings")


def get_db():
    """DB 인스턴스 반환"""
    if not DB_AVAILABLE:
        return None
    return CollectionSettingsDB()


# HTML 템플릿 로드 함수
def load_template():
    """HTML 템플릿 파일 로드"""
    try:
        template_path = Path(__file__).parent / "templates" / "collection_settings.html"
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "<h1>템플릿 로드 실패</h1><p>collection_settings.html 파일을 찾을 수 없습니다.</p>"


@bp.route("/ui")
def settings_ui():
    """설정 관리 UI 페이지"""
    return load_template()


@bp.route("/sources", methods=["GET"])
def get_sources():
    """모든 수집 소스 목록 조회"""
    if not DB_AVAILABLE:
        return jsonify({"error": "Database not available"}), 500

    try:
        db = get_db()
        sources = db.get_all_sources()
        return jsonify(sources)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/sources", methods=["POST"])
def add_source():
    """새 수집 소스 추가"""
    if not DB_AVAILABLE:
        return jsonify({"error": "Database not available"}), 500

    try:
        data = request.get_json() or {}

        name = data.get("name", "").strip()
        display_name = data.get("display_name", "").strip()
        base_url = data.get("base_url", "").strip()
        config_str = data.get("config", "{}")
        enabled = data.get("enabled", True)

        if not name or not display_name or not base_url:
            return (
                jsonify({"success": False, "error": "필수 필드가 누락되었습니다"}),
                400,
            )

        # JSON 설정 파싱
        try:
            import json

            config = json.loads(config_str) if config_str else {}
        except json.JSONDecodeError:
            return (
                jsonify(
                    {"success": False, "error": "설정 JSON 형식이 올바르지 않습니다"}
                ),
                400,
            )

        db = get_db()
        success = db.save_source_config(name, display_name, base_url, config, enabled)

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "소스 저장 실패"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/sources/<source_name>/toggle", methods=["POST"])
def toggle_source(source_name):
    """소스 활성화/비활성화 토글"""
    if not DB_AVAILABLE:
        return jsonify({"error": "Database not available"}), 500

    try:
        data = request.get_json() or {}
        enabled = data.get("enabled", True)

        db = get_db()
        # 기존 설정 조회
        source_config = db.get_source_config(source_name)
        if not source_config:
            return jsonify({"success": False, "error": "소스를 찾을 수 없습니다"}), 404

        # 상태 업데이트
        success = db.save_source_config(
            source_name,
            source_config["display_name"],
            source_config["base_url"],
            source_config["config"],
            enabled,
        )

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "상태 변경 실패"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/credentials", methods=["POST"])
def save_credentials():
    """자격증명 저장"""
    if not DB_AVAILABLE:
        return jsonify({"error": "Database not available"}), 500

    try:
        data = request.get_json() or {}

        source_name = data.get("source_name", "").strip()
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not source_name or not username or not password:
            return jsonify({"success": False, "error": "모든 필드가 필요합니다"}), 400

        db = get_db()
        success = db.save_credentials(source_name, username, password)

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "자격증명 저장 실패"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/test/<source_name>", methods=["POST"])
def test_collection(source_name):
    """수집 테스트"""
    if not DB_AVAILABLE:
        return jsonify({"error": "Database not available"}), 500

    try:
        # 기존 수집기 사용하여 테스트
        from ..collection_db_collector import DatabaseCollectionSystem

        collector = DatabaseCollectionSystem()
        result = collector.collect_from_source(source_name)

        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/test-connection/<source_name>", methods=["POST"])
def test_connection(source_name):
    """연결 테스트"""
    if not DB_AVAILABLE:
        return jsonify({"error": "Database not available"}), 500

    try:
        db = get_db()

        # 설정 및 자격증명 확인
        source_config = db.get_source_config(source_name)
        credentials = db.get_credentials(source_name)

        if not source_config:
            return jsonify({"success": False, "error": "소스 설정이 없습니다"})

        if not credentials:
            return jsonify({"success": False, "error": "자격증명이 없습니다"})

        # 간단한 연결 테스트 (ping 형태)
        import requests

        base_url = source_config["base_url"]
        timeout = source_config.get("config", {}).get("timeout", 10)

        response = requests.get(base_url, timeout=timeout)

        if response.status_code == 200:
            return jsonify(
                {"success": True, "message": f"연결 성공 ({response.status_code})"}
            )
        else:
            return jsonify(
                {"success": False, "error": f"연결 실패: HTTP {response.status_code}"}
            )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
