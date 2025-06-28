#!/usr/bin/env python3
"""
SECUDIUM 강제 로그인 후 데이터 수집
"""
import requests
import json
import re
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

BASE_URL = "https://secudium.skinfosec.co.kr"
USERNAME = "nextrade"
PASSWORD = "Sprtmxm1@3"

def force_login_and_collect():
    """강제 로그인 후 데이터 수집"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest'
    })
    
    print("1. 첫 번째 로그인 시도...")
    
    # 첫 번째 로그인 시도
    login_data = {
        'lang': 'ko',
        'is_otp': 'N',
        'is_expire': 'N',
        'login_name': USERNAME,
        'password': PASSWORD,
        'otp_value': ''
    }
    
    first_resp = session.post(f"{BASE_URL}/isap-api/loginProcess", data=login_data, verify=False)
    print(f"   응답: {first_resp.status_code}")
    
    if first_resp.status_code == 200:
        try:
            auth_data = first_resp.json()
            
            if auth_data.get('response', {}).get('code') == 'already.login':
                print("   기존 세션 감지됨")
                print("\n2. 강제 로그인 시도...")
                
                # 강제 로그인 - is_expire를 Y로 설정
                force_login_data = {
                    'lang': 'ko',
                    'is_otp': 'N',
                    'is_expire': 'Y',  # 기존 세션 종료
                    'login_name': USERNAME,
                    'password': PASSWORD,
                    'otp_value': ''
                }
                
                second_resp = session.post(f"{BASE_URL}/isap-api/loginProcess", data=force_login_data, verify=False)
                print(f"   강제 로그인 응답: {second_resp.status_code}")
                
                if second_resp.status_code == 200:
                    auth_data = second_resp.json()
                    
            # 로그인 성공 확인
            if auth_data.get('response', {}).get('error') == False:
                token = auth_data['response']['token']
                print(f"\n   ✅ 로그인 성공!")
                print(f"   토큰: {token[:50]}...")
                print(f"   권한: {auth_data['response'].get('role', [])}")
                
                # 토큰을 헤더에 추가
                session.headers.update({
                    'Authorization': f'Bearer {token}',
                    'Token': token,
                    'X-Token': token,
                    'X-AUTH-TOKEN': token
                })
                
                print("\n3. 블랙리스트 데이터 수집...")
                
                # myinfo로 인증 확인
                myinfo_resp = session.get(f"{BASE_URL}/isap-api/myinfo", verify=False)
                print(f"\n   내 정보 확인: {myinfo_resp.status_code}")
                if myinfo_resp.status_code == 200:
                    print(f"   ✅ 인증 확인됨")
                
                # 블랙리스트 엔드포인트
                endpoints = [
                    '/isap-api/secinfo/list/black_ip',
                    '/isap-api/secinfo/preview/black_ip',
                    '/isap-api/file/SECINFO/download?file_name=black_ip',
                    '/secinfo/black_ip',
                    '/isap-api/secinfo/data',
                    '/isap-api/secinfo/blacklist'
                ]
                
                collected_ips = set()
                
                for endpoint in endpoints:
                    try:
                        print(f"\n   시도: {endpoint}")
                        resp = session.get(f"{BASE_URL}{endpoint}", verify=False, timeout=30)
                        print(f"      응답: {resp.status_code}")
                        
                        if resp.status_code == 200:
                            content_type = resp.headers.get('Content-Type', '')
                            print(f"      타입: {content_type}")
                            
                            # JSON 응답
                            if 'json' in content_type:
                                try:
                                    data = resp.json()
                                    
                                    # 데이터 구조 분석
                                    if isinstance(data, dict):
                                        print(f"      구조: {list(data.keys())}")
                                        
                                        # response 필드 확인
                                        if 'response' in data:
                                            response = data['response']
                                            if isinstance(response, list):
                                                print(f"      데이터: {len(response)}개")
                                                for item in response[:3]:
                                                    print(f"         {item}")
                                                    
                                                # IP 추출
                                                for item in response:
                                                    if isinstance(item, dict):
                                                        # IP 필드 찾기
                                                        for key, value in item.items():
                                                            if isinstance(value, str) and re.match(r'^\d+\.\d+\.\d+\.\d+$', value):
                                                                collected_ips.add(value)
                                                    elif isinstance(item, str) and re.match(r'^\d+\.\d+\.\d+\.\d+$', item):
                                                        collected_ips.add(item)
                                        
                                        # data 필드 확인
                                        elif 'data' in data:
                                            data_field = data['data']
                                            if isinstance(data_field, list):
                                                print(f"      데이터: {len(data_field)}개")
                                                
                                    elif isinstance(data, list):
                                        print(f"      리스트: {len(data)}개")
                                        for item in data[:3]:
                                            print(f"         {item}")
                                            
                                except json.JSONDecodeError:
                                    print(f"      JSON 파싱 실패")
                            
                            # 텍스트/HTML 응답에서 IP 추출
                            else:
                                text = resp.text
                                if len(text) < 500:
                                    print(f"      내용: {text}")
                                
                                # IP 패턴 찾기
                                ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', text)
                                real_ips = [ip for ip in ips if not ip.startswith(('127.', '192.168.', '10.', '172.'))]
                                
                                if real_ips:
                                    collected_ips.update(real_ips)
                                    print(f"      IP 발견: {len(real_ips)}개")
                                    print(f"      샘플: {real_ips[:5]}")
                                    
                    except Exception as e:
                        print(f"      오류: {e}")
                
                # 결과 출력
                if collected_ips:
                    print(f"\n\n🎉 총 {len(collected_ips)}개의 실제 IP 수집 성공!")
                    print(f"샘플 IP:")
                    for ip in sorted(collected_ips)[:20]:
                        print(f"   {ip}")
                    
                    # 파일로 저장
                    with open('secudium_collected_ips.txt', 'w') as f:
                        for ip in sorted(collected_ips):
                            f.write(f"{ip}\n")
                    print(f"\n💾 secudium_collected_ips.txt에 저장됨")
                else:
                    print(f"\n❌ IP를 찾지 못했습니다.")
                    
            else:
                print(f"   ❌ 로그인 실패: {auth_data.get('response', {}).get('message', 'Unknown error')}")
                
        except Exception as e:
            print(f"   오류: {e}")
            print(f"   응답: {first_resp.text[:500]}")

if __name__ == "__main__":
    force_login_and_collect()