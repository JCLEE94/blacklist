#!/usr/bin/env python3
"""
SECUDIUM ISAP API 탐색
"""
import requests
import json
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

BASE_URL = "https://secudium.skinfosec.co.kr"
USERNAME = "nextrade"
PASSWORD = "Sprtmxm1@3"

def test_secudium_isap_api():
    """SECUDIUM ISAP API 테스트"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest'
    })
    
    print("1. 로그인...")
    try:
        # 메인 페이지
        session.get(BASE_URL, verify=False)
        
        # 로그인
        login_data = {
            'lang': 'ko',
            'is_otp': 'N',
            'is_expire': 'N', 
            'login_name': USERNAME,
            'password': PASSWORD,
            'otp_value': ''
        }
        
        login_resp = session.get(f"{BASE_URL}/login", params=login_data, verify=False)
        print(f"   로그인: {login_resp.status_code}")
        
    except Exception as e:
        print(f"   로그인 실패: {e}")
        return
    
    print("\n2. ISAP API 탐색...")
    
    # 가능한 ISAP API 엔드포인트들
    isap_endpoints = [
        '/isap-api',
        '/isap-api/',
        '/isap-api/status',
        '/isap-api/info',
        '/isap-api/dashboard',
        '/isap-api/blacklist',
        '/isap-api/blacklist/list',
        '/isap-api/threats',
        '/isap-api/ips',
        '/isap-api/scan',
        '/isap-api/scan/list',
        '/isap-api/security',
        '/isap-api/security/blacklist',
        '/isap-api/data/blacklist',
        '/isap-api/secinfo/list',
        '/isap-api/secinfo/blacklist'
    ]
    
    for endpoint in isap_endpoints:
        print(f"\n   엔드포인트: {endpoint}")
        try:
            resp = session.get(f"{BASE_URL}{endpoint}", verify=False)
            print(f"      상태: {resp.status_code}")
            
            if resp.status_code == 200:
                content_type = resp.headers.get('Content-Type', '')
                print(f"      Content-Type: {content_type}")
                
                if 'json' in content_type.lower():
                    try:
                        data = resp.json()
                        print(f"      JSON 타입: {type(data)}")
                        
                        if isinstance(data, list):
                            print(f"      배열 길이: {len(data)}")
                            if len(data) > 0:
                                print(f"      첫 번째 항목: {json.dumps(data[0], indent=2, ensure_ascii=False)}")
                        elif isinstance(data, dict):
                            print(f"      딕셔너리 키: {list(data.keys())}")
                            for key, value in data.items():
                                if isinstance(value, list):
                                    print(f"      {key}: 배열 ({len(value)}개)")
                                elif isinstance(value, dict):
                                    print(f"      {key}: 객체 ({list(value.keys())})")
                                else:
                                    print(f"      {key}: {value}")
                    except:
                        print(f"      JSON 파싱 실패: {resp.text[:200]}...")
                else:
                    # HTML 응답
                    text_content = resp.text
                    print(f"      HTML 길이: {len(text_content)}")
                    
                    if 'ip' in text_content.lower():
                        import re
                        ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
                        ips = ip_pattern.findall(text_content)
                        if ips:
                            unique_ips = list(set(ips))
                            print(f"      IP 발견: {len(unique_ips)}개")
                            print(f"      샘플: {unique_ips[:5]}")
            
            elif resp.status_code == 401:
                print("      ❌ 인증 필요")
            elif resp.status_code == 403:
                print("      ❌ 접근 금지")
            elif resp.status_code == 404:
                print("      ❌ 없음")
            else:
                print(f"      응답: {resp.text[:100]}...")
                
        except Exception as e:
            print(f"      오류: {e}")
    
    print("\n3. POST 방식으로 데이터 요청 시도...")
    
    # POST로 데이터 요청
    post_endpoints = [
        '/isap-api/blacklist',
        '/isap-api/scan/list',
        '/isap-api/secinfo/list'
    ]
    
    for endpoint in post_endpoints:
        print(f"\n   POST {endpoint}")
        try:
            # 다양한 POST 데이터 형식 시도
            post_data_variants = [
                {},  # 빈 데이터
                {'limit': 100},  # 제한
                {'page': 1, 'size': 100},  # 페이징
                {'type': 'blacklist'},  # 타입
                {'format': 'json'},  # 포맷
            ]
            
            for post_data in post_data_variants:
                resp = session.post(f"{BASE_URL}{endpoint}", data=post_data, verify=False)
                
                if resp.status_code == 200:
                    print(f"      POST 성공 (데이터: {post_data})")
                    
                    try:
                        json_data = resp.json()
                        print(f"      응답: {json.dumps(json_data, indent=2, ensure_ascii=False)}")
                        
                        # 성공하면 더 자세히 분석
                        if isinstance(json_data, dict) and 'data' in json_data:
                            data_list = json_data['data']
                            if isinstance(data_list, list) and len(data_list) > 0:
                                print(f"      ✅ 데이터 발견: {len(data_list)}개 항목")
                                return json_data
                                
                    except:
                        print(f"      HTML 응답: {len(resp.text)} bytes")
                        if 'ip' in resp.text.lower():
                            print("      IP 관련 내용 포함")
                    
                    break  # 성공하면 다른 데이터 형식 시도 안함
                elif resp.status_code != 404:
                    print(f"      상태: {resp.status_code}")
                    
        except Exception as e:
            print(f"      오류: {e}")

if __name__ == "__main__":
    test_secudium_isap_api()