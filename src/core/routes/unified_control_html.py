from flask import Flask, Blueprint, jsonify, request, redirect, url_for, render_template
import logging

logger = logging.getLogger(__name__)

#!/usr/bin/env python3
"""
통합 제어 대시보드 HTML 라우트
Flask 템플릿을 사용한 최적화된 구조로 리팩토링됨
"""


# Blueprint 생성
unified_dashboard_bp = Blueprint("unified_dashboard", __name__)


@unified_dashboard_bp.route("/unified-dashboard")
def unified_dashboard():
    """통합 제어 대시보드 메인 페이지"""
    return render_template("unified_dashboard.html")


@unified_dashboard_bp.route("/control")
def control_alias():
    """대시보드 접근 단축 URL"""
    return render_template("unified_dashboard.html")


@unified_dashboard_bp.route("/dashboard-old")
def dashboard_alias():
    """대시보드 접근 별칭 URL (임시 비활성화)"""
    return render_template("unified_dashboard.html")


# 레거시 호환성을 위한 함수
def get_unified_dashboard_html():
    """
    DEPRECATED: 레거시 호환성을 위한 함수
    새 코드에서는 render_template('unified_dashboard.html')을 직접 사용하세요
    """
    return render_template("unified_dashboard.html")


# 레거시 변수명 유지 (기존 코드와의 호환성)
UNIFIED_DASHBOARD_HTML = (
    "<!-- HTML은 이제 templates/unified_dashboard.html에 있습니다 -->"
)
