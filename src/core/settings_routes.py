#!/usr/bin/env python3
"""
설정 관리 API 엔드포인트
"""
from flask import Blueprint, request, jsonify, render_template
import logging
import jwt
from datetime import datetime
import os
import json
from pathlib import Path

from src.config.settings import settings
from .container import get_container

logger = logging.getLogger(__name__)

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/settings')
def settings_page():
    """설정 페이지 렌더링"""
    container = get_container()
    
    # 현재 설정 값 가져오기
    context = {
        'regtech_username': settings.regtech_username,
        'secudium_username': settings.secudium_username,
        'auto_collection': getattr(settings, 'auto_collection', True),
        'collection_interval': getattr(settings, 'collection_interval', 6),
        'data_retention': getattr(settings, 'data_retention', 90),
        'server_uptime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'db_size': '계산 중...',
        'cache_status': '활성',
        'active_ips': '계산 중...'
    }
    
    return render_template('settings.html', **context)


@settings_bp.route('/api/settings/regtech/auth', methods=['POST'])
def update_regtech_auth():
    """REGTECH 인증 정보 업데이트"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': '사용자명과 비밀번호가 필요합니다.'
            }), 400
        
        # 자동 로그인 모듈 가져오기
        from .regtech_auto_login import get_regtech_auth
        auth = get_regtech_auth()
        
        # 인증 정보 업데이트 및 테스트
        if auth.update_credentials(username, password):
            # 토큰 정보 가져오기
            token = auth._current_token
            
            # JWT 디코드
            jwt_token = token.replace("Bearer", "").strip()
            payload = jwt.decode(jwt_token, options={"verify_signature": False})
            
            return jsonify({
                'success': True,
                'token': token,
                'expires_at': payload.get('exp', 0),
                'username': payload.get('username', username),
                'message': 'REGTECH 인증 성공'
            })
        else:
            return jsonify({
                'success': False,
                'error': '인증 실패. 사용자명과 비밀번호를 확인하세요.'
            })
            
    except Exception as e:
        logger.error(f"REGTECH 인증 업데이트 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@settings_bp.route('/api/settings/regtech/refresh-token', methods=['POST'])
def refresh_regtech_token():
    """REGTECH Bearer Token 갱신"""
    try:
        from .regtech_auto_login import get_regtech_auth
        auth = get_regtech_auth()
        
        # 강제로 새 토큰 발급
        auth._current_token = None  # 현재 토큰 무효화
        token = auth.get_valid_token()
        
        if token:
            # JWT 디코드
            jwt_token = token.replace("Bearer", "").strip()
            payload = jwt.decode(jwt_token, options={"verify_signature": False})
            
            return jsonify({
                'success': True,
                'token': token,
                'expires_at': payload.get('exp', 0),
                'username': payload.get('username', 'unknown'),
                'message': 'Bearer Token이 갱신되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'error': '토큰 갱신 실패. 인증 정보를 확인하세요.'
            })
            
    except Exception as e:
        logger.error(f"토큰 갱신 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@settings_bp.route('/api/settings/regtech/token-status')
def regtech_token_status():
    """현재 REGTECH 토큰 상태 확인"""
    try:
        from .regtech_auto_login import get_regtech_auth
        auth = get_regtech_auth()
        
        # 파일에서 토큰 로드
        token = auth._load_token_from_file()
        
        if token:
            is_valid = auth._is_token_valid(token)
            
            # JWT 디코드
            jwt_token = token.replace("Bearer", "").strip()
            payload = jwt.decode(jwt_token, options={"verify_signature": False})
            
            return jsonify({
                'has_token': True,
                'is_valid': is_valid,
                'token': token if is_valid else None,
                'expires_at': payload.get('exp', 0),
                'username': payload.get('username', 'unknown')
            })
        else:
            return jsonify({
                'has_token': False,
                'is_valid': False
            })
            
    except Exception as e:
        logger.error(f"토큰 상태 확인 오류: {e}")
        return jsonify({
            'has_token': False,
            'is_valid': False,
            'error': str(e)
        })


@settings_bp.route('/api/collection/regtech/test', methods=['POST'])
def test_regtech_collection():
    """REGTECH 수집 테스트"""
    try:
        from .regtech_auto_login import get_regtech_auth
        import requests
        from datetime import datetime, timedelta
        
        auth = get_regtech_auth()
        token = auth.get_valid_token()
        
        if not token:
            return jsonify({
                'success': False,
                'error': '유효한 토큰이 없습니다.'
            })
        
        # 간단한 수집 테스트
        session = requests.Session()
        session.cookies.set('regtech-va', token, domain='regtech.fsec.or.kr', path='/')
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        
        # Advisory 페이지 접근 테스트
        resp = session.get(
            'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList',
            timeout=30
        )
        
        if resp.status_code == 200 and 'login' not in resp.url:
            # 페이지에서 총 건수 추출
            import re
            match = re.search(r'총\s*<em[^>]*>([0-9,]+)</em>', resp.text)
            ip_count = match.group(1) if match else '알 수 없음'
            
            return jsonify({
                'success': True,
                'ip_count': ip_count,
                'message': f'REGTECH 접근 성공. 총 {ip_count}개 IP 확인'
            })
        else:
            return jsonify({
                'success': False,
                'error': '데이터 접근 실패'
            })
            
    except Exception as e:
        logger.error(f"수집 테스트 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@settings_bp.route('/api/settings/secudium/auth', methods=['POST'])
def update_secudium_auth():
    """SECUDIUM 인증 정보 업데이트"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': '사용자명과 비밀번호가 필요합니다.'
            }), 400
        
        # 설정 업데이트
        settings.secudium_username = username
        settings.secudium_password = password
        
        # 설정 파일에 저장
        config_file = Path(settings.data_dir) / ".secudium_credentials.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        config_data = {
            'username': username,
            'password': password,
            'updated_at': datetime.now().isoformat()
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        os.chmod(config_file, 0o600)
        
        return jsonify({
            'success': True,
            'message': 'SECUDIUM 인증 정보가 저장되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"SECUDIUM 인증 업데이트 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500