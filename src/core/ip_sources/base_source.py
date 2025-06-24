"""
Base class for IP source plugins
모든 IP 소스 플러그인이 상속해야 하는 기본 클래스
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class IPEntry:
    """IP 엔트리 데이터 클래스"""
    ip_address: str
    source_name: str
    category: str = "blacklist"  # blacklist, whitelist, greylist
    confidence: float = 1.0  # 0.0 ~ 1.0
    detection_date: datetime = None
    expiry_date: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.detection_date is None:
            self.detection_date = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class SourceConfig:
    """소스 설정 데이터 클래스"""
    name: str
    enabled: bool = True
    update_interval: int = 3600  # seconds
    priority: int = 1  # 1=highest, 10=lowest
    settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.settings is None:
            self.settings = {}


class BaseIPSource(ABC):
    """
    모든 IP 소스 플러그인의 기본 클래스
    
    새로운 IP 소스를 추가하려면 이 클래스를 상속하고
    필요한 메서드들을 구현하세요.
    """
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._last_update = None
        self._error_count = 0
        self._max_errors = 5
        
    @property
    @abstractmethod
    def source_name(self) -> str:
        """소스 이름 반환"""
        pass
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """소스 타입 반환 (api, file, database, etc.)"""
        pass
    
    @property
    @abstractmethod
    def supported_formats(self) -> List[str]:
        """지원하는 데이터 형식 목록"""
        pass
    
    @abstractmethod
    def fetch_data(self) -> Iterator[IPEntry]:
        """
        데이터를 가져와서 IPEntry 객체들을 생성
        
        Yields:
            IPEntry: 개별 IP 엔트리
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """설정 유효성 검사"""
        pass
    
    def preprocess_data(self, raw_data: Any) -> Any:
        """
        원시 데이터 전처리 (선택사항)
        
        Args:
            raw_data: 원시 데이터
            
        Returns:
            전처리된 데이터
        """
        return raw_data
    
    def is_valid_ip(self, ip: str) -> bool:
        """IP 주소 유효성 검사"""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    def should_update(self) -> bool:
        """업데이트가 필요한지 확인"""
        if not self.config.enabled:
            return False
            
        if self._error_count >= self._max_errors:
            self.logger.warning(f"Source {self.source_name} disabled due to too many errors")
            return False
            
        if self._last_update is None:
            return True
            
        elapsed = (datetime.utcnow() - self._last_update).total_seconds()
        return elapsed >= self.config.update_interval
    
    def update(self) -> Dict[str, Any]:
        """
        데이터 업데이트 실행
        
        Returns:
            Dict: 업데이트 결과 정보
        """
        if not self.should_update():
            return {"status": "skipped", "reason": "not_needed"}
        
        try:
            self.logger.info(f"Updating data from {self.source_name}")
            
            start_time = datetime.utcnow()
            entries = list(self.fetch_data())
            end_time = datetime.utcnow()
            
            self._last_update = end_time
            self._error_count = 0
            
            result = {
                "status": "success",
                "source": self.source_name,
                "entries_count": len(entries),
                "duration": (end_time - start_time).total_seconds(),
                "timestamp": end_time.isoformat(),
                "entries": entries
            }
            
            self.logger.info(f"Successfully fetched {len(entries)} entries from {self.source_name}")
            return result
            
        except Exception as e:
            self._error_count += 1
            self.logger.error(f"Error updating from {self.source_name}: {str(e)}")
            
            return {
                "status": "error",
                "source": self.source_name,
                "error": str(e),
                "error_count": self._error_count,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_metadata(self) -> Dict[str, Any]:
        """소스 메타데이터 반환"""
        return {
            "name": self.source_name,
            "type": self.source_type,
            "enabled": self.config.enabled,
            "priority": self.config.priority,
            "update_interval": self.config.update_interval,
            "supported_formats": self.supported_formats,
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "error_count": self._error_count,
            "settings": self.config.settings
        }
    
    def health_check(self) -> Dict[str, Any]:
        """소스 상태 확인"""
        try:
            is_healthy = self.validate_config() and self._error_count < self._max_errors
            
            return {
                "healthy": is_healthy,
                "source": self.source_name,
                "error_count": self._error_count,
                "max_errors": self._max_errors,
                "enabled": self.config.enabled,
                "last_update": self._last_update.isoformat() if self._last_update else None
            }
        except Exception as e:
            return {
                "healthy": False,
                "source": self.source_name,
                "error": str(e)
            }