#!/usr/bin/env python3
"""
수집 진행 상황 추적 및 시각화 모듈
"""
import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class CollectionStatus(Enum):
    """수집 상태"""
    IDLE = "idle"
    PREPARING = "preparing"
    AUTHENTICATING = "authenticating"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class CollectionProgress:
    """수집 진행 상황 데이터"""
    source: str
    status: CollectionStatus = CollectionStatus.IDLE
    message: str = ""
    current_step: int = 0
    total_steps: int = 0
    current_item: int = 0
    total_items: int = 0
    percentage: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'source': self.source,
            'status': self.status.value,
            'message': self.message,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'current_item': self.current_item,
            'total_items': self.total_items,
            'percentage': round(self.percentage, 2),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration': self._get_duration(),
            'error': self.error,
            'details': self.details
        }
    
    def _get_duration(self) -> Optional[float]:
        """경과 시간 계산 (초)"""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()

class CollectionProgressTracker:
    """수집 진행 상황 추적기"""
    
    def __init__(self):
        self._progress_map: Dict[str, CollectionProgress] = {}
        self._lock = threading.Lock()
        
    def start_collection(self, source: str, total_steps: int = 5) -> None:
        """수집 시작"""
        with self._lock:
            self._progress_map[source] = CollectionProgress(
                source=source,
                status=CollectionStatus.PREPARING,
                message="수집 준비 중...",
                total_steps=total_steps,
                started_at=datetime.now()
            )
            logger.info(f"[{source}] 수집 시작")
    
    def update_status(self, source: str, status: CollectionStatus, message: str = "") -> None:
        """상태 업데이트"""
        with self._lock:
            if source not in self._progress_map:
                return
            
            progress = self._progress_map[source]
            progress.status = status
            progress.message = message or self._get_default_message(status)
            
            # 단계별 진행률 업데이트
            step_progress = {
                CollectionStatus.PREPARING: 1,
                CollectionStatus.AUTHENTICATING: 2,
                CollectionStatus.DOWNLOADING: 3,
                CollectionStatus.PROCESSING: 4,
                CollectionStatus.SAVING: 5,
                CollectionStatus.COMPLETED: 5,
            }
            
            if status in step_progress:
                progress.current_step = step_progress[status]
                progress.percentage = (progress.current_step / progress.total_steps) * 100
            
            if status in [CollectionStatus.COMPLETED, CollectionStatus.FAILED, CollectionStatus.CANCELLED]:
                progress.completed_at = datetime.now()
            
            logger.info(f"[{source}] 상태 변경: {status.value} - {message}")
    
    def update_progress(self, source: str, current_item: int, total_items: int, 
                       message: Optional[str] = None) -> None:
        """진행률 업데이트"""
        with self._lock:
            if source not in self._progress_map:
                return
            
            progress = self._progress_map[source]
            progress.current_item = current_item
            progress.total_items = total_items
            
            if total_items > 0:
                # 간단하게 현재/전체 비율로 계산
                progress.percentage = (current_item / total_items) * 100
                progress.current = current_item
                progress.total = total_items
            
            if message:
                progress.message = message
            else:
                progress.message = f"{current_item}/{total_items} 처리 중..."
    
    def set_error(self, source: str, error: str) -> None:
        """에러 설정"""
        with self._lock:
            if source not in self._progress_map:
                return
            
            progress = self._progress_map[source]
            progress.status = CollectionStatus.FAILED
            progress.error = error
            progress.message = f"오류 발생: {error}"
            progress.completed_at = datetime.now()
            logger.error(f"[{source}] 수집 실패: {error}")
    
    def fail_collection(self, source: str, error: str) -> None:
        """수집 실패 처리 (set_error의 별칭)"""
        self.set_error(source, error)
    
    def complete_collection(self, source: str, message: str = "수집 완료", 
                           details: Optional[Dict[str, Any]] = None) -> None:
        """수집 완료"""
        with self._lock:
            if source not in self._progress_map:
                return
            
            progress = self._progress_map[source]
            progress.status = CollectionStatus.COMPLETED
            progress.message = message
            progress.percentage = 100.0
            progress.completed_at = datetime.now()
            
            if details:
                progress.details.update(details)
            
            logger.info(f"[{source}] 수집 완료: {message}")
    
    def get_progress(self, source: str) -> Optional[Dict[str, Any]]:
        """특정 소스의 진행 상황 조회"""
        with self._lock:
            if source in self._progress_map:
                return self._progress_map[source].to_dict()
            return None
    
    def get_all_progress(self) -> Dict[str, Dict[str, Any]]:
        """모든 진행 상황 조회"""
        with self._lock:
            return {
                source: progress.to_dict() 
                for source, progress in self._progress_map.items()
            }
    
    def get_active_collections(self) -> Dict[str, Dict[str, Any]]:
        """진행 중인 수집만 조회"""
        with self._lock:
            active_statuses = [
                CollectionStatus.PREPARING,
                CollectionStatus.AUTHENTICATING,
                CollectionStatus.DOWNLOADING,
                CollectionStatus.PROCESSING,
                CollectionStatus.SAVING
            ]
            return {
                source: progress.to_dict()
                for source, progress in self._progress_map.items()
                if progress.status in active_statuses
            }
    
    def clear_completed(self) -> None:
        """완료된 수집 기록 삭제"""
        with self._lock:
            completed_sources = [
                source for source, progress in self._progress_map.items()
                if progress.status in [CollectionStatus.COMPLETED, CollectionStatus.FAILED, CollectionStatus.CANCELLED]
            ]
            for source in completed_sources:
                del self._progress_map[source]
    
    def _get_default_message(self, status: CollectionStatus) -> str:
        """상태별 기본 메시지"""
        messages = {
            CollectionStatus.IDLE: "대기 중",
            CollectionStatus.PREPARING: "수집 준비 중...",
            CollectionStatus.AUTHENTICATING: "인증 중...",
            CollectionStatus.DOWNLOADING: "데이터 다운로드 중...",
            CollectionStatus.PROCESSING: "데이터 처리 중...",
            CollectionStatus.SAVING: "저장 중...",
            CollectionStatus.COMPLETED: "수집 완료",
            CollectionStatus.FAILED: "수집 실패",
            CollectionStatus.CANCELLED: "수집 취소됨"
        }
        return messages.get(status, "")

# 전역 진행 상황 추적기
_progress_tracker = None

def get_progress_tracker() -> CollectionProgressTracker:
    """진행 상황 추적기 싱글톤 인스턴스"""
    global _progress_tracker
    if _progress_tracker is None:
        _progress_tracker = CollectionProgressTracker()
    return _progress_tracker