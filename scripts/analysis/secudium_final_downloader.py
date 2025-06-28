#!/usr/bin/env python3
"""
SECUDIUM 최종 엑셀 다운로더 - 정확한 URL 패턴 사용
"""
import requests
import json
import re
import pandas as pd
from datetime import datetime
import os
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

BASE_URL = "https://secudium.skinfosec.co.kr"
USERNAME = "nextrade"
PASSWORD = "Sprtmxm1@3"

def download_secudium_blacklist():
    """SECUDIUM 블랙리스트 엑셀 다운로드 및 IP 추출"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*'
    })
    
    print("=== SECUDIUM 블랙리스트 다운로드 ===\n")
    
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
        print(f"   토큰: {token[:50]}...")
        
        print("\n2. 블랙리스트 게시판 조회...")
        
        # 게시판 리스트
        list_resp = session.get(f"{BASE_URL}/isap-api/secinfo/list/black_ip", verify=False)
        data = list_resp.json()
        rows = data.get('rows', [])
        
        if rows:
            print(f"   게시글 {len(rows)}개 발견\n")
            
            all_ips = set()
            
            # 최신 5개 게시글 처리
            for idx, row in enumerate(rows[:5]):
                row_data = row.get('data', [])
                if len(row_data) > 5:
                    title = row_data[2]
                    date = row_data[4]
                    download_html = row_data[5]
                    
                    print(f"3. [{idx+1}] {title}")
                    print(f"   날짜: {date}")
                    
                    # 다운로드 정보 추출
                    match = re.search(r'download\s*\(\s*["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']', download_html)
                    
                    if match:
                        server_file_name = match.group(1)  # UUID
                        file_name = match.group(2)         # 실제 파일명
                        
                        print(f"   파일: {file_name}")
                        
                        # 정확한 다운로드 URL (HAR 분석 결과)
                        download_url = f"{BASE_URL}/isap-api/file/SECINFO/download"
                        params = {
                            'X-Auth-Token': token,
                            'serverFileName': server_file_name,
                            'fileName': file_name
                        }
                        
                        print(f"   다운로드 중...")
                        dl_resp = session.get(download_url, params=params, verify=False)
                        
                        if dl_resp.status_code == 200 and len(dl_resp.content) > 1000:
                            # 파일 저장
                            output_dir = "data/secudium"
                            os.makedirs(output_dir, exist_ok=True)
                            
                            output_file = os.path.join(output_dir, f"secudium_{datetime.now().strftime('%Y%m%d')}_{idx}.xlsx")
                            with open(output_file, 'wb') as f:
                                f.write(dl_resp.content)
                            
                            print(f"   ✅ 저장: {output_file} ({len(dl_resp.content):,} bytes)")
                            
                            # 엑셀에서 IP 추출
                            try:
                                # 엑셀 읽기
                                df = pd.read_excel(output_file, engine='openpyxl')
                                print(f"   엑셀 로드: {df.shape[0]}행 x {df.shape[1]}열")
                                
                                # IP 컬럼 찾기
                                ip_count = 0
                                for col in df.columns:
                                    # IP 패턴이 있는 컬럼 찾기
                                    if df[col].dtype == 'object':
                                        for value in df[col].dropna():
                                            str_value = str(value)
                                            # IP 패턴 확인
                                            if re.match(r'^\d+\.\d+\.\d+\.\d+$', str_value.strip()):
                                                parts = str_value.strip().split('.')
                                                if all(0 <= int(p) <= 255 for p in parts):
                                                    if not str_value.startswith(('127.', '192.168.', '10.', '172.')):
                                                        all_ips.add(str_value.strip())
                                                        ip_count += 1
                                
                                print(f"   IP 추출: {ip_count}개")
                                
                            except Exception as e:
                                print(f"   엑셀 파싱 오류: {e}")
                                
                                # XLS 형식으로 재시도
                                try:
                                    df = pd.read_excel(output_file, engine='xlrd')
                                    print(f"   XLS로 재시도: {df.shape}")
                                    
                                    for col in df.columns:
                                        if df[col].dtype == 'object':
                                            for value in df[col].dropna():
                                                str_value = str(value).strip()
                                                if re.match(r'^\d+\.\d+\.\d+\.\d+$', str_value):
                                                    parts = str_value.split('.')
                                                    if all(0 <= int(p) <= 255 for p in parts):
                                                        if not str_value.startswith(('127.', '192.168.', '10.', '172.')):
                                                            all_ips.add(str_value)
                                            
                                except Exception as e2:
                                    print(f"   XLS 파싱도 실패: {e2}")
                        else:
                            print(f"   ❌ 다운로드 실패: {dl_resp.status_code}")
                    
                    print()
            
            # 결과 저장
            if all_ips:
                print(f"\n=== 수집 완료 ===")
                print(f"✅ 총 {len(all_ips)}개의 고유 IP 수집")
                print(f"\n샘플 IP (처음 20개):")
                for i, ip in enumerate(sorted(all_ips)[:20]):
                    print(f"   {i+1:2d}. {ip}")
                
                # 텍스트 파일로 저장
                output_txt = os.path.join("data/secudium", f"collected_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                with open(output_txt, 'w') as f:
                    for ip in sorted(all_ips):
                        f.write(f"{ip}\n")
                
                print(f"\n💾 {output_txt}에 저장 완료")
                
                # JSON으로도 저장
                output_json = os.path.join("data/secudium", f"collected_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                with open(output_json, 'w') as f:
                    json.dump({
                        'source': 'SECUDIUM',
                        'date': datetime.now().isoformat(),
                        'total_ips': len(all_ips),
                        'ips': sorted(all_ips)
                    }, f, indent=2, ensure_ascii=False)
                
                print(f"💾 {output_json}에 메타데이터 저장 완료")
                
                return list(all_ips)
            else:
                print("\n❌ IP를 수집하지 못했습니다.")
                return []
                
    else:
        print(f"   ❌ 로그인 실패: {auth_data.get('response', {}).get('message', 'Unknown error')}")
        return []

if __name__ == "__main__":
    ips = download_secudium_blacklist()
    if ips:
        print(f"\n🎉 성공적으로 {len(ips)}개의 IP를 수집했습니다!")
    else:
        print(f"\n💔 IP 수집에 실패했습니다.")