#!/usr/bin/env python3
"""
통합 수집기 시스템 (Unified Collector System)
모든 IP 소스의 수집을 통합 관리하는 리팩토링된 시스템
"""

import os
import json
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import traceback
from pathlib import Path

logger = logging.getLogger(__name__)


class CollectionStatus(Enum):
    """수집 상태 열거형"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CollectionResult:
    """수집 결과 데이터 클래스"""
    source_name: str
    status: CollectionStatus
    collected_count: int = 0
    error_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def duration(self) -> Optional[float]:
        """수집 소요 시간 (초)"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        """수집 성공률"""
        total = self.collected_count + self.error_count
        if total == 0:
            return 0.0
        return (self.collected_count / total) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        result = asdict(self)
        result['status'] = self.status.value
        result['duration'] = self.duration
        result['success_rate'] = self.success_rate
        if self.start_time:
            result['start_time'] = self.start_time.isoformat()
        if self.end_time:
            result['end_time'] = self.end_time.isoformat()
        return result


@dataclass
class CollectionConfig:
    """수집 설정 데이터 클래스"""
    enabled: bool = True
    interval: int = 3600  # 기본 1시간
    max_retries: int = 3
    timeout: int = 300  # 기본 5분
    parallel_workers: int = 1
    settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.settings is None:
            self.settings = {}


class BaseCollector(ABC):
    """
    모든 수집기의 기본 클래스
    통일된 인터페이스 제공
    """
    
    def __init__(self, name: str, config: CollectionConfig):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self._current_result = None
        self._is_running = False
        self._cancel_requested = False
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """소스 타입 반환"""
        pass
    
    @property
    def is_running(self) -> bool:
        """수집 중 여부"""
        return self._is_running
    
    @property
    def current_result(self) -> Optional[CollectionResult]:
        """현재 수집 결과"""
        return self._current_result
    
    def cancel(self):
        """수집 취소 요청"""
        self._cancel_requested = True
        self.logger.info(f"수집 취소 요청: {self.name}")
    
    @abstractmethod
    async def _collect_data(self) -> List[Any]:
        """
        실제 데이터 수집 구현
        각 수집기에서 구현해야 함
        """
        pass
    
    def _should_cancel(self) -> bool:
        """취소 요청 확인"""
        return self._cancel_requested
    
    async def collect(self) -> CollectionResult:
        """
        수집 실행 (공통 로직)
        """
        if not self.config.enabled:
            self.logger.info(f"수집기 비활성화됨: {self.name}")
            return CollectionResult(
                source_name=self.name,
                status=CollectionStatus.CANCELLED,
                error_message="수집기가 비활성화되어 있습니다."
            )
        
        if self._is_running:
            self.logger.warning(f"수집기 이미 실행 중: {self.name}")
            return CollectionResult(
                source_name=self.name,
                status=CollectionStatus.FAILED,
                error_message="수집기가 이미 실행 중입니다."
            )
        
        self._is_running = True
        self._cancel_requested = False
        
        # 수집 결과 초기화
        self._current_result = CollectionResult(
            source_name=self.name,
            status=CollectionStatus.RUNNING,
            start_time=datetime.now()
        )
        
        retries = 0
        while retries <= self.config.max_retries:
            try:
                self.logger.info(f"수집 시작: {self.name} (시도 {retries + 1}/{self.config.max_retries + 1})")
                
                # 타임아웃 설정
                collected_data = await asyncio.wait_for(
                    self._collect_data(),
                    timeout=self.config.timeout
                )
                
                if self._should_cancel():
                    self._current_result.status = CollectionStatus.CANCELLED
                    self._current_result.error_message = "사용자에 의해 취소됨"
                    break
                
                # 수집 성공
                self._current_result.status = CollectionStatus.COMPLETED
                self._current_result.collected_count = len(collected_data)
                self._current_result.end_time = datetime.now()
                
                self.logger.info(f"수집 완료: {self.name} - {len(collected_data)}개 수집")
                break
                
            except asyncio.TimeoutError:
                error_msg = f"수집 타임아웃: {self.name} ({self.config.timeout}초)"
                self.logger.error(error_msg)
                self._current_result.error_message = error_msg
                self._current_result.status = CollectionStatus.FAILED
                retries += 1
                
            except Exception as e:
                error_msg = f"수집 오류: {self.name} - {str(e)}"
                self.logger.error(error_msg)
                self.logger.error(traceback.format_exc())
                
                self._current_result.error_message = error_msg
                self._current_result.status = CollectionStatus.FAILED
                self._current_result.error_count += 1
                retries += 1
                
                if retries <= self.config.max_retries:
                    await asyncio.sleep(2 ** retries)  # 지수 백오프
        
        self._is_running = False
        self._current_result.end_time = datetime.now()
        
        return self._current_result
    
    def health_check(self) -> Dict[str, Any]:
        """수집기 상태 점검"""
        return {
            "name": self.name,
            "type": self.source_type,
            "enabled": self.config.enabled,
            "is_running": self.is_running,
            "last_result": self._current_result.to_dict() if self._current_result else None
        }


class UnifiedCollectionManager:
    """
    통합 수집 관리자
    모든 수집기를 통합 관리
    """
    
    def __init__(self, config_path: str = "instance/unified_collection_config.json"):
        self.config_path = Path(config_path)
        self.collectors: Dict[str, BaseCollector] = {}
        self.global_config = self._load_config()
        
        # 수집 상태 추적
        self.collection_history: List[CollectionResult] = []
        self.max_history_size = 100
        
        self.logger = logging.getLogger(__name__)
    
    def _load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 기본 설정
                default_config = {
                    "global_enabled": True,
                    "concurrent_collections": 3,
                    "retry_delay": 5,
                    "collectors": {}
                }
                self._save_config(default_config)
                return default_config
        except Exception as e:
            self.logger.error(f"설정 파일 로드 실패: {e}")
            return {"global_enabled": True, "collectors": {}}
    
    def _save_config(self, config: Dict[str, Any]):
        """설정 파일 저장"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"설정 파일 저장 실패: {e}")
    
    def register_collector(self, collector: BaseCollector):
        """수집기 등록"""
        self.collectors[collector.name] = collector
        self.logger.info(f"수집기 등록: {collector.name}")
    
    def unregister_collector(self, name: str):
        """수집기 등록 해제"""
        if name in self.collectors:
            del self.collectors[name]
            self.logger.info(f"수집기 등록 해제: {name}")
    
    def get_collector(self, name: str) -> Optional[BaseCollector]:
        """수집기 조회"""
        return self.collectors.get(name)
    
    def list_collectors(self) -> List[str]:
        """수집기 목록 조회"""
        return list(self.collectors.keys())
    
    async def collect_all(self) -> Dict[str, CollectionResult]:
        """모든 수집기 실행"""
        if not self.global_config.get("global_enabled", True):
            self.logger.info("전역 수집이 비활성화되어 있습니다.")
            return {}
        
        self.logger.info("전체 수집 시작")
        
        # 세마포어를 사용한 동시 수집 제한
        semaphore = asyncio.Semaphore(
            self.global_config.get("concurrent_collections", 3)
        )
        
        async def collect_with_semaphore(collector: BaseCollector):
            async with semaphore:
                return await collector.collect()
        
        # 모든 수집기 병렬 실행
        tasks = [
            collect_with_semaphore(collector) 
            for collector in self.collectors.values()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 정리
        collection_results = {}
        for i, result in enumerate(results):
            collector_name = list(self.collectors.keys())[i]
            
            if isinstance(result, Exception):
                collection_results[collector_name] = CollectionResult(
                    source_name=collector_name,
                    status=CollectionStatus.FAILED,
                    error_message=str(result)
                )
            else:
                collection_results[collector_name] = result
        
        # 히스토리 저장
        for result in collection_results.values():
            self.collection_history.append(result)
        
        # 히스토리 크기 제한
        if len(self.collection_history) > self.max_history_size:
            self.collection_history = self.collection_history[-self.max_history_size:]
        
        self.logger.info("전체 수집 완료")
        return collection_results
    
    async def collect_single(self, collector_name: str) -> Optional[CollectionResult]:
        """단일 수집기 실행"""
        collector = self.collectors.get(collector_name)
        if not collector:
            self.logger.error(f"수집기를 찾을 수 없습니다: {collector_name}")
            return None
        
        result = await collector.collect()
        self.collection_history.append(result)
        
        return result
    
    def cancel_collection(self, collector_name: str):
        """수집 취소"""
        collector = self.collectors.get(collector_name)
        if collector:
            collector.cancel()
    
    def cancel_all_collections(self):
        """모든 수집 취소"""
        for collector in self.collectors.values():
            collector.cancel()
    
    def get_status(self) -> Dict[str, Any]:
        """전체 상태 조회"""
        return {
            "global_enabled": self.global_config.get("global_enabled", True),
            "collectors": {
                name: collector.health_check()
                for name, collector in self.collectors.items()
            },
            "running_collectors": [
                name for name, collector in self.collectors.items()
                if collector.is_running
            ],
            "total_collectors": len(self.collectors),
            "recent_results": [
                result.to_dict() for result in self.collection_history[-10:]
            ]
        }
    
    def enable_global_collection(self):
        """전역 수집 활성화"""
        self.global_config["global_enabled"] = True
        self._save_config(self.global_config)
        self.logger.info("전역 수집 활성화")
    
    def disable_global_collection(self):
        """전역 수집 비활성화"""
        self.global_config["global_enabled"] = False
        self._save_config(self.global_config)
        self.logger.info("전역 수집 비활성화")
    
    def enable_collector(self, name: str):
        """수집기 활성화"""
        collector = self.collectors.get(name)
        if collector:
            collector.config.enabled = True
            self.logger.info(f"수집기 활성화: {name}")
    
    def disable_collector(self, name: str):
        """수집기 비활성화"""
        collector = self.collectors.get(name)
        if collector:
            collector.config.enabled = False
            self.logger.info(f"수집기 비활성화: {name}")


# 사용 예시
if __name__ == "__main__":
    async def main():
        # 통합 수집 관리자 생성
        manager = UnifiedCollectionManager()
        
        # 수집기 등록 (실제 구현체는 별도 파일에서)
        # manager.register_collector(RegtechCollector(...))
        # manager.register_collector(SecudiumCollector(...))
        
        # 전체 수집 실행
        results = await manager.collect_all()
        
        # 결과 출력
        for name, result in results.items():
            print(f"{name}: {result.status.value} - {result.collected_count}개 수집")
    
    asyncio.run(main())