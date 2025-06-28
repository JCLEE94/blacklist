#!/usr/bin/env python3
"""
작동하는 SECUDIUM 수집기 - POST 로그인과 토큰 사용
"""
import requests
import json
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

BASE_URL = "https://secudium.skinfosec.co.kr"
USERNAME = "nextrade"
PASSWORD = "Sprtmxm1@3"

def collect_secudium_data():
    """SECUDIUM에서 실제 데이터 수집"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest'
    })
    
    print("1. POST로 로그인...")
    
    # POST로 로그인
    login_data = {
        'lang': 'ko',
        'is_otp': 'N',
        'is_expire': 'N',
        'login_name': USERNAME,
        'password': PASSWORD,
        'otp_value': ''
    }
    
    login_resp = session.post(f"{BASE_URL}/isap-api/loginProcess", data=login_data, verify=False)
    print(f"   로그인 응답: {login_resp.status_code}")
    
    if login_resp.status_code == 200:
        try:
            auth_data = login_resp.json()
            if auth_data.get('response', {}).get('error') == False:
                token = auth_data['response']['token']
                print(f"   ✅ 로그인 성공!")
                print(f"   토큰: {token[:50]}...")
                
                # 토큰을 헤더에 추가
                session.headers.update({
                    'Authorization': f'Bearer {token}',
                    'Token': token,
                    'X-Token': token
                })
                
                print("\n2. 블랙리스트 데이터 수집...")
                
                # 다양한 엔드포인트 시도
                endpoints = [
                    '/isap-api/secinfo/list/black_ip',
                    '/isap-api/secinfo/blacklist',
                    '/isap-api/secinfo/data',
                    '/isap-api/data/blacklist',
                    '/isap-api/file/SECINFO/download',
                    '/secinfo/black_ip',
                    '/secinfo/blacklist'
                ]
                
                for endpoint in endpoints:
                    try:
                        resp = session.get(f"{BASE_URL}{endpoint}", verify=False)
                        print(f"\n   {endpoint}: {resp.status_code}")
                        
                        if resp.status_code == 200:
                            content_type = resp.headers.get('Content-Type', '')
                            print(f"      Content-Type: {content_type}")
                            
                            if 'json' in content_type:
                                data = resp.json()
                                print(f"      데이터 타입: {type(data)}")
                                
                                if isinstance(data, list):
                                    print(f"      IP 개수: {len(data)}개")
                                    if len(data) > 0:
                                        print(f"      샘플:")
                                        for item in data[:5]:
                                            print(f"         {item}")
                                        
                                        # 실제 IP 추출
                                        import re
                                        all_text = json.dumps(data)
                                        ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', all_text)
                                        real_ips = [ip for ip in ips if not ip.startswith(('127.', '192.168.', '10.', '172.'))]
                                        
                                        if real_ips:
                                            print(f"\n      🎉 실제 IP {len(set(real_ips))}개 발견!")
                                            print(f"      IP 샘플: {list(set(real_ips))[:10]}")
                                            
                                            # 파일로 저장
                                            with open('secudium_real_ips.txt', 'w') as f:
                                                for ip in sorted(set(real_ips)):
                                                    f.write(f"{ip}\n")
                                            print(f"\n      💾 secudium_real_ips.txt에 저장됨")
                                            
                                            return list(set(real_ips))
                                            
                                elif isinstance(data, dict):
                                    print(f"      키: {list(data.keys())}")
                                    
                                    # dict 내부의 리스트 찾기
                                    for key, value in data.items():
                                        if isinstance(value, list) and len(value) > 0:
                                            print(f"      {key}: {len(value)}개 항목")
                                            
                            else:
                                # HTML이면 파싱
                                if len(resp.text) < 1000:
                                    print(f"      응답: {resp.text}")
                                else:
                                    # IP 패턴 찾기
                                    import re
                                    ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', resp.text)
                                    real_ips = [ip for ip in ips if not ip.startswith(('127.', '192.168.', '10.', '172.'))]
                                    
                                    if real_ips:
                                        print(f"      HTML에서 IP {len(set(real_ips))}개 발견")
                                        print(f"      샘플: {list(set(real_ips))[:5]}")
                                        
                    except Exception as e:
                        print(f"   {endpoint} 오류: {e}")
                
            else:
                print(f"   ❌ 로그인 실패: {auth_data}")
                
        except Exception as e:
            print(f"   로그인 응답 파싱 오류: {e}")
            print(f"   응답: {login_resp.text}")

if __name__ == "__main__":
    collect_secudium_data()