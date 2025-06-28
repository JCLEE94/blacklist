#!/usr/bin/env python3
"""
SECUDIUM 엑셀 파일 다운로드 및 IP 추출
"""
import requests
import json
import re
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

BASE_URL = "https://secudium.skinfosec.co.kr"
USERNAME = "nextrade"
PASSWORD = "Sprtmxm1@3"

def download_and_extract_ips():
    """SECUDIUM에서 최신 엑셀 다운로드하고 IP 추출"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest'
    })
    
    print("1. 로그인...")
    
    # 강제 로그인
    login_data = {
        'lang': 'ko',
        'is_otp': 'N',
        'is_expire': 'Y',  # 강제 로그인
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
        
        print("\n2. 블랙리스트 게시판 조회...")
        
        # 게시판 리스트 가져오기
        list_resp = session.get(f"{BASE_URL}/isap-api/secinfo/list/black_ip", verify=False)
        
        if list_resp.status_code == 200:
            data = list_resp.json()
            rows = data.get('rows', [])
            
            if rows:
                print(f"   게시글 {len(rows)}개 발견")
                
                # 최신 게시글부터 처리
                all_ips = set()
                downloaded_files = []
                
                for idx, row in enumerate(rows[:5]):  # 최신 5개만
                    row_data = row.get('data', [])
                    if len(row_data) > 5:
                        title = row_data[2]  # 제목
                        author = row_data[3]  # 작성자
                        date = row_data[4]    # 날짜
                        download_html = row_data[5]  # 다운로드 버튼
                        
                        print(f"\n   [{idx+1}] {title}")
                        print(f"       작성자: {author}, 날짜: {date}")
                        
                        # 다운로드 정보 추출
                        download_match = re.search(r'download\s*\(\s*["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']', download_html)
                        
                        if download_match:
                            file_id = download_match.group(1)
                            file_name = download_match.group(2)
                            
                            print(f"       파일: {file_name}")
                            
                            # 파일 다운로드
                            download_url = f"{BASE_URL}/isap-api/file/SECINFO/download"
                            
                            # 파라미터로 시도
                            params = {
                                'file_id': file_id,
                                'file_name': file_name
                            }
                            
                            print(f"       다운로드 시도...")
                            dl_resp = session.get(download_url, params=params, verify=False)
                            
                            if dl_resp.status_code != 200:
                                # POST로 재시도
                                dl_resp = session.post(download_url, data=params, verify=False)
                            
                            if dl_resp.status_code == 200 and len(dl_resp.content) > 1000:
                                # 파일 저장
                                output_file = f"secudium_{datetime.now().strftime('%Y%m%d')}_{idx}.xlsx"
                                with open(output_file, 'wb') as f:
                                    f.write(dl_resp.content)
                                
                                print(f"       ✅ 저장: {output_file}")
                                downloaded_files.append(output_file)
                                
                                # 엑셀에서 IP 추출
                                try:
                                    # 여러 형식 시도
                                    try:
                                        df = pd.read_excel(output_file)
                                    except:
                                        df = pd.read_excel(output_file, engine='openpyxl')
                                    
                                    print(f"       엑셀 로드 성공: {df.shape}")
                                    
                                    # 모든 컬럼에서 IP 패턴 찾기
                                    for col in df.columns:
                                        if df[col].dtype == 'object':  # 문자열 컬럼만
                                            for value in df[col].dropna():
                                                str_value = str(value)
                                                # IP 패턴 매칭
                                                ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', str_value)
                                                for ip in ips:
                                                    # 실제 IP인지 검증
                                                    parts = ip.split('.')
                                                    if all(0 <= int(p) <= 255 for p in parts):
                                                        if not ip.startswith(('127.', '192.168.', '10.', '172.')):
                                                            all_ips.add(ip)
                                    
                                    print(f"       IP 수집: {len(all_ips)}개")
                                    
                                except Exception as e:
                                    print(f"       엑셀 파싱 오류: {e}")
                                    
                                    # 바이너리에서 직접 IP 찾기
                                    try:
                                        content = dl_resp.content.decode('utf-8', errors='ignore')
                                        ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', content)
                                        real_ips = [ip for ip in ips if not ip.startswith(('127.', '192.168.', '10.', '172.'))]
                                        all_ips.update(real_ips)
                                        print(f"       바이너리에서 IP 추출: {len(real_ips)}개")
                                    except:
                                        pass
                            
                            else:
                                print(f"       ❌ 다운로드 실패: {dl_resp.status_code}")
                                
                                # 다른 방법 시도 - 직접 ID로 접근
                                view_url = f"{BASE_URL}/isap-api/secinfo/view/black_ip/{row['id']}"
                                view_resp = session.get(view_url, verify=False)
                                
                                if view_resp.status_code == 200:
                                    print(f"       상세 페이지 접근 성공")
                                    try:
                                        view_data = view_resp.json()
                                        print(json.dumps(view_data, indent=2, ensure_ascii=False)[:500])
                                    except:
                                        pass
                
                # 결과 출력
                if all_ips:
                    print(f"\n\n🎉 총 {len(all_ips)}개의 실제 IP 수집 성공!")
                    print(f"\n샘플 IP:")
                    for ip in sorted(all_ips)[:20]:
                        print(f"   {ip}")
                    
                    # 파일로 저장
                    with open('secudium_extracted_ips.txt', 'w') as f:
                        for ip in sorted(all_ips):
                            f.write(f"{ip}\n")
                    print(f"\n💾 secudium_extracted_ips.txt에 저장됨")
                    
                    return list(all_ips)
                else:
                    print(f"\n❌ IP를 추출하지 못했습니다.")
                    
            else:
                print(f"   ❌ 게시글이 없습니다.")
                
    else:
        print(f"   ❌ 로그인 실패")

if __name__ == "__main__":
    download_and_extract_ips()