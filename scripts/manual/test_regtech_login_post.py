#!/usr/bin/env python3
"""
REGTECH POST 로그인 테스트
PowerShell 스크립트를 Python으로 변환
"""
import requests
from urllib.parse import quote

def test_login_post():
    """POST 방식으로 직접 로그인"""
    print("🔐 REGTECH POST 로그인 테스트\n")
    
    session = requests.Session()
    
    # 쿠키 설정 (PowerShell과 동일)
    session.cookies.set('_ga', 'GA1.1.215465125.1748404470', domain='.fsec.or.kr', path='/')
    session.cookies.set('regtech-front', 'DD67ADD62D6F8B127F3F5D9367FF4567', domain='regtech.fsec.or.kr', path='/')
    session.cookies.set('_ga_7WRDYHF66J', 'GS2.1.s1751032862$o16$g1$t1751040133$j52$l0$h0', domain='.fsec.or.kr', path='/')
    
    # 헤더 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Origin': 'https://regtech.fsec.or.kr',
        'Referer': 'https://regtech.fsec.or.kr/login/loginForm',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }
    
    # 로그인 데이터 (PowerShell과 동일)
    login_data = {
        'login_error': '',
        'txId': '',
        'token': '',
        'memberId': '',
        'smsTimeExcess': 'N',
        'username': 'nextrade',
        'password': 'Sprtmxm1@3'  # URL 인코딩 불필요 (requests가 자동 처리)
    }
    
    try:
        print("📤 로그인 요청 전송...")
        response = session.post(
            'https://regtech.fsec.or.kr/login/addLogin',
            headers=headers,
            data=login_data,
            allow_redirects=False,  # 리다이렉트 수동 처리
            timeout=30
        )
        
        print(f"응답 상태: {response.status_code}")
        
        # 응답 헤더 확인
        if 'Location' in response.headers:
            print(f"리다이렉트: {response.headers['Location']}")
            
            # 에러 확인
            if 'error=true' in response.headers['Location']:
                print("❌ 로그인 실패 - error=true")
                return None
        
        # 쿠키 확인
        print("\n🍪 응답 쿠키:")
        for cookie in session.cookies:
            print(f"  {cookie.name}: {cookie.value[:50]}...")
            
            # Bearer token 찾기
            if cookie.name == 'regtech-va' and cookie.value.startswith('Bearer'):
                print(f"\n✅ Bearer Token 발견!")
                print(f"토큰: {cookie.value[:100]}...")
                return cookie.value
        
        # 리다이렉트 따라가기
        if response.status_code == 302 and 'Location' in response.headers:
            print("\n📍 리다이렉트 따라가기...")
            redirect_url = response.headers['Location']
            if not redirect_url.startswith('http'):
                redirect_url = f"https://regtech.fsec.or.kr{redirect_url}"
                
            redirect_resp = session.get(redirect_url, headers=headers, timeout=30)
            print(f"리다이렉트 응답: {redirect_resp.status_code}")
            
            # 다시 쿠키 확인
            for cookie in session.cookies:
                if cookie.name == 'regtech-va' and cookie.value.startswith('Bearer'):
                    print(f"\n✅ Bearer Token 발견 (리다이렉트 후)!")
                    print(f"토큰: {cookie.value[:100]}...")
                    return cookie.value
        
        # 응답 본문 일부 확인
        if len(response.text) < 1000:
            print(f"\n응답 본문: {response.text}")
        else:
            # 로그인 성공 여부 확인
            if 'logout' in response.text or '로그아웃' in response.text:
                print("✅ 로그인 성공한 것으로 보임")
            elif 'login' in response.text or '로그인' in response.text:
                print("❌ 아직 로그인 페이지")
                
        return None
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_with_token(token):
    """얻은 토큰으로 데이터 접근 테스트"""
    if not token:
        return
        
    print(f"\n🧪 토큰 유효성 테스트...")
    
    session = requests.Session()
    session.cookies.set('regtech-va', token, domain='regtech.fsec.or.kr', path='/')
    
    try:
        response = session.get(
            'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList',
            timeout=30,
            allow_redirects=False
        )
        
        if response.status_code == 200:
            print("✅ Advisory 페이지 접근 성공!")
            
            # 로그인 확인
            if 'login' not in response.url and 'loginForm' not in response.text:
                print("✅ 토큰이 유효합니다!")
                return True
            else:
                print("❌ 로그인 페이지로 리다이렉트됨")
        else:
            print(f"❌ 접근 실패: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")
        
    return False


if __name__ == "__main__":
    # 로그인 시도
    bearer_token = test_login_post()
    
    if bearer_token:
        print(f"\n🎉 Bearer Token 획득 성공!")
        print(f"\n사용법:")
        print(f"export REGTECH_BEARER_TOKEN=\"{bearer_token}\"")
        
        # 토큰 테스트
        test_with_token(bearer_token)
    else:
        print("\n💥 Bearer Token을 얻지 못했습니다.")
        print("\n가능한 원인:")
        print("1. 비밀번호가 변경됨")
        print("2. 계정이 잠김")
        print("3. 추가 인증 필요 (OTP 등)")
        print("4. 쿠키 값이 만료됨")