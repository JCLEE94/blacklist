#!/usr/bin/env python3
"""
REGTECH 세션 기반 수집기 - HAR 분석 결과 활용
단계별 인증 후 Excel 다운로드
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
from datetime import datetime, timedelta
from typing import List, Dict, Any
from src.config.settings import settings

class RegtechSessionCollector:
    """HAR 분석 기반 세션 인증 수집기"""
    
    def __init__(self):
        self.base_url = "https://regtech.fsec.or.kr"
        self.session = requests.Session()
        self.authenticated = False
        
        # HAR에서 추출한 정확한 브라우저 헤더
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        })
    
    def authenticate(self) -> bool:
        """단계별 인증 수행"""
        print("🔐 REGTECH 인증 시작...")
        
        try:
            # 1. 메인 페이지 접속하여 세션 초기화
            print("1️⃣ 메인 페이지 접속...")
            main_resp = self.session.get(f"{self.base_url}/main/main")
            print(f"   Status: {main_resp.status_code}")
            
            # 2. 로그인 폼 페이지 접속
            print("2️⃣ 로그인 폼 접속...")
            login_form_resp = self.session.get(f"{self.base_url}/login/loginForm")
            print(f"   Status: {login_form_resp.status_code}")
            
            # CSRF 토큰이나 숨겨진 필드 추출
            csrf_token = self._extract_csrf_token(login_form_resp.text)
            if csrf_token:
                print(f"   CSRF 토큰 발견: {csrf_token[:20]}...")
            
            # 3. 로그인 시도
            print("3️⃣ 로그인 시도...")
            login_data = {
                'memberId': settings.regtech_username,
                'memberPw': settings.regtech_password,
                'userType': '1'
            }
            
            # CSRF 토큰이 있으면 추가
            if csrf_token:
                login_data['_token'] = csrf_token
            
            login_resp = self.session.post(
                f"{self.base_url}/login/addLogin",
                data=login_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Origin': self.base_url,
                    'Referer': f"{self.base_url}/login/loginForm",
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-User': '?1',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
            
            print(f"   Status: {login_resp.status_code}")
            print(f"   Final URL: {login_resp.url}")
            print(f"   쿠키: {len(self.session.cookies)}개")
            
            # 로그인 성공 여부 확인
            if 'error=true' in login_resp.url or 'login' in login_resp.url.lower():
                print("   ❌ 로그인 실패")
                return False
            
            # 4. Advisory 페이지 접속하여 세션 확인
            print("4️⃣ Advisory 페이지 접속...")
            advisory_resp = self.session.get(f"{self.base_url}/fcti/securityAdvisory/advisoryList")
            print(f"   Status: {advisory_resp.status_code}")
            
            if advisory_resp.status_code == 200 and '로그인' not in advisory_resp.text:
                print("   ✅ 세션 인증 성공")
                self.authenticated = True
                return True
            else:
                print("   ❌ 세션 인증 실패")
                return False
        
        except Exception as e:
            print(f"   ❌ 인증 오류: {e}")
            return False
    
    def _extract_csrf_token(self, html_content: str) -> str:
        """HTML에서 CSRF 토큰 추출"""
        # 다양한 CSRF 토큰 패턴 시도
        patterns = [
            r'name="_token"[^>]*value="([^"]+)"',
            r'name="csrf_token"[^>]*value="([^"]+)"',
            r'name="authenticity_token"[^>]*value="([^"]+)"',
            r'"_token"\s*:\s*"([^"]+)"',
            r"'_token'\s*:\s*'([^']+)'"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def collect_blacklist_data(self, start_date: str = None, end_date: str = None, max_size: int = 5000) -> Dict[str, Any]:
        """인증된 세션으로 블랙리스트 데이터 수집"""
        
        if not self.authenticated:
            print("❌ 인증되지 않은 상태입니다.")
            return {'success': False, 'error': 'Not authenticated'}
        
        print("📊 블랙리스트 데이터 수집 시작...")
        
        # 기본 날짜 설정
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
        
        print(f"📅 수집 기간: {start_date} ~ {end_date}")
        
        # HAR 분석 결과를 바탕으로 한 정확한 파라미터
        form_data = [
            ("page", "0"),
            ("tabSort", "blacklist"),
            ("excelDownload", "security,blacklist,weakpoint,"),
            ("cveId", ""),
            ("ipId", ""),
            ("estId", ""),
            ("startDate", start_date),
            ("endDate", end_date),
            ("findCondition", "all"),
            ("findKeyword", ""),
            ("excelDown", "security"),
            ("excelDown", "blacklist"),
            ("excelDown", "weakpoint"),
            ("size", str(max_size))
        ]
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': self.base_url,
            'Referer': f"{self.base_url}/fcti/securityAdvisory/advisoryList",
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }
        
        try:
            print("📡 Excel 다운로드 요청...")
            response = self.session.post(
                f"{self.base_url}/fcti/securityAdvisory/advisoryListDownloadXlsx",
                data=form_data,
                headers=headers,
                timeout=120,
                stream=True
            )
            
            print(f"📊 응답 상태: {response.status_code}")
            print(f"📝 Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            print(f"📎 Content-Disposition: {response.headers.get('Content-Disposition', 'N/A')}")
            
            if response.status_code == 200:
                return self._process_response(response, start_date, end_date)
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'response_preview': response.text[:300]
                }
                
        except Exception as e:
            print(f"❌ 수집 오류: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _process_response(self, response: requests.Response, start_date: str, end_date: str) -> Dict[str, Any]:
        """응답 처리 및 데이터 추출"""
        
        content_type = response.headers.get('Content-Type', '').lower()
        content_disp = response.headers.get('Content-Disposition', '')
        
        print(f"🔍 응답 분석: {content_type}")
        
        if 'excel' in content_type or 'spreadsheet' in content_type or 'filename=' in content_disp:
            print("📋 Excel 파일 다운로드 성공!")
            return self._parse_excel_data(response.content, start_date, end_date)
        
        elif 'text/html' in content_type:
            html_content = response.text
            if '로그인' in html_content or 'login' in html_content.lower():
                print("❌ 세션 만료 - 로그인 페이지로 리다이렉트")
                return {
                    'success': False,
                    'error': 'Session expired - redirected to login',
                    'requires_reauth': True
                }
            else:
                print("🔍 HTML 응답에서 IP 추출 시도")
                return self._parse_html_data(html_content, start_date, end_date)
        
        elif 'application/json' in content_type:
            print("📊 JSON 응답 처리")
            return self._parse_json_data(response.text, start_date, end_date)
        
        else:
            print(f"❓ 알 수 없는 응답 형식: {content_type}")
            return {
                'success': False,
                'error': 'Unknown response format',
                'content_type': content_type,
                'content_preview': response.text[:500]
            }
    
    def _parse_excel_data(self, excel_content: bytes, start_date: str, end_date: str) -> Dict[str, Any]:
        """Excel 파일에서 IP 데이터 추출"""
        try:
            # 임시 파일로 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(excel_content)
                tmp_path = tmp_file.name
            
            print(f"📁 임시 파일 저장: {tmp_path}")
            
            # Excel 파일 읽기
            df = pd.read_excel(tmp_path)
            print(f"📊 Excel 데이터: {len(df)} 행, {len(df.columns)} 열")
            print(f"📋 컬럼: {list(df.columns)}")
            
            # IP 데이터 추출
            ip_data = self._extract_ips_from_dataframe(df)
            
            # 결과 파일 저장
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = Path(__file__).parent.parent / 'data' / 'regtech'
            output_dir.mkdir(parents=True, exist_ok=True)
            
            excel_file = output_dir / f'regtech_session_{timestamp}.xlsx'
            json_file = output_dir / f'regtech_data_{timestamp}.json'
            
            # 원본 Excel 저장
            with open(excel_file, 'wb') as f:
                f.write(excel_content)
            
            # JSON으로 저장
            result_data = {
                'collection_date': timestamp,
                'period': f"{start_date}_{end_date}",
                'source_method': 'session_authenticated',
                'total_records': len(df),
                'ip_count': len(ip_data),
                'data': ip_data
            }
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            # 임시 파일 삭제
            os.unlink(tmp_path)
            
            print(f"✅ 데이터 추출 완료: {len(ip_data)}개 IP")
            print(f"📁 저장 위치: {json_file}")
            
            return {
                'success': True,
                'method': 'session_excel_download',
                'total_records': len(df),
                'ip_count': len(ip_data),
                'data': ip_data,
                'files': {
                    'excel': str(excel_file),
                    'json': str(json_file)
                }
            }
            
        except Exception as e:
            print(f"❌ Excel 파싱 오류: {e}")
            return {
                'success': False,
                'error': f'Excel parsing failed: {e}'
            }
    
    def _parse_html_data(self, html_content: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """HTML에서 IP 데이터 추출"""
        
        # IP 패턴 찾기
        ip_pattern = r'\\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b'
        ips = re.findall(ip_pattern, html_content)
        
        print(f"🔍 발견된 IP: {len(set(ips))}개")
        
        # 공인 IP만 필터링
        public_ips = []
        for ip in set(ips):
            if self._is_public_ip(ip):
                public_ips.append({
                    'ip': ip,
                    'source': 'REGTECH',
                    'detection_date': datetime.now().strftime('%Y-%m-%d'),
                    'method': 'html_extraction'
                })
        
        return {
            'success': len(public_ips) > 0,
            'method': 'html_extraction',
            'ip_count': len(public_ips),
            'data': public_ips,
            'raw_ips_found': len(ips)
        }
    
    def _parse_json_data(self, json_text: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """JSON 응답에서 데이터 추출"""
        try:
            data = json.loads(json_text)
            print(f"📊 JSON 데이터 구조: {list(data.keys()) if isinstance(data, dict) else type(data)}")
            
            return {
                'success': True,
                'method': 'json_api',
                'data': data
            }
            
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error': f'JSON parsing failed: {e}'
            }
    
    def _extract_ips_from_dataframe(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """DataFrame에서 IP 데이터 추출"""
        ip_data = []
        
        # IP 관련 컬럼 찾기
        ip_columns = []
        for col in df.columns:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in ['ip', '아이피', 'addr', 'address']):
                ip_columns.append(col)
        
        print(f"🔍 IP 관련 컬럼: {ip_columns}")
        
        if not ip_columns:
            # 모든 컬럼에서 IP 패턴 찾기
            ip_pattern = r'\\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b'
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
                                'column': col,
                                'row_index': idx,
                                'method': 'session_excel'
                            })
        else:
            # IP 컬럼에서 직접 추출
            for col in ip_columns:
                for idx, ip in enumerate(df[col]):
                    ip_str = str(ip).strip()
                    if self._is_valid_ip(ip_str) and self._is_public_ip(ip_str):
                        ip_data.append({
                            'ip': ip_str,
                            'source': 'REGTECH',
                            'detection_date': datetime.now().strftime('%Y-%m-%d'),
                            'column': col,
                            'row_index': idx,
                            'method': 'session_excel',
                            'additional_data': {c: str(df.iloc[idx][c]) for c in df.columns if c != col}
                        })
        
        return ip_data
    
    def _is_valid_ip(self, ip: str) -> bool:
        """IP 주소 유효성 검증"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                if not (0 <= int(part) <= 255):
                    return False
            return True
        except:
            return False
    
    def _is_public_ip(self, ip: str) -> bool:
        """공인 IP 여부 확인"""
        if not self._is_valid_ip(ip):
            return False
        
        parts = ip.split('.')
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

