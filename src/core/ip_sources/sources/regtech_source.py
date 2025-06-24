#!/usr/bin/env python3
"""
RegTech (금보원) IP 소스
금융보안원 레그테크 포털에서 요주의 IP 수집
"""

import requests
import json
import re
import os
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from .base_source import BaseIPSource
import glob

class RegTechSource(BaseIPSource):
    """RegTech 금융보안원 IP 소스"""
    
    def __init__(self, config=None):
        super().__init__()
        self.name = "regtech_fsec"
        self.description = "금융보안원 레그테크 포털 요주의 IP"
        self.base_url = "https://regtech.fsec.or.kr"
        self.priority = 8  # 높은 우선순위
        
        # 설정 로드
        self.config = config or {}
        self.username = self.config.get('username') or os.getenv('BLACKLIST_USERNAME')
        self.password = self.config.get('password') or os.getenv('BLACKLIST_PASSWORD')
        
        # 세션 초기화
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        self._logged_in = False
    
    def is_available(self):
        """소스 사용 가능 여부 확인"""
        if not self.username or not self.password:
            return False, "블랙리스트 계정 정보가 필요합니다."
        
        try:
            # 레그테크 사이트 접근 테스트
            response = self.session.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                return True, "RegTech 사이트 접근 가능"
            else:
                return False, f"RegTech 사이트 접근 실패: {response.status_code}"
        except Exception as e:
            return False, f"RegTech 사이트 연결 오류: {e}"
    
    def collect_ips(self, **kwargs):
        """IP 수집 실행"""
        try:
            print(f"🏛️ {self.name} 소스에서 IP 수집 시작...")
            
            # 1. 엑셀 파일 기반 수집 (우선)
            excel_ips = self._collect_from_excel_files()
            
            # 2. 웹 스크래핑 수집 (보조)
            web_ips = self._collect_from_web_scraping()
            
            # 3. 기존 파싱된 데이터 로드
            cached_ips = self._load_cached_data()
            
            # 모든 IP 통합
            all_ips = set()
            all_ips.update(excel_ips)
            all_ips.update(web_ips)
            all_ips.update(cached_ips)
            
            # 결과 정리
            final_ips = sorted(list(all_ips))
            
            result = {
                'ips': final_ips,
                'total_count': len(final_ips),
                'source_breakdown': {
                    'excel_files': len(excel_ips),
                    'web_scraping': len(web_ips),
                    'cached_data': len(cached_ips)
                },
                'collection_method': 'multi_source_regtech',
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"   ✅ 총 {len(final_ips)}개 IP 수집 완료")
            print(f"      - 엑셀: {len(excel_ips)}개")
            print(f"      - 웹: {len(web_ips)}개") 
            print(f"      - 캐시: {len(cached_ips)}개")
            
            return result
            
        except Exception as e:
            print(f"   ❌ RegTech IP 수집 실패: {e}")
            return {'ips': [], 'total_count': 0, 'error': str(e)}
    
    def _collect_from_excel_files(self):
        """엑셀 파일에서 IP 수집"""
        excel_ips = set()
        
        try:
            # RegTech 관련 엑셀 파일 찾기
            excel_patterns = [
                "downloads/regtech_excel/*.xlsx",
                "downloads/regtech_excel/*.xls",
                "data/blacklist/regtech*/*.xlsx"
            ]
            
            found_files = []
            for pattern in excel_patterns:
                found_files.extend(glob.glob(pattern, recursive=True))
            
            if not found_files:
                return excel_ips
            
            print(f"   📊 {len(found_files)}개 엑셀 파일 처리 중...")
            
            for file_path in found_files:
                try:
                    # 엑셀 파일 읽기
                    excel_data = pd.read_excel(file_path, sheet_name=None)
                    
                    for sheet_name, df in excel_data.items():
                        # 각 셀에서 IP 찾기
                        for idx, row in df.iterrows():
                            for col_name, cell_value in row.items():
                                str_value = str(cell_value) if pd.notna(cell_value) else ""
                                
                                # IP 패턴 찾기
                                ip_matches = re.findall(r'\\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b', str_value)
                                for ip in ip_matches:
                                    if self._is_valid_public_ip(ip):
                                        excel_ips.add(ip)
                                        
                except Exception as e:
                    print(f"      ⚠️ 엑셀 파일 처리 실패 ({file_path}): {e}")
                    continue
            
            print(f"      ✅ 엑셀에서 {len(excel_ips)}개 IP 추출")
            
        except Exception as e:
            print(f"      ❌ 엑셀 파일 수집 실패: {e}")
        
        return excel_ips
    
    def _collect_from_web_scraping(self):
        """웹 스크래핑으로 IP 수집"""
        web_ips = set()
        
        try:
            if not self.username or not self.password:
                print(f"      ⚠️ 웹 스크래핑: 계정 정보 없음")
                return web_ips
            
            # 로그인 시도
            if self._login():
                print(f"      🔐 로그인 성공, 웹 데이터 수집 중...")
                
                # 보안 권고사항 페이지에서 IP 수집
                advisory_url = f"{self.base_url}/fcti/securityAdvisory/advisoryList"
                
                for page in range(1, 6):  # 최대 5페이지
                    try:
                        params = {'page': page, 'size': 100}
                        response = self.session.get(advisory_url, params=params, timeout=30)
                        
                        if response.status_code == 200:
                            page_ips = self._extract_ips_from_html(response.text)
                            web_ips.update(page_ips)
                            
                            if not page_ips:  # 더 이상 데이터가 없으면 중단
                                break
                        else:
                            break
                            
                    except Exception as e:
                        print(f"         ⚠️ 페이지 {page} 처리 실패: {e}")
                        break
                
                print(f"      ✅ 웹에서 {len(web_ips)}개 IP 수집")
            else:
                print(f"      ❌ 로그인 실패, 웹 수집 건너뜀")
        
        except Exception as e:
            print(f"      ❌ 웹 스크래핑 실패: {e}")
        
        return web_ips
    
    def _load_cached_data(self):
        """기존 파싱된 데이터 로드"""
        cached_ips = set()
        
        try:
            # 기존 저장된 RegTech 데이터 디렉토리들
            data_dirs = [
                "data/blacklist/regtech_watchlist",
                "data/blacklist/regtech_comprehensive", 
                "data/blacklist/regtech_excel_parsed",
                "data/blacklist/regtech_integrated"
            ]
            
            for data_dir in data_dirs:
                if os.path.exists(data_dir):
                    # 최신 월별 데이터 로드
                    month_dirs = sorted([d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))])
                    
                    for month_dir in month_dirs[-3:]:  # 최근 3개월
                        month_path = os.path.join(data_dir, month_dir)
                        
                        # IP 파일들 찾기
                        ip_files = glob.glob(f"{month_path}/*ips*.txt")
                        
                        for ip_file in ip_files:
                            try:
                                with open(ip_file, 'r') as f:
                                    for line in f:
                                        ip = line.strip()
                                        if self._is_valid_public_ip(ip):
                                            cached_ips.add(ip)
                            except Exception as e:
                                continue
            
            if cached_ips:
                print(f"      ✅ 캐시에서 {len(cached_ips)}개 IP 로드")
            
        except Exception as e:
            print(f"      ❌ 캐시 데이터 로드 실패: {e}")
        
        return cached_ips
    
    def _login(self):
        """RegTech 로그인"""
        if self._logged_in:
            return True
        
        try:
            # 로그인 페이지 접속
            login_url = f"{self.base_url}/member/login"
            login_page = self.session.get(login_url, timeout=30)
            
            if login_page.status_code != 200:
                return False
            
            # 로그인 데이터
            login_data = {
                'username': self.username,
                'password': self.password
            }
            
            # 로그인 요청
            login_response = self.session.post(login_url, data=login_data, timeout=30, allow_redirects=True)
            
            # 로그인 성공 확인
            if 'login' not in login_response.url.lower():
                self._logged_in = True
                return True
            
            return False
            
        except Exception as e:
            print(f"         ❌ 로그인 오류: {e}")
            return False
    
    def _extract_ips_from_html(self, html_content):
        """HTML에서 IP 추출"""
        page_ips = set()
        
        try:
            # IP 패턴으로 추출
            ip_pattern = r'\\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b'
            found_ips = re.findall(ip_pattern, html_content)
            
            for ip in found_ips:
                if self._is_valid_public_ip(ip):
                    page_ips.add(ip)
        
        except Exception as e:
            print(f"         ❌ HTML IP 추출 실패: {e}")
        
        return page_ips
    
    def _is_valid_public_ip(self, ip_string):
        """공인 IP 유효성 검증"""
        try:
            parts = ip_string.split('.')
            if len(parts) != 4:
                return False
            
            for part in parts:
                num = int(part)
                if not (0 <= num <= 255):
                    return False
            
            # 사설 IP나 로컬 IP 제외
            if (ip_string.startswith(('192.168.', '10.', '172.')) or
                ip_string.startswith(('127.', '0.0.', '255.255.')) or
                ip_string in ['0.0.0.0', '255.255.255.255']):
                return False
            
            return True
            
        except:
            return False
    
    def get_source_info(self):
        """소스 정보 반환"""
        return {
            'name': self.name,
            'description': self.description,
            'type': 'regtech_portal',
            'priority': self.priority,
            'requires_auth': True,
            'data_types': ['excel_files', 'web_scraping', 'cached_data'],
            'update_frequency': 'daily',
            'reliability': 'high'
        }