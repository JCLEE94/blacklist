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
        
        # 소스별 분포 계산 (하드코딩 제거)
        source_distribution = calculate_source_distribution(stats)
        
        return render_template('dashboard.html', 
                             health=health,
                             collection_status=collection_status,
                             stats=stats,
                             source_distribution=source_distribution)
    except Exception as e:
        logger.error(f"홈페이지 대시보드 렌더링 실패: {e}")
        # 오류 시 간단한 JSON 응답으로 폴백
        return jsonify({
            "message": "Blacklist Management System",
            "version": "1.0.0",
            "status": "Dashboard temporarily unavailable",
            "endpoints": {
                "health": "/health",
                "dashboard": "/api/docs", 
                "blacklist": "/api/blacklist/active",
                "fortigate": "/api/fortigate",
                "stats": "/api/stats",
                "collection_status": "/api/collection/status"
            },
            "error": str(e)
        }), 500

def calculate_source_distribution(stats):
    """실제 데이터를 기반으로 소스별 분포 계산"""
    try:
        sources = stats.get('sources', {})
        total = sum(source.get('total_ips', 0) for source in sources.values())
        
        if total == 0:
            # 데이터가 없을 때 기본값
            return {
                'regtech': {'count': 0, 'percentage': 0},
                'secudium': {'count': 0, 'percentage': 0},
                'public': {'count': 0, 'percentage': 0}
            }
        
        regtech_count = sources.get('regtech', {}).get('total_ips', 0)
        secudium_count = sources.get('secudium', {}).get('total_ips', 0)
        public_count = total - regtech_count - secudium_count
        
        return {
            'regtech': {
                'count': regtech_count,
                'percentage': round((regtech_count / total) * 100, 1) if total > 0 else 0
            },
            'secudium': {
                'count': secudium_count,
                'percentage': round((secudium_count / total) * 100, 1) if total > 0 else 0
            },
            'public': {
                'count': max(0, public_count),
                'percentage': round((max(0, public_count) / total) * 100, 1) if total > 0 else 0
            }
        }
    except Exception as e:
        logger.error(f"소스별 분포 계산 실패: {e}")
        # 오류 시 기본값 반환
        return {
            'regtech': {'count': 0, 'percentage': 0},
            'secudium': {'count': 0, 'percentage': 0},
            'public': {'count': 0, 'percentage': 0}
        }

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