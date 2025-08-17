#!/usr/bin/env python3
"""
REGTECH 데이터 파싱 모듈
regtech_collector.py에서 분리된 데이터 파싱 기능
"""

import logging
import pandas as pd
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from io import BytesIO

from ..common.ip_utils import IPUtils

logger = logging.getLogger(__name__)


class RegtechParser:
    """
REGTECH 데이터 파싱 전담 클래스
    """
    
    def __init__(self):
        self.ip_utils = IPUtils()
        
    def parse_excel_file(self, file_content: bytes, filename: str = "regtech_data.xlsx") -> List[Dict[str, Any]]:
        """
Excel 파일에서 IP 데이터 추출
        
        Args:
            file_content: Excel 파일 내용 (bytes)
            filename: 파일명 (로그용)
            
        Returns:
            List[Dict]: 추출된 IP 데이터 목록
        """
        try:
            logger.info(f"Parsing Excel file: {filename}")
            
            # Excel 파일 읽기
            excel_buffer = BytesIO(file_content)
            
            # 가능한 모든 시트 시도
            try:
                # 기본 시트
                df = pd.read_excel(excel_buffer, sheet_name=0)
            except Exception:
                # 다른 시트명 시도
                try:
                    df = pd.read_excel(excel_buffer, sheet_name=1)
                except Exception:
                    # 첫 번째 시트 강제 사용
                    excel_buffer.seek(0)
                    df = pd.read_excel(excel_buffer)
                    
            if df.empty:
                logger.warning(f"Empty Excel file: {filename}")
                return []
                
            logger.info(f"Excel file loaded: {len(df)} rows, columns: {list(df.columns)}")
            
            # IP 데이터 추출
            extracted_data = self._extract_ip_data_from_dataframe(df)
            
            logger.info(f"Extracted {len(extracted_data)} IP entries from {filename}")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Failed to parse Excel file {filename}: {e}")
            return []
            
    def _extract_ip_data_from_dataframe(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
DataFrame에서 IP 데이터 추출
        
        Args:
            df: pandas DataFrame
            
        Returns:
            List[Dict]: 추출된 IP 데이터
        """
        extracted_data = []
        
        # 가능한 IP 주소 패턴
        ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
        
        # 날짜 패턴 (다양한 형식 지원)
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{4}/\d{2}/\d{2}',  # YYYY/MM/DD
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d{4}\.\d{2}\.\d{2}'  # YYYY.MM.DD
        ]
        
        for index, row in df.iterrows():
            try:
                # 각 셀에서 IP 주소 찾기
                for col_name, cell_value in row.items():
                    if pd.isna(cell_value):
                        continue
                        
                    cell_str = str(cell_value)
                    
                    # IP 주소 찾기
                    ip_matches = ip_pattern.findall(cell_str)
                    
                    for ip in ip_matches:
                        if self.ip_utils.is_valid_ip(ip) and not self.ip_utils.is_private_ip(ip):
                            # 날짜 정보 추출 시도
                            detection_date = self._extract_date_from_row(row)
                            
                            # 위협 레벨 추출 시도
                            threat_level = self._extract_threat_level_from_row(row)
                            
                            # 데이터 엔트리 생성
                            entry = {
                                'ip_address': ip,
                                'source': 'REGTECH',
                                'threat_level': threat_level,
                                'detection_date': detection_date,
                                'raw_data': {
                                    'row_index': index,
                                    'column': col_name,
                                    'cell_value': cell_str[:200],  # 처음 200자만
                                    'extracted_at': datetime.now().isoformat()
                                }
                            }
                            
                            extracted_data.append(entry)
                            
            except Exception as e:
                logger.warning(f"Error processing row {index}: {e}")
                continue
                
        # 중복 IP 제거
        unique_data = self._remove_duplicate_ips(extracted_data)
        
        return unique_data
        
    def _extract_date_from_row(self, row: pd.Series) -> Optional[str]:
        """행에서 날짜 정보 추출"""
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{4}/\d{2}/\d{2}',
            r'\d{2}/\d{2}/\d{4}',
            r'\d{4}\.\d{2}\.\d{2}'
        ]
        
        for value in row.values:
            if pd.isna(value):
                continue
                
            value_str = str(value)
            
            for pattern in date_patterns:
                match = re.search(pattern, value_str)
                if match:
                    try:
                        # 날짜 형식 정규화
                        date_str = match.group()
                        
                        # 다양한 형식 파싱 시도
                        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%Y.%m.%d']:
                            try:
                                parsed_date = datetime.strptime(date_str, fmt)
                                return parsed_date.strftime('%Y-%m-%d')
                            except ValueError:
                                continue
                                
                    except Exception:
                        continue
                        
        # 기본값: 오늘 날짜
        return datetime.now().strftime('%Y-%m-%d')
        
    def _extract_threat_level_from_row(self, row: pd.Series) -> str:
        """행에서 위협 레벨 추출"""
        threat_indicators = {
            'HIGH': ['심각', '위험', 'critical', 'high', '높음'],
            'MEDIUM': ['보통', 'medium', '중간', '주의'],
            'LOW': ['낮음', 'low', '경미', '미비']
        }
        
        for value in row.values:
            if pd.isna(value):
                continue
                
            value_str = str(value).lower()
            
            for level, indicators in threat_indicators.items():
                for indicator in indicators:
                    if indicator.lower() in value_str:
                        return level
                        
        # 기본값: MEDIUM
        return 'MEDIUM'
        
    def _remove_duplicate_ips(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중복 IP 주소 제거"""
        seen_ips = set()
        unique_data = []
        
        for entry in data:
            ip = entry['ip_address']
            if ip not in seen_ips:
                seen_ips.add(ip)
                unique_data.append(entry)
                
        if len(data) != len(unique_data):
            logger.info(f"Removed {len(data) - len(unique_data)} duplicate IPs")
            
        return unique_data
        
    def validate_ip_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
IP 데이터 유효성 검증
        
        Args:
            data: 검증할 IP 데이터 목록
            
        Returns:
            List[Dict]: 유효한 IP 데이터 목록
        """
        valid_data = []
        
        for entry in data:
            try:
                ip = entry.get('ip_address')
                
                # IP 주소 유효성 검증
                if not ip or not self.ip_utils.is_valid_ip(ip):
                    logger.warning(f"Invalid IP address: {ip}")
                    continue
                    
                # 사설 IP 제외
                if self.ip_utils.is_private_ip(ip):
                    logger.debug(f"Skipping private IP: {ip}")
                    continue
                    
                # 필수 필드 검증
                if not entry.get('source'):
                    entry['source'] = 'REGTECH'
                    
                if not entry.get('threat_level'):
                    entry['threat_level'] = 'MEDIUM'
                    
                if not entry.get('detection_date'):
                    entry['detection_date'] = datetime.now().strftime('%Y-%m-%d')
                    
                valid_data.append(entry)
                
            except Exception as e:
                logger.warning(f"Error validating IP entry: {e}")
                continue
                
        logger.info(f"Validated {len(valid_data)} out of {len(data)} IP entries")
        return valid_data
