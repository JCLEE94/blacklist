#!/usr/bin/env python3
"""
REGTECH 로그인 프로세스 상세 디버깅
"""
import requests
from bs4 import BeautifulSoup
import json

def debug_login_process():
    """로그인 프로세스 상세 분석"""
    print("🔍 REGTECH 로그인 프로세스 디버깅\n")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    try:
        # 1. 메인 페이지 - 세션 초기화
        print("1. 메인 페이지 접속...")
        main_resp = session.get('https://regtech.fsec.or.kr/main/main', timeout=30)
        print(f"   Status: {main_resp.status_code}")
        print(f"   Cookies after main: {list(session.cookies.keys())}")
        
        # 2. 로그인 페이지
        print("\n2. 로그인 페이지 접속...")
        login_page = session.get('https://regtech.fsec.or.kr/login/loginForm', timeout=30)
        print(f"   Status: {login_page.status_code}")
        
        # 로그인 페이지에서 추가 정보 추출
        soup = BeautifulSoup(login_page.text, 'html.parser')
        
        # CSRF 토큰이나 hidden 필드 확인
        form = soup.find('form')
        if form:
            hidden_inputs = form.find_all('input', {'type': 'hidden'})
            if hidden_inputs:
                print("   Hidden fields found:")
                for inp in hidden_inputs:
                    print(f"     - {inp.get('name', 'unnamed')}: {inp.get('value', 'no-value')}")
        
        # 3. 로그인 시도 - 다양한 방법
        print("\n3. 로그인 시도...")
        
        # 방법 1: 원래 방식
        login_data = {
            'memberId': 'nextrade',
            'memberPw': 'Sprtmxm1@3'
        }
        
        print("   방법 1: addLogin 엔드포인트")
        login_resp = session.post(
            'https://regtech.fsec.or.kr/login/addLogin',
            data=login_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Referer': 'https://regtech.fsec.or.kr/login/loginForm'
            },
            timeout=30,
            allow_redirects=False
        )
        
        print(f"   Status: {login_resp.status_code}")
        print(f"   Response type: {login_resp.headers.get('Content-Type', 'unknown')}")
        
        # 응답 분석
        if login_resp.status_code == 200:
            # JSON 응답 시도
            try:
                result = login_resp.json()
                print(f"   JSON Response: {json.dumps(result, ensure_ascii=False, indent=2)}")
            except:
                # HTML 응답인 경우
                print("   Not JSON response")
                if len(login_resp.text) < 500:
                    print(f"   Response: {login_resp.text}")
                else:
                    # 오류 메시지 찾기
                    error_soup = BeautifulSoup(login_resp.text, 'html.parser')
                    error_msgs = error_soup.find_all(text=lambda t: 'error' in t.lower() or '오류' in t or '실패' in t)
                    if error_msgs:
                        print("   Error messages found:")
                        for msg in error_msgs[:3]:
                            print(f"     - {msg.strip()}")
        
        # 리다이렉트 확인
        if 'Location' in login_resp.headers:
            print(f"   Redirect to: {login_resp.headers['Location']}")
            
            # 리다이렉트 URL에 error 파라미터 확인
            if 'error=' in login_resp.headers['Location']:
                print("   ❌ 로그인 실패 - error 파라미터 감지")
        
        # 쿠키 확인
        print(f"\n   Cookies after login: {list(session.cookies.keys())}")
        for cookie in session.cookies:
            if 'auth' in cookie.name.lower() or 'token' in cookie.name.lower():
                print(f"     - {cookie.name}: {cookie.value[:20]}...")
        
        # 4. 로그인 성공 확인
        print("\n4. 로그인 성공 여부 확인...")
        
        # Advisory 페이지 접근
        test_resp = session.get(
            'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList',
            timeout=30,
            allow_redirects=False
        )
        
        print(f"   Advisory Status: {test_resp.status_code}")
        
        if test_resp.status_code == 302:
            print(f"   ❌ Redirected to: {test_resp.headers.get('Location', 'unknown')}")
            print("   로그인이 되지 않았습니다.")
        elif test_resp.status_code == 200:
            # 로그인 폼이 있는지 확인
            test_soup = BeautifulSoup(test_resp.text, 'html.parser')
            if test_soup.find('form', {'id': 'loginForm'}) or 'login' in test_resp.url:
                print("   ❌ 로그인 페이지가 표시됨")
            else:
                print("   ✅ Advisory 페이지 접근 성공!")
                
                # 사용자 정보 확인
                user_info = test_soup.find(text=lambda t: 'nextrade' in t if t else False)
                if user_info:
                    print(f"   로그인 사용자: {user_info.strip()}")
                
                return True
        
        # 5. 대체 로그인 방법 시도
        print("\n5. 대체 방법: loginProc 엔드포인트 시도...")
        
        # 새 세션으로 재시도
        new_session = requests.Session()
        new_session.headers.update(session.headers)
        
        # 메인 페이지
        new_session.get('https://regtech.fsec.or.kr/main/main', timeout=30)
        
        # 로그인 페이지
        new_session.get('https://regtech.fsec.or.kr/login/loginForm', timeout=30)
        
        # loginProc 엔드포인트 시도
        alt_login_resp = new_session.post(
            'https://regtech.fsec.or.kr/login/loginProc',
            data=login_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': 'https://regtech.fsec.or.kr/login/loginForm'
            },
            timeout=30,
            allow_redirects=True
        )
        
        print(f"   Alt Login Status: {alt_login_resp.status_code}")
        print(f"   Final URL: {alt_login_resp.url}")
        
        if 'main' in alt_login_resp.url or 'advisory' in alt_login_resp.url:
            print("   ✅ 대체 로그인 성공!")
            return True
        
        return False
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_login_process()
    if success:
        print("\n✅ 로그인 프로세스 성공!")
    else:
        print("\n❌ 로그인 프로세스 실패")
        print("\n💡 가능한 원인:")
        print("   1. 계정이 잠겼거나 비밀번호가 변경됨")
        print("   2. 서버에서 추가 인증 요구 (OTP, CAPTCHA 등)")
        print("   3. API 엔드포인트가 변경됨")
        print("   4. IP 차단 또는 rate limiting")