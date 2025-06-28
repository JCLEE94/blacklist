#!/usr/bin/env python3
"""
SECUDIUM 다운로드 메커니즘 디버깅
"""
import requests
import json
import re
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

BASE_URL = "https://secudium.skinfosec.co.kr"
USERNAME = "nextrade"
PASSWORD = "Sprtmxm1@3"

# 로그인
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': '*/*',
    'X-Requested-With': 'XMLHttpRequest'
})

print("1. 로그인...")
login_data = {
    'lang': 'ko',
    'is_otp': 'N',
    'is_expire': 'Y',
    'login_name': USERNAME,
    'password': PASSWORD,
    'otp_value': ''
}

login_resp = session.post(f"{BASE_URL}/isap-api/loginProcess", data=login_data, verify=False)
auth_data = login_resp.json()

if auth_data.get('response', {}).get('error') == False:
    token = auth_data['response']['token']
    print(f"   ✅ 로그인 성공")
    
    session.headers.update({
        'Authorization': f'Bearer {token}',
        'X-AUTH-TOKEN': token
    })
    
    print("\n2. 다운로드 메커니즘 분석...")
    
    # 게시판에서 첫 번째 항목 가져오기
    list_resp = session.get(f"{BASE_URL}/isap-api/secinfo/list/black_ip", verify=False)
    data = list_resp.json()
    
    if data.get('rows'):
        first_row = data['rows'][0]
        download_html = first_row['data'][5]
        
        print(f"   다운로드 HTML: {download_html}")
        
        # download 함수 파라미터 추출
        match = re.search(r'download\s*\(\s*["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']', download_html)
        if match:
            file_id = match.group(1)
            file_name = match.group(2)
            
            print(f"\n   파일 ID: {file_id}")
            print(f"   파일명: {file_name}")
            
            print("\n3. 다양한 다운로드 방법 시도...")
            
            # 방법 1: 직접 경로
            urls = [
                f"/isap-api/file/SECINFO/download/{file_id}",
                f"/isap-api/file/SECINFO/download?file_id={file_id}",
                f"/isap-api/file/SECINFO/download?file_name={file_name}",
                f"/isap-api/file/SECINFO/download?id={file_id}&name={file_name}",
                f"/isap-api/file/download/{file_id}",
                f"/file/SECINFO/download/{file_id}",
                f"/download/{file_id}",
                f"/isap-api/secinfo/download/{file_id}"
            ]
            
            for url in urls:
                try:
                    print(f"\n   시도: {url}")
                    resp = session.get(f"{BASE_URL}{url}", verify=False)
                    print(f"      상태: {resp.status_code}")
                    print(f"      크기: {len(resp.content)} bytes")
                    print(f"      타입: {resp.headers.get('Content-Type', 'Unknown')}")
                    
                    # 실제 파일인지 확인
                    if resp.status_code == 200 and len(resp.content) > 5000:
                        # 엑셀 파일 시그니처 확인
                        if resp.content[:4] == b'PK\x03\x04':  # XLSX
                            print(f"      ✅ XLSX 파일 감지!")
                            with open('secudium_download.xlsx', 'wb') as f:
                                f.write(resp.content)
                            print(f"      💾 secudium_download.xlsx로 저장")
                            break
                        elif resp.content[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':  # XLS
                            print(f"      ✅ XLS 파일 감지!")
                            with open('secudium_download.xls', 'wb') as f:
                                f.write(resp.content)
                            print(f"      💾 secudium_download.xls로 저장")
                            break
                    
                    if resp.status_code == 200 and len(resp.content) < 1000:
                        print(f"      응답: {resp.text[:200]}")
                        
                except Exception as e:
                    print(f"      오류: {e}")
            
            # 방법 2: POST 요청
            print("\n4. POST 방법 시도...")
            
            post_data_variants = [
                {'file_id': file_id},
                {'id': file_id},
                {'file_name': file_name},
                {'file_id': file_id, 'file_name': file_name},
                {'uuid': file_id},
                {'guid': file_id}
            ]
            
            for post_data in post_data_variants:
                try:
                    print(f"\n   POST 데이터: {post_data}")
                    resp = session.post(f"{BASE_URL}/isap-api/file/SECINFO/download", 
                                      data=post_data, verify=False)
                    print(f"      상태: {resp.status_code}")
                    print(f"      크기: {len(resp.content)} bytes")
                    
                    if resp.status_code == 200 and len(resp.content) > 5000:
                        if resp.content[:4] == b'PK\x03\x04' or resp.content[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
                            print(f"      ✅ 엑셀 파일 감지!")
                            ext = 'xlsx' if resp.content[:4] == b'PK\x03\x04' else 'xls'
                            with open(f'secudium_download.{ext}', 'wb') as f:
                                f.write(resp.content)
                            print(f"      💾 secudium_download.{ext}로 저장")
                            break
                            
                except Exception as e:
                    print(f"      오류: {e}")
            
            # 방법 3: HAR 파일 분석에서 찾은 패턴
            print("\n5. HAR 분석 기반 시도...")
            
            # archives 폴더의 HAR 데이터 참조
            har_url = f"/isap-api/file/SECINFO/hasFile?file_name={file_name}"
            print(f"\n   파일 존재 확인: {har_url}")
            
            has_file_resp = session.get(f"{BASE_URL}{har_url}", verify=False)
            print(f"      상태: {has_file_resp.status_code}")
            if has_file_resp.status_code == 200:
                print(f"      응답: {has_file_resp.text}")