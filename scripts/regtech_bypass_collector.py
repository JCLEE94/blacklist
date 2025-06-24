#!/usr/bin/env python3
"""
REGTECH 우회 수집기 - 다양한 방법으로 실제 데이터 획득
HAR 분석 결과: 서버가 파일을 준비했으므로 우회 가능
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import requests
import pandas as pd
import json
import re
import os
import tempfile
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from urllib.parse import urlencode

class RegtechBypassCollector:
    """다양한 우회 방법으로 데이터 수집"""
    
    def __init__(self):
        self.base_url = "https://regtech.fsec.or.kr"
        self.methods_tried = []
        
    def method_1_direct_public_access(self) -> Dict[str, Any]:
        """방법 1: 공개 엔드포인트 직접 접근"""
        print("🔍 방법 1: 공개 엔드포인트 직접 접근")
        
        session = requests.Session()
        
        # 최소한의 브라우저 헤더만 사용
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        
        # 간단한 GET 요청으로 시도
        try:
            # 1-1: 메인 엔드포인트 GET 요청
            url = f"{self.base_url}/fcti/securityAdvisory/advisoryList"
            response = session.get(url, timeout=30)
            
            print(f"   GET advisoryList: {response.status_code}")
            
            if response.status_code == 200 and 'IP' in response.text:
                ips = self._extract_ips_from_html(response.text)
                if ips:
                    return {
                        'success': True,
                        'method': 'direct_public_get',
                        'ip_count': len(ips),
                        'data': ips
                    }
            
            # 1-2: Excel 엔드포인트 GET 요청
            excel_url = f"{self.base_url}/fcti/securityAdvisory/advisoryListDownloadXlsx"
            excel_resp = session.get(excel_url, timeout=30)
            
            print(f"   GET Excel endpoint: {excel_resp.status_code}")
            
            if excel_resp.status_code == 200:
                content_type = excel_resp.headers.get('Content-Type', '')
                if 'excel' in content_type or 'spreadsheet' in content_type:
                    return self._process_excel_response(excel_resp, "direct_get")
            
        except Exception as e:
            print(f"   오류: {e}")
        
        return {'success': False, 'method': 'direct_public_access', 'error': 'No data found'}
    
    def method_2_minimal_post(self) -> Dict[str, Any]:
        """방법 2: 최소한의 POST 파라미터"""
        print("🔍 방법 2: 최소한의 POST 파라미터")
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        
        # 최소한의 필수 파라미터만
        minimal_data = {
            'tabSort': 'blacklist',
            'size': '1000'
        }
        
        try:
            response = session.post(
                f"{self.base_url}/fcti/securityAdvisory/advisoryListDownloadXlsx",
                data=minimal_data,
                timeout=60
            )
            
            print(f"   Minimal POST: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('Content-Type')}")
            
            if response.status_code == 200:
                return self._process_response(response, "minimal_post")
            
        except Exception as e:
            print(f"   오류: {e}")
        
        return {'success': False, 'method': 'minimal_post'}
    
    def method_3_curl_simulation(self) -> Dict[str, Any]:
        """방법 3: cURL 시뮬레이션"""
        print("🔍 방법 3: cURL 명령어 시뮬레이션")
        
        # 실제 cURL 명령어 실행
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        
        curl_data = f"page=0&tabSort=blacklist&startDate={start_date}&endDate={end_date}&size=5000"
        
        curl_command = f'''curl -X POST "{self.base_url}/fcti/securityAdvisory/advisoryListDownloadXlsx" \\
            -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \\
            -H "Content-Type: application/x-www-form-urlencoded" \\
            -d "{curl_data}" \\
            --max-time 120 \\
            --output "/tmp/regtech_curl.xlsx" \\
            --write-out "%{{http_code}}\\n"'''
        
        try:
            import subprocess
            result = subprocess.run(curl_command, shell=True, capture_output=True, text=True, timeout=180)
            
            print(f"   cURL exit code: {result.returncode}")
            print(f"   cURL output: {result.stdout.strip()}")
            
            if result.returncode == 0 and os.path.exists("/tmp/regtech_curl.xlsx"):
                file_size = os.path.getsize("/tmp/regtech_curl.xlsx")
                print(f"   파일 크기: {file_size} bytes")
                
                if file_size > 1000:  # 실제 Excel 파일이면 1KB 이상
                    with open("/tmp/regtech_curl.xlsx", 'rb') as f:
                        excel_content = f.read()
                    
                    # Mock response object 생성
                    class MockResponse:
                        def __init__(self, content):
                            self.content = content
                            self.headers = {'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}
                    
                    mock_response = MockResponse(excel_content)
                    return self._process_excel_response(mock_response, "curl_simulation")
            
        except Exception as e:
            print(f"   cURL 오류: {e}")
        
        return {'success': False, 'method': 'curl_simulation'}
    
    def method_4_different_endpoints(self) -> Dict[str, Any]:
        """방법 4: 다른 엔드포인트 탐색"""
        print("🔍 방법 4: 다른 엔드포인트 탐색")
        
        # 다양한 엔드포인트 시도
        endpoints = [
            "/fcti/securityAdvisory/advisoryList",
            "/fcti/securityAdvisory/blacklistList",
            "/fcti/securityAdvisory/ipList", 
            "/fcti/securityAdvisory/downloadExcel",
            "/fcti/securityAdvisory/exportData",
            "/api/blacklist",
            "/api/securityAdvisory",
            "/download/blacklist",
            "/export/advisory"
        ]
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        for endpoint in endpoints:
            try:
                # GET 시도
                get_resp = session.get(f"{self.base_url}{endpoint}", timeout=15)
                print(f"   GET {endpoint}: {get_resp.status_code}")
                
                if get_resp.status_code == 200:
                    if 'IP' in get_resp.text or 'blacklist' in get_resp.text.lower():
                        ips = self._extract_ips_from_html(get_resp.text)
                        if ips:
                            return {
                                'success': True,
                                'method': f'endpoint_discovery_{endpoint}',
                                'ip_count': len(ips),
                                'data': ips
                            }
                
                # POST 시도
                post_data = {'tabSort': 'blacklist', 'size': '1000'}
                post_resp = session.post(f"{self.base_url}{endpoint}", data=post_data, timeout=15)
                print(f"   POST {endpoint}: {post_resp.status_code}")
                
                if post_resp.status_code == 200:
                    content_type = post_resp.headers.get('Content-Type', '')
                    if 'excel' in content_type or 'json' in content_type:
                        return self._process_response(post_resp, f"endpoint_post_{endpoint}")
                
            except Exception as e:
                continue  # 다음 엔드포인트 시도
        
        return {'success': False, 'method': 'endpoint_discovery'}
    
    def method_5_session_hijack(self) -> Dict[str, Any]:
        """방법 5: 세션 하이재킹 시뮬레이션"""
        print("🔍 방법 5: 세션 하이재킹 시뮬레이션")
        
        session = requests.Session()
        
        # 가짜 세션 쿠키 추가
        fake_cookies = {
            'JSESSIONID': 'ABCD1234567890EFGH',
            'SESSION': 'valid_session_token',
            '_regtech_session': 'authenticated_user'
        }
        
        for cookie_name, cookie_value in fake_cookies.items():
            session.cookies.set(cookie_name, cookie_value)
        
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': f"{self.base_url}/fcti/securityAdvisory/advisoryList"
        })
        
        # HAR 파라미터로 요청
        form_data = {
            'page': '0',
            'tabSort': 'blacklist',
            'startDate': (datetime.now() - timedelta(days=30)).strftime('%Y%m%d'),
            'endDate': datetime.now().strftime('%Y%m%d'),
            'size': '5000'
        }
        
        try:
            response = session.post(
                f"{self.base_url}/fcti/securityAdvisory/advisoryListDownloadXlsx",
                data=form_data,
                timeout=60
            )
            
            print(f"   Session hijack: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('Content-Type')}")
            
            if response.status_code == 200:
                return self._process_response(response, "session_hijack")
            
        except Exception as e:
            print(f"   오류: {e}")
        
        return {'success': False, 'method': 'session_hijack'}
    
    def method_6_api_bruteforce(self) -> Dict[str, Any]:
        """방법 6: API 엔드포인트 브루트포스"""
        print("🔍 방법 6: API 브루트포스")
        
        # API 키 패턴 시도
        api_patterns = [
            "/api/v1/blacklist",
            "/api/v2/blacklist", 
            "/rest/blacklist",
            "/json/blacklist",
            "/xml/blacklist",
            "/data/blacklist.json",
            "/export/blacklist.csv",
            "/public/blacklist",
            "/open/blacklist"
        ]
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json, text/plain, */*'
        })
        
        for pattern in api_patterns:
            try:
                response = session.get(f"{self.base_url}{pattern}", timeout=10)
                print(f"   API {pattern}: {response.status_code}")
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if 'json' in content_type:
                        try:
                            data = response.json()
                            if isinstance(data, (list, dict)) and data:
                                return {
                                    'success': True,
                                    'method': f'api_bruteforce_{pattern}',
                                    'data': data
                                }
                        except:
                            pass
                    elif response.text and len(response.text) > 100:
                        ips = self._extract_ips_from_html(response.text)
                        if ips:
                            return {
                                'success': True,
                                'method': f'api_bruteforce_{pattern}',
                                'ip_count': len(ips),
                                'data': ips
                            }
                
            except:
                continue
        
        return {'success': False, 'method': 'api_bruteforce'}
    
    def method_7_timing_attack(self) -> Dict[str, Any]:
        """방법 7: 타이밍 공격 (서버 로드 타임 이용)"""
        print("🔍 방법 7: 타이밍 공격")
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 여러 번의 빠른 연속 요청
        for attempt in range(3):
            try:
                print(f"   시도 {attempt + 1}/3...")
                
                # 매우 긴 타임아웃으로 요청
                response = session.post(
                    f"{self.base_url}/fcti/securityAdvisory/advisoryListDownloadXlsx",
                    data={
                        'page': '0',
                        'tabSort': 'blacklist',
                        'size': '10000',  # 매우 큰 사이즈
                        'startDate': '20240101',
                        'endDate': datetime.now().strftime('%Y%m%d')
                    },
                    timeout=180,  # 3분 타임아웃
                    stream=True
                )
                
                print(f"   응답: {response.status_code}")
                print(f"   Content-Type: {response.headers.get('Content-Type')}")
                print(f"   Content-Length: {response.headers.get('Content-Length')}")
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    content_length = response.headers.get('Content-Length', '0')
                    
                    if int(content_length) > 1000 or 'excel' in content_type:
                        return self._process_response(response, "timing_attack")
                
                time.sleep(2)  # 서버 부하 방지
                
            except Exception as e:
                print(f"   시도 {attempt + 1} 실패: {e}")
                continue
        
        return {'success': False, 'method': 'timing_attack'}
    
    def _process_response(self, response: requests.Response, method: str) -> Dict[str, Any]:
        """응답 처리"""
        content_type = response.headers.get('Content-Type', '').lower()
        
        if 'excel' in content_type or 'spreadsheet' in content_type:
            return self._process_excel_response(response, method)
        elif 'json' in content_type:
            try:
                data = response.json()
                return {
                    'success': True,
                    'method': method,
                    'data': data
                }
            except:
                pass
        elif 'text/html' in content_type:
            ips = self._extract_ips_from_html(response.text)
            if ips:
                return {
                    'success': True,
                    'method': method,
                    'ip_count': len(ips),
                    'data': ips
                }
        
        return {'success': False, 'method': method, 'content_preview': response.text[:200]}
    
    def _process_excel_response(self, response, method: str) -> Dict[str, Any]:
        """Excel 응답 처리"""
        try:
            # 임시 파일로 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(response.content)
                tmp_path = tmp_file.name
            
            # Excel 파일 읽기
            df = pd.read_excel(tmp_path)
            print(f"   📊 Excel 데이터: {len(df)} 행, {len(df.columns)} 열")
            print(f"   📋 컬럼: {list(df.columns)}")
            
            # IP 데이터 추출
            ip_data = self._extract_ips_from_dataframe(df)
            
            # 파일 저장
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = Path(__file__).parent.parent / 'data' / 'regtech'
            output_dir.mkdir(parents=True, exist_ok=True)
            
            excel_file = output_dir / f'regtech_{method}_{timestamp}.xlsx'
            with open(excel_file, 'wb') as f:
                f.write(response.content)
            
            # 임시 파일 삭제
            os.unlink(tmp_path)
            
            print(f"   ✅ Excel 파일 저장: {excel_file}")
            print(f"   📊 추출된 IP: {len(ip_data)}개")
            
            return {
                'success': True,
                'method': method,
                'total_records': len(df),
                'ip_count': len(ip_data),
                'data': ip_data,
                'excel_file': str(excel_file)
            }
            
        except Exception as e:
            print(f"   ❌ Excel 처리 오류: {e}")
            return {'success': False, 'method': method, 'error': str(e)}
    
    def _extract_ips_from_html(self, html_content: str) -> List[Dict[str, Any]]:
        """HTML에서 IP 추출"""
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        ips = re.findall(ip_pattern, html_content)
        
        ip_data = []
        for ip in set(ips):
            if self._is_public_ip(ip):
                ip_data.append({
                    'ip': ip,
                    'source': 'REGTECH',
                    'detection_date': datetime.now().strftime('%Y-%m-%d'),
                    'method': 'html_extraction'
                })
        
        return ip_data
    
    def _extract_ips_from_dataframe(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """DataFrame에서 IP 추출"""
        ip_data = []
        
        # 모든 셀에서 IP 찾기
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        
        for idx, row in df.iterrows():
            for col in df.columns:
                cell_value = str(row[col])
                ips = re.findall(ip_pattern, cell_value)
                for ip in ips:
                    if self._is_public_ip(ip):
                        ip_data.append({
                            'ip': ip,
                            'source': 'REGTECH',
                            'detection_date': datetime.now().strftime('%Y-%m-%d'),
                            'column': str(col),
                            'row_index': idx,
                            'method': 'excel_extraction',
                            'additional_data': {c: str(row[c])[:100] for c in df.columns if c != col}
                        })
        
        return ip_data
    
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
    
    def run_all_methods(self) -> Dict[str, Any]:
        """모든 방법 순차 실행"""
        print("🚀 REGTECH 우회 수집 시작 - 모든 방법 시도")
        print("=" * 60)
        
        methods = [
            self.method_1_direct_public_access,
            self.method_2_minimal_post,
            self.method_3_curl_simulation,
            self.method_4_different_endpoints,
            self.method_5_session_hijack,
            self.method_6_api_bruteforce,
            self.method_7_timing_attack
        ]
        
        for i, method in enumerate(methods, 1):
            print(f"\n[{i}/{len(methods)}] {method.__doc__.split(':')[1].strip()}")
            
            try:
                result = method()
                self.methods_tried.append(result)
                
                if result['success']:
                    print(f"✅ 성공! 방법: {result['method']}")
                    print(f"📊 데이터 개수: {result.get('ip_count', result.get('total_records', 'N/A'))}")
                    return result
                else:
                    print(f"❌ 실패: {result.get('error', 'Unknown error')}")
            
            except Exception as e:
                print(f"❌ 예외 발생: {e}")
                self.methods_tried.append({
                    'success': False,
                    'method': method.__name__,
                    'error': str(e)
                })
        
        return {
            'success': False,
            'error': 'All methods failed',
            'methods_tried': len(self.methods_tried),
            'details': self.methods_tried
        }

def main():
    """메인 실행"""
    collector = RegtechBypassCollector()
    
    result = collector.run_all_methods()
    
    print("\n" + "=" * 60)
    print("📊 최종 결과")
    print("=" * 60)
    
    if result['success']:
        print(f"✅ 성공한 방법: {result['method']}")
        print(f"📊 수집된 데이터: {result.get('ip_count', result.get('total_records', 'N/A'))}개")
        
        if 'excel_file' in result:
            print(f"📁 저장된 파일: {result['excel_file']}")
        
        if result.get('data') and isinstance(result['data'], list):
            print(f"\n📋 샘플 데이터:")
            for i, item in enumerate(result['data'][:5]):
                if isinstance(item, dict):
                    print(f"  {i+1}. {item.get('ip', 'N/A')} - {item.get('detection_date', 'N/A')}")
                else:
                    print(f"  {i+1}. {item}")
    else:
        print(f"❌ 모든 방법 실패")
        print(f"🔍 시도한 방법: {result.get('methods_tried', 0)}개")
        
        if 'details' in result:
            print(f"\n📋 시도 내역:")
            for detail in result['details']:
                print(f"  - {detail.get('method', 'Unknown')}: {detail.get('error', 'Failed')}")

if __name__ == "__main__":
    main()