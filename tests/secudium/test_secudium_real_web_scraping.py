#!/usr/bin/env python3
"""
SECUDIUM 실제 웹 데이터 수집 테스트
로그인 후 실제 페이지들을 탐색하여 IP 데이터 찾기
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

def test_real_secudium_data():
    """실제 SECUDIUM 데이터 수집 테스트"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    print("1. SECUDIUM 로그인...")
    try:
        # 메인 페이지 접속
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
        print(f"   로그인 상태: {login_resp.status_code}")
        
    except Exception as e:
        print(f"   로그인 실패: {e}")
        return
    
    print("\n2. 메인 대시보드 페이지 분석...")
    
    # 로그인 후 메인 페이지들 확인
    main_pages = ['/', '/main', '/dashboard', '/home', '/index']
    
    for page in main_pages:
        try:
            resp = session.get(f"{BASE_URL}{page}", verify=False)
            if resp.status_code == 200:
                print(f"\n   페이지: {page}")
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # 모든 링크 찾기
                links = soup.find_all('a', href=True)
                data_links = []
                
                for link in links:
                    href = link['href']
                    text = link.text.strip()
                    
                    # 데이터, 리포트, 블랙리스트 관련 링크 찾기
                    keywords = ['데이터', '리포트', '보고서', '통계', '분석', '목록', '리스트', 
                               'data', 'report', 'list', 'blacklist', 'threat', 'ip', 'scan']
                    
                    if any(keyword in text.lower() for keyword in keywords) or \
                       any(keyword in href.lower() for keyword in keywords):
                        data_links.append((text, href))
                
                if data_links:
                    print(f"   데이터 관련 링크:")
                    for text, href in data_links:
                        print(f"      {text}: {href}")
                        
                        # 실제 페이지 접근
                        if href.startswith('/'):
                            try:
                                data_resp = session.get(f"{BASE_URL}{href}", verify=False)
                                print(f"         → 상태: {data_resp.status_code}")
                                
                                if data_resp.status_code == 200:
                                    # 페이지에서 실제 IP 찾기
                                    ips = find_real_ips_in_page(data_resp.text)
                                    if ips:
                                        print(f"         → 실제 IP 발견: {len(ips)}개")
                                        print(f"         → 샘플: {ips[:5]}")
                                        
                                        # 테이블이나 다운로드 링크 찾기
                                        download_links = find_download_links(data_resp.text)
                                        if download_links:
                                            print(f"         → 다운로드 링크:")
                                            for dl_text, dl_href in download_links:
                                                print(f"            {dl_text}: {dl_href}")
                                                
                                                # 다운로드 시도
                                                if dl_href.startswith('/'):
                                                    try:
                                                        dl_resp = session.get(f"{BASE_URL}{dl_href}", verify=False)
                                                        if dl_resp.status_code == 200:
                                                            # 다운로드된 파일에서 IP 찾기
                                                            file_ips = extract_ips_from_download(dl_resp)
                                                            if file_ips:
                                                                print(f"               → 다운로드에서 {len(file_ips)}개 IP 발견!")
                                                                return file_ips
                                                    except:
                                                        pass
                            except Exception as e:
                                print(f"         → 오류: {e}")
                
        except Exception as e:
            print(f"   페이지 {page} 오류: {e}")
    
    print("\n3. 직접 API 엔드포인트 탐색...")
    
    # 가능한 데이터 엔드포인트들
    data_endpoints = [
        '/data/blacklist',
        '/api/data/blacklist',
        '/report/blacklist',
        '/export/blacklist',
        '/download/blacklist',
        '/list/blacklist',
        '/blacklist/download',
        '/blacklist/export',
        '/secinfo/blacklist',
        '/threat/list',
        '/malware/list',
        '/ip/list'
    ]
    
    for endpoint in data_endpoints:
        try:
            resp = session.get(f"{BASE_URL}{endpoint}", verify=False)
            print(f"\n   {endpoint}: {resp.status_code}")
            
            if resp.status_code == 200:
                # JSON 응답 체크
                try:
                    data = resp.json()
                    print(f"      JSON 응답: {type(data)}")
                    if isinstance(data, list) and len(data) > 0:
                        print(f"      데이터 개수: {len(data)}")
                        print(f"      첫 번째 항목: {data[0]}")
                except:
                    # HTML에서 IP 찾기
                    ips = find_real_ips_in_page(resp.text)
                    if ips:
                        print(f"      실제 IP {len(ips)}개 발견: {ips[:5]}")
                        return ips
                        
        except Exception as e:
            print(f"   {endpoint} 오류: {e}")
    
    print("\n4. 폼과 POST 요청 탐색...")
    
    # 메인 페이지에서 폼 찾기
    try:
        main_resp = session.get(BASE_URL, verify=False)
        soup = BeautifulSoup(main_resp.text, 'html.parser')
        
        forms = soup.find_all('form')
        for i, form in enumerate(forms):
            action = form.get('action', '')
            method = form.get('method', 'GET')
            
            print(f"\n   폼 {i+1}: {method} {action}")
            
            # 폼 필드 확인
            inputs = form.find_all('input')
            form_data = {}
            
            for inp in inputs:
                name = inp.get('name', '')
                value = inp.get('value', '')
                input_type = inp.get('type', 'text')
                
                if name and name not in ['login_name', 'password']:
                    form_data[name] = value
                    print(f"      {name}: {value} ({input_type})")
            
            # 폼 제출해보기 (데이터 요청 같은 경우)
            if action and any(keyword in action.lower() for keyword in ['data', 'report', 'export']):
                try:
                    if method.upper() == 'POST':
                        form_resp = session.post(f"{BASE_URL}{action}", data=form_data, verify=False)
                    else:
                        form_resp = session.get(f"{BASE_URL}{action}", params=form_data, verify=False)
                    
                    print(f"      폼 제출: {form_resp.status_code}")
                    
                    if form_resp.status_code == 200:
                        ips = find_real_ips_in_page(form_resp.text)
                        if ips:
                            print(f"      폼에서 실제 IP {len(ips)}개 발견!")
                            return ips
                            
                except Exception as e:
                    print(f"      폼 제출 오류: {e}")
                    
    except Exception as e:
        print(f"   폼 분석 오류: {e}")
    
    print("\n❌ 실제 SECUDIUM 데이터를 찾을 수 없습니다.")
    return []

