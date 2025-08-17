#!/usr/bin/env python3
"""
수집 대시보드 라우트
Collection Dashboard Routes
"""

import json
import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, render_template, current_app
from typing import Dict, List, Any

from ..collection_dashboard import CollectionDashboard
from ..data_processor import DataProcessor
from ..regtech_simple_collector import RegtechSimpleCollector
from ..advanced_analytics import AdvancedAnalytics

logger = logging.getLogger(__name__)

# Blueprint 생성
collection_dashboard_bp = Blueprint('collection_dashboard', __name__)


@collection_dashboard_bp.route('/dashboard')
def dashboard_page():
    """대시보드 페이지"""
    return render_template('collection_dashboard.html')


@collection_dashboard_bp.route('/api/collection/dashboard')
def get_dashboard_data():
    """대시보드 데이터 API"""
    try:
        dashboard = CollectionDashboard()
        data = dashboard.get_dashboard_summary()
        
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"대시보드 데이터 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@collection_dashboard_bp.route('/api/collection/calendar')
def get_collection_calendar():
    """수집 캘린더 데이터"""
    try:
        days = request.args.get('days', 30, type=int)
        dashboard = CollectionDashboard()
        calendar_data = dashboard.get_collection_calendar(days)
        
        return jsonify({
            'success': True,
            'data': calendar_data
        })
    except Exception as e:
        logger.error(f"캘린더 데이터 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@collection_dashboard_bp.route('/api/collection/trends')
def get_collection_trends():
    """수집 트렌드 데이터"""
    try:
        days = request.args.get('days', 7, type=int)
        dashboard = CollectionDashboard()
        trends_data = dashboard.get_collection_trends(days)
        
        return jsonify({
            'success': True,
            'data': trends_data
        })
    except Exception as e:
        logger.error(f"트렌드 데이터 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@collection_dashboard_bp.route('/api/collection/missing-days')
def get_missing_days():
    """미수집일 목록"""
    try:
        days_back = request.args.get('days_back', 30, type=int)
        dashboard = CollectionDashboard()
        missing_days = dashboard.identify_missing_collections(days_back)
        
        return jsonify({
            'success': True,
            'data': {
                'missing_days': missing_days,
                'count': len(missing_days)
            }
        })
    except Exception as e:
        logger.error(f"미수집일 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@collection_dashboard_bp.route('/api/collection/collect-date', methods=['POST'])
def collect_specific_date():
    """특정 날짜 데이터 수집"""
    try:
        data = request.get_json()
        target_date = data.get('date')
        
        if not target_date:
            return jsonify({
                'success': False,
                'error': '날짜가 필요합니다'
            }), 400
        
        # 날짜 검증
        try:
            datetime.strptime(target_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'success': False,
                'error': '잘못된 날짜 형식입니다'
            }), 400
        
        # 비동기 수집 시작 (실제로는 백그라운드 태스크 사용)
        success = _start_date_collection(target_date)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'{target_date} 수집이 시작되었습니다',
                'date': target_date
            })
        else:
            return jsonify({
                'success': False,
                'error': '수집 시작에 실패했습니다'
            }), 500
            
    except Exception as e:
        logger.error(f"특정 날짜 수집 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@collection_dashboard_bp.route('/api/collection/collect-missing-days', methods=['POST'])
def collect_missing_days():
    """미수집일 일괄 수집"""
    try:
        dashboard = CollectionDashboard()
        missing_days = dashboard.identify_missing_collections(30)
        
        if not missing_days:
            return jsonify({
                'success': True,
                'message': '미수집일이 없습니다',
                'collected_days': []
            })
        
        # 최대 10일로 제한
        limited_days = missing_days[:10]
        
        # 비동기 수집 시작
        success_count = 0
        for date in limited_days:
            if _start_date_collection(date):
                success_count += 1
        
        return jsonify({
            'success': True,
            'message': f'{success_count}/{len(limited_days)}일 수집이 시작되었습니다',
            'collected_days': limited_days[:success_count]
        })
        
    except Exception as e:
        logger.error(f"미수집일 일괄 수집 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@collection_dashboard_bp.route('/api/collection/auto-collect', methods=['POST'])
def toggle_auto_collection():
    """자동 수집 토글"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)
        
        # 자동 수집 설정 저장 (실제로는 설정 파일이나 DB에 저장)
        config_path = "data/auto_collection_config.json"
        
        import os
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump({
                'enabled': enabled,
                'updated_at': datetime.now().isoformat()
            }, f)
        
        return jsonify({
            'success': True,
            'message': f'자동 수집이 {"활성화" if enabled else "비활성화"}되었습니다',
            'enabled': enabled
        })
        
    except Exception as e:
        logger.error(f"자동 수집 설정 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@collection_dashboard_bp.route('/api/collection/data-quality')
def get_data_quality():
    """데이터 품질 분석"""
    try:
        processor = DataProcessor()
        stats = processor.get_processing_statistics()
        
        # 품질 점수 계산
        total_ips = stats.get('total_ips', 0)
        threat_levels = stats.get('threat_levels', {})
        
        quality_score = 0.0
        if total_ips > 0:
            # 위험도 분포에 따른 품질 점수
            critical_count = threat_levels.get('CRITICAL', 0)
            high_count = threat_levels.get('HIGH', 0)
            medium_count = threat_levels.get('MEDIUM', 0)
            
            quality_score = (
                (critical_count * 1.0 + high_count * 0.8 + medium_count * 0.6) / 
                total_ips * 100
            )
        
        return jsonify({
            'success': True,
            'data': {
                'quality_score': round(quality_score, 1),
                'total_ips': total_ips,
                'threat_distribution': threat_levels,
                'country_distribution': stats.get('countries', {}),
                'source_distribution': stats.get('sources', {}),
                'generated_at': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"데이터 품질 분석 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@collection_dashboard_bp.route('/api/collection/deduplication', methods=['POST'])
def run_deduplication():
    """중복 제거 실행"""
    try:
        # 중복 IP 찾기 및 제거
        removed_count = _perform_deduplication()
        
        return jsonify({
            'success': True,
            'message': f'{removed_count}개의 중복 항목이 제거되었습니다',
            'removed_count': removed_count
        })
        
    except Exception as e:
        logger.error(f"중복 제거 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _start_date_collection(target_date: str) -> bool:
    """특정 날짜 수집 시작 (내부 함수)"""
    try:
        # REGTECH 수집기로 해당 날짜 데이터 수집
        collector = RegtechSimpleCollector(
            username='nextrade',  # 환경변수에서 가져와야 함
            password='Sprtmxm1@3'
        )
        
        # 날짜 범위 설정
        start_date = target_date
        end_date = target_date
        
        # 수집 실행
        result = collector.collect_from_web(start_date, end_date)
        
        if result.get('success'):
            # 수집 기록
            dashboard = CollectionDashboard()
            dashboard.record_daily_collection(
                collection_date=target_date,
                source='REGTECH',
                total_collected=result.get('total_collected', 0),
                new_ips=result.get('total_collected', 0),
                status='success'
            )
            
            # 데이터 처리
            processor = DataProcessor()
            processor.process_collected_data()
            
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"날짜별 수집 시작 오류 {target_date}: {e}")
        return False


def _perform_deduplication() -> int:
    """중복 제거 실행 (내부 함수)"""
    try:
        import sqlite3
        
        conn = sqlite3.connect('instance/blacklist.db')
        cursor = conn.cursor()
        
        # 중복 IP 찾기 (같은 IP를 가진 레코드 중 가장 오래된 것만 유지)
        cursor.execute("""
            DELETE FROM blacklist_entries 
            WHERE id NOT IN (
                SELECT MIN(id) 
                FROM blacklist_entries 
                GROUP BY ip_address
            )
        """)
        
        removed_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"중복 제거 완료: {removed_count}개 항목 제거")
        return removed_count
        
    except Exception as e:
        logger.error(f"중복 제거 실행 오류: {e}")
        return 0


@collection_dashboard_bp.route('/api/analytics/threat-intelligence')
def get_threat_intelligence():
    """위협 인텔리전스 보고서"""
    try:
        analytics = AdvancedAnalytics()
        report = analytics.get_threat_intelligence_report()
        
        return jsonify({
            'success': True,
            'data': report
        })
    except Exception as e:
        logger.error(f"위협 인텔리전스 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@collection_dashboard_bp.route('/api/analytics/network-analysis')
def get_network_analysis():
    """네트워크 분석"""
    try:
        analytics = AdvancedAnalytics()
        analysis = analytics.get_network_analysis()
        
        return jsonify({
            'success': True,
            'data': analysis
        })
    except Exception as e:
        logger.error(f"네트워크 분석 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@collection_dashboard_bp.route('/api/analytics/attack-correlations')
def get_attack_correlations():
    """공격 상관관계 분석"""
    try:
        analytics = AdvancedAnalytics()
        correlations = analytics.get_attack_correlation_analysis()
        
        return jsonify({
            'success': True,
            'data': correlations
        })
    except Exception as e:
        logger.error(f"공격 상관관계 분석 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@collection_dashboard_bp.route('/api/analytics/predictions')
def get_predictive_insights():
    """예측 인사이트"""
    try:
        analytics = AdvancedAnalytics()
        predictions = analytics.get_predictive_insights()
        
        return jsonify({
            'success': True,
            'data': predictions
        })
    except Exception as e:
        logger.error(f"예측 인사이트 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@collection_dashboard_bp.route('/api/analytics/comprehensive-report')
def get_comprehensive_report():
    """종합 분석 보고서"""
    try:
        format_type = request.args.get('format', 'json')
        analytics = AdvancedAnalytics()
        report = analytics.generate_threat_report_export(format_type)
        
        return jsonify({
            'success': True,
            'data': report
        })
    except Exception as e:
        logger.error(f"종합 보고서 생성 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@collection_dashboard_bp.route('/analytics')
def analytics_dashboard():
    """고급 분석 대시보드 페이지"""
    return render_template('analytics_dashboard.html')