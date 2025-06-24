#!/usr/bin/env python3
"""
SECUDIUM IP 소스
SECUDIUM Threat Intelligence 포털에서 위협 IP 수집
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator
from ..base_source import BaseIPSource, IPEntry, SourceConfig

logger = logging.getLogger(__name__)


class SecudiumSource(BaseIPSource):
    """SECUDIUM Threat Intelligence IP 소스"""
    
    @property
    def source_name(self) -> str:
        return "SECUDIUM"
    
    @property
    def source_type(self) -> str:
        return "api"  # API/Web-based source
    
    @property
    def supported_formats(self) -> List[str]:
        return ["json", "excel", "csv"]
    
    def __init__(self, config: SourceConfig):
        super().__init__(config)
        self.description = "SECUDIUM Threat Intelligence Portal"
        self.base_url = "https://secudium.skinfosec.co.kr"
        self.priority = 7  # High priority threat intelligence
        
        # 설정 로드
        self.username = self.config.settings.get('username') or os.getenv('SECUDIUM_USERNAME', 'nextrade')
        self.password = self.config.settings.get('password') or os.getenv('SECUDIUM_PASSWORD', 'Sprtmxm1@3')
        
        # Data paths
        self.data_dir = Path("data/sources/secudium")
        self.backup_dir = Path("backup")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 세션 초기화
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        self._logged_in = False
        self._last_collection_data = None
    
    def validate_config(self) -> bool:
        """설정 유효성 검사"""
        if not self.username or not self.password:
            self.logger.error("SECUDIUM credentials not configured")
            return False
        
        try:
            # Test connectivity
            response = self.session.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                self.logger.info("SECUDIUM site connectivity verified")
                return True
            else:
                self.logger.error(f"SECUDIUM site returned status {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to connect to SECUDIUM: {e}")
            return False
    
    def fetch_data(self) -> Iterator[IPEntry]:
        """
        SECUDIUM 데이터 수집
        
        Note: 현재 SECUDIUM은 SMS OTP 인증이 필요하여 완전 자동화가 어려움
        기존 백업 데이터나 수동 수집된 데이터를 사용
        """
        try:
            # Try to get data from existing backups first
            backup_data = self._load_backup_data()
            if backup_data:
                self.logger.info(f"Loading {len(backup_data)} IPs from backup data")
                for ip_data in backup_data:
                    yield self._create_ip_entry(ip_data)
                return
            
            # Try to collect fresh data (requires manual intervention for OTP)
            fresh_data = self._attempt_collection()
            if fresh_data:
                self.logger.info(f"Collected {len(fresh_data)} fresh IPs from SECUDIUM")
                for ip_data in fresh_data:
                    yield self._create_ip_entry(ip_data)
            else:
                self.logger.warning("No SECUDIUM data available - requires manual collection due to OTP")
                
        except Exception as e:
            self.logger.error(f"Failed to fetch SECUDIUM data: {e}")
            self._error_count += 1
    
    def _load_backup_data(self) -> Optional[List[Dict]]:
        """기존 백업 데이터 로드"""
        backup_files = [
            "backup/20250616_103103/data_backup/secudium_blacklist.json",
            "data/sources/secudium/latest_collection.json",
            "instance/secudium_data.json"
        ]
        
        for backup_file in backup_files:
            try:
                backup_path = Path(backup_file)
                if backup_path.exists():
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if isinstance(data, dict) and 'blacklist' in data:
                        self.logger.info(f"Loaded backup data from {backup_file}")
                        return data['blacklist']
                    elif isinstance(data, list):
                        self.logger.info(f"Loaded backup data from {backup_file}")
                        return data
                        
            except Exception as e:
                self.logger.debug(f"Could not load backup from {backup_file}: {e}")
        
        return None
    
    def _attempt_collection(self) -> Optional[List[Dict]]:
        """
        신규 데이터 수집 시도
        OTP 문제로 인해 실제로는 수동 개입이 필요
        """
        try:
            # Check if we have a recent collection script result
            collection_files = list(Path("data/downloads/secudium").glob("*.json"))
            if collection_files:
                # Get the most recent file
                latest_file = max(collection_files, key=lambda x: x.stat().st_mtime)
                with open(latest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, list) and len(data) > 0:
                    self.logger.info(f"Using recent collection data from {latest_file}")
                    return data
            
        except Exception as e:
            self.logger.debug(f"No recent collection data available: {e}")
        
        return None
    
    def _create_ip_entry(self, ip_data: Dict) -> IPEntry:
        """IP 데이터를 IPEntry 객체로 변환"""
        
        # Handle different data formats
        if isinstance(ip_data, str):
            # Simple IP string
            return IPEntry(
                ip_address=ip_data,
                source_name=self.source_name,
                category="blacklist",
                confidence=0.8,
                detection_date=datetime.utcnow(),
                metadata={
                    "threat_level": "unknown",
                    "category": "unknown"
                }
            )
        
        # Structured data format
        ip_address = ip_data.get('ip', '')
        if not ip_address:
            raise ValueError(f"No IP address found in data: {ip_data}")
        
        # Map threat levels to confidence scores
        threat_level = ip_data.get('threat_level', 'medium')
        confidence_map = {
            'critical': 0.95,
            'high': 0.85,
            'medium': 0.75,
            'low': 0.65,
            'unknown': 0.5
        }
        
        confidence = confidence_map.get(threat_level, 0.75)
        if 'confidence' in ip_data:
            confidence = max(confidence, ip_data['confidence'] / 100.0)
        
        # Parse dates
        detection_date = datetime.utcnow()
        if 'first_seen' in ip_data:
            try:
                detection_date = datetime.fromisoformat(ip_data['first_seen'].replace('Z', '+00:00'))
            except:
                pass
        
        metadata = {
            "threat_level": threat_level,
            "category": ip_data.get('category', 'unknown'),
            "last_seen": ip_data.get('last_seen'),
            "attack_types": ip_data.get('attack_types', []),
            "geolocation": ip_data.get('geolocation', {}),
            "source_confidence": ip_data.get('confidence', 95)
        }
        
        return IPEntry(
            ip_address=ip_address,
            source_name=self.source_name,
            category="blacklist",
            confidence=confidence,
            detection_date=detection_date,
            metadata=metadata
        )
    
    def get_collection_status(self) -> Dict[str, Any]:
        """수집 상태 정보 반환"""
        return {
            "source_name": self.source_name,
            "source_type": self.source_type,
            "last_update": self._last_update,
            "error_count": self._error_count,
            "max_errors": self._max_errors,
            "is_healthy": self._error_count < self._max_errors,
            "requires_manual_intervention": True,  # Due to OTP requirement
            "credentials_configured": bool(self.username and self.password),
            "site_accessible": self.validate_config(),
            "backup_data_available": self._load_backup_data() is not None
        }
    
    def trigger_manual_collection(self) -> Dict[str, Any]:
        """
        수동 수집 트리거 (실제로는 안내 메시지 반환)
        """
        return {
            "status": "manual_intervention_required",
            "message": "SECUDIUM collection requires SMS OTP verification",
            "instructions": [
                "1. Run: python3 scripts/secudium_auto_collector.py",
                "2. Complete SMS OTP verification when prompted",
                "3. Data will be automatically imported after collection",
                "4. Check collection status via API"
            ],
            "alternative": "Import existing backup data using import_secudium_backup.py"
        }
    
    def import_backup_data(self, backup_file: str = None) -> Dict[str, Any]:
        """백업 데이터 임포트"""
        try:
            if not backup_file:
                backup_file = "backup/20250616_103103/data_backup/secudium_blacklist.json"
            
            backup_path = Path(backup_file)
            if not backup_path.exists():
                return {
                    "status": "error",
                    "message": f"Backup file not found: {backup_file}"
                }
            
            with open(backup_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, dict) and 'blacklist' in data:
                ip_count = len(data['blacklist'])
                metadata = data.get('metadata', {})
                
                # Save to current data directory
                current_data_file = self.data_dir / "imported_data.json"
                with open(current_data_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                return {
                    "status": "success",
                    "message": f"Successfully imported {ip_count} IPs from backup",
                    "ip_count": ip_count,
                    "metadata": metadata,
                    "saved_to": str(current_data_file)
                }
            else:
                return {
                    "status": "error",
                    "message": "Invalid backup data format"
                }
                
        except Exception as e:
            self.logger.error(f"Failed to import backup data: {e}")
            return {
                "status": "error",
                "message": f"Import failed: {str(e)}"
            }