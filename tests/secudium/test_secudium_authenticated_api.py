#!/usr/bin/env python3
"""
SECUDIUM 인증된 상태에서 API 테스트
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

BASE_URL = "https://secudium.skinfosec.co.kr"
USERNAME = "nextrade"
PASSWORD = "Sprtmxm1@3"

def test_authenticated_secudium_api():
    """인증 후 SECUDIUM API 테스트"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    print("1. 로그인...")
    try:
        # 메인 페이지로 세션 초기화
        session.get(BASE_URL, verify=False)
        
        # 로그인 (GET 방식으로 성공함)
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
        
        if login_resp.status_code != 200:
            print("   로그인 실패")
            return
            
    except Exception as e:
        print(f"   로그인 오류: {e}")
        return
    
    print("\n2. 인증된 상태에서 ISAP API 테스트...")
    
    # 발견된 ISAP API 엔드포인트 테스트
    isap_endpoints = [
        # 기본 ISAP 엔드포인트
        '/isap-api',
        
        # 인증이 필요했던 엔드포인트들
        '/isap-api/secinfo/list',
        '/isap-api/secinfo/blacklist',
        
        # 추가 가능성 있는 엔드포인트들
        '/isap-api/dashboard',
        '/isap-api/data',
        '/isap-api/list',
        '/isap-api/export',
        '/isap-api/report',
        '/isap-api/threat',
        '/isap-api/ip',
        '/isap-api/malware',
        '/isap-api/file',
        '/isap-api/url'
    ]
    
    # Ajax 헤더 설정
    session.headers.update({
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
    })
    
    for endpoint in isap_endpoints:
        print(f"\n   테스트: {endpoint}")
        try:
            # GET 요청
            resp = session.get(f"{BASE_URL}{endpoint}", verify=False)
            print(f"      GET 상태: {resp.status_code}")
            
            if resp.status_code == 200:
                content_type = resp.headers.get('Content-Type', '')
                print(f"      Content-Type: {content_type}")
                
                # JSON 응답 체크
                if 'json' in content_type:
                    try:
                        data = resp.json()
                        print(f"      JSON 타입: {type(data)}")
                        
                        if isinstance(data, list):
                            print(f"      배열 길이: {len(data)}")
                            if len(data) > 0:
                                print(f"      첫 번째 항목: {json.dumps(data[0], indent=2, ensure_ascii=False)}")
                        elif isinstance(data, dict):
                            print(f"      딕셔너리 키: {list(data.keys())}")
                            
                            # 데이터가 있는지 확인
                            if 'data' in data:
                                print(f"      데이터 필드: {type(data['data'])}")
                                if isinstance(data['data'], list):
                                    print(f"      데이터 개수: {len(data['data'])}")
                                    if len(data['data']) > 0:
                                        print(f"      첫 번째 데이터: {data['data'][0]}")
                            
                            # 성공 여부 확인
                            if 'success' in data:
                                print(f"      성공 여부: {data['success']}")
                                
                    except ValueError:
                        print(f"      JSON 파싱 실패")
                        if len(resp.text) < 500:
                            print(f"      응답: {resp.text}")
                        else:
                            print(f"      HTML 응답 ({len(resp.text)} bytes)")
                            
                            # IP 패턴 찾기
                            import re
                            ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
                            ips = ip_pattern.findall(resp.text)
                            if ips:
                                unique_ips = list(set(ips))
                                print(f"      IP 발견: {len(unique_ips)}개")
                                print(f"      샘플: {unique_ips[:5]}")
                
                # POST로도 시도
                print(f"      POST 시도...")
                post_resp = session.post(f"{BASE_URL}{endpoint}", data={}, verify=False)
                if post_resp.status_code == 200 and post_resp.status_code != resp.status_code:
                    print(f"      POST 성공: {post_resp.status_code}")
                    try:
                        post_data = post_resp.json()
                        print(f"      POST JSON: {type(post_data)}")
                    except:
                        pass
                        
            elif resp.status_code == 401:
                print("      ❌ 여전히 인증 필요")
            elif resp.status_code == 403:
                print("      ❌ 접근 권한 없음")
            elif resp.status_code == 404:
                print("      ❌ 없음")
            else:
                print(f"      기타 상태: {resp.status_code}")
                if resp.text and len(resp.text) < 200:
                    print(f"      응답: {resp.text}")
                    
        except Exception as e:
            print(f"      오류: {e}")
    
    print("\n3. 메인 페이지에서 추가 링크/폼 찾기...")
    try:
        # 로그인 후 메인 페이지 다시 확인
        main_resp = session.get(BASE_URL, verify=False)
        soup = BeautifulSoup(main_resp.text, 'html.parser')
        
        # 모든 링크 확인
        links = soup.find_all('a', href=True)
        interesting_links = []
        
        for link in links:
            href = link['href']
            text = link.text.strip()
            
            # API, 데이터, 리포트 관련 링크 찾기
            if any(keyword in href.lower() for keyword in ['api', 'data', 'report', 'export', 'list', 'blacklist']):
                interesting_links.append((text, href))
            elif any(keyword in text.lower() for keyword in ['데이터', '리포트', '목록', '차단', '위협']):
                interesting_links.append((text, href))
        
        if interesting_links:
            print("   흥미로운 링크들:")
            for text, href in interesting_links:
                print(f"      {text}: {href}")
                
                # 링크 테스트
                if href.startswith('/'):
                    try:
                        link_resp = session.get(f"{BASE_URL}{href}", verify=False)
                        print(f"         → 상태: {link_resp.status_code}")
                        
                        if link_resp.status_code == 200:
                            # IP 패턴 체크
                            import re
                            ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
                            ips = ip_pattern.findall(link_resp.text)
                            if ips:
                                unique_ips = list(set(ips))
                                print(f"         → IP 발견: {len(unique_ips)}개")
                                
                    except:
                        pass
        
        # 폼 확인
        forms = soup.find_all('form')
        for i, form in enumerate(forms):
            action = form.get('action', '')
            method = form.get('method', 'GET')
            print(f"   폼 {i+1}: {method} {action}")
            
            # 폼 필드 확인
            inputs = form.find_all('input')
            for inp in inputs:
                name = inp.get('name', '')
                input_type = inp.get('type', 'text')
                if name:
                    print(f"      {name} ({input_type})")
                    
    except Exception as e:
        print(f"   페이지 분석 오류: {e}")

if __name__ == "__main__":
    test_authenticated_secudium_api()