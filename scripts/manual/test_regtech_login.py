#!/usr/bin/env python3
"""
REGTECH 로그인 테스트 - 수정된 방식
"""
import requests
import os

def test_regtech_login():
    """REGTECH 로그인 테스트"""
    print("🧪 REGTECH 로그인 테스트 시작")
    
    # 설정 로드
    username = "nextrade"
    password = "Sprtmxm1@3"
    base_url = "https://regtech.fsec.or.kr"
    
    print(f"Username: {username}")
    print(f"Base URL: {base_url}")
    
    # 세션 생성
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    try:
        # 1. 메인 페이지 접속
        print("1. 메인 페이지 접속...")
        main_resp = session.get(f"{base_url}/main/main", timeout=30)
        print(f"   메인 페이지: {main_resp.status_code}")
        
        # 2. 로그인 폼 접속
        print("2. 로그인 폼 접속...")
        form_resp = session.get(f"{base_url}/login/loginForm", timeout=30)
        print(f"   로그인 폼: {form_resp.status_code}")
        
        # 3. 로그인 수행
        print("3. 로그인 수행...")
        login_data = {
            'memberId': username,
            'memberPw': password
        }
        
        login_resp = session.post(
            f"{base_url}/login/addLogin",
            data=login_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': f"{base_url}/login/loginForm"
            },
            timeout=30
        )
        
        print(f"   로그인 응답: {login_resp.status_code}")
        print(f"   응답 내용: {login_resp.text[:200]}")
        
        # 4. IP 목록 페이지 접근 테스트
        print("4. IP 목록 페이지 접근...")
        test_resp = session.get(f"{base_url}/fcti/securityAdvisory/advisoryList", timeout=30)
        print(f"   IP 목록 페이지: {test_resp.status_code}")
        
        if test_resp.status_code == 200:
            print("   ✅ 로그인 성공! IP 목록 페이지 접근 가능")
            
            # IP 데이터 샘플 추출
            content = test_resp.text
            print(f"   페이지 길이: {len(content)} 바이트")
            
            # 5. blacklist 탭으로 직접 이동 시도
            print("5. blacklist 탭 데이터 가져오기...")
            
            # HAR 파일에서 보면 changeTab('blacklist') 같은 함수로 탭 변경
            # 실제 데이터는 AJAX로 로드될 수 있음
            blacklist_params = {
                'tab': 'blacklist',
                'page': '1',
                'size': '10'
            }
            
            blacklist_resp = session.get(
                f"{base_url}/fcti/securityAdvisory/advisoryList", 
                params=blacklist_params,
                timeout=30
            )
            
            print(f"   blacklist 탭 응답: {blacklist_resp.status_code}")
            blacklist_content = blacklist_resp.text
            
            if "요주의 IP" in blacklist_content or "IP" in blacklist_content:
                print("   ✅ blacklist 탭에서 IP 데이터 확인")
                
                # 총 건수 추출
                import re
                count_match = re.search(r'총\s*<em>\s*([0-9,]+)', blacklist_content)
                if count_match:
                    total_count = count_match.group(1)
                    print(f"   📊 총 IP 건수: {total_count}")
                
                # IP 주소 패턴 검색
                ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                ips = re.findall(ip_pattern, blacklist_content)
                if ips:
                    print(f"   📊 발견된 IP 샘플: {ips[:5]}")
                    return True
                else:
                    print("   ❌ IP 주소 패턴을 찾을 수 없음")
            else:
                print("   ❌ blacklist 탭에서도 IP 데이터 없음")
                
                # 페이지 내용에서 유용한 정보 찾기
                if "로그인" in blacklist_content:
                    print("   ⚠️ 여전히 로그인이 필요한 상태일 수 있음")
                
                # JavaScript 함수나 API 엔드포인트 찾기
                if "advisoryList" in blacklist_content:
                    print("   ✅ advisoryList 관련 코드 발견")
                
                if "blacklist" in blacklist_content.lower():
                    print("   ✅ blacklist 관련 코드 발견")
        elif test_resp.status_code == 302:
            print("   ❌ 로그인 실패 - 로그인 페이지로 리다이렉트")
            print(f"   리다이렉트 위치: {test_resp.headers.get('Location', 'N/A')}")
        else:
            print(f"   ⚠️ 예상하지 못한 응답: {test_resp.status_code}")
        
        return False
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    success = test_regtech_login()
    if success:
        print("\n🎉 REGTECH 로그인 및 데이터 접근 성공!")
    else:
        print("\n💥 REGTECH 로그인 또는 데이터 접근 실패")