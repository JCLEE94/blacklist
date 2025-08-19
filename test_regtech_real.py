#!/usr/bin/env python3
"""
REGTECH 실제 로그인 및 데이터 수집 테스트
"""

import requests
from datetime import datetime, timedelta
import json
import re

# SSL 경고 무시
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class REGTECHRealCollector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://regtech.fsec.or.kr',
            'Referer': 'https://regtech.fsec.or.kr/login/loginForm'
        })
        self.base_url = "https://regtech.fsec.or.kr"
        
    def login(self):
        """REGTECH 로그인"""
        print("🔐 REGTECH 로그인 시도...")
        
        # 1. 로그인 페이지 접속 (세션 쿠키 획득)
        login_page_url = f"{self.base_url}/login/loginForm"
        print(f"  1단계: 로그인 페이지 접속 {login_page_url}")
        
        try:
            response = self.session.get(login_page_url, verify=False, timeout=30)
            print(f"    상태 코드: {response.status_code}")
            
            # CSRF 토큰 찾기
            csrf_token = None
            if '_csrf' in response.text:
                match = re.search(r'name="_csrf"\s+value="([^"]+)"', response.text)
                if match:
                    csrf_token = match.group(1)
                    print(f"    CSRF 토큰 발견: {csrf_token[:20]}...")
            
            # 2. 로그인 요청
            login_url = f"{self.base_url}/login/loginProcess"
            print(f"  2단계: 로그인 처리 {login_url}")
            
            login_data = {
                'loginID': 'nextrade',
                'loginPW': 'Sprtmxm1@3',
                'saveID': 'N'
            }
            
            if csrf_token:
                login_data['_csrf'] = csrf_token
            
            # 로그인 헤더 추가
            login_headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            response = self.session.post(
                login_url,
                data=login_data,
                headers=login_headers,
                verify=False,
                timeout=30,
                allow_redirects=False
            )
            
            print(f"    상태 코드: {response.status_code}")
            
            # 3. 로그인 성공 확인
            if response.status_code in [200, 302]:
                # 리다이렉트 확인
                if 'location' in response.headers:
                    redirect_url = response.headers['location']
                    print(f"    리다이렉트: {redirect_url}")
                    
                    # 메인 페이지로 이동
                    if 'main' in redirect_url.lower() or 'index' in redirect_url.lower():
                        print("✅ 로그인 성공!")
                        return True
                
                # 응답 내용 확인
                if response.text:
                    if 'success' in response.text.lower() or '성공' in response.text:
                        print("✅ 로그인 성공!")
                        return True
                    elif 'fail' in response.text.lower() or '실패' in response.text:
                        print(f"❌ 로그인 실패: {response.text[:200]}")
                        return False
                
                # 세션 확인
                print("  3단계: 세션 확인")
                check_url = f"{self.base_url}/main"
                response = self.session.get(check_url, verify=False, timeout=30)
                
                if response.status_code == 200 and 'login' not in response.url.lower():
                    print("✅ 로그인 성공 (세션 확인)")
                    return True
                    
            print(f"❌ 로그인 실패")
            return False
            
        except Exception as e:
            print(f"❌ 로그인 오류: {e}")
            return False
    
    def search_blacklist(self):
        """블랙리스트 검색"""
        print("\n📊 블랙리스트 데이터 검색...")
        
        # 여러 가능한 URL 시도
        search_urls = [
            '/board/boardList?menuCode=HPHB0620101',  # 악성IP차단
            '/board/boardList?menuCode=HPHB0620102',  # 악성코드
            '/api/blacklist/search',
            '/threat/blacklist/list',
            '/security/iplist'
        ]
        
        collected_data = []
        
        for path in search_urls:
            url = f"{self.base_url}{path}"
            print(f"  시도: {url}")
            
            try:
                # 검색 파라미터
                params = {
                    'searchType': 'all',
                    'searchKeyword': '',
                    'startDate': (datetime.now() - timedelta(days=7)).strftime('%Y%m%d'),
                    'endDate': datetime.now().strftime('%Y%m%d'),
                    'pageIndex': 1,
                    'pageSize': 100
                }
                
                response = self.session.get(
                    url,
                    params=params,
                    verify=False,
                    timeout=30
                )
                
                print(f"    상태: {response.status_code}")
                
                if response.status_code == 200:
                    # HTML 파싱
                    if 'text/html' in response.headers.get('content-type', ''):
                        # IP 패턴 찾기
                        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
                        ips = re.findall(ip_pattern, response.text)
                        
                        if ips:
                            print(f"    ✅ {len(ips)}개 IP 발견")
                            for ip in ips[:10]:  # 처음 10개만
                                collected_data.append({
                                    'ip': ip,
                                    'source': 'REGTECH',
                                    'date': datetime.now().strftime('%Y-%m-%d'),
                                    'url': url
                                })
                            break
                    
                    # JSON 응답
                    elif 'application/json' in response.headers.get('content-type', ''):
                        data = response.json()
                        print(f"    JSON 응답: {list(data.keys())}")
                        
            except Exception as e:
                print(f"    오류: {e}")
                continue
        
        return collected_data
    
    def download_excel(self):
        """엑셀 파일 다운로드 시도"""
        print("\n📥 엑셀 다운로드 시도...")
        
        download_urls = [
            '/board/excelDownload',
            '/api/blacklist/export',
            '/threat/export/excel'
        ]
        
        for path in download_urls:
            url = f"{self.base_url}{path}"
            print(f"  시도: {url}")
            
            try:
                response = self.session.post(
                    url,
                    data={
                        'startDate': (datetime.now() - timedelta(days=1)).strftime('%Y%m%d'),
                        'endDate': datetime.now().strftime('%Y%m%d')
                    },
                    verify=False,
                    timeout=30
                )
                
                if response.status_code == 200:
                    # 엑셀 파일인지 확인
                    content_type = response.headers.get('content-type', '')
                    if 'excel' in content_type or 'spreadsheet' in content_type:
                        print(f"    ✅ 엑셀 파일 다운로드 성공")
                        
                        # 파일 저장
                        filename = f"regtech_blacklist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        with open(filename, 'wb') as f:
                            f.write(response.content)
                        print(f"    💾 저장: {filename}")
                        return filename
                        
            except Exception as e:
                print(f"    오류: {e}")
                
        return None

def main():
    print("=" * 60)
    print("REGTECH 실제 로그인 및 데이터 수집 테스트")
    print("=" * 60)
    
    collector = REGTECHRealCollector()
    
    # 1. 로그인
    if not collector.login():
        print("\n❌ 로그인 실패로 테스트 중단")
        return
    
    # 2. 블랙리스트 검색
    blacklist_data = collector.search_blacklist()
    
    if blacklist_data:
        print(f"\n✅ 수집 성공: {len(blacklist_data)}개 항목")
        
        # JSON 저장
        output_file = f"regtech_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(blacklist_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 저장: {output_file}")
        
        # 샘플 출력
        print("\n📋 수집된 데이터 샘플:")
        for item in blacklist_data[:5]:
            print(f"  - IP: {item['ip']}")
    else:
        print("\n⚠️ 블랙리스트 데이터를 찾을 수 없습니다")
    
    # 3. 엑셀 다운로드 시도
    excel_file = collector.download_excel()
    if excel_file:
        print(f"\n✅ 엑셀 파일 다운로드 완료: {excel_file}")

if __name__ == "__main__":
    main()