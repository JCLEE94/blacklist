#!/usr/bin/env python3
"""
/secinfo/blacklist 엔드포인트 상세 분석
"""
import requests
from bs4 import BeautifulSoup
import re
import json
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

BASE_URL = "https://secudium.skinfosec.co.kr"
USERNAME = "nextrade"
PASSWORD = "Sprtmxm1@3"

def analyze_secinfo_endpoint():
    """secinfo/blacklist 엔드포인트 상세 분석"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    print("1. 로그인...")
    # 로그인
    session.get(BASE_URL, verify=False)
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
    
    print("\n2. /secinfo/blacklist 분석...")
    
    try:
        resp = session.get(f"{BASE_URL}/secinfo/blacklist", verify=False)
        print(f"   상태: {resp.status_code}")
        print(f"   Content-Type: {resp.headers.get('Content-Type', 'Unknown')}")
        print(f"   Content-Length: {len(resp.text)}")
        
        if resp.status_code == 200:
            # HTML 파싱
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 페이지 제목
            title = soup.find('title')
            if title:
                print(f"   페이지 제목: {title.text.strip()}")
            
            # 테이블 찾기
            tables = soup.find_all('table')
            print(f"\n   테이블 개수: {len(tables)}")
            
            for i, table in enumerate(tables):
                print(f"\n   테이블 {i+1}:")
                rows = table.find_all('tr')
                print(f"      행 개수: {len(rows)}")
                
                # 헤더 확인
                if rows:
                    first_row = rows[0]
                    headers = [th.text.strip() for th in first_row.find_all(['th', 'td'])]
                    print(f"      헤더: {headers}")
                
                # 실제 데이터 확인 (처음 3행)
                for j, row in enumerate(rows[1:4]):  # 헤더 제외하고 처음 3행
                    cells = [td.text.strip() for td in row.find_all('td')]
                    if cells:
                        print(f"      데이터 {j+1}: {cells}")
                        
                        # IP 패턴 체크
                        for cell in cells:
                            if re.match(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', cell):
                                print(f"         → IP 발견: {cell}")
            
            # 폼 찾기
            forms = soup.find_all('form')
            print(f"\n   폼 개수: {len(forms)}")
            
            for i, form in enumerate(forms):
                action = form.get('action', '')
                method = form.get('method', 'GET')
                print(f"\n   폼 {i+1}: {method} {action}")
                
                inputs = form.find_all('input')
                for inp in inputs:
                    name = inp.get('name', '')
                    value = inp.get('value', '')
                    input_type = inp.get('type', 'text')
                    if name:
                        print(f"      {name}: {value} ({input_type})")
            
            # JavaScript에서 AJAX 호출 찾기
            scripts = soup.find_all('script')
            ajax_calls = []
            
            for script in scripts:
                if script.string:
                    # AJAX URL 패턴 찾기
                    url_patterns = re.findall(r'url\s*:\s*["\']([^"\']+)["\']', script.string)
                    ajax_calls.extend(url_patterns)
                    
                    # fetch 패턴 찾기
                    fetch_patterns = re.findall(r'fetch\s*\(\s*["\']([^"\']+)["\']', script.string)
                    ajax_calls.extend(fetch_patterns)
            
            if ajax_calls:
                print(f"\n   JavaScript AJAX 호출:")
                for call in set(ajax_calls):
                    print(f"      {call}")
                    
                    # AJAX 엔드포인트 테스트
                    if call.startswith('/'):
                        try:
                            ajax_resp = session.get(f"{BASE_URL}{call}", verify=False)
                            print(f"         → {ajax_resp.status_code}")
                            
                            if ajax_resp.status_code == 200:
                                try:
                                    ajax_data = ajax_resp.json()
                                    print(f"         → JSON: {type(ajax_data)}")
                                    if isinstance(ajax_data, list):
                                        print(f"         → 데이터 개수: {len(ajax_data)}")
                                        if len(ajax_data) > 0:
                                            print(f"         → 첫 번째: {ajax_data[0]}")
                                except:
                                    # HTML에서 IP 찾기
                                    ips = find_ips(ajax_resp.text)
                                    if ips:
                                        print(f"         → IP 발견: {len(ips)}개")
                        except:
                            pass
            
            # 직접 IP 패턴 찾기
            all_ips = find_ips(resp.text)
            if all_ips:
                print(f"\n   페이지에서 발견된 IP: {len(all_ips)}개")
                print(f"   샘플: {all_ips[:10]}")
            
            # 페이지 전체 출력 (처음 2000자)
            print(f"\n   페이지 내용 (처음 2000자):")
            print(f"   {resp.text[:2000]}...")
            
    except Exception as e:
        print(f"   오류: {e}")

def find_ips(text):
    """텍스트에서 실제 IP 주소 찾기"""
    ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
    found_ips = ip_pattern.findall(text)
    
    real_ips = []
    for ip in found_ips:
        try:
            parts = [int(p) for p in ip.split('.')]
            if all(0 <= p <= 255 for p in parts):
                # 로컬/사설 IP 제외
                if not (ip.startswith(('127.', '192.168.', '10.', '172.')) or
                       ip.startswith(('0.', '255.')) or
                       ip == '0.0.0.0' or ip == '255.255.255.255'):
                    real_ips.append(ip)
        except:
            continue
    
    return list(set(real_ips))

if __name__ == "__main__":
    analyze_secinfo_endpoint()