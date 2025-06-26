"""루트 경로 라우트 추가"""
from flask import Blueprint, redirect, jsonify, render_template
import logging
import asyncio

root_bp = Blueprint('root', __name__)
logger = logging.getLogger(__name__)

@root_bp.route('/')
def index():
    """루트 경로 - 대시보드 직접 렌더링"""
    try:
        # 서비스 인스턴스 가져오기
        from .unified_service import get_unified_service
        service = get_unified_service()
        
        # 시스템 상태 정보 수집
        health = service.get_health()
        collection_status = service.get_collection_status()
        result = asyncio.run(service.get_statistics())
        
        stats = result.get('statistics', {}) if result.get('success') else {}
        
        return render_template('dashboard.html', 
                             health=health,
                             collection_status=collection_status,
                             stats=stats)
    except Exception as e:
        logger.error(f"홈페이지 대시보드 렌더링 실패: {e}")
        # 오류 시 API 엔드포인트 목록으로 폴백
        return jsonify({
            "message": "Blacklist Management System",
            "version": "1.0.0",
            "endpoints": {
                "health": "/health",
                "dashboard": "/api/docs", 
                "blacklist": "/api/blacklist/active",
                "fortigate": "/api/fortigate",
                "stats": "/api/stats",
                "collection_status": "/api/collection/status"
            },
            "error": "Dashboard rendering failed, showing API endpoints instead"
        })

@root_bp.route('/api')
def api_root():
    """API 루트 - 사용 가능한 엔드포인트 목록"""
    return jsonify({
        "message": "Blacklist Management API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "api_docs": "/api/docs",
            "blacklist": "/api/blacklist/active",
            "fortigate": "/api/fortigate",
            "stats": "/api/stats",
            "collection_status": "/api/collection/status"
        }
    })