def main():
    """메인 실행 함수"""
    collector = RegtechSessionCollector()
    
    # 1. 인증 수행
    if not collector.authenticate():
        print("❌ 인증 실패 - 수집을 중단합니다.")
        return
    
    # 2. 데이터 수집
    result = collector.collect_blacklist_data(max_size=5000)
    
    print("\\n" + "="*60)
    print("📊 최종 수집 결과")
    print("="*60)
    
    if result['success']:
        print(f"✅ 성공: {result['method']}")
        print(f"📊 총 레코드: {result.get('total_records', 'N/A')}")
        print(f"🎯 IP 개수: {result.get('ip_count', 0)}")
        
        if 'files' in result:
            print(f"📁 저장 파일:")
            for file_type, file_path in result['files'].items():
                print(f"  - {file_type}: {file_path}")
        
        if result.get('data'):
            print(f"\\n📋 샘플 데이터:")
            for i, item in enumerate(result['data'][:5]):
                print(f"  {i+1}. {item.get('ip', 'N/A')} - {item.get('detection_date', 'N/A')}")
    else:
        print(f"❌ 실패: {result.get('error', 'Unknown error')}")
        if 'response_preview' in result:
            print(f"📝 응답 미리보기: {result['response_preview']}")

if __name__ == "__main__":
    main()