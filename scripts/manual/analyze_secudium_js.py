#!/usr/bin/env python3
"""
SECUDIUM JavaScript 분석하여 실제 로그인 방식 찾기
"""
import requests
from bs4 import BeautifulSoup
import re
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

def analyze_secudium_javascript():
    """SECUDIUM JavaScript에서 로그인 로직 분석"""
    
    session = requests.Session()
    BASE_URL = "https://secudium.skinfosec.co.kr"
    
    print("SECUDIUM JavaScript 분석...")
    try:
        resp = session.get(BASE_URL, verify=False)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 모든 스크립트 태그 분석
        scripts = soup.find_all('script')
        print(f"총 {len(scripts)}개 스크립트 발견")
        
        for i, script in enumerate(scripts):
            if script.get('src'):
                # 외부 스크립트 파일
                script_url = script['src']
                if not script_url.startswith('http'):
                    script_url = BASE_URL + script_url
                
                print(f"\n스크립트 {i+1}: {script_url}")
                try:
                    script_resp = session.get(script_url, verify=False)
                    if script_resp.status_code == 200:
                        script_content = script_resp.text
                        
                        # 로그인 관련 함수 찾기
                        login_patterns = [
                            r'function\s+login\s*\([^)]*\)\s*{[^}]*}',
                            r'login\s*:\s*function[^}]*}',
                            r'\.post\s*\([^)]*login[^)]*\)',
                            r'ajax\s*\([^}]*login[^}]*\)',
                            r'fetch\s*\([^)]*login[^)]*\)'
                        ]
                        
                        for pattern in login_patterns:
                            matches = re.findall(pattern, script_content, re.IGNORECASE | re.DOTALL)
                            if matches:
                                print(f"      로그인 관련 코드 발견:")
                                for match in matches[:2]:  # 처음 2개만 출력
                                    print(f"      {match[:200]}...")
                        
                        # URL 패턴 찾기
                        url_patterns = re.findall(r'["\']([^"\']*(?:login|auth|api)[^"\']*)["\']', script_content)
                        if url_patterns:
                            print(f"      관련 URL: {set(url_patterns)}")
                            
                except Exception as e:
                    print(f"      스크립트 로드 실패: {e}")
            
            elif script.string:
                # 인라인 스크립트
                script_content = script.string
                
                # 로그인 관련 코드 찾기
                if any(keyword in script_content.lower() for keyword in ['login', 'signin', 'auth']):
                    print(f"\n인라인 스크립트 {i+1}에서 로그인 관련 코드 발견:")
                    
                    # 함수 정의 찾기
                    functions = re.findall(r'function\s+\w+\s*\([^)]*\)\s*{[^}]*login[^}]*}', script_content, re.IGNORECASE | re.DOTALL)
                    for func in functions:
                        print(f"      함수: {func[:300]}...")
                    
                    # Ajax/Fetch 호출 찾기
                    ajax_calls = re.findall(r'(?:ajax|fetch|post)\s*\([^}]*\)', script_content, re.IGNORECASE | re.DOTALL)
                    for call in ajax_calls:
                        print(f"      Ajax 호출: {call[:200]}...")
                    
                    # 이벤트 리스너 찾기
                    events = re.findall(r'addEventListener\s*\([^}]*\)', script_content, re.IGNORECASE | re.DOTALL)
                    for event in events:
                        print(f"      이벤트: {event[:150]}...")
        
        # 폼 action 다시 확인
        forms = soup.find_all('form')
        print(f"\n폼 분석:")
        for form in forms:
            print(f"   Action: {form.get('action', 'None')}")
            print(f"   Method: {form.get('method', 'None')}")
            print(f"   ID: {form.get('id', 'None')}")
            print(f"   Class: {form.get('class', 'None')}")
            
            # 폼과 연결된 JavaScript 찾기
            form_id = form.get('id')
            if form_id and any(script.string and form_id in script.string for script in scripts):
                print(f"   폼 {form_id}와 연결된 JavaScript 발견")
        
        # 버튼 분석
        buttons = soup.find_all(['button', 'input'], type=['button', 'submit'])
        print(f"\n버튼 분석:")
        for button in buttons:
            onclick = button.get('onclick', '')
            if onclick:
                print(f"   버튼 onclick: {onclick}")
            
            button_id = button.get('id', '')
            if button_id:
                print(f"   버튼 ID: {button_id}")
                
                # 이 버튼과 관련된 JavaScript 찾기
                for script in scripts:
                    if script.string and button_id in script.string:
                        lines = script.string.split('\n')
                        for line in lines:
                            if button_id in line:
                                print(f"      관련 코드: {line.strip()}")
        
    except Exception as e:
        print(f"분석 오류: {e}")

if __name__ == "__main__":
    analyze_secudium_javascript()