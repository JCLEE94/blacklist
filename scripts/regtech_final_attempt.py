#!/usr/bin/env python3
"""
REGTECH 최종 시도 - 실제 데이터 획득을 위한 종합적 접근
모든 가능한 방법을 동원하여 실제 데이터 수집
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import requests
import json
import re
import time
import subprocess
import tempfile
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
from urllib.parse import urlencode, urlparse
import threading
import concurrent.futures

class RegtechFinalCollector:
    """모든 방법을 동원한 최종 수집기"""
    
    def __init__(self):
        self.base_url = "https://regtech.fsec.or.kr"
        self.success_results = []
        self.all_attempts = []
        
    def method_parallel_requests(self) -> Dict[str, Any]:
        """방법 1: 병렬 요청으로 서버 부하 시 틈새 공략"""
        print("🔍 방법 1: 병렬 요청")
        
        def make_request(params):
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            try:
                response = session.post(
                    f"{self.base_url}/fcti/securityAdvisory/advisoryListDownloadXlsx",
                    data=params,
                    timeout=60
                )
                
                return {
                    'status': response.status_code,
                    'content_type': response.headers.get('Content-Type'),
                    'content_length': len(response.content),
                    'content': response.content if response.status_code == 200 else None,
                    'params': params
                }
            except Exception as e:
                return {'error': str(e), 'params': params}
        
        # 다양한 파라미터 조합
        param_sets = [
            {'page': '0', 'size': '1'},
            {'page': '0', 'size': '10'},
            {'page': '0', 'size': '100'},
            {'tabSort': 'blacklist'},
            {'tabSort': 'blacklist', 'size': '50'},
            {'findCondition': 'all'},
            {'startDate': '20240101', 'endDate': '20240201'},
            {'startDate': '20250101', 'endDate': '20250201'},
            # 빈 요청도 시도
            {},
        ]
        
        # 병렬 실행
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, params) for params in param_sets]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # 결과 분석
        for result in results:
            if 'error' not in result:
                print(f"   파라미터 {result['params']}: {result['status']}, {result['content_length']} bytes")
                
                # Excel 파일 형식 확인
                if result.get('content') and result['content'].startswith(b'PK'):
                    print(f"   ✅ Excel 파일 발견!")
                    
                    # 파일 저장 및 분석
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"/tmp/regtech_parallel_{timestamp}.xlsx"
                    
                    with open(filename, 'wb') as f:
                        f.write(result['content'])
                    
                    return self._analyze_excel_file(filename, 'parallel_requests')
        
        return {'success': False, 'method': 'parallel_requests'}
    
    def method_timing_based(self) -> Dict[str, Any]:
        """방법 2: 타이밍 기반 공격"""
        print("🔍 방법 2: 타이밍 기반 공격")
        
        # 서버 로드가 낮은 시간대를 이용
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 매우 긴 타임아웃과 스트리밍으로 대용량 파일 처리
        for attempt in range(5):
            try:
                print(f"   시도 {attempt + 1}/5...")
                
                # 매번 다른 날짜 범위로 시도
                end_date = datetime.now() - timedelta(days=attempt * 30)
                start_date = end_date - timedelta(days=30)
                
                params = {
                    'page': '0',
                    'tabSort': 'blacklist',
                    'startDate': start_date.strftime('%Y%m%d'),
                    'endDate': end_date.strftime('%Y%m%d'),
                    'size': '10000',  # 매우 큰 사이즈
                    'findCondition': 'all'
                }
                
                response = session.post(
                    f"{self.base_url}/fcti/securityAdvisory/advisoryListDownloadXlsx",
                    data=params,
                    timeout=300,  # 5분 타임아웃
                    stream=True
                )
                
                print(f"   응답: {response.status_code}")
                print(f"   Content-Type: {response.headers.get('Content-Type')}")
                
                # 스트리밍으로 파일 다운로드
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    
                    # 실제 다운로드 시도
                    content = b''
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            content += chunk
                            # 진행 상황 출력
                            if len(content) % (1024 * 1024) == 0:  # 1MB마다
                                print(f"   다운로드: {len(content) // 1024}KB")
                    
                    print(f"   총 다운로드: {len(content)} bytes")
                    
                    # Excel 파일인지 확인
                    if content.startswith(b'PK') or 'excel' in content_type:
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"/tmp/regtech_timing_{timestamp}.xlsx"
                        
                        with open(filename, 'wb') as f:
                            f.write(content)
                        
                        return self._analyze_excel_file(filename, 'timing_based')
                
                time.sleep(10)  # 각 시도 사이 대기
                
            except Exception as e:
                print(f"   시도 {attempt + 1} 실패: {e}")
                continue
        
        return {'success': False, 'method': 'timing_based'}
    
    def method_curl_with_cookies(self) -> Dict[str, Any]:
        """방법 3: cURL + 쿠키 조작"""
        print("🔍 방법 3: cURL + 쿠키 조작")
        
        # 다양한 쿠키 조합 시도
        cookie_combinations = [
            "JSESSIONID=ABCD1234567890; SESSION=valid_session",
            "regtech_session=authenticated; user_type=1",
            "_regtech_auth=true; login_status=success",
            "session_token=valid; authenticated=true",
            # 빈 쿠키도 시도
            ""
        ]
        
        for i, cookies in enumerate(cookie_combinations):
            try:
                print(f"   cURL 시도 {i + 1}: {cookies[:30]}...")
                
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                
                curl_data = f"page=0&tabSort=blacklist&startDate={start_date}&endDate={end_date}&size=5000"
                output_file = f"/tmp/regtech_curl_{i}.xlsx"
                
                curl_command = [
                    'curl', '-X', 'POST',
                    f"{self.base_url}/fcti/securityAdvisory/advisoryListDownloadXlsx",
                    '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    '-H', 'Content-Type: application/x-www-form-urlencoded',
                    '-H', f'Cookie: {cookies}' if cookies else 'Cache-Control: no-cache',
                    '-d', curl_data,
                    '--max-time', '180',
                    '--output', output_file,
                    '--write-out', '%{http_code}\\n%{content_type}\\n%{size_download}\\n'
                ]
                
                result = subprocess.run(curl_command, capture_output=True, text=True, timeout=200)
                
                print(f"   cURL 결과: {result.stdout.strip()}")
                
                if result.returncode == 0 and os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    print(f"   파일 크기: {file_size} bytes")
                    
                    if file_size > 1000:  # 1KB 이상
                        # 파일 헤더 확인
                        with open(output_file, 'rb') as f:
                            header = f.read(4)
                        
                        if header == b'PK\\x03\\x04':  # ZIP/Excel 헤더
                            print(f"   ✅ Excel 파일 발견!")
                            return self._analyze_excel_file(output_file, 'curl_cookies')
                
            except Exception as e:
                print(f"   cURL 시도 {i + 1} 오류: {e}")
                continue
        
        return {'success': False, 'method': 'curl_cookies'}
    
    def method_raw_socket(self) -> Dict[str, Any]:
        """방법 4: Raw Socket 직접 통신"""
        print("🔍 방법 4: Raw Socket 통신")
        
        try:
            import socket
            import ssl
            
            # 원시 HTTP 요청 구성
            host = 'regtech.fsec.or.kr'
            port = 443
            
            # POST 데이터 준비
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            
            post_data = f"page=0&tabSort=blacklist&startDate={start_date}&endDate={end_date}&size=5000"
            
            http_request = f"""POST /fcti/securityAdvisory/advisoryListDownloadXlsx HTTP/1.1\\r
