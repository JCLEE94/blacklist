#!/usr/bin/env python3
"""
REGTECH 올바른 로그인 프로세스로 데이터 수집
1. /member/findOneMember로 사용자 확인
2. /login/addLogin으로 실제 로그인
"""

import os
import re
import json
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

def collect_with_correct_login():
    """올바른 로그인 프로세스로 데이터 수집"""
    
    username = os.getenv('REGTECH_USERNAME', '')
    password = os.getenv('REGTECH_PASSWORD', '')
    base_url = "https://regtech.fsec.or.kr"
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': base_url,
        'Referer': f'{base_url}/login/loginForm'
    })
    
    collected_ips = []
    
    # 1. 로그인 페이지 접속 (세션 쿠키 획득)
    print(f"🔐 Step 1: Getting session cookie...")
    login_page = session.get(f'{base_url}/login/loginForm')
    print(f"  Initial cookies: {list(session.cookies.keys())}")
    
    # 2. 사용자 확인 API 호출
    print(f"\n🔐 Step 2: Verifying user ({username})...")
    verify_data = {
        'memberId': username,
        'memberPw': password
    }
    
    verify_resp = session.post(
        f'{base_url}/member/findOneMember',
        data=verify_data
    )
    
    print(f"  Verify status: {verify_resp.status_code}")
    
    if verify_resp.status_code == 200:
        print("  ✅ User verified successfully")
        
        # 3. 실제 로그인
        print(f"\n🔐 Step 3: Performing actual login...")
        
        # Form 데이터 준비
        login_form_data = {
            'username': username,
            'password': password,
            'login_error': '',
            'txId': '',
            'token': '',
            'memberId': '',
            'smsTimeExcess': 'N'
        }
        
        # addLogin 엔드포인트로 POST
        session.headers.update({
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        
        login_resp = session.post(
            f'{base_url}/login/addLogin',
            data=login_form_data,
            allow_redirects=True
        )
        
        print(f"  Login status: {login_resp.status_code}")
        print(f"  Final URL: {login_resp.url}")
        print(f"  Cookies: {list(session.cookies.keys())}")
        
        # 로그인 성공 확인
        if 'logout' in login_resp.text.lower() or '로그아웃' in login_resp.text:
            print("  ✅ Login successful!")
        else:
            print("  ⚠️ Login status uncertain")
            
            # 디버깅을 위해 응답 일부 저장
            with open('login_response.html', 'w', encoding='utf-8') as f:
                f.write(login_resp.text[:5000])
            print("  Response saved to login_response.html for debugging")
        
        # 4. 데이터 수집
        print(f"\n🔍 Step 4: Collecting blacklist data...")
        
        # 4-1. Advisory List 시도
        advisory_url = f"{base_url}/fcti/securityAdvisory/advisoryList"
        print(f"  Accessing: {advisory_url}")
        
        # 날짜 범위 설정
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # POST 파라미터
        list_params = {
            'page': '1',
            'size': '100',
            'rows': '100',
            'startDate': start_date.strftime('%Y%m%d'),
            'endDate': end_date.strftime('%Y%m%d'),
            'tabSort': 'blacklist',
            'findCondition': 'all',
            'findKeyword': ''
        }
        
        # 헤더 업데이트
        session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        
        list_resp = session.post(advisory_url, data=list_params)
        print(f"    Status: {list_resp.status_code}")
        
        if list_resp.status_code == 200:
            soup = BeautifulSoup(list_resp.text, 'html.parser')
            
            # 테이블 찾기
            tables = soup.find_all('table')
            print(f"    Tables: {len(tables)}")
            
            # tbody 행 찾기
            rows = soup.select('tbody tr')
            print(f"    Rows: {len(rows)}")
            
            # IP 패턴 찾기
            ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
            
            for row in rows:
                cells = row.find_all('td')
                for cell in cells:
                    text = cell.get_text(strip=True)
                    ips = ip_pattern.findall(text)
                    
                    for ip in ips:
                        octets = ip.split('.')
                        try:
                            if all(0 <= int(o) <= 255 for o in octets):
                                if not ip.startswith(('127.', '192.168.', '10.', '172.', '0.')):
                                    if ip not in collected_ips:
                                        collected_ips.append(ip)
                                        print(f"      ✅ Found: {ip}")
                        except:
                            pass
            
            # 페이지 내 모든 텍스트에서도 IP 찾기
            page_text = soup.get_text()
            all_ips = ip_pattern.findall(page_text)
            
            for ip in all_ips:
                octets = ip.split('.')
                try:
                    if all(0 <= int(o) <= 255 for o in octets):
                        if not ip.startswith(('127.', '192.168.', '10.', '172.', '0.')):
                            if ip not in collected_ips:
                                collected_ips.append(ip)
                                print(f"      ✅ Found in page: {ip}")
                except:
                    pass
        
        # 4-2. Board List 시도
        if len(collected_ips) == 0:
            board_url = f"{base_url}/board/boardList"
            print(f"\n  Trying board: {board_url}")
            
            board_params = {
                'menuCode': 'HPHB0620101',
                'pageIndex': '1',
                'pageSize': '100'
            }
            
            board_resp = session.get(board_url, params=board_params)
            print(f"    Status: {board_resp.status_code}")
            
            if board_resp.status_code == 200:
                soup = BeautifulSoup(board_resp.text, 'html.parser')
                
                # 게시판 내용에서 IP 찾기
                all_text = soup.get_text()
                ips = ip_pattern.findall(all_text)
                
                for ip in ips:
                    octets = ip.split('.')
                    try:
                        if all(0 <= int(o) <= 255 for o in octets):
                            if not ip.startswith(('127.', '192.168.', '10.', '172.', '0.')):
                                if ip not in collected_ips:
                                    collected_ips.append(ip)
                                    print(f"      ✅ Found in board: {ip}")
                    except:
                        pass
        
        # 4-3. Excel 다운로드 시도
        if len(collected_ips) == 0:
            excel_url = f"{base_url}/board/excelDownload"
            print(f"\n  Trying Excel download: {excel_url}")
            
            excel_params = {
                'menuCode': 'HPHB0620101',
                'startDate': start_date.strftime('%Y%m%d'),
                'endDate': end_date.strftime('%Y%m%d')
            }
            
            excel_resp = session.post(excel_url, data=excel_params, stream=True)
            print(f"    Status: {excel_resp.status_code}")
            print(f"    Content-Type: {excel_resp.headers.get('Content-Type', '')}")
            
            # Excel 파일인지 확인
            content_type = excel_resp.headers.get('Content-Type', '').lower()
            if 'excel' in content_type or 'spreadsheet' in content_type:
                print("    ✅ Excel file received")
                
                # 파일 저장
                excel_path = f"/tmp/regtech_excel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                with open(excel_path, 'wb') as f:
                    for chunk in excel_resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"    Saved to: {excel_path}")
                
                # Excel 파싱
                try:
                    import pandas as pd
                    df = pd.read_excel(excel_path)
                    print(f"    Excel shape: {df.shape}")
                    print(f"    Columns: {df.columns.tolist()}")
                    
                    # IP 컬럼 찾기
                    for col in df.columns:
                        for idx, val in df[col].dropna().items():
                            val_str = str(val)
                            ips = ip_pattern.findall(val_str)
                            for ip in ips:
                                if ip not in collected_ips:
                                    collected_ips.append(ip)
                                    print(f"      ✅ Found in Excel: {ip}")
                except Exception as e:
                    print(f"    Excel parsing error: {e}")
    
    else:
        print(f"  ❌ User verification failed: {verify_resp.status_code}")
        if verify_resp.text:
            print(f"  Response: {verify_resp.text[:200]}")
    
    # 5. 결과
    print(f"\n{'='*60}")
    print(f"📊 총 {len(collected_ips)}개 IP 수집")
    
    if collected_ips:
        # 중복 제거
        unique_ips = list(set(collected_ips))
        print(f"   중복 제거 후: {len(unique_ips)}개")
        
        print("\n처음 10개 IP:")
        for i, ip in enumerate(unique_ips[:10], 1):
            print(f"  {i}. {ip}")
        
        # IP 데이터 형식 변환
        ip_data_list = []
        for ip in unique_ips:
            ip_data_list.append({
                "ip": ip,
                "source": "REGTECH",
                "description": "Malicious IP from REGTECH",
                "detection_date": datetime.now().strftime('%Y-%m-%d'),
                "confidence": "high"
            })
        
        return ip_data_list
    
    return []


if __name__ == "__main__":
    print("🚀 REGTECH Correct Login Process Collection")
    print("="*60)
    
    ips = collect_with_correct_login()
    
    if ips:
        print(f"\n✅ 성공! {len(ips)}개 실제 IP 수집")
        
        # PostgreSQL에 저장
        try:
            from src.core.data_storage_fixed import FixedDataStorage
            storage = FixedDataStorage()
            result = storage.store_ips(ips, "REGTECH")
            
            if result.get("success"):
                print(f"✅ PostgreSQL 저장 완료: {result.get('imported_count')}개")
            else:
                print(f"❌ 저장 실패: {result.get('error')}")
        except Exception as e:
            print(f"❌ 저장 중 오류: {e}")
    else:
        print("\n❌ 데이터를 찾을 수 없음")
        print("\n다음 단계:")
        print("1. 브라우저에서 직접 로그인하여 데이터 확인")
        print("2. HAR 파일로 정확한 요청 시퀀스 캡처")
        print("3. 쿠키 문자열로 직접 인증")