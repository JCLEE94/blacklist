#!/usr/bin/env python3
"""
REGTECH Deep Search Collector
깊은 탐색을 통한 추가 데이터 발굴
- 숨겨진 API 엔드포인트 탐색
- JavaScript 변수에서 데이터 추출  
- 다양한 menuCode 시도
- AJAX 요청 분석
"""

import os
import re
import json
import requests
import sys
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dotenv import load_dotenv

sys.path.insert(0, '/home/jclee/app/blacklist')
load_dotenv()

def deep_search_regtech():
    """깊은 탐색으로 REGTECH 데이터 발굴"""
    
    username = os.getenv('REGTECH_USERNAME', '')
    password = os.getenv('REGTECH_PASSWORD', '')
    
    if not username or not password:
        print("❌ REGTECH 자격증명이 설정되지 않음")
        return []
    
    base_url = "https://regtech.fsec.or.kr"
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    collected_ips = set()  # 중복 방지를 위해 set 사용
    
    try:
        # 1. 로그인
        print(f"🔐 REGTECH 로그인: {username}")
        session.get(f'{base_url}/login/loginForm')
        
        verify_data = {'memberId': username, 'memberPw': password}
        session.headers.update({
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        
        verify_resp = session.post(f"{base_url}/member/findOneMember", data=verify_data)
        if verify_resp.status_code != 200:
            print(f"❌ 사용자 확인 실패")
            return []
        
        login_form_data = {
            'username': username, 'password': password, 'login_error': '',
            'txId': '', 'token': '', 'memberId': '', 'smsTimeExcess': 'N'
        }
        
        login_resp = session.post(f"{base_url}/login/addLogin", data=login_form_data, allow_redirects=True)
        if login_resp.status_code != 200 or 'main' not in login_resp.url:
            print("❌ 로그인 실패")
            return []
        
        print("✅ 로그인 성공")
        
        # 2. 깊은 탐색 시작
        print("\n🔍 깊은 탐색 시작...")
        
        # 2-1. 다양한 menuCode 시도
        menu_codes = [
            'HPHB0620101',  # 기본
            'HPHB0620102', 'HPHB0620103', 'HPHB0620104', 'HPHB0620105',
            'HPHB0610101', 'HPHB0610102', 'HPHB0610103',
            'HPHB0630101', 'HPHB0630102', 'HPHB0630103',
            'THREAT001', 'THREAT002', 'THREAT003',
            'BLACKLIST01', 'BLACKLIST02', 'BLACKLIST03',
            'SECURITY01', 'SECURITY02', 'SECURITY03'
        ]
        
        print(f"📋 다양한 menuCode 시도 ({len(menu_codes)}개)...")
        for menu_code in menu_codes:
            print(f"  menuCode: {menu_code}")
            
            # Board List 시도
            try:
                board_url = f"{base_url}/board/boardList"
                board_params = {'menuCode': menu_code, 'pageSize': '1000'}
                board_resp = session.get(board_url, params=board_params)
                
                if board_resp.status_code == 200:
                    soup = BeautifulSoup(board_resp.text, 'html.parser')
                    ips = extract_ips_from_soup(soup)
                    if ips:
                        collected_ips.update(ips)
                        print(f"    Board: {len(ips)}개 발견")
            except Exception as e:
                pass
            
            # Excel Download 시도
            try:
                excel_url = f"{base_url}/board/excelDownload"
                excel_params = {
                    'menuCode': menu_code,
                    'pageSize': '1000',
                    'startDate': '20240101',
                    'endDate': '20251231'
                }
                excel_resp = session.post(excel_url, data=excel_params)
                
                if excel_resp.status_code == 200:
                    content_type = excel_resp.headers.get('Content-Type', '').lower()
                    if 'excel' in content_type or 'spreadsheet' in content_type:
                        excel_ips = process_excel_response(excel_resp, menu_code)
                        if excel_ips:
                            collected_ips.update(excel_ips)
                            print(f"    Excel: {len(excel_ips)}개 발견")
            except Exception as e:
                pass
        
        # 2-2. API 엔드포인트 탐색
        api_endpoints = [
            '/api/blacklist/list',
            '/api/blacklist/search', 
            '/api/threat/list',
            '/api/threat/search',
            '/api/malware/list',
            '/api/security/advisory',
            '/api/fcti/blacklist',
            '/api/fcti/threat',
            '/board/selectIpPoolList',
            '/board/selectBlackList',
            '/board/selectThreatList',
            '/fcti/api/blacklist',
            '/fcti/api/threat',
            '/fcti/api/malware',
            '/threat/api/blacklist',
            '/security/api/blacklist'
        ]
        
        print(f"\n🔌 API 엔드포인트 탐색 ({len(api_endpoints)}개)...")
        for endpoint in api_endpoints:
            print(f"  API: {endpoint}")
            
            try:
                # GET 시도
                get_resp = session.get(f"{base_url}{endpoint}")
                if get_resp.status_code == 200:
                    try:
                        data = get_resp.json()
                        ips = extract_ips_from_json(data)
                        if ips:
                            collected_ips.update(ips)
                            print(f"    GET JSON: {len(ips)}개 발견")
                    except:
                        # HTML 응답일 수도 있음
                        soup = BeautifulSoup(get_resp.text, 'html.parser')
                        ips = extract_ips_from_soup(soup)
                        if ips:
                            collected_ips.update(ips)
                            print(f"    GET HTML: {len(ips)}개 발견")
                
                # POST 시도 (다양한 파라미터)
                post_params_list = [
                    {},
                    {'size': '1000', 'page': '1'},
                    {'menuCode': 'HPHB0620101', 'size': '1000'},
                    {'type': 'blacklist', 'limit': '1000'},
                    {'category': 'threat', 'limit': '1000'},
                    {'search': 'ip', 'limit': '1000'}
                ]
                
                for post_params in post_params_list:
                    try:
                        post_resp = session.post(f"{base_url}{endpoint}", data=post_params)
                        if post_resp.status_code == 200:
                            try:
                                data = post_resp.json()
                                ips = extract_ips_from_json(data)
                                if ips:
                                    collected_ips.update(ips)
                                    print(f"    POST JSON: {len(ips)}개 발견")
                            except:
                                soup = BeautifulSoup(post_resp.text, 'html.parser')
                                ips = extract_ips_from_soup(soup)
                                if ips:
                                    collected_ips.update(ips)
                                    print(f"    POST HTML: {len(ips)}개 발견")
                    except:
                        pass
                        
            except Exception as e:
                pass
        
        # 2-3. JavaScript 변수 탐색
        print(f"\n🔬 JavaScript 변수 탐색...")
        
        js_pages = [
            '/main/main',
            '/fcti/securityAdvisory/advisoryList',
            '/board/boardList?menuCode=HPHB0620101',
            '/dashboard',
            '/statistics'
        ]
        
        for page_url in js_pages:
            try:
                resp = session.get(f"{base_url}{page_url}")
                if resp.status_code == 200:
                    # JavaScript 변수에서 IP 패턴 찾기
                    js_ips = extract_ips_from_javascript(resp.text)
                    if js_ips:
                        collected_ips.update(js_ips)
                        print(f"  JS ({page_url}): {len(js_ips)}개 발견")
            except:
                pass
        
        # 2-4. 숨겨진 페이지 탐색
        print(f"\n🕵️ 숨겨진 페이지 탐색...")
        
        hidden_paths = [
            '/admin/blacklist',
            '/admin/threat', 
            '/admin/security',
            '/management/blacklist',
            '/management/threat',
            '/report/blacklist',
            '/report/threat',
            '/data/blacklist',
            '/data/threat',
            '/export/blacklist',
            '/export/threat',
            '/download/blacklist',
            '/download/threat'
        ]
        
        for path in hidden_paths:
            try:
                resp = session.get(f"{base_url}{path}")
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    ips = extract_ips_from_soup(soup)
                    if ips:
                        collected_ips.update(ips)
                        print(f"  Hidden ({path}): {len(ips)}개 발견")
            except:
                pass
        
        print(f"\n📊 깊은 탐색 결과: {len(collected_ips)}개 고유 IP")
        
        # IP 데이터 형식 변환
        ip_data_list = []
        for ip in collected_ips:
            ip_data_list.append({
                "ip": ip,
                "source": "REGTECH",
                "description": "Malicious IP from REGTECH (deep search)",
                "detection_date": datetime.now().strftime('%Y-%m-%d'),
                "confidence": "high"
            })
        
        return ip_data_list
    
    except Exception as e:
        print(f"❌ 깊은 탐색 중 오류: {e}")
        return []
    
    finally:
        session.close()


def extract_ips_from_soup(soup):
    """BeautifulSoup에서 IP 추출"""
    ips = []
    ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
    
    # 모든 텍스트에서 IP 찾기
    all_text = soup.get_text()
    found_ips = ip_pattern.findall(all_text)
    
    for ip in found_ips:
        if is_valid_ip(ip):
            ips.append(ip)
    
    return ips


def extract_ips_from_json(data):
    """JSON 데이터에서 IP 추출"""
    ips = []
    ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
    
    def extract_from_obj(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    extract_from_obj(value)
                elif isinstance(value, str):
                    found_ips = ip_pattern.findall(value)
                    for ip in found_ips:
                        if is_valid_ip(ip):
                            ips.append(ip)
        elif isinstance(obj, list):
            for item in obj:
                extract_from_obj(item)
        elif isinstance(obj, str):
            found_ips = ip_pattern.findall(obj)
            for ip in found_ips:
                if is_valid_ip(ip):
                    ips.append(ip)
    
    extract_from_obj(data)
    return ips


def extract_ips_from_javascript(html_text):
    """JavaScript 코드에서 IP 추출"""
    ips = []
    ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
    
    # script 태그 내용 추출
    script_pattern = re.compile(r'<script[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE)
    scripts = script_pattern.findall(html_text)
    
    for script in scripts:
        # JavaScript 변수에서 IP 찾기
        found_ips = ip_pattern.findall(script)
        for ip in found_ips:
            if is_valid_ip(ip):
                ips.append(ip)
    
    return ips


def is_valid_ip(ip):
    """IP 주소 유효성 검사"""
    try:
        octets = ip.split('.')
        if len(octets) != 4:
            return False
        
        for octet in octets:
            num = int(octet)
            if not (0 <= num <= 255):
                return False
        
        # 로컬/예약 IP 제외
        if ip.startswith(('127.', '192.168.', '10.', '172.', '0.', '255.')):
            return False
        
        # 멀티캐스트/브로드캐스트 제외
        first_octet = int(octets[0])
        if first_octet >= 224:
            return False
        
        return True
    
    except:
        return False


def process_excel_response(excel_resp, menu_code):
    """Excel 응답 처리"""
    try:
        import pandas as pd
        
        excel_path = f"/tmp/regtech_excel_{menu_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        with open(excel_path, 'wb') as f:
            for chunk in excel_resp.iter_content(chunk_size=8192):
                f.write(chunk)
        
        df = pd.read_excel(excel_path)
        
        ips = []
        ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        
        for col in df.columns:
            for val in df[col].dropna():
                val_str = str(val)
                found_ips = ip_pattern.findall(val_str)
                
                for ip in found_ips:
                    if is_valid_ip(ip):
                        ips.append(ip)
        
        try:
            os.unlink(excel_path)
        except:
            pass
        
        return ips
    
    except Exception as e:
        return []


def store_collected_data(ip_data_list):
    """수집된 데이터를 PostgreSQL에 저장"""
    if not ip_data_list:
        return {"success": False, "message": "No data to store"}
    
    try:
        from src.core.data_storage_fixed import FixedDataStorage
        storage = FixedDataStorage()
        result = storage.store_ips(ip_data_list, "REGTECH")
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    print("🚀 REGTECH Deep Search Collector")
    print("="*60)
    
    # 깊은 탐색 실행
    ips = deep_search_regtech()
    
    if ips:
        print(f"\n✅ {len(ips)}개 IP 깊은 탐색 성공")
        
        # 처음 20개 표시
        print("\n처음 20개 IP:")
        for i, ip_data in enumerate(ips[:20], 1):
            print(f"  {i:2d}. {ip_data['ip']}")
        
        if len(ips) > 20:
            print(f"  ... 외 {len(ips) - 20}개")
        
        # PostgreSQL에 저장
        result = store_collected_data(ips)
        
        if result.get("success"):
            print(f"\n✅ PostgreSQL 저장 완료:")
            print(f"  - 신규 저장: {result.get('imported_count', 0)}개")
            print(f"  - 중복 제외: {result.get('duplicate_count', 0)}개")
            print(f"  - 전체 DB: {result.get('total_count', 0)}개")
        else:
            print(f"\n❌ 저장 실패: {result.get('error', 'Unknown error')}")
    else:
        print("\n❌ 깊은 탐색에서 수집된 데이터가 없음")
    
    print("\n🔍 깊은 탐색 완료!")