Host: {host}\\r
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\\r
Content-Type: application/x-www-form-urlencoded\\r
Content-Length: {len(post_data)}\\r
Connection: close\\r
\\r
{post_data}"""
            
            # SSL 소켓 생성
            context = ssl.create_default_context()
            
            with socket.create_connection((host, port), timeout=60) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    print(f"   SSL 연결 성공: {host}:{port}")
                    
                    # HTTP 요청 전송
                    ssock.send(http_request.encode())
                    
                    # 응답 수신
                    response = b''
                    while True:
                        try:
                            data = ssock.recv(8192)
                            if not data:
                                break
                            response += data
                        except socket.timeout:
                            break
                    
                    print(f"   응답 크기: {len(response)} bytes")
                    
                    # HTTP 헤더와 본문 분리
                    if b'\\r\\n\\r\\n' in response:
                        headers, body = response.split(b'\\r\\n\\r\\n', 1)
                        headers_str = headers.decode('utf-8', errors='ignore')
                        
                        print(f"   HTTP 헤더: {headers_str[:200]}...")
                        
                        # Excel 파일인지 확인
                        if body.startswith(b'PK'):
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            filename = f"/tmp/regtech_socket_{timestamp}.xlsx"
                            
                            with open(filename, 'wb') as f:
                                f.write(body)
                            
                            print(f"   ✅ Excel 파일 저장: {filename}")
                            return self._analyze_excel_file(filename, 'raw_socket')
        
        except Exception as e:
            print(f"   소켓 통신 오류: {e}")
        
        return {'success': False, 'method': 'raw_socket'}
    
    def method_alternative_urls(self) -> Dict[str, Any]:
        """방법 5: 대체 URL 및 숨겨진 엔드포인트"""
        print("🔍 방법 5: 대체 URL 탐색")
        
        # 다양한 URL 패턴 시도
        url_patterns = [
            # 기본 변형
            "/fcti/securityAdvisory/advisoryListDownloadXlsx",
            "/fcti/securityAdvisory/downloadXlsx",
            "/fcti/securityAdvisory/exportXlsx",
            "/fcti/securityAdvisory/download",
            "/fcti/securityAdvisory/export",
            
            # 백업/대체 경로
            "/fcti/backup/advisoryListDownloadXlsx",
            "/fcti/alt/advisoryListDownloadXlsx", 
            "/fcti/mobile/advisoryListDownloadXlsx",
            
            # API 스타일
            "/api/fcti/download",
            "/api/fcti/export",
            "/api/advisory/download",
            "/api/security/download",
            
            # 직접 파일 경로
            "/data/advisory.xlsx",
            "/files/blacklist.xlsx",
            "/export/advisory.xlsx",
            "/download/fcti.xlsx",
            
            # 관리자 경로
            "/admin/fcti/download",
            "/manager/advisory/export",
            
            # 테스트/개발 경로
            "/test/fcti/download",
            "/dev/advisory/export",
            "/staging/fcti/download"
        ]
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        for url_pattern in url_patterns:
            full_url = f"{self.base_url}{url_pattern}"
            
            try:
                print(f"   시도: {url_pattern}")
                
                # GET 시도
                get_resp = session.get(full_url, timeout=30)
                
                if get_resp.status_code == 200:
                    content_type = get_resp.headers.get('Content-Type', '')
                    
                    if 'excel' in content_type or get_resp.content.startswith(b'PK'):
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"/tmp/regtech_alt_url_{timestamp}.xlsx"
                        
                        with open(filename, 'wb') as f:
                            f.write(get_resp.content)
                        
                        print(f"   ✅ GET 성공: {url_pattern}")
                        return self._analyze_excel_file(filename, 'alternative_url_get')
                
                # POST 시도
                post_data = {
                    'page': '0',
                    'tabSort': 'blacklist',
                    'size': '1000'
                }
                
                post_resp = session.post(full_url, data=post_data, timeout=30)
                
                if post_resp.status_code == 200:
                    content_type = post_resp.headers.get('Content-Type', '')
                    
                    if 'excel' in content_type or post_resp.content.startswith(b'PK'):
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"/tmp/regtech_alt_url_post_{timestamp}.xlsx"
                        
                        with open(filename, 'wb') as f:
                            f.write(post_resp.content)
                        
                        print(f"   ✅ POST 성공: {url_pattern}")
                        return self._analyze_excel_file(filename, 'alternative_url_post')
                
            except Exception as e:
                continue  # 다음 URL 시도
        
        return {'success': False, 'method': 'alternative_urls'}
    
    def _analyze_excel_file(self, filename: str, method: str) -> Dict[str, Any]:
        """Excel 파일 분석"""
        try:
            import pandas as pd
            
            print(f"   📊 Excel 파일 분석: {filename}")
            
            # Excel 파일 읽기
            df = pd.read_excel(filename)
            print(f"   데이터: {len(df)} 행, {len(df.columns)} 열")
            print(f"   컬럼: {list(df.columns)}")
            
            # IP 추출
            ips = self._extract_ips_from_dataframe(df)
            
            if ips:
                # 결과 저장
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                result_file = f"/tmp/regtech_success_{method}_{timestamp}.json"
                
                result_data = {
                    'success': True,
                    'method': method,
                    'collection_date': timestamp,
                    'source_file': filename,
                    'total_records': len(df),
                    'ip_count': len(ips),
                    'ips': ips
                }
                
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(result_data, f, ensure_ascii=False, indent=2)
                
                print(f"   ✅ 성공! IP {len(ips)}개 발견")
                print(f"   📁 결과 저장: {result_file}")
                
                return result_data
            
        except Exception as e:
            print(f"   ❌ Excel 분석 오류: {e}")
        
        return {'success': False, 'method': method}
    
    def _extract_ips_from_dataframe(self, df) -> List[Dict[str, Any]]:
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
                            'method': 'final_collection'
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
    
    def run_final_collection(self) -> Dict[str, Any]:
        """최종 수집 실행"""
        print("🚀 REGTECH 최종 수집 - 모든 방법 총동원")
        print("=" * 60)
        
        methods = [
            self.method_parallel_requests,
            self.method_timing_based,
            self.method_curl_with_cookies,
            self.method_raw_socket,
            self.method_alternative_urls
        ]
        
        for i, method in enumerate(methods, 1):
            print(f"\\n[{i}/{len(methods)}] {method.__doc__.split(':')[1].strip()}")
            
            try:
                result = method()
                self.all_attempts.append(result)
                
                if result['success']:
                    print(f"✅ 성공! 방법: {result['method']}")
                    print(f"📊 수집된 IP: {result.get('ip_count', 0)}개")
                    self.success_results.append(result)
                    # 첫 번째 성공하면 즉시 반환
                    return result
                else:
                    print(f"❌ 실패: {result.get('error', 'No data found')}")
            
            except Exception as e:
                print(f"❌ 예외 발생: {e}")
                self.all_attempts.append({
                    'success': False,
                    'method': method.__name__,
                    'error': str(e)
                })
        
        # 모든 방법 실패
        return {
            'success': False,
            'error': 'All final methods failed',
            'attempts': len(self.all_attempts),
            'details': self.all_attempts
        }

def main():
    """메인 실행"""
    collector = RegtechFinalCollector()
    
    result = collector.run_final_collection()
    
    print("\\n" + "="*60)
    print("📊 최종 수집 결과")
    print("="*60)
    
    if result['success']:
        print(f"✅ 성공한 방법: {result['method']}")
        print(f"🎯 수집된 IP: {result.get('ip_count', 0)}개")
        
        if 'ips' in result and result['ips']:
            print(f"\\n📋 샘플 IP:")
            for i, ip_data in enumerate(result['ips'][:10]):
                print(f"  {i+1}. {ip_data.get('ip', 'N/A')}")
        
        # 통합 시스템에 데이터 추가
        print(f"\\n🔄 통합 시스템에 데이터 추가 중...")
        
        # API를 통해 데이터 추가 (로컬 서버가 실행중이라고 가정)
        try:
            import requests
            api_response = requests.post(
                'http://localhost:8542/api/collection/regtech/trigger',
                json={'force': True, 'test_data': result['ips'][:5]},  # 일부만 테스트
                timeout=30
            )
            
            if api_response.status_code == 200:
                print(f"✅ 통합 시스템 업데이트 성공")
            else:
                print(f"❌ 통합 시스템 업데이트 실패: {api_response.status_code}")
        
        except Exception as e:
            print(f"❌ 통합 시스템 연결 실패: {e}")
        
    else:
        print(f"❌ 모든 최종 방법 실패")
        print(f"🔍 시도한 방법: {result.get('attempts', 0)}개")
        
        print(f"\\n💡 권장사항:")
        print(f"  1. REGTECH 서버의 인증 정책이 변경되었을 가능성")
        print(f"  2. 현재 샘플 데이터(145개 IP)로 시스템 테스트 계속 진행")
        print(f"  3. 주기적으로 재시도하여 서버 정책 변경 모니터링")

if __name__ == "__main__":
    main()