def find_real_ips_in_page(html_text):
    """페이지에서 실제 IP 주소 찾기 (테스트 데이터 제외)"""
    ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
    found_ips = ip_pattern.findall(html_text)
    
    # 유효한 실제 IP만 필터링 (로컬/테스트 IP 제외)
    real_ips = []
    for ip in found_ips:
        try:
            parts = [int(p) for p in ip.split('.')]
            
            # 유효한 IP 범위 체크
            if all(0 <= p <= 255 for p in parts):
                # 로컬/사설/테스트 IP 제외
                if not (ip.startswith(('127.', '192.168.', '10.', '172.')) or
                       ip.startswith(('0.', '255.')) or
                       ip == '0.0.0.0' or ip == '255.255.255.255'):
                    real_ips.append(ip)
        except:
            continue
    
    return list(set(real_ips))  # 중복 제거

def find_download_links(html_text):
    """다운로드 링크 찾기"""
    soup = BeautifulSoup(html_text, 'html.parser')
    download_links = []
    
    # 다운로드 관련 링크 찾기
    links = soup.find_all('a', href=True)
    for link in links:
        href = link['href']
        text = link.text.strip()
        
        # 다운로드 관련 키워드
        download_keywords = ['다운로드', 'download', 'export', '내보내기', 'excel', 'csv', 'json']
        
        if any(keyword in text.lower() for keyword in download_keywords) or \
           any(keyword in href.lower() for keyword in download_keywords):
            download_links.append((text, href))
    
    return download_links

def extract_ips_from_download(response):
    """다운로드된 파일에서 IP 추출"""
    try:
        # JSON 시도
        data = response.json()
        ips = []
        
        def extract_from_json(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if 'ip' in key.lower() and isinstance(value, str):
                        if re.match(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', value):
                            ips.append(value)
                    elif isinstance(value, (dict, list)):
                        extract_from_json(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_from_json(item)
        
        extract_from_json(data)
        return find_real_ips_in_page(' '.join(ips))
        
    except:
        # 텍스트에서 IP 찾기
        return find_real_ips_in_page(response.text)

if __name__ == "__main__":
    real_ips = test_real_secudium_data()
    
    if real_ips:
        print(f"\n✅ 총 {len(real_ips)}개의 실제 IP 발견!")
        print(f"샘플: {real_ips[:10]}")
    else:
        print("\n❌ 실제 SECUDIUM IP 데이터를 찾지 못했습니다.")