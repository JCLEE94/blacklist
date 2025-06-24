#!/usr/bin/env python3
"""
REGTECH 브라우저 자동화 - 실제 브라우저로 데이터 수집
Selenium을 사용하여 실제 브라우저 환경에서 데이터 수집
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import time
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List
import tempfile
import os

# Selenium이 없는 경우를 대비한 fallback
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.keys import Keys
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

class RegtechBrowserCollector:
    """브라우저 자동화를 통한 REGTECH 데이터 수집"""
    
    def __init__(self):
        self.base_url = "https://regtech.fsec.or.kr"
        self.driver = None
        self.download_dir = "/tmp/regtech_downloads"
        
        # 다운로드 디렉토리 생성
        os.makedirs(self.download_dir, exist_ok=True)
    
    def setup_browser(self) -> bool:
        """브라우저 설정 및 초기화"""
        if not SELENIUM_AVAILABLE:
            print("❌ Selenium이 설치되지 않음. pip install selenium 필요")
            return False
        
        try:
            # Chrome 옵션 설정
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # 백그라운드 실행
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            # 다운로드 설정
            prefs = {
                "download.default_directory": self.download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # 브라우저 시작
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            
            print("✅ 브라우저 초기화 완료")
            return True
            
        except Exception as e:
            print(f"❌ 브라우저 초기화 실패: {e}")
            return False
    
    def method_1_guest_access(self) -> Dict[str, Any]:
        """방법 1: 게스트 접근으로 공개 데이터 확인"""
        print("🔍 방법 1: 게스트 접근")
        
        try:
            # 메인 페이지 접속
            self.driver.get(f"{self.base_url}/main/main")
            time.sleep(3)
            
            print(f"   페이지 제목: {self.driver.title}")
            
            # 공개 데이터 링크 찾기
            public_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'advisory') or contains(@href, 'blacklist')]")
            
            for link in public_links[:5]:  # 처음 5개만 시도
                try:
                    href = link.get_attribute('href')
                    text = link.text.strip()
                    
                    if href and ('advisory' in href or 'blacklist' in href.lower()):
                        print(f"   공개 링크 시도: {text} -> {href}")
                        
                        link.click()
                        time.sleep(3)
                        
                        # 페이지에서 IP 찾기
                        ips = self._extract_ips_from_page()
                        if ips:
                            return {
                                'success': True,
                                'method': 'guest_access',
                                'ips': ips,
                                'source_url': href
                            }
                        
                        self.driver.back()
                        time.sleep(2)
                
                except Exception as e:
                    continue
            
        except Exception as e:
            print(f"   오류: {e}")
        
        return {'success': False, 'method': 'guest_access'}
    
    def method_2_direct_advisory_access(self) -> Dict[str, Any]:
        """방법 2: Advisory 페이지 직접 접근"""
        print("🔍 방법 2: Advisory 페이지 직접 접근")
        
        try:
            # Advisory 페이지 직접 접속
            self.driver.get(f"{self.base_url}/fcti/securityAdvisory/advisoryList")
            time.sleep(5)
            
            print(f"   현재 URL: {self.driver.current_url}")
            
            # 로그인 페이지로 리다이렉트되었는지 확인
            if 'login' in self.driver.current_url.lower():
                print("   ❌ 로그인 페이지로 리다이렉트됨")
            else:
                print("   ✅ Advisory 페이지 접근 성공")
                
                # 페이지에서 데이터 추출
                ips = self._extract_ips_from_page()
                if ips:
                    return {
                        'success': True,
                        'method': 'direct_advisory',
                        'ips': ips
                    }
                
                # Excel 다운로드 버튼 찾기
                download_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), '다운로드') or contains(text(), 'Excel') or contains(text(), '엑셀')]")
                
                for button in download_buttons:
                    try:
                        button_text = button.text
                        print(f"   다운로드 버튼 시도: {button_text}")
                        
                        button.click()
                        time.sleep(5)
                        
                        # 다운로드된 파일 확인
                        downloaded_files = self._check_downloaded_files()
                        if downloaded_files:
                            return self._process_downloaded_files(downloaded_files, 'direct_advisory')
                    
                    except Exception as e:
                        continue
        
        except Exception as e:
            print(f"   오류: {e}")
        
        return {'success': False, 'method': 'direct_advisory'}
    
    def method_3_form_manipulation(self) -> Dict[str, Any]:
        """방법 3: 숨겨진 폼 조작"""
        print("🔍 방법 3: 숨겨진 폼 조작")
        
        try:
            self.driver.get(f"{self.base_url}/fcti/securityAdvisory/advisoryList")
            time.sleep(5)
            
            # 숨겨진 폼 찾기
            forms = self.driver.find_elements(By.TAG_NAME, "form")
            print(f"   발견된 폼: {len(forms)}개")
            
            for i, form in enumerate(forms):
                try:
                    action = form.get_attribute('action')
                    method = form.get_attribute('method')
                    
                    if action and ('download' in action.lower() or 'excel' in action.lower()):
                        print(f"   폼 {i}: {method} {action}")
                        
                        # 폼 내 숨겨진 입력 수정
                        hidden_inputs = form.find_elements(By.XPATH, ".//input[@type='hidden']")
                        
                        for hidden_input in hidden_inputs:
                            name = hidden_input.get_attribute('name')
                            if name in ['page', 'size', 'tabSort']:
                                self.driver.execute_script(f"arguments[0].value = arguments[1];", hidden_input, 
                                                         '0' if name == 'page' else '5000' if name == 'size' else 'blacklist')
                        
                        # 폼 제출
                        form.submit()
                        time.sleep(10)
                        
                        # 다운로드 확인
                        downloaded_files = self._check_downloaded_files()
                        if downloaded_files:
                            return self._process_downloaded_files(downloaded_files, 'form_manipulation')
                
                except Exception as e:
                    continue
        
        except Exception as e:
            print(f"   오류: {e}")
        
        return {'success': False, 'method': 'form_manipulation'}
    
    def method_4_javascript_execution(self) -> Dict[str, Any]:
        """방법 4: JavaScript 직접 실행"""
        print("🔍 방법 4: JavaScript 직접 실행")
        
        try:
            self.driver.get(f"{self.base_url}/fcti/securityAdvisory/advisoryList")
            time.sleep(5)
            
            # JavaScript로 Ajax 요청 실행
            js_scripts = [
                # 기본 Ajax 요청
                '''
                fetch('/fcti/securityAdvisory/advisoryListDownloadXlsx', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: 'page=0&tabSort=blacklist&size=5000'
                }).then(response => response.blob()).then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'regtech_data.xlsx';
                    a.click();
                    return 'download_started';
                });
                ''',
                
                # jQuery Ajax 요청
                '''
                if (typeof $ !== 'undefined') {
                    $.post('/fcti/securityAdvisory/advisoryListDownloadXlsx', {
                        page: 0,
                        tabSort: 'blacklist',
                        size: 5000
                    }).done(function(data) {
                        console.log('Ajax success');
                        return 'ajax_success';
                    });
                }
                ''',
                
                # XMLHttpRequest
                '''
                var xhr = new XMLHttpRequest();
                xhr.open('POST', '/fcti/securityAdvisory/advisoryListDownloadXlsx', true);
                xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
                xhr.responseType = 'blob';
                xhr.onload = function() {
                    if (xhr.status === 200) {
                        var blob = xhr.response;
                        var url = window.URL.createObjectURL(blob);
                        var a = document.createElement('a');
                        a.href = url;
                        a.download = 'regtech_xhr.xlsx';
                        a.click();
                    }
                };
                xhr.send('page=0&tabSort=blacklist&size=5000');
                return 'xhr_sent';
                '''
            ]
            
            for i, script in enumerate(js_scripts):
                try:
                    print(f"   JavaScript 스크립트 {i+1} 실행...")
                    result = self.driver.execute_script(script)
                    print(f"   결과: {result}")
                    
                    time.sleep(10)  # 다운로드 대기
                    
                    downloaded_files = self._check_downloaded_files()
                    if downloaded_files:
                        return self._process_downloaded_files(downloaded_files, f'javascript_{i+1}')
                
                except Exception as e:
                    print(f"   스크립트 {i+1} 오류: {e}")
                    continue
        
        except Exception as e:
            print(f"   오류: {e}")
        
        return {'success': False, 'method': 'javascript_execution'}
    
    def method_5_network_intercept(self) -> Dict[str, Any]:
        """방법 5: 네트워크 요청 가로채기"""
        print("🔍 방법 5: 네트워크 요청 가로채기")
        
        try:
            # Chrome DevTools Protocol 활성화
            self.driver.execute_cdp_cmd('Network.enable', {})
            
            # 네트워크 이벤트 리스너 등록
            network_logs = []
            
            def log_request(message):
                network_logs.append(message)
            
            self.driver.add_cdp_listener('Network.responseReceived', log_request)
            
            # 페이지 접속
            self.driver.get(f"{self.base_url}/fcti/securityAdvisory/advisoryList")
            time.sleep(5)
            
            # 모든 Ajax 관련 버튼 클릭
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            
            for button in buttons:
                try:
                    button_text = button.text.lower()
                    if any(keyword in button_text for keyword in ['조회', '검색', '다운로드', '엑셀']):
                        print(f"   버튼 클릭: {button.text}")
                        button.click()
                        time.sleep(3)
                except:
                    continue
            
            # 네트워크 로그에서 Excel 응답 찾기
            for log_entry in network_logs:
                response = log_entry.get('response', {})
                url = response.get('url', '')
                
                if 'xlsx' in url or 'excel' in url.lower():
                    print(f"   Excel 응답 발견: {url}")
                    
                    # 응답 본문 가져오기
                    try:
                        response_body = self.driver.execute_cdp_cmd('Network.getResponseBody', {
                            'requestId': log_entry.get('requestId')
                        })
                        
                        if response_body.get('base64Encoded'):
                            import base64
                            excel_data = base64.b64decode(response_body.get('body'))
                            
                            filename = f"{self.download_dir}/network_intercept.xlsx"
                            with open(filename, 'wb') as f:
                                f.write(excel_data)
                            
                            return self._process_downloaded_files([filename], 'network_intercept')
                    
                    except Exception as e:
                        print(f"   응답 본문 가져오기 실패: {e}")
        
        except Exception as e:
            print(f"   오류: {e}")
        
        return {'success': False, 'method': 'network_intercept'}
    
    def _extract_ips_from_page(self) -> List[str]:
        """현재 페이지에서 IP 추출"""
        try:
            page_source = self.driver.page_source
            
            import re
            ip_pattern = r'\\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b'
            ips = re.findall(ip_pattern, page_source)
            
            # 공인 IP만 필터링
            public_ips = []
            for ip in set(ips):
                if self._is_public_ip(ip):
                    public_ips.append(ip)
            
            if public_ips:
                print(f"   페이지에서 발견된 공인 IP: {len(public_ips)}개")
            
            return public_ips
        
        except Exception as e:
            print(f"   IP 추출 오류: {e}")
            return []
    
    def _check_downloaded_files(self) -> List[str]:
        """다운로드된 파일 확인"""
        try:
            files = []
            for filename in os.listdir(self.download_dir):
                file_path = os.path.join(self.download_dir, filename)
                if os.path.isfile(file_path) and filename.endswith(('.xlsx', '.xls', '.csv')):
                    # 파일 크기가 충분한지 확인
                    if os.path.getsize(file_path) > 1000:  # 1KB 이상
                        files.append(file_path)
            
            return files
        
        except Exception as e:
            print(f"   파일 확인 오류: {e}")
            return []
    
    def _process_downloaded_files(self, files: List[str], method: str) -> Dict[str, Any]:
        """다운로드된 파일 처리"""
        try:
            for file_path in files:
                print(f"   파일 처리: {file_path}")
                
                # Excel 파일 읽기
                df = pd.read_excel(file_path)
                print(f"   데이터: {len(df)} 행, {len(df.columns)} 열")
                print(f"   컬럼: {list(df.columns)}")
                
                # IP 추출
                ips = self._extract_ips_from_dataframe(df)
                
                if ips:
                    # 결과 파일 저장
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    result_file = f"/tmp/regtech_browser_{method}_{timestamp}.json"
                    
                    result_data = {
                        'collection_date': timestamp,
                        'method': f'browser_{method}',
                        'source_file': file_path,
                        'total_records': len(df),
                        'ip_count': len(ips),
                        'data': ips
                    }
                    
                    with open(result_file, 'w', encoding='utf-8') as f:
                        json.dump(result_data, f, ensure_ascii=False, indent=2)
                    
                    print(f"   ✅ 결과 저장: {result_file}")
                    
                    return {
                        'success': True,
                        'method': f'browser_{method}',
                        'ip_count': len(ips),
                        'ips': ips,
                        'source_file': file_path,
                        'result_file': result_file
                    }
        
        except Exception as e:
            print(f"   파일 처리 오류: {e}")
        
        return {'success': False, 'method': method}
    
    def _extract_ips_from_dataframe(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """DataFrame에서 IP 추출"""
        ips = []
        
        import re
        ip_pattern = r'\\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b'
        
        for idx, row in df.iterrows():
            for col in df.columns:
                cell_value = str(row[col])
                found_ips = re.findall(ip_pattern, cell_value)
                
                for ip in found_ips:
                    if self._is_public_ip(ip):
                        ips.append({
                            'ip': ip,
                            'source': 'REGTECH',
                            'detection_date': datetime.now().strftime('%Y-%m-%d'),
                            'column': str(col),
                            'row_index': idx,
                            'method': 'browser_extraction'
                        })
        
        return ips
    
    def _is_public_ip(self, ip: str) -> bool:
        """공인 IP 확인"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            
            first = int(parts[0])
            second = int(parts[1])
            
            # 사설 IP 제외
            if first == 10:
                return False
            if first == 172 and 16 <= second <= 31:
                return False
            if first == 192 and second == 168:
                return False
            if first == 127:
                return False
            if first == 0 or first >= 224:
                return False
            
            return True
        except:
            return False
    
    def run_all_browser_methods(self) -> Dict[str, Any]:
        """모든 브라우저 방법 실행"""
        print("🚀 브라우저 자동화 기반 REGTECH 수집")
        print("=" * 60)
        
        if not self.setup_browser():
            return {'success': False, 'error': 'Browser setup failed'}
        
        methods = [
            self.method_1_guest_access,
            self.method_2_direct_advisory_access,
            self.method_3_form_manipulation,
            self.method_4_javascript_execution,
            self.method_5_network_intercept
        ]
        
        try:
            for i, method in enumerate(methods, 1):
                print(f"\\n[{i}/{len(methods)}] {method.__doc__.split(':')[1].strip()}")
                
                try:
                    result = method()
                    
                    if result['success']:
                        print(f"✅ 성공! 방법: {result['method']}")
                        print(f"📊 데이터 개수: {result.get('ip_count', 'N/A')}")
                        return result
                    else:
                        print(f"❌ 실패: {result.get('error', 'No data found')}")
                
                except Exception as e:
                    print(f"❌ 예외 발생: {e}")
        
        finally:
            if self.driver:
                self.driver.quit()
                print("🔒 브라우저 종료")
        
        return {'success': False, 'error': 'All browser methods failed'}

def main():
    """메인 실행 함수"""
    collector = RegtechBrowserCollector()
    
    result = collector.run_all_browser_methods()
    
    print("\\n" + "="*60)
    print("📊 브라우저 자동화 최종 결과")
    print("="*60)
    
    if result['success']:
        print(f"✅ 성공한 방법: {result['method']}")
        print(f"🎯 수집된 IP: {result.get('ip_count', 0)}개")
        
        if 'result_file' in result:
            print(f"📁 결과 파일: {result['result_file']}")
        
        if result.get('ips'):
            print(f"\\n📋 샘플 IP:")
            for i, ip_data in enumerate(result['ips'][:5]):
                if isinstance(ip_data, dict):
                    print(f"  {i+1}. {ip_data.get('ip', 'N/A')}")
                else:
                    print(f"  {i+1}. {ip_data}")
    else:
        print(f"❌ 브라우저 자동화 실패: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    if not SELENIUM_AVAILABLE:
        print("❌ Selenium이 필요합니다.")
        print("설치: pip install selenium")
        print("Chrome 드라이버도 필요합니다.")
    else:
        main()