#!/usr/bin/env python3
"""
SECUDIUM 데이터 상세 확인
"""
import requests
import json
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

BASE_URL = "https://secudium.skinfosec.co.kr"
USERNAME = "nextrade"
PASSWORD = "Sprtmxm1@3"

# 강제 로그인
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest'
})

print("1. 강제 로그인...")
login_data = {
    'lang': 'ko',
    'is_otp': 'N',
    'is_expire': 'Y',  # 강제 로그인
    'login_name': USERNAME,
    'password': PASSWORD,
    'otp_value': ''
}

resp = session.post(f"{BASE_URL}/isap-api/loginProcess", data=login_data, verify=False)
auth_data = resp.json()

if auth_data.get('response', {}).get('error') == False:
    token = auth_data['response']['token']
    print(f"   ✅ 로그인 성공")
    
    session.headers.update({
        'Authorization': f'Bearer {token}',
        'X-AUTH-TOKEN': token
    })
    
    print("\n2. black_ip 리스트 상세 확인...")
    
    # 리스트 API 호출
    list_resp = session.get(f"{BASE_URL}/isap-api/secinfo/list/black_ip", verify=False)
    if list_resp.status_code == 200:
        data = list_resp.json()
        print(f"   전체 응답:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # 데이터가 있으면 상세 조회
        if data.get('rows'):
            print(f"\n   데이터 {len(data['rows'])}개 발견!")
            for row in data['rows'][:5]:
                print(f"   - {row}")
        else:
            print(f"\n   rows가 비어있음. 다른 필드 확인...")
            
            # 페이징 파라미터 추가
            params = {
                'page': 1,
                'rows': 100,
                'sidx': 'idx',
                'sord': 'desc'
            }
            
            print(f"\n3. 페이징 파라미터로 재시도...")
            paged_resp = session.get(f"{BASE_URL}/isap-api/secinfo/list/black_ip", 
                                   params=params, verify=False)
            if paged_resp.status_code == 200:
                paged_data = paged_resp.json()
                print(json.dumps(paged_data, indent=2, ensure_ascii=False))
    
    # 특정 ID로 직접 조회
    print(f"\n4. 특정 ID 조회 시도...")
    for idx in range(20000, 20010):  # 샘플 ID 범위
        view_resp = session.get(f"{BASE_URL}/isap-api/secinfo/view/black_ip/{idx}", verify=False)
        if view_resp.status_code == 200:
            print(f"   ID {idx}: 성공")
            view_data = view_resp.json()
            print(json.dumps(view_data, indent=2, ensure_ascii=False))
            break