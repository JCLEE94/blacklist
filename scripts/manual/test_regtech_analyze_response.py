#!/usr/bin/env python3
"""
REGTECH 응답 분석 - JavaScript 코드 확인
"""
import requests
from bs4 import BeautifulSoup
import re
import json

def analyze_regtech_response():
    """REGTECH 응답의 JavaScript 코드 분석"""
    print("🔍 REGTECH 응답 분석")
    
    base_url = "https://regtech.fsec.or.kr"
    bearer_token = "BearereyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJuZXh0cmFkZSIsIm9yZ2FubmFtZSI6IuuEpeyKpO2KuOugiIzydtOuTnCIsImlkIjoibmV4dHJhZGUiLCJleHAiOjE3NTExMTkyNzYsInVzZXJuYW1lIjoi7J6l7ZmN7KSAIn0.YwZHoHZCVqDnaryluB0h5_ituxYcaRz4voT7GRfgrNrP86W8TfvBuJbHMON4tJa4AQmNP-XhC_PuAVPQTjJADA"
    
    session = requests.Session()
    session.cookies.set('regtech-va', bearer_token, domain='regtech.fsec.or.kr', path='/')
    
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })
    
    try:
        # POST 요청
        form_data = {
            'page': '0',
            'tabSort': 'blacklist',
            'startDate': '20250301',
            'endDate': '20250627',
            'size': '100'
        }
        
        response = session.post(
            f"{base_url}/fcti/securityAdvisory/advisoryList",
            data=form_data,
            timeout=30
        )
        
        print(f"응답 상태: {response.status_code}")
        print(f"응답 크기: {len(response.text)} bytes")
        
        # HTML 파싱
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. JavaScript 함수 찾기
        scripts = soup.find_all('script')
        print(f"\n📜 발견된 스크립트 태그: {len(scripts)}개")
        
        for i, script in enumerate(scripts):
            if script.string:
                content = script.string.strip()
                if len(content) > 50:  # 의미있는 스크립트만
                    print(f"\n--- 스크립트 {i+1} ---")
                    
                    # AJAX 호출 패턴 찾기
                    ajax_patterns = [
                        r'\.ajax\s*\(',
                        r'fetch\s*\(',
                        r'XMLHttpRequest',
                        r'advisoryList',
                        r'blacklist',
                        r'loadData',
                        r'getData',
                        r'pageMove',
                        r'search'
                    ]
                    
                    for pattern in ajax_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            print(f"✅ '{pattern}' 패턴 발견")
                            
                            # 해당 부분 추출
                            matches = re.finditer(pattern, content, re.IGNORECASE)
                            for match in matches:
                                start = max(0, match.start() - 100)
                                end = min(len(content), match.end() + 200)
                                context = content[start:end]
                                print(f"컨텍스트: ...{context}...")
        
        # 2. 숨겨진 입력 필드 찾기
        hidden_inputs = soup.find_all('input', type='hidden')
        print(f"\n🔐 숨겨진 입력 필드: {len(hidden_inputs)}개")
        for inp in hidden_inputs:
            print(f"  - {inp.get('name', 'N/A')}: {inp.get('value', 'N/A')}")
        
        # 3. 데이터 테이블 컨테이너 찾기
        data_containers = soup.find_all(['div', 'table'], id=re.compile(r'(list|data|result|blacklist)', re.I))
        print(f"\n📊 데이터 컨테이너 후보: {len(data_containers)}개")
        for container in data_containers:
            print(f"  - {container.name} id={container.get('id', 'N/A')} class={container.get('class', 'N/A')}")
        
        # 4. AJAX URL 패턴 찾기
        url_pattern = r'["\']([^"\']*(?:ajax|api|data|list|blacklist)[^"\']*)["\']'
        urls = re.findall(url_pattern, response.text, re.IGNORECASE)
        unique_urls = list(set(urls))
        
        print(f"\n🌐 발견된 URL 패턴: {len(unique_urls)}개")
        for url in unique_urls[:10]:  # 처음 10개만
            if not url.startswith('http') and not url.startswith('#'):
                print(f"  - {url}")
        
        # 5. 폼 액션 확인
        forms = soup.find_all('form')
        print(f"\n📝 폼: {len(forms)}개")
        for form in forms:
            print(f"  - action={form.get('action', 'N/A')} method={form.get('method', 'N/A')}")
        
        # 6. 데이터가 로드될 가능성이 있는 요소
        data_elements = soup.find_all(['tbody', 'ul', 'div'], class_=re.compile(r'(list|data|content|result)', re.I))
        print(f"\n🎯 데이터 로드 대상 요소: {len(data_elements)}개")
        for elem in data_elements[:5]:
            print(f"  - {elem.name} class={elem.get('class', 'N/A')} children={len(elem.find_all())}")
        
        # 응답 일부 저장 (디버깅용)
        with open('regtech_response.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("\n💾 응답이 regtech_response.html로 저장됨")
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_regtech_response()