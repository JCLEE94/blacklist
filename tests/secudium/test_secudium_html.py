#!/usr/bin/env python3
"""
SECUDIUM HTML 분석
"""
import requests
from bs4 import BeautifulSoup
import re

def analyze_secudium_html():
    """SECUDIUM HTML 페이지 분석"""
    
    session = requests.Session()
    BASE_URL = "https://secudium.skinfosec.co.kr"
    
    print("SECUDIUM 메인 페이지 분석...")
    try:
        resp = session.get(BASE_URL, verify=False)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 로그인 폼 찾기
        forms = soup.find_all('form')
        print(f"\n폼 개수: {len(forms)}")
        
        for i, form in enumerate(forms):
            print(f"\n폼 {i+1}:")
            print(f"  Action: {form.get('action', 'None')}")
            print(f"  Method: {form.get('method', 'None')}")
            
            # 입력 필드 찾기
            inputs = form.find_all('input')
            for inp in inputs:
                print(f"  Input: name='{inp.get('name')}', type='{inp.get('type')}', id='{inp.get('id')}'")
        
        # JavaScript에서 API 엔드포인트 찾기
        scripts = soup.find_all('script')
        print(f"\n\n스크립트 개수: {len(scripts)}")
        
        api_patterns = []
        for script in scripts:
            if script.string:
                # API URL 패턴 찾기
                urls = re.findall(r'["\']([^"\']*(?:api|login|auth|blacklist)[^"\']*)["\']', script.string)
                api_patterns.extend(urls)
                
                # Ajax 요청 패턴 찾기
                if 'ajax' in script.string.lower() or 'fetch' in script.string.lower():
                    print("\nAjax/Fetch 패턴 발견:")
                    lines = script.string.split('\n')
                    for line in lines:
                        if any(keyword in line.lower() for keyword in ['url:', 'endpoint', 'api', 'login']):
                            print(f"  {line.strip()}")
        
        if api_patterns:
            print("\n\nAPI 패턴 발견:")
            for pattern in set(api_patterns):
                if not pattern.startswith('http') and not pattern.startswith('//'):
                    print(f"  {pattern}")
        
        # 링크 분석
        links = soup.find_all('a', href=True)
        login_links = []
        for link in links:
            href = link['href']
            text = link.text.strip()
            if any(keyword in text.lower() or keyword in href.lower() for keyword in ['login', '로그인', 'signin']):
                login_links.append((text, href))
        
        if login_links:
            print("\n\n로그인 관련 링크:")
            for text, href in login_links[:5]:
                print(f"  {text}: {href}")
                
    except Exception as e:
        print(f"오류: {e}")

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')
    analyze_secudium_html()