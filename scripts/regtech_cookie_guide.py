#!/usr/bin/env python3
"""
REGTECH 쿠키 기반 수집 가이드
"""

import requests
import json
from datetime import datetime

def show_cookie_guide():
    """쿠키 수집 가이드 출력"""
    print("=" * 70)
    print("🍪 REGTECH 쿠키 기반 수집 가이드")
    print("=" * 70)
    
    print("\n📋 단계별 진행 방법:")
    print("1️⃣ 브라우저에서 REGTECH 로그인")
    print("   - URL: https://regtech.fsec.or.kr/login/loginForm")
    print("   - ID: nextrade")
    print("   - PW: Sprtmxm1@3")
    
    print("\n2️⃣ 개발자 도구에서 쿠키 확인")
    print("   - F12 키 눌러 개발자 도구 열기")
    print("   - Application 탭 → Cookies → regtech.fsec.or.kr")
    print("   - 또는 Network 탭에서 요청 헤더의 Cookie 값")
    
    print("\n3️⃣ 중요한 쿠키들:")
    print("   - JSESSIONID: 세션 유지")
    print("   - regtech-front: 프론트엔드 세션")
    print("   - loginToken: 인증 토큰 (있는 경우)")
    
    print("\n4️⃣ 쿠키 문자열 형식:")
    print("   JSESSIONID=ABC123; regtech-front=XYZ789; ...")
    
    print("\n📝 쿠키 복사 방법:")
    print("   Chrome: Network 탭 → 요청 선택 → Headers → Request Headers → Cookie")
    print("   Firefox: Network 탭 → 요청 선택 → Headers → Request Headers → Cookie")
    
    print("\n⚠️ 보안 주의사항:")
    print("   - 쿠키는 민감한 인증 정보입니다")
    print("   - 타인과 공유하지 마세요")
    print("   - 세션 만료 시 재로그인 필요")

def test_cookie_format():
    """쿠키 형식 테스트"""
    print("\n" + "=" * 70)
    print("🧪 쿠키 형식 테스트")
    print("=" * 70)
    
    # 테스트 쿠키 예시
    test_cookies = {
        'JSESSIONID': '1234567890ABCDEF',
        'regtech-front': 'SAMPLE-SESSION-ID',
        'Path': '/',
        'loginToken': 'sample-auth-token-123'
    }
    
    print("\n📋 테스트 쿠키 예시:")
    for name, value in test_cookies.items():
        print(f"   {name}={value}")
    
    # 쿠키 문자열 생성
    cookie_string = '; '.join([f"{name}={value}" for name, value in test_cookies.items()])
    print(f"\n🔗 결합된 쿠키 문자열:")
    print(f"   {cookie_string}")
    
    return cookie_string

def create_cookie_collection_script():
    """실제 쿠키 수집 스크립트 생성"""
    script_content = '''#!/usr/bin/env python3
"""
REGTECH 실제 쿠키 수집 스크립트
브라우저에서 복사한 쿠키로 데이터 수집
"""

import requests
import json
import re
from datetime import datetime, timedelta

# 여기에 브라우저에서 복사한 쿠키 문자열 입력
COOKIE_STRING = ""  # 예: "JSESSIONID=ABC123; regtech-front=XYZ789"

def collect_with_cookies():
    session = requests.Session()
    
    # 쿠키 설정
    if COOKIE_STRING:
        for cookie in COOKIE_STRING.split(';'):
            if '=' in cookie:
                name, value = cookie.strip().split('=', 1)
                session.cookies.set(name, value)
    
    # 헤더 설정
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://regtech.fsec.or.kr/'
    })
    
    # 데이터 수집 시도
    urls = [
        'https://regtech.fsec.or.kr/board/boardList?menuCode=HPHB0620101',
        'https://regtech.fsec.or.kr/main',
        'https://regtech.fsec.or.kr/api/blacklist/list'
    ]
    
    for url in urls:
        try:
            response = session.get(url, verify=False, timeout=30)
            print(f"URL: {url}")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                # IP 패턴 찾기
                ip_pattern = r'\\b(?:\\d{1,3}\\.){3}\\d{1,3}\\b'
                ips = re.findall(ip_pattern, response.text)
                
                if ips:
                    unique_ips = list(set(ips))[:10]  # 처음 10개
                    print(f"Found IPs: {unique_ips}")
                    
                    # 결과 저장
                    result = {
                        'source': 'REGTECH',
                        'url': url,
                        'collected_at': datetime.now().isoformat(),
                        'ips': unique_ips
                    }
                    
                    filename = f"regtech_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    with open(filename, 'w') as f:
                        json.dump(result, f, indent=2)
                    
                    print(f"Saved: {filename}")
                    break
                    
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    if not COOKIE_STRING:
        print("⚠️ COOKIE_STRING 변수에 브라우저 쿠키를 설정하세요")
    else:
        collect_with_cookies()
'''
    
    with open('regtech_cookie_collector.py', 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"\n💾 스크립트 생성: regtech_cookie_collector.py")
    print(f"   1. 파일을 열어서 COOKIE_STRING 변수에 쿠키 입력")
    print(f"   2. python3 regtech_cookie_collector.py 실행")

def show_curl_examples():
    """curl 명령어 예시"""
    print("\n" + "=" * 70)
    print("🌐 curl 명령어 예시")
    print("=" * 70)
    
    print(f"\n📝 기본 형태:")
    print(f'curl -H "Cookie: JSESSIONID=YOUR_SESSION_ID; regtech-front=YOUR_FRONT_ID" \\')
    print(f'     -H "User-Agent: Mozilla/5.0..." \\')
    print(f'     "https://regtech.fsec.or.kr/board/boardList?menuCode=HPHB0620101"')
    
    print(f"\n📝 Excel 다운로드:")
    print(f'curl -H "Cookie: YOUR_COOKIES" \\')
    print(f'     -o "blacklist.xlsx" \\')
    print(f'     "https://regtech.fsec.or.kr/board/excelDownload?menuCode=HPHB0620101"')

def main():
    show_cookie_guide()
    test_cookie_format()
    create_cookie_collection_script()
    show_curl_examples()
    
    print("\n" + "=" * 70)
    print("✅ 가이드 생성 완료")
    print("=" * 70)
    print("\n다음 단계:")
    print("1. 브라우저에서 REGTECH 로그인")
    print("2. 쿠키 복사")
    print("3. regtech_cookie_collector.py 수정")
    print("4. 스크립트 실행")

if __name__ == "__main__":
    main()