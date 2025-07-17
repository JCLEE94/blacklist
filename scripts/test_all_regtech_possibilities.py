#!/usr/bin/env python3
"""
REGTECH 모든 가능성 테스트
- 다양한 인증 방식
- 다양한 다운로드 URL
- 다양한 파라미터 조합
"""

import requests
import json
import os
from datetime import datetime, timedelta
import logging
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RegtechAllPossibilitiesTest:
    def __init__(self):
        self.base_url = "https://regtech.fsec.or.kr"
        self.username = "nextrade"
        self.password = "Sprtmxm1@3"
        self.session = None
        
    def test_all_methods(self):
        """모든 방법 테스트"""
        
        # 1. 쿠키 기반 인증
        logger.info("=" * 50)
        logger.info("1. 쿠키 기반 인증 테스트")
        logger.info("=" * 50)
        self.test_cookie_auth()
        
        # 2. 표준 로그인
        logger.info("\n" + "=" * 50)
        logger.info("2. 표준 로그인 테스트")
        logger.info("=" * 50)
        self.test_standard_login()
        
        # 3. API 엔드포인트 탐색
        logger.info("\n" + "=" * 50)
        logger.info("3. API 엔드포인트 탐색")
        logger.info("=" * 50)
        self.test_api_endpoints()
        
        # 4. 페이지 내 JavaScript 분석
        logger.info("\n" + "=" * 50)
        logger.info("4. JavaScript 코드 분석")
        logger.info("=" * 50)
        self.analyze_javascript()
        
        # 5. Form 기반 다운로드
        logger.info("\n" + "=" * 50)
        logger.info("5. Form 기반 다운로드 테스트")
        logger.info("=" * 50)
        self.test_form_download()
        
    def test_cookie_auth(self):
        """쿠키 기반 인증"""
        # 쿠키 파일에서 로드
        cookie_file = "data/regtech/cookies.json"
        if os.path.exists(cookie_file):
            with open(cookie_file, 'r') as f:
                cookies = json.load(f)
            
            self.session = requests.Session()
            self.session.cookies.update(cookies)
            
            # 보안권고 페이지 테스트
            resp = self.session.get(f"{self.base_url}/fcti/securityAdvisory/advisoryList")
            logger.info(f"쿠키 인증 결과: {resp.status_code}")
            logger.info(f"최종 URL: {resp.url}")
            
            if 'login' not in resp.url:
                logger.info("✅ 쿠키 인증 성공")
                self.test_downloads_with_session()
            else:
                logger.info("❌ 쿠키 인증 실패")
                
    def test_standard_login(self):
        """표준 로그인 절차"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
        })
        
        # 1단계: 메인 페이지
        main_resp = self.session.get(f"{self.base_url}/")
        logger.info(f"메인 페이지: {main_resp.status_code}")
        
        # 2단계: 로그인 페이지
        login_page = self.session.get(f"{self.base_url}/fcti/login/loginPage")
        logger.info(f"로그인 페이지: {login_page.status_code}")
        
        # 3단계: 로그인 처리
        login_data = {
            'username': self.username,
            'password': self.password,
            'login_error': '',
            'txId': '',
            'token': '',
            'memberId': '',
            'smsTimeExcess': 'N'
        }
        
        login_resp = self.session.post(
            f"{self.base_url}/fcti/login/loginUser",
            data=login_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': self.base_url,
                'Referer': f"{self.base_url}/fcti/login/loginPage"
            }
        )
        
        logger.info(f"로그인 응답: {login_resp.status_code}")
        
        # 4단계: 리다이렉트 따라가기
        if login_resp.status_code in [302, 303]:
            location = login_resp.headers.get('Location', '')
            if location and not location.startswith('http'):
                location = self.base_url + location
            
            # 모든 리다이렉트 따라가기
            final_resp = self.session.get(location, allow_redirects=True)
            logger.info(f"최종 페이지: {final_resp.url}")
            
            # 보안권고 페이지 접속 시도
            advisory_resp = self.session.get(f"{self.base_url}/fcti/securityAdvisory/advisoryList")
            if 'login' not in advisory_resp.url:
                logger.info("✅ 표준 로그인 성공")
                self.test_downloads_with_session()
            else:
                logger.info("❌ 표준 로그인 실패")
                
    def test_downloads_with_session(self):
        """현재 세션으로 다운로드 테스트"""
        if not self.session:
            return
            
        # 날짜 설정
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        
        # 다양한 URL 패턴
        download_urls = [
            # 기본 URL들
            "/fcti/securityAdvisory/advisoryListDownloadXlsx",
            "/fcti/securityAdvisory/advisoryListDownload.xlsx",
            "/fcti/securityAdvisory/downloadExcel",
            "/fcti/securityAdvisory/download",
            "/fcti/securityAdvisory/excelDownload",
            
            # 확장자 포함
            "/fcti/securityAdvisory/advisoryList.xlsx",
            "/fcti/securityAdvisory/export.xlsx",
            
            # 액션 기반
            "/fcti/securityAdvisory/advisoryList.do?cmd=excel",
            "/fcti/securityAdvisory/advisoryList?download=excel",
            "/fcti/securityAdvisory/advisoryList?format=xlsx"
        ]
        
        # 다양한 파라미터 조합
        param_sets = [
            {
                'startDate': start_date,
                'endDate': end_date,
                'blockRule': '',
                'blockTarget': ''
            },
            {
                'start_date': start_date,
                'end_date': end_date,
                'block_rule': '',
                'block_target': ''
            },
            {
                'fromDate': start_date,
                'toDate': end_date,
                'blockRule': '',
                'blockTarget': ''
            },
            {
                'searchStartDate': start_date,
                'searchEndDate': end_date,
                'searchBlockRule': '',
                'searchBlockTarget': ''
            }
        ]
        
        for url in download_urls:
            full_url = self.base_url + url
            logger.info(f"\n테스트 URL: {full_url}")
            
            for i, params in enumerate(param_sets):
                try:
                    # GET 요청
                    resp = self.session.get(full_url, params=params, allow_redirects=False)
                    self.check_response(resp, f"GET 파라미터셋 {i+1}")
                    
                    # POST 요청
                    resp = self.session.post(full_url, data=params, allow_redirects=False)
                    self.check_response(resp, f"POST 파라미터셋 {i+1}")
                    
                except Exception as e:
                    logger.error(f"요청 실패: {e}")
                    
    def check_response(self, resp, method_name):
        """응답 확인"""
        logger.info(f"  {method_name}: {resp.status_code}")
        
        if resp.status_code == 200:
            content_type = resp.headers.get('Content-Type', '')
            logger.info(f"    Content-Type: {content_type}")
            
            # Excel 파일 확인
            if any(x in content_type.lower() for x in ['excel', 'spreadsheet', 'octet-stream', 'zip']):
                logger.info(f"    ✅ Excel 파일 감지! 크기: {len(resp.content)} bytes")
                
                # ZIP 헤더 확인 (Excel은 ZIP 형식)
                if resp.content[:2] == b'PK':
                    logger.info("    ✅ 유효한 ZIP/Excel 파일!")
                    
                    # 파일 저장
                    filename = f"test_download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    with open(filename, 'wb') as f:
                        f.write(resp.content)
                    logger.info(f"    파일 저장: {filename}")
                    
                    # pandas로 읽기 시도
                    try:
                        import pandas as pd
                        df = pd.read_excel(filename)
                        logger.info(f"    ✅ Excel 파일 파싱 성공! 행 수: {len(df)}")
                        logger.info(f"    컬럼: {list(df.columns)}")
                        return True
                    except Exception as e:
                        logger.error(f"    ❌ Excel 파싱 실패: {e}")
                else:
                    logger.info("    ❌ ZIP 헤더가 아님")
            else:
                # HTML인 경우 내용 확인
                if 'html' in content_type:
                    if len(resp.text) < 1000:
                        logger.info(f"    HTML 응답: {resp.text[:200]}")
                    else:
                        # 로그인 페이지인지 확인
                        if 'login' in resp.text.lower()[:500]:
                            logger.info("    ❌ 로그인 페이지로 리다이렉트")
                        else:
                            logger.info("    HTML 페이지 (데이터 페이지일 수 있음)")
                            
        elif resp.status_code == 302:
            location = resp.headers.get('Location', '')
            logger.info(f"    리다이렉트: {location}")
            
    def test_api_endpoints(self):
        """API 엔드포인트 탐색"""
        if not self.session:
            self.test_standard_login()
            
        if not self.session:
            return
            
        # API 스타일 엔드포인트
        api_urls = [
            "/fcti/api/securityAdvisory/list",
            "/fcti/api/advisory/list",
            "/fcti/rest/securityAdvisory/list",
            "/fcti/ajax/securityAdvisory/list",
            "/fcti/data/securityAdvisory/list",
            "/fcti/json/securityAdvisory/list",
            "/fcti/securityAdvisory/data",
            "/fcti/securityAdvisory/getList",
            "/fcti/securityAdvisory/search"
        ]
        
        for url in api_urls:
            full_url = self.base_url + url
            logger.info(f"\nAPI 테스트: {full_url}")
            
            # JSON 헤더 추가
            headers = {
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            try:
                resp = self.session.get(full_url, headers=headers)
                logger.info(f"  응답: {resp.status_code}")
                
                if resp.status_code == 200:
                    content_type = resp.headers.get('Content-Type', '')
                    logger.info(f"  Content-Type: {content_type}")
                    
                    if 'json' in content_type:
                        try:
                            data = resp.json()
                            logger.info(f"  ✅ JSON 데이터 수신!")
                            logger.info(f"  데이터 구조: {list(data.keys()) if isinstance(data, dict) else f'{len(data)}개 항목'}")
                        except:
                            pass
                            
            except Exception as e:
                logger.error(f"  요청 실패: {e}")
                
    def analyze_javascript(self):
        """페이지의 JavaScript 코드 분석"""
        if not self.session:
            self.test_standard_login()
            
        if not self.session:
            return
            
        # 보안권고 페이지 가져오기
        resp = self.session.get(f"{self.base_url}/fcti/securityAdvisory/advisoryList")
        
        if resp.status_code == 200 and 'login' not in resp.url:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # JavaScript 코드 찾기
            scripts = soup.find_all('script')
            logger.info(f"발견된 스크립트 태그: {len(scripts)}개")
            
            for i, script in enumerate(scripts):
                if script.string:
                    # 다운로드 관련 코드 찾기
                    if any(keyword in script.string for keyword in ['download', 'excel', 'export', 'xlsx']):
                        logger.info(f"\n스크립트 {i+1}에서 다운로드 관련 코드 발견:")
                        
                        # 관련 라인만 추출
                        lines = script.string.split('\n')
                        for line in lines:
                            if any(keyword in line.lower() for keyword in ['download', 'excel', 'export', 'xlsx', 'url', 'action']):
                                logger.info(f"  {line.strip()}")
                                
    def test_form_download(self):
        """Form 기반 다운로드"""
        if not self.session:
            self.test_standard_login()
            
        if not self.session:
            return
            
        # 보안권고 페이지에서 form 찾기
        resp = self.session.get(f"{self.base_url}/fcti/securityAdvisory/advisoryList")
        
        if resp.status_code == 200 and 'login' not in resp.url:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Form 태그 찾기
            forms = soup.find_all('form')
            logger.info(f"발견된 form 태그: {len(forms)}개")
            
            for i, form in enumerate(forms):
                action = form.get('action', '')
                method = form.get('method', 'get').upper()
                
                if any(keyword in action.lower() for keyword in ['download', 'excel', 'export']):
                    logger.info(f"\nForm {i+1} - 다운로드 관련:")
                    logger.info(f"  Action: {action}")
                    logger.info(f"  Method: {method}")
                    
                    # Hidden input 찾기
                    hidden_inputs = form.find_all('input', type='hidden')
                    for inp in hidden_inputs:
                        logger.info(f"  Hidden: {inp.get('name')} = {inp.get('value')}")
                        
            # 다운로드 버튼 찾기
            download_buttons = soup.find_all(['button', 'a', 'input'], 
                text=lambda t: t and any(k in t.lower() for k in ['excel', '다운로드', 'download', '엑셀']))
            
            logger.info(f"\n다운로드 버튼: {len(download_buttons)}개 발견")
            for btn in download_buttons:
                logger.info(f"  태그: {btn.name}")
                logger.info(f"  텍스트: {btn.get_text(strip=True)}")
                logger.info(f"  onclick: {btn.get('onclick', '')}")
                logger.info(f"  href: {btn.get('href', '')}")

if __name__ == "__main__":
    tester = RegtechAllPossibilitiesTest()
    tester.test_all_methods()