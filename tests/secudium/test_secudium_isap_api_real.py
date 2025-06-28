#!/usr/bin/env python3
"""
실제 SECUDIUM ISAP API 테스트
JavaScript에서 발견한 api_host 활용
"""
import requests
import json
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

BASE_URL = "https://secudium.skinfosec.co.kr"
API_HOST = "https://secudium.skinfosec.co.kr/isap-api"
USERNAME = "nextrade"
PASSWORD = "Sprtmxm1@3"

def test_isap_api_real():
    """실제 ISAP API 테스트"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest'
    })
    
    print("1. 로그인...")
    
    # 메인 페이지에서 세션 쿠키 받기
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
    print(f"   쿠키: {dict(session.cookies)}")
    
    print(f"\n2. ISAP API 테스트 ({API_HOST})...")
    
    # ISAP API 엔드포인트들
    api_endpoints = [
        # 기본 정보
        '',
        '/status',
        '/info',
        '/version',
        
        # 사용자 정보
        '/user/info',
        '/user/profile',
        '/myinfo',
        
        # 보안 정보
        '/secinfo',
        '/secinfo/list',
        '/secinfo/blacklist',
        '/secinfo/data',
        
        # 데이터
        '/data',
        '/data/list',
        '/data/blacklist',
        '/data/export',
        
        # 블랙리스트
        '/blacklist',
        '/blacklist/list',
        '/blacklist/data',
        '/blacklist/export',
        
        # 위협 정보
        '/threat',
        '/threat/list',
        '/threat/data',
        
        # 리포트
        '/report',
        '/report/list',
        '/report/data',
        
        # 익스포트
        '/export',
        '/export/blacklist',
        '/export/data'
    ]
    
    successful_endpoints = []
    
    for endpoint in api_endpoints:
        url = f"{API_HOST}{endpoint}"
        try:
            # GET 요청
            resp = session.get(url, verify=False, timeout=10)
            print(f"\n   GET {endpoint}: {resp.status_code}")
            
            if resp.status_code == 200:
                successful_endpoints.append(endpoint)
                content_type = resp.headers.get('Content-Type', '')
                print(f"      Content-Type: {content_type}")
                
                if 'json' in content_type:
                    try:
                        data = resp.json()
                        print(f"      JSON: {type(data)}")
                        
                        if isinstance(data, list):
                            print(f"      배열 길이: {len(data)}")
                            if len(data) > 0:
                                print(f"      첫 번째 항목: {json.dumps(data[0], indent=2, ensure_ascii=False)}")
                                
                                # IP 패턴 체크
                                item_str = str(data[0])
                                import re
                                ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', item_str)
                                if ips:
                                    print(f"      → IP 발견: {ips}")
                                    
                        elif isinstance(data, dict):
                            print(f"      딕셔너리 키: {list(data.keys())}")
                            
                            # 데이터 필드 확인
                            for key, value in data.items():
                                if isinstance(value, list):
                                    print(f"      {key}: 배열 ({len(value)}개)")
                                    if len(value) > 0:
                                        print(f"         첫 번째: {value[0]}")
                                elif isinstance(value, str) and len(value) < 100:
                                    print(f"      {key}: {value}")
                                    
                            # 전체 데이터에서 IP 찾기
                            data_str = json.dumps(data)
                            import re
                            ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', data_str)
                            real_ips = [ip for ip in ips if not ip.startswith(('127.', '192.168.', '10.', '172.'))]
                            if real_ips:
                                print(f"      → 실제 IP 발견: {len(real_ips)}개")
                                print(f"      → 샘플: {real_ips[:5]}")
                                
                    except ValueError as e:
                        print(f"      JSON 파싱 실패: {e}")
                        print(f"      응답 길이: {len(resp.text)}")
                        if len(resp.text) < 500:
                            print(f"      응답: {resp.text}")
                else:
                    print(f"      HTML 응답: {len(resp.text)} bytes")
                    if len(resp.text) < 500:
                        print(f"      내용: {resp.text}")
            
            elif resp.status_code == 401:
                print(f"      인증 필요")
            elif resp.status_code == 403:
                print(f"      접근 금지")
            elif resp.status_code == 404:
                print(f"      없음")
            else:
                print(f"      기타: {resp.status_code}")
                if len(resp.text) < 200:
                    print(f"      응답: {resp.text}")
            
            # POST도 시도해보기 (성공한 엔드포인트만)
            if resp.status_code == 200:
                try:
                    post_resp = session.post(url, json={}, verify=False, timeout=10)
                    if post_resp.status_code != resp.status_code:
                        print(f"      POST {endpoint}: {post_resp.status_code}")
                        if post_resp.status_code == 200:
                            try:
                                post_data = post_resp.json()
                                print(f"         POST JSON: {type(post_data)}")
                            except:
                                print(f"         POST 응답: {len(post_resp.text)} bytes")
                except:
                    pass
                    
        except Exception as e:
            print(f"   {endpoint} 오류: {e}")
    
    print(f"\n3. 성공한 엔드포인트 요약:")
    for endpoint in successful_endpoints:
        print(f"   ✅ {endpoint}")
    
    # 성공한 엔드포인트가 있으면 추가 분석
    if successful_endpoints:
        print(f"\n4. 상세 분석...")
        
        for endpoint in successful_endpoints[:3]:  # 처음 3개만
            url = f"{API_HOST}{endpoint}"
            try:
                resp = session.get(url, verify=False)
                print(f"\n   {endpoint} 상세:")
                
                if 'json' in resp.headers.get('Content-Type', ''):
                    data = resp.json()
                    print(f"      전체 JSON: {json.dumps(data, indent=2, ensure_ascii=False)}")
                else:
                    print(f"      전체 응답: {resp.text}")
                    
            except Exception as e:
                print(f"   {endpoint} 상세 분석 오류: {e}")

if __name__ == "__main__":
    test_isap_api_real()