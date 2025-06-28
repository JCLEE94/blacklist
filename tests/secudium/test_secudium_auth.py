#!/usr/bin/env python3
"""
SECUDIUM 인증 및 데이터 수집 테스트
실제 웹사이트 동작을 분석하여 정확한 수집 방법 파악
"""
import requests
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# SECUDIUM 설정
BASE_URL = "https://www.boho.or.kr"
USERNAME = "nextrade"
PASSWORD = "Sprtmxm1@3"

def test_secudium_auth():
    """SECUDIUM 인증 및 데이터 수집 테스트"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })
    
    print("1. 메인 페이지 접속...")
    try:
        # 메인 페이지 접속
        main_resp = session.get(BASE_URL)
        print(f"   상태 코드: {main_resp.status_code}")
        print(f"   쿠키: {dict(session.cookies)}")
    except Exception as e:
        print(f"   메인 페이지 접속 실패: {e}")
        return
    
    print("\n2. 로그인 시도...")
    # 로그인 데이터
    login_data = {
        'lang': 'ko',
        'is_otp': 'N',
        'login_name': USERNAME,
        'password': PASSWORD,
        'otp_value': ''
    }
    
    # 로그인 요청
    login_url = f"{BASE_URL}/isap-api/loginProcess"
    
    session.headers.update({
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': BASE_URL,
        'Referer': f"{BASE_URL}/"
    })
    
    try:
        login_resp = session.post(login_url, data=login_data)
        print(f"   상태 코드: {login_resp.status_code}")
        print(f"   응답 헤더: {dict(login_resp.headers)}")
        print(f"   쿠키: {dict(session.cookies)}")
        
        if login_resp.text:
            try:
                resp_json = login_resp.json()
                print(f"   응답 JSON: {json.dumps(resp_json, indent=2, ensure_ascii=False)}")
            except:
                print(f"   응답 텍스트: {login_resp.text[:500]}")
    except Exception as e:
        print(f"   로그인 요청 실패: {e}")
        return
    
    print("\n3. 블랙리스트 데이터 접근 시도...")
    # 여러 가능한 엔드포인트 시도
    endpoints = [
        "/isap-api/secinfo/list/ictiboard",
        "/data/json/internet_activity.do", 
        "/data/json/blacklistInfo.do",
        "/data/json/cyber_black_ip.do"
    ]
    
    for endpoint in endpoints:
        print(f"\n   엔드포인트 시도: {endpoint}")
        try:
            # JSON 요청용 헤더
            session.headers.update({
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': f"{BASE_URL}/"
            })
            
            # 파라미터 설정
            params = {
                'sdate': '',
                'edate': '',
                'count': '10',
                'page': '1'
            }
            
            resp = session.get(f"{BASE_URL}{endpoint}", params=params)
            print(f"      상태 코드: {resp.status_code}")
            
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    print(f"      응답 타입: {type(data)}")
                    if isinstance(data, dict):
                        print(f"      응답 키: {list(data.keys())}")
                        if 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                            print(f"      데이터 개수: {len(data['data'])}")
                            print(f"      첫 번째 항목: {json.dumps(data['data'][0], indent=2, ensure_ascii=False)}")
                    elif isinstance(data, list) and len(data) > 0:
                        print(f"      데이터 개수: {len(data)}")
                        print(f"      첫 번째 항목: {json.dumps(data[0], indent=2, ensure_ascii=False)}")
                except:
                    print(f"      응답: {resp.text[:200]}...")
            else:
                print(f"      실패: {resp.status_code}")
        except Exception as e:
            print(f"      오류: {e}")
    
    print("\n4. 웹 페이지에서 데이터 확인...")
    # 웹 페이지 접근
    web_urls = [
        "/main/security_info.do",
        "/kor/data/secNotice.do",
        "/data/secNoticeView.do"
    ]
    
    for url in web_urls:
        print(f"\n   페이지 시도: {url}")
        try:
            resp = session.get(f"{BASE_URL}{url}")
            print(f"      상태 코드: {resp.status_code}")
            if resp.status_code == 200:
                # HTML에서 데이터 테이블이나 IP 정보 찾기
                if "black" in resp.text.lower() or "ip" in resp.text.lower():
                    print("      블랙리스트 또는 IP 관련 내용 발견")
                if "tbody" in resp.text or "table" in resp.text:
                    print("      테이블 구조 발견")
        except Exception as e:
            print(f"      오류: {e}")

if __name__ == "__main__":
    test_secudium_auth()