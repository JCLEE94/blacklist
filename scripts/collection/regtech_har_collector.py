#!/usr/bin/env python3
"""
HAR 분석 기반 REGTECH 직접 수집
인증 없이 Excel 다운로드 엔드포인트 활용
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import requests
import pandas as pd
import json
import re
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import tempfile

class RegtechDirectCollector:
    """HAR 분석 기반 직접 수집기"""
    
    def __init__(self):
        self.base_url = "https://regtech.fsec.or.kr"
        self.excel_endpoint = "/fcti/securityAdvisory/advisoryListDownloadXlsx"
        self.session = requests.Session()
        
        # HAR에서 추출한 헤더 설정
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
    
    def collect_blacklist_data(self, start_date: str = None, end_date: str = None, max_size: int = 5000) -> Dict[str, Any]:
        """
        HAR 기반 직접 데이터 수집
        
        Args:
            start_date: 시작 날짜 (YYYYMMDD)
            end_date: 종료 날짜 (YYYYMMDD) 
            max_size: 최대 수집 개수
        """
        print("🚀 REGTECH 직접 수집 시작 (HAR 기반)")
        
        # 기본 날짜 설정 (최근 3개월)
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
        
        print(f"📅 수집 기간: {start_date} ~ {end_date}")
        
        # 세션 초기화 및 메인 페이지 접속
        try:
            print("🔗 메인 페이지 접속 중...")
            main_response = self.session.get(f"{self.base_url}/")
            print(f"📄 메인 페이지 응답: {main_response.status_code}")
            
            # Advisory 리스트 페이지 접속 (세션 유지용)
            print("📋 Advisory 리스트 페이지 접속...")
            advisory_response = self.session.get(f"{self.base_url}/fcti/securityAdvisory/advisoryList")
            print(f"📄 Advisory 페이지 응답: {advisory_response.status_code}")
            
        except Exception as e:
            print(f"⚠️ 세션 초기화 실패: {e}")
        
        # HAR에서 추출한 정확한 파라미터 (Document 분석 결과 적용)
        form_data = {
            'page': '0',
            'tabSort': 'blacklist',  # 블랙리스트 데이터만
            'excelDownload': 'security,blacklist,weakpoint,',
            'cveId': '',
            'ipId': '',
            'estId': '',
            'startDate': start_date,
            'endDate': end_date,
            'findCondition': 'all',
            'findKeyword': '',
            'excelDown': 'blacklist',  # 블랙리스트만 선택
            'size': str(max_size)
        }
        
        # Document 분석 결과에 따른 정확한 헤더
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
            print("📡 Excel 다운로드 요청 중...")
            response = self.session.post(
                f"{self.base_url}{self.excel_endpoint}",
                data=form_data,
                headers=headers,
                timeout=60,
                stream=True
            )
            
            print(f"📊 응답 상태: {response.status_code}")
            print(f"📝 Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            print(f"📎 Content-Disposition: {response.headers.get('Content-Disposition', 'N/A')}")
            print(f"🔗 최종 URL: {response.url}")
            
            if response.status_code == 200:
                return self._process_response(response, start_date, end_date)
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'response_text': response.text[:500],
                    'final_url': response.url
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
        
        if 'excel' in content_type or 'spreadsheet' in content_type or 'filename=' in content_disp:
            print("📋 Excel 파일 다운로드 성공!")
            return self._parse_excel_data(response.content, start_date, end_date)
        
        elif 'text/html' in content_type:
            print("🔍 HTML 응답 - IP 데이터 추출 시도")
            return self._parse_html_data(response.text, start_date, end_date)
        
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
            
            # 파일 저장
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = Path(__file__).parent.parent.parent / 'data' / 'regtech'
            output_dir.mkdir(parents=True, exist_ok=True)
            
            excel_file = output_dir / f'regtech_excel_{timestamp}.xlsx'
            json_file = output_dir / f'regtech_data_{timestamp}.json'
            
            # 원본 Excel 저장
            with open(excel_file, 'wb') as f:
                f.write(excel_content)
            
            # JSON으로 저장
            result_data = {
                'collection_date': timestamp,
                'period': f"{start_date}_{end_date}",
                'source_method': 'direct_excel',
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
                'method': 'excel_download',
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
        
        # 로그인 페이지 확인
        if '로그인' in html_content or 'login' in html_content.lower():
            print("❌ 로그인 페이지로 리다이렉트됨")
            return {
                'success': False,
                'error': 'Redirected to login page',
                'requires_auth': True
            }
        
        # IP 패턴 찾기
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        ips = re.findall(ip_pattern, html_content)
        
        # 테이블 데이터 찾기
        table_pattern = r'<table[^>]*>.*?</table>'
        tables = re.findall(table_pattern, html_content, re.DOTALL)
        
        print(f"🔍 발견된 IP: {len(set(ips))}개")
        print(f"📊 발견된 테이블: {len(tables)}개")
        
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
            'raw_ips_found': len(ips),
            'tables_found': len(tables)
        }
    
    def _parse_json_data(self, json_text: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """JSON 응답에서 데이터 추출"""
        try:
            data = json.loads(json_text)
            print(f"📊 JSON 데이터 구조: {list(data.keys()) if isinstance(data, dict) else type(data)}")
            
            # JSON에서 IP 추출 로직 구현
            # (실제 응답 구조에 따라 수정 필요)
            
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
                                'column': col,
                                'row_index': idx,
                                'method': 'excel_extraction'
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
                            'method': 'excel_extraction',
                            # 다른 컬럼 데이터도 포함
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
    collector = RegtechDirectCollector()
    
    # 최근 30일 데이터 수집
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
    
    result = collector.collect_blacklist_data(start_date, end_date, max_size=5000)
    
    print("\n" + "="*60)
    print("📊 수집 결과")
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
            print(f"\n📋 샘플 데이터:")
            for i, item in enumerate(result['data'][:3]):
                print(f"  {i+1}. {item.get('ip', 'N/A')} - {item.get('detection_date', 'N/A')}")
    else:
        print(f"❌ 실패: {result.get('error', 'Unknown error')}")
        if 'response_text' in result:
            print(f"📝 응답: {result['response_text']}")

if __name__ == "__main__":
    main()