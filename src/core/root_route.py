"""루트 경로 라우트 추가"""
from flask import Blueprint, redirect, jsonify

root_bp = Blueprint('root', __name__)

@root_bp.route('/')
def index():
    """루트 경로 - API 문서로 리다이렉트"""
    return redirect('/api/docs', code=302)

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