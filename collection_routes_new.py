# 새로운 수집 관련 라우트 (간소화)

@unified_bp.route('/api/collection/status', methods=['GET'])
def collection_status():
    """수집 상태 및 통계 (읽기 전용)"""
    try:
        status = service.get_collection_status()
        
        # 수집 통계 추가
        stats = service.get_collection_statistics()
        
        return jsonify({
            'status': 'auto_collection',  # 항상 자동 수집 모드
            'auto_collection': True,
            'regtech_interval': '3_months',  # 3개월 이내 자동 수집
            'secudium_interval': '3_days',   # 3일 이내 자동 수집
            'statistics': stats,
            'last_collection': status.get('last_collection'),
            'logs': status.get('logs', [])[-10:]  # 최근 10개 로그만
        })
    except Exception as e:
        logger.error(f"Collection status error: {e}")
        return jsonify(create_error_response(e)), 500

@unified_bp.route('/api/collection/statistics', methods=['GET'])
def collection_statistics():
    """수집 통계 상세 정보"""
    try:
        # 날짜별 수집 통계
        daily_stats = service.get_daily_collection_stats()
        
        # 소스별 통계
        source_stats = service.get_source_statistics()
        
        return jsonify({
            'success': True,
            'daily_stats': daily_stats,
            'source_stats': source_stats,
            'summary': {
                'total_days_collected': len(daily_stats),
                'total_ips': sum(day.get('count', 0) for day in daily_stats),
                'regtech_total': source_stats.get('regtech', {}).get('total', 0),
                'secudium_total': source_stats.get('secudium', {}).get('total', 0)
            }
        })
    except Exception as e:
        logger.error(f"Collection statistics error: {e}")
        return jsonify(create_error_response(e)), 500

@unified_bp.route('/api/collection/intervals', methods=['GET'])
def get_collection_intervals():
    """수집 간격 설정 조회"""
    try:
        intervals = service.get_collection_intervals()
        
        return jsonify({
            'success': True,
            'intervals': intervals,
            'regtech_days': intervals.get('regtech_days', 90),  # 3개월
            'secudium_days': intervals.get('secudium_days', 3)   # 3일
        })
    except Exception as e:
        logger.error(f"Get collection intervals error: {e}")
        return jsonify(create_error_response(e)), 500

@unified_bp.route('/api/collection/intervals', methods=['POST'])
def update_collection_intervals():
    """수집 간격 설정 업데이트"""
    try:
        data = request.get_json() or {}
        
        regtech_days = data.get('regtech_days', 90)
        secudium_days = data.get('secudium_days', 3)
        
        # 유효성 검사
        if not (1 <= regtech_days <= 365):
            return jsonify({
                'success': False,
                'error': 'REGTECH 수집 간격은 1-365일 사이여야 합니다.'
            }), 400
            
        if not (1 <= secudium_days <= 30):
            return jsonify({
                'success': False,
                'error': 'SECUDIUM 수집 간격은 1-30일 사이여야 합니다.'
            }), 400
        
        result = service.update_collection_intervals(regtech_days, secudium_days)
        
        return jsonify({
            'success': True,
            'message': '수집 간격이 업데이트되었습니다.',
            'intervals': {
                'regtech_days': regtech_days,
                'secudium_days': secudium_days
            }
        })
    except Exception as e:
        logger.error(f"Update collection intervals error: {e}")
        return jsonify(create_error_response(e)), 500