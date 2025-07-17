#!/usr/bin/env python3
"""
REGTECH AJAX 기반 데이터 수집 테스트
웹 페이지가 AJAX로 데이터를 로드하는 경우를 처리
"""

import requests
import json
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_ajax_collection():
    """AJAX 기반 데이터 수집 테스트"""
    
    # 세션 생성
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'X-Requested-With': 'XMLHttpRequest'
    })
    
    # 1. 로그인
    logger.info("=== 로그인 시도 ===")
    login_url = "https://regtech.fsec.or.kr/fcti/login/loginUser"
    login_data = {
        'username': 'nextrade',
        'password': 'Sprtmxm1@3',
        'login_error': '',
        'txId': '',
        'token': '',
        'memberId': '',
        'smsTimeExcess': 'N'
    }
    
    login_resp = session.post(login_url, data=login_data, allow_redirects=False)
    logger.info(f"로그인 응답: {login_resp.status_code}")
    
    # 리다이렉트 처리
    if login_resp.status_code == 302:
        redirect_url = login_resp.headers.get('Location', '')
        if not redirect_url.startswith('http'):
            redirect_url = f"https://regtech.fsec.or.kr{redirect_url}"
        
        # 메인 페이지로 이동
        main_resp = session.get("https://regtech.fsec.or.kr/main/main")
        logger.info(f"메인 페이지 응답: {main_resp.status_code}")
    
    # 2. AJAX로 목록 데이터 가져오기
    logger.info("\n=== AJAX 목록 요청 ===")
    
    # 날짜 설정
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    # AJAX 요청 URL (추정)
    ajax_urls = [
        "https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryListData",
        "https://regtech.fsec.or.kr/fcti/securityAdvisory/getAdvisoryList",
        "https://regtech.fsec.or.kr/fcti/securityAdvisory/list.ajax",
        "https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList.do"
    ]
    
    for ajax_url in ajax_urls:
        logger.info(f"\n시도: {ajax_url}")
        
        params = {
            'startDate': start_date.strftime('%Y%m%d'),
            'endDate': end_date.strftime('%Y%m%d'),
            'blockRule': '',
            'blockTarget': '',
            'page': '1',
            'rows': '1000'  # 많은 데이터 요청
        }
        
        try:
            resp = session.get(ajax_url, params=params)
            logger.info(f"응답 코드: {resp.status_code}")
            logger.info(f"Content-Type: {resp.headers.get('Content-Type')}")
            
            if resp.status_code == 200:
                # JSON 응답 시도
                if 'application/json' in resp.headers.get('Content-Type', ''):
                    try:
                        data = resp.json()
                        logger.info(f"JSON 데이터 수신: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                        return data
                    except:
                        pass
                
                # HTML 응답인 경우
                if len(resp.text) < 1000:
                    logger.info(f"응답 내용: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"요청 실패: {e}")
    
    # 3. POST 방식 시도
    logger.info("\n=== POST 방식 AJAX 시도 ===")
    for ajax_url in ajax_urls:
        logger.info(f"\nPOST 시도: {ajax_url}")
        
        data = {
            'startDate': start_date.strftime('%Y%m%d'),
            'endDate': end_date.strftime('%Y%m%d'),
            'blockRule': '',
            'blockTarget': '',
            'page': '1',
            'rows': '1000'
        }
        
        try:
            resp = session.post(ajax_url, data=data)
            logger.info(f"응답 코드: {resp.status_code}")
            
            if resp.status_code == 200 and len(resp.text) < 10000:
                logger.info(f"응답 샘플: {resp.text[:300]}")
        except Exception as e:
            logger.error(f"POST 요청 실패: {e}")
    
    # 4. 직접 페이지 파싱 시도
    logger.info("\n=== 페이지 직접 파싱 ===")
    page_url = "https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList"
    page_resp = session.get(page_url)
    
    if page_resp.status_code == 200:
        # JavaScript 변수에서 데이터 찾기
        import re
        
        # var data = [...] 패턴 찾기
        data_pattern = re.compile(r'var\s+(?:data|list|items)\s*=\s*(\[.*?\]);', re.DOTALL)
        matches = data_pattern.findall(page_resp.text)
        
        if matches:
            for match in matches:
                try:
                    data = json.loads(match)
                    logger.info(f"JavaScript 데이터 발견: {len(data)}개 항목")
                    return data
                except:
                    pass
    
    return None

if __name__ == "__main__":
    result = test_ajax_collection()
    
    if result:
        print(f"\n✅ 데이터 수집 성공!")
        if isinstance(result, list):
            print(f"총 {len(result)}개 항목")
        elif isinstance(result, dict):
            print(f"데이터 구조: {list(result.keys())}")
    else:
        print("\n❌ 데이터 수집 실패")