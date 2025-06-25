#!/usr/bin/env python3
"""
수집기 수정 스크립트
REGTECH와 SECUDIUM 수집기의 인증 문제를 해결합니다.
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트 추가
sys.path.append(str(Path(__file__).parent.parent))

# 간단한 설정 클래스
class SimpleSettings:
    """환경변수 기반 간단한 설정"""
    regtech_username = os.getenv('REGTECH_USERNAME', 'nextrade')
    regtech_password = os.getenv('REGTECH_PASSWORD', 'Sprtmxm1@3')
    secudium_username = os.getenv('SECUDIUM_USERNAME', 'nextrade')
    secudium_password = os.getenv('SECUDIUM_PASSWORD', 'Sprtmxm1@3')
    secudium_base_url = os.getenv('SECUDIUM_BASE_URL', 'https://secudium.skinfosec.co.kr')

settings = SimpleSettings()

def test_regtech_simple():
    """REGTECH 간단한 수집 테스트"""
    print("\n" + "="*60)
    print("REGTECH 간단한 수집 테스트")
    print("="*60)
    
    try:
        # 직접 구현
        base_url = "https://regtech.fsec.or.kr"
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 1. 로그인 폼 접근
        print("1. 로그인 폼 접근...")
        form_resp = session.get(f"{base_url}/login/loginForm", timeout=30)
        print(f"   상태: {form_resp.status_code}")
        
        # 2. 로그인 시도
        print("2. 로그인 시도...")
        login_data = {
            'memberId': settings.regtech_username,
            'memberPw': settings.regtech_password,
            'userType': '1'
        }
        
        login_resp = session.post(
            f"{base_url}/login/addLogin",
            data=login_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': f"{base_url}/login/loginForm"
            },
            timeout=30,
            allow_redirects=False
        )
        
        print(f"   상태: {login_resp.status_code}")
        print(f"   리다이렉트: {login_resp.headers.get('Location', 'None')}")
        
        # 로그인 실패 확인
        if 'error=true' in str(login_resp.headers.get('Location', '')):
            print("   ❌ 로그인 실패 - 자격증명 오류")
            print("   현재 REGTECH 서버가 로그인을 거부하고 있습니다.")
            print("   가능한 원인:")
            print("   - 비밀번호 변경됨")
            print("   - 계정 잠김")
            print("   - 서버 정책 변경")
            return False
        
        # 3. 블랙리스트 데이터 수집 시도
        print("3. 블랙리스트 데이터 수집 시도...")
        
        # advisoryList 페이지 접근 (세션 확인)
        advisory_resp = session.get(f"{base_url}/fcti/securityAdvisory/advisoryList", timeout=30)
        if 'login' in advisory_resp.url:
            print("   ❌ 세션 인증 실패")
            return False
        
        # 블랙리스트 데이터 요청
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        post_data = {
            'page': '0',
            'tabSort': 'blacklist',
            'startDate': start_date.strftime('%Y%m%d'),
            'endDate': end_date.strftime('%Y%m%d'),
            'findKeyword': '',
            'size': '5000'
        }
        
        data_resp = session.post(
            f"{base_url}/fcti/securityAdvisory/advisoryList",
            data=post_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': f"{base_url}/fcti/securityAdvisory/advisoryList"
            },
            timeout=30
        )
        
        print(f"   상태: {data_resp.status_code}")
        print(f"   응답 크기: {len(data_resp.text)} bytes")
        
        if data_resp.status_code == 200 and len(data_resp.text) > 1000:
            # HTML에서 IP 추출 (간단한 정규식)
            import re
            ip_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
            ips = re.findall(ip_pattern, data_resp.text)
            print(f"   ✅ 추출된 IP 개수: {len(set(ips))}")
            return True
        else:
            print("   ❌ 데이터 수집 실패")
            return False
            
    except Exception as e:
        print(f"오류 발생: {e}")
        return False

def test_secudium_simple():
    """SECUDIUM 간단한 수집 테스트"""
    print("\n" + "="*60)
    print("SECUDIUM 간단한 수집 테스트")
    print("="*60)
    
    try:
        # 올바른 URL 사용
        base_url = settings.secudium_base_url
        print(f"Base URL: {base_url}")
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 1. 로그인 페이지 접근
        print("1. 로그인 페이지 접근...")
        try:
            login_page = session.get(f"{base_url}/login", timeout=30)
            print(f"   상태: {login_page.status_code}")
        except Exception as e:
            print(f"   ❌ 연결 실패: {e}")
            return False
        
        # 2. 로그인 시도
        print("2. 로그인 시도...")
        login_data = {
            'lang': 'ko',
            'is_otp': 'N',
            'is_expire': 'Y',
            'login_name': settings.secudium_username,
            'password': settings.secudium_password,
            'otp_value': ''
        }
        
        login_resp = session.post(
            f"{base_url}/isap-api/loginProcess",
            data=login_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': f"{base_url}/login"
            },
            timeout=30
        )
        
        print(f"   상태: {login_resp.status_code}")
        
        # 응답 확인
        if login_resp.status_code == 200:
            try:
                result = login_resp.json()
                if result.get('error'):
                    print(f"   ❌ 로그인 실패: {result.get('message', 'Unknown error')}")
                    return False
                else:
                    print("   ✅ 로그인 성공")
            except:
                # JSON이 아닌 경우 HTML 확인
                if 'logout' in login_resp.text or 'DashBoard' in login_resp.text:
                    print("   ✅ 로그인 성공 (HTML 응답)")
                else:
                    print("   ❌ 로그인 실패")
                    return False
        
        # 3. 블랙리스트 데이터 수집
        print("3. 블랙리스트 데이터 수집...")
        
        # 날짜 설정
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        params = {
            'board_idx': '',
            'view_count': '100',
            'search_keyword': '',
            'page': '1',
            'sort_key': 'REG_DT',
            'sort_type': 'DESC',
            'view_mode': 'card',
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }
        
        data_resp = session.get(
            f"{base_url}/secinfo/black_ip",
            params=params,
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': f"{base_url}/secinfo/black_ip"
            },
            timeout=30
        )
        
        print(f"   상태: {data_resp.status_code}")
        
        if data_resp.status_code == 200:
            try:
                data = data_resp.json()
                items = data.get('list', [])
                print(f"   ✅ 수집된 IP 개수: {len(items)}")
                return True
            except:
                print("   ❌ 데이터 파싱 실패")
                return False
        else:
            print("   ❌ 데이터 수집 실패")
            return False
            
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_simple_collectors():
    """간단한 수집기 생성"""
    print("\n" + "="*60)
    print("간단한 수집기 파일 생성")
    print("="*60)
    
    # REGTECH 수집기
    regtech_content = '''#!/usr/bin/env python3
"""
REGTECH 간단한 수집기
환경변수 문제를 피하기 위한 독립 실행 수집기
"""
import os
import requests
import re
import json
from datetime import datetime, timedelta
from pathlib import Path

class SimpleRegtechCollector:
    def __init__(self):
        self.base_url = "https://regtech.fsec.or.kr"
        self.username = os.getenv('REGTECH_USERNAME', 'nextrade')
        self.password = os.getenv('REGTECH_PASSWORD', 'Sprtmxm1@3')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def collect(self):
        """데이터 수집"""
        print("REGTECH 수집 시작...")
        
        # 로그인
        login_data = {
            'memberId': self.username,
            'memberPw': self.password,
            'userType': '1'
        }
        
        login_resp = self.session.post(
            f"{self.base_url}/login/addLogin",
            data=login_data,
            timeout=30
        )
        
        if 'error=true' in login_resp.url:
            print("로그인 실패")
            return []
        
        # 데이터 수집
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        post_data = {
            'page': '0',
            'tabSort': 'blacklist',
            'startDate': start_date.strftime('%Y%m%d'),
            'endDate': end_date.strftime('%Y%m%d'),
            'size': '5000'
        }
        
        resp = self.session.post(
            f"{self.base_url}/fcti/securityAdvisory/advisoryList",
            data=post_data,
            timeout=30
        )
        
        # IP 추출
        ip_pattern = r'\\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\b'
        ips = list(set(re.findall(ip_pattern, resp.text)))
        
        print(f"수집된 IP: {len(ips)}개")
        return ips

if __name__ == "__main__":
    collector = SimpleRegtechCollector()
    ips = collector.collect()
    
    # 결과 저장
    Path("data").mkdir(exist_ok=True)
    with open("data/regtech_ips.json", "w") as f:
        json.dump({"ips": ips, "collected_at": datetime.now().isoformat()}, f, indent=2)
'''
    
    # SECUDIUM 수집기
    secudium_content = '''#!/usr/bin/env python3
"""
SECUDIUM 간단한 수집기
환경변수 문제를 피하기 위한 독립 실행 수집기
"""
import os
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path

class SimpleSecudiumCollector:
    def __init__(self):
        self.base_url = os.getenv('SECUDIUM_BASE_URL', 'https://secudium.skinfosec.co.kr')
        self.username = os.getenv('SECUDIUM_USERNAME', 'nextrade')
        self.password = os.getenv('SECUDIUM_PASSWORD', 'Sprtmxm1@3')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def collect(self):
        """데이터 수집"""
        print(f"SECUDIUM 수집 시작... (URL: {self.base_url})")
        
        # 로그인
        login_data = {
            'lang': 'ko',
            'is_otp': 'N',
            'is_expire': 'Y',
            'login_name': self.username,
            'password': self.password,
            'otp_value': ''
        }
        
        login_resp = self.session.post(
            f"{self.base_url}/isap-api/loginProcess",
            data=login_data,
            timeout=30
        )
        
        if login_resp.status_code != 200:
            print("로그인 실패")
            return []
        
        # 데이터 수집
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        params = {
            'view_count': '1000',
            'page': '1',
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }
        
        resp = self.session.get(
            f"{self.base_url}/secinfo/black_ip",
            params=params,
            timeout=30
        )
        
        if resp.status_code != 200:
            print("데이터 수집 실패")
            return []
        
        # IP 추출
        data = resp.json()
        ips = [item.get('mal_ip') for item in data.get('list', []) if item.get('mal_ip')]
        
        print(f"수집된 IP: {len(ips)}개")
        return ips

if __name__ == "__main__":
    collector = SimpleSecudiumCollector()
    ips = collector.collect()
    
    # 결과 저장
    Path("data").mkdir(exist_ok=True)
    with open("data/secudium_ips.json", "w") as f:
        json.dump({"ips": ips, "collected_at": datetime.now().isoformat()}, f, indent=2)
'''
    
    # 파일 저장
    Path("scripts/collection").mkdir(parents=True, exist_ok=True)
    
    with open("scripts/collection/simple_regtech_collector.py", "w") as f:
        f.write(regtech_content)
    print("✅ scripts/collection/simple_regtech_collector.py 생성됨")
    
    with open("scripts/collection/simple_secudium_collector.py", "w") as f:
        f.write(secudium_content)
    print("✅ scripts/collection/simple_secudium_collector.py 생성됨")

def main():
    """메인 함수"""
    print("수집기 문제 해결 도구")
    print(f"실행 시간: {datetime.now()}")
    
    # 간단한 테스트
    regtech_ok = test_regtech_simple()
    secudium_ok = test_secudium_simple()
    
    # 간단한 수집기 생성
    create_simple_collectors()
    
    print("\n" + "="*60)
    print("진단 결과")
    print("="*60)
    print(f"REGTECH: {'❌ 인증 실패 (서버 정책 변경)' if not regtech_ok else '✅ 정상'}")
    print(f"SECUDIUM: {'✅ 정상' if secudium_ok else '❌ 실패'}")
    
    print("\n권장 사항:")
    print("1. REGTECH: 관리자에게 계정 상태 확인 요청")
    print("2. SECUDIUM: 생성된 simple_secudium_collector.py 사용")
    print("3. 환경변수 설정 확인:")
    print("   export SECUDIUM_BASE_URL='https://secudium.skinfosec.co.kr'")

if __name__ == "__main__":
    main()