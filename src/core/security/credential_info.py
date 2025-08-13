"""
자격증명 정보 데이터 클래스

자격증명 관리에 필요한 데이터 구조를 정의합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


@dataclass
class CredentialInfo:
    """자격증명 정보 클래스"""
    service: str
    username: str
    password: str
    additional_data: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    is_encrypted: bool = False
    
    def is_expired(self) -> bool:
        """자격증명 만료 여부 확인"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def expires_soon(self, days: int = 7) -> bool:
        """자격증명이 곧 만료되는지 확인"""
        if self.expires_at is None:
            return False
        return datetime.now() + timedelta(days=days) > self.expires_at
    
    def update_last_used(self):
        """마지막 사용 시간 업데이트"""
        self.last_used = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'service': self.service,
            'username': self.username,
            'password': self.password if not self.is_encrypted else '***ENCRYPTED***',
            'additional_data': self.additional_data,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat(),
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'is_encrypted': self.is_encrypted
        }
