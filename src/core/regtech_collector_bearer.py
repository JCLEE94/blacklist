#!/usr/bin/env python3
"""
REGTECH Bearer Token 기반 수집기
"""

import os
import json
import logging
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path
import re
from bs4 import BeautifulSoup
import subprocess
import tempfile

from src.core.models import BlacklistEntry
from src.config.settings import settings

logger = logging.getLogger(__name__)


class RegtechBearerCollector:
    """
    REGTECH Bearer Token 인증 기반 수집기
    PowerShell 스크립트 방식을 Python으로 재현
    """
    
    def __init__(self, data_dir: str, cache_backend=None):
        self.data_dir = data_dir
        self.regtech_dir = os.path.join(data_dir, 'regtech')
        os.makedirs(self.regtech_dir, exist_ok=True)
        
        self.base_url = "https://regtech.fsec.or.kr"
        
        # Bearer Token (PowerShell 스크립트에서 제공)
        self.bearer_token = "BearereyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJuZXh0cmFkZSIsIm9yZ2FubmFtZSI6IuuEpeyKpO2KuOugiOydtOuTnCIsImlkIjoibmV4dHJhZGUiLCJleHAiOjE3NTExMTkyNzYsInVzZXJuYW1lIjoi7J6l7ZmN7KSAIn0.YwZHoHZCVqDnaryluB0h5_ituxYcaRz4voT7GRfgrNrP86W8TfvBuJbHMON4tJa4AQmNP-XhC_PuAVPQTjJADA"
        
        logger.info(f"REGTECH Bearer 수집기 초기화 완료")
    
    def collect_with_powershell(self, start_date: str = None, end_date: str = None) -> List[BlacklistEntry]:
        """
        PowerShell을 직접 실행하여 데이터 수집
        Linux에서는 pwsh (PowerShell Core) 필요
        """
        logger.info("PowerShell을 통한 REGTECH 수집 시작")
        
        # 날짜 설정
        if not start_date or not end_date:
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=30)
            start_date = start_dt.strftime('%Y%m%d')
            end_date = end_dt.strftime('%Y%m%d')
        
        # PowerShell 스크립트 생성
        ps_script = f'''
$url = "https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList"
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$session.UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Bearer Token 쿠키 추가
$session.Cookies.Add((New-Object System.Net.Cookie("regtech-va", "{self.bearer_token}", "/", "regtech.fsec.or.kr")))

# POST 데이터
$body = @{{
    "page" = "0"
    "tabSort" = "blacklist"
    "startDate" = "{start_date}"
    "endDate" = "{end_date}"
    "size" = "100"
}}

try {{
    $response = Invoke-WebRequest -UseBasicParsing -Uri $url -Method POST -WebSession $session -Body $body -ContentType "application/x-www-form-urlencoded"
    $response.Content
}} catch {{
    Write-Error $_.Exception.Message
}}
'''
        
        try:
            # PowerShell Core 실행 (Linux에서는 pwsh 필요)
            result = subprocess.run(
                ['pwsh', '-Command', ps_script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                # HTML 파싱
                return self._parse_html_response(result.stdout)
            else:
                logger.error(f"PowerShell 실행 실패: {result.stderr}")
                return []
                
        except FileNotFoundError:
            logger.warning("PowerShell Core (pwsh)가 설치되지 않음. Python 방식으로 시도...")
            return self.collect_with_python(start_date, end_date)
        except Exception as e:
            logger.error(f"PowerShell 수집 중 오류: {e}")
            return []
    
    def collect_with_python(self, start_date: str = None, end_date: str = None) -> List[BlacklistEntry]:
        """
        Python requests를 사용한 수집 (Bearer Token 인증)
        """
        logger.info("Python Bearer Token 인증으로 REGTECH 수집")
        
        # 날짜 설정
        if not start_date or not end_date:
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=30)
            start_date = start_dt.strftime('%Y%m%d')
            end_date = end_dt.strftime('%Y%m%d')
        
        logger.info(f"수집 날짜: {start_date} ~ {end_date}")
        
        try:
            # 세션 생성
            session = requests.Session()
            
            # Bearer Token 쿠키 설정
            session.cookies.set(
                'regtech-va', 
                self.bearer_token,
                domain='regtech.fsec.or.kr',
                path='/'
            )
            
            # 헤더 설정
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            })
            
            # POST 요청
            form_data = {
                'page': '0',
                'tabSort': 'blacklist',
                'startDate': start_date,
                'endDate': end_date,
                'findCondition': 'all',
                'findKeyword': '',
                'size': '100'
            }
            
            response = session.post(
                f"{self.base_url}/fcti/securityAdvisory/advisoryList",
                data=form_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': f"{self.base_url}/fcti/securityAdvisory/advisoryList"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"응답 받음: {len(response.text)} bytes")
                
                # HTML 파싱
                collected_ips = self._parse_html_response(response.text)
                
                if not collected_ips:
                    # JavaScript 렌더링 필요 확인
                    if 'javascript' in response.text.lower() or 'ajax' in response.text.lower():
                        logger.warning("JavaScript 렌더링이 필요함. Selenium 사용 고려")
                        # TODO: Selenium 구현
                
                return collected_ips
            else:
                logger.error(f"요청 실패: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Python 수집 중 오류: {e}")
            return []
    
    def _parse_html_response(self, html_content: str) -> List[BlacklistEntry]:
        """
        HTML 응답에서 IP 추출
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            ip_entries = []
            
            # IP 패턴
            ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
            
            # 1. 테이블에서 IP 찾기
            tables = soup.find_all('table')
            logger.info(f"테이블 {len(tables)}개 발견")
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:  # 헤더 제외
                    cells = row.find_all(['td', 'th'])
                    if cells:
                        row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                        
                        # IP 찾기
                        ips = ip_pattern.findall(row_text)
                        for ip in ips:
                            if self._is_valid_public_ip(ip):
                                # 추가 정보 추출 시도
                                country = 'Unknown'
                                attack_type = 'REGTECH'
                                date_str = datetime.now().strftime('%Y-%m-%d')
                                
                                # 국가 정보 찾기
                                for cell in cells:
                                    text = cell.get_text(strip=True)
                                    if len(text) == 2 and text.isalpha():  # 국가 코드
                                        country = text
                                        break
                                
                                entry = BlacklistEntry(
                                    ip=ip,
                                    country=country,
                                    attack_type=attack_type,
                                    source='REGTECH',
                                    detection_date=date_str,
                                    description='REGTECH 위협정보'
                                )
                                ip_entries.append(entry)
                                break  # 행당 하나의 IP만
            
            # 2. 테이블 외부 IP 검색 (fallback)
            if not ip_entries:
                all_ips = ip_pattern.findall(html_content)
                seen = set()
                
                for ip in all_ips:
                    if ip not in seen and self._is_valid_public_ip(ip):
                        seen.add(ip)
                        entry = BlacklistEntry(
                            ip=ip,
                            country='Unknown',
                            attack_type='REGTECH',
                            source='REGTECH',
                            detection_date=datetime.now().strftime('%Y-%m-%d'),
                            description='REGTECH 위협정보'
                        )
                        ip_entries.append(entry)
            
            logger.info(f"파싱 결과: {len(ip_entries)}개 IP 추출")
            return ip_entries
            
        except Exception as e:
            logger.error(f"HTML 파싱 오류: {e}")
            return []
    
    def _is_valid_public_ip(self, ip: str) -> bool:
        """공인 IP 여부 확인"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            
            # 각 부분이 0-255 범위인지 확인
            for part in parts:
                if not 0 <= int(part) <= 255:
                    return False
            
            # 사설 IP 제외
            if (parts[0] == '10' or
                (parts[0] == '172' and 16 <= int(parts[1]) <= 31) or
                (parts[0] == '192' and parts[1] == '168') or
                parts[0] in ['0', '127', '255']):
                return False
            
            return True
        except:
            return False
    
    def collect_from_web(self, max_pages: int = 5, page_size: int = 100,
                        parallel_workers: int = 1, start_date: str = None,
                        end_date: str = None) -> List[BlacklistEntry]:
        """
        웹에서 데이터 수집 (Bearer Token 인증 사용)
        """
        # Python 방식 우선 시도
        collected = self.collect_with_python(start_date, end_date)
        
        # 실패시 PowerShell 시도
        if not collected:
            logger.info("Python 수집 실패, PowerShell 시도...")
            collected = self.collect_with_powershell(start_date, end_date)
        
        return collected


def create_regtech_bearer_collector(data_dir: str, cache_backend=None) -> RegtechBearerCollector:
    """Bearer Token 기반 REGTECH 수집기 생성"""
    return RegtechBearerCollector(data_dir, cache_backend)