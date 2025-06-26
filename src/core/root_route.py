"""루트 경로 라우트 추가"""
from flask import Blueprint, redirect, jsonify, render_template
import logging
import asyncio

root_bp = Blueprint('root', __name__)
logger = logging.getLogger(__name__)

@root_bp.route('/')
def index():
    """루트 경로 - 대시보드로 리다이렉트"""
    return redirect('/dashboard', code=302)

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