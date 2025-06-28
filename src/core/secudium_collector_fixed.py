#!/usr/bin/env python3
"""
SECUDIUM 수집기 - 실제로는 파일 기반으로 작동
OTP 인증이 필요하므로 수동으로 다운로드한 파일을 처리
"""

import os
import json
import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path

from src.core.models import BlacklistEntry
from src.config.settings import settings

logger = logging.getLogger(__name__)

class SecudiumCollector:
    """
    SECUDIUM 수집기
    - 실제로는 수동으로 다운로드한 Excel/JSON 파일 처리
    - OTP 인증으로 인해 자동화 불가
    """
    
    def __init__(self, data_dir: str, cache_backend=None):
        self.data_dir = data_dir
        self.secudium_dir = os.path.join(data_dir, 'secudium')
        os.makedirs(self.secudium_dir, exist_ok=True)
        
        logger.info(f"SECUDIUM 수집기 초기화 (파일 기반): {self.secudium_dir}")
    
    def collect_from_file(self, filepath: str = None) -> List[BlacklistEntry]:
        """파일에서 SECUDIUM 데이터 수집"""
        
        # 기본 파일 경로들
        if not filepath:
            possible_files = [
                os.path.join(self.data_dir, "secudium_test_data.json"),
                os.path.join(self.data_dir, "secudium_test_data.xlsx"),
                os.path.join(self.secudium_dir, "latest.json"),
                os.path.join(self.secudium_dir, "latest.xlsx"),
            ]
            
            # 존재하는 첫 번째 파일 사용
            for file in possible_files:
                if os.path.exists(file):
                    filepath = file
                    break
        
        if not filepath or not os.path.exists(filepath):
            logger.warning("SECUDIUM 데이터 파일을 찾을 수 없습니다")
            return []
        
        logger.info(f"SECUDIUM 파일 처리: {filepath}")
        
        # 파일 형식에 따라 처리
        if filepath.endswith('.json'):
            return self._process_json_file(filepath)
        elif filepath.endswith('.xlsx') or filepath.endswith('.xls'):
            return self._process_excel_file(filepath)
        else:
            logger.error(f"지원하지 않는 파일 형식: {filepath}")
            return []
    
    def _process_json_file(self, filepath: str) -> List[BlacklistEntry]:
        """JSON 파일 처리"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            entries = []
            details = data.get('details', [])
            
            for item in details:
                entry = BlacklistEntry(
                    ip_address=item.get('ip_address', item.get('ip', '')),
                    country=item.get('country', 'Unknown'),
                    reason=item.get('attack_type', 'SECUDIUM'),
                    source='SECUDIUM',
                    reg_date=item.get('detection_date', datetime.now().strftime('%Y-%m-%d')),
                    exp_date=None,
                    is_active=True,
                    threat_level=item.get('threat_level', 'high'),
                    source_details={
                        'type': 'SECUDIUM',
                        'attack': item.get('attack_type', 'Unknown')
                    }
                )
                entries.append(entry)
            
            logger.info(f"JSON에서 {len(entries)}개 IP 로드")
            return entries
            
        except Exception as e:
            logger.error(f"JSON 파일 처리 오류: {e}")
            return []
    
    def _process_excel_file(self, filepath: str) -> List[BlacklistEntry]:
        """Excel 파일 처리"""
        try:
            df = pd.read_excel(filepath)
            entries = []
            
            # IP 컬럼 찾기
            ip_columns = [col for col in df.columns if 'ip' in str(col).lower()]
            if not ip_columns:
                logger.error("IP 컬럼을 찾을 수 없습니다")
                return []
            
            ip_column = ip_columns[0]
            
            for _, row in df.iterrows():
                ip = str(row[ip_column]).strip()
                if not ip or ip == 'nan':
                    continue
                
                entry = BlacklistEntry(
                    ip_address=ip,
                    country=row.get('country', 'Unknown'),
                    reason=row.get('attack_type', 'SECUDIUM'),
                    source='SECUDIUM',
                    reg_date=row.get('detection_date', datetime.now().strftime('%Y-%m-%d')),
                    exp_date=None,
                    is_active=True,
                    threat_level=row.get('threat_level', 'high'),
                    source_details={
                        'type': 'SECUDIUM',
                        'attack': row.get('attack_type', 'Unknown')
                    }
                )
                entries.append(entry)
            
            logger.info(f"Excel에서 {len(entries)}개 IP 로드")
            return entries
            
        except Exception as e:
            logger.error(f"Excel 파일 처리 오류: {e}")
            return []
    
    def auto_collect(self) -> Dict[str, Any]:
        """자동 수집 (실제로는 파일 기반)"""
        try:
            logger.info("SECUDIUM 파일 기반 수집 시작")
            
            # 파일에서 데이터 수집
            collected_data = self.collect_from_file()
            
            if collected_data:
                # 결과 저장
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                result_file = os.path.join(self.secudium_dir, f'collected_{timestamp}.json')
                
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'source': 'SECUDIUM',
                        'collected_at': datetime.now().isoformat(),
                        'total_ips': len(collected_data),
                        'ips': [entry.ip_address for entry in collected_data]
                    }, f, indent=2, ensure_ascii=False)
                
                return {
                    'success': True,
                    'message': f'SECUDIUM 수집 완료: {len(collected_data)}개 IP',
                    'total_collected': len(collected_data),
                    'ips': collected_data
                }
            else:
                return {
                    'success': False,
                    'message': 'SECUDIUM 데이터를 찾을 수 없습니다',
                    'total_collected': 0
                }
                
        except Exception as e:
            logger.error(f"SECUDIUM 수집 중 오류: {e}")
            return {
                'success': False,
                'message': f'수집 오류: {str(e)}',
                'total_collected': 0
            }
    
    # 호환성을 위한 더미 메서드들
    def login(self) -> bool:
        """더미 로그인 메서드 (파일 기반이므로 불필요)"""
        logger.info("SECUDIUM은 파일 기반으로 작동합니다 (로그인 불필요)")
        return True
    
    def collect_blacklist_data(self, count: int = 100) -> List[Dict[str, Any]]:
        """더미 블랙리스트 수집 메서드"""
        entries = self.collect_from_file()
        return [{
            'ip': entry.ip_address,
            'country': entry.country,
            'attack_type': entry.reason,
            'source': 'SECUDIUM'
        } for entry in entries[:count]]