#!/usr/bin/env python3
"""
메모리 최적화 코어 모듈
메모리 사용량 모니터링 및 최적화 기능

단순한 기능으로 테스트 안정성을 위해 최소한으로 구현
"""

import gc
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

import psutil


@dataclass
class MemoryStats:
    """메모리 통계 데이터 클래스"""
    total_memory: int = 0
    available_memory: int = 0
    used_memory: int = 0
    memory_percent: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'total_memory': self.total_memory,
            'available_memory': self.available_memory,
            'used_memory': self.used_memory,
            'memory_percent': self.memory_percent,
            'timestamp': self.timestamp.isoformat()
        }


class CoreMemoryOptimizer:
    """
    코어 메모리 최적화 클래스
    
    메모리 사용량 모니터링과 기본적인 최적화 기능 제공
    """
    
    def __init__(self, auto_gc: bool = True, gc_threshold: float = 80.0):
        """
        초기화
        
        Args:
            auto_gc: 자동 가비지 컶렉션 활성화 여부
            gc_threshold: 자동 GC 실행 임계값 (%)
        """
        self.auto_gc = auto_gc
        self.gc_threshold = gc_threshold
        self._monitoring = False
        self._monitor_thread = None
        self._stats_history = []
        
    def get_memory_stats(self) -> MemoryStats:
        """현재 메모리 통계 조회"""
        try:
            memory = psutil.virtual_memory()
            return MemoryStats(
                total_memory=memory.total,
                available_memory=memory.available,
                used_memory=memory.used,
                memory_percent=memory.percent
            )
        except Exception:
            # 폴백: 기본값 반환
            return MemoryStats()
    
    def optimize_memory(self) -> Dict[str, Any]:
        """메모리 최적화 실행"""
        before_stats = self.get_memory_stats()
        
        # 가비지 컴렉션 실행
        collected = gc.collect()
        
        after_stats = self.get_memory_stats()
        
        return {
            'success': True,
            'objects_collected': collected,
            'memory_before': before_stats.to_dict(),
            'memory_after': after_stats.to_dict(),
            'memory_freed': before_stats.used_memory - after_stats.used_memory,
            'timestamp': datetime.now().isoformat()
        }
    
    def start_monitoring(self, interval: float = 10.0) -> bool:
        """메모리 모니터링 시작"""
        if self._monitoring:
            return False
            
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
        return True
    
    def stop_monitoring(self) -> bool:
        """메모리 모니터링 중지"""
        if not self._monitoring:
            return False
            
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
        return True
    
    def _monitor_loop(self, interval: float):
        """모니터링 루프 (내부 사용)"""
        while self._monitoring:
            try:
                stats = self.get_memory_stats()
                self._stats_history.append(stats)
                
                # 이력 제한 (100개)
                if len(self._stats_history) > 100:
                    self._stats_history.pop(0)
                
                # 자동 GC 체크
                if self.auto_gc and stats.memory_percent > self.gc_threshold:
                    self.optimize_memory()
                
                time.sleep(interval)
            except Exception:
                continue
    
    def get_stats_history(self) -> list:
        """통계 이력 조회"""
        return [stats.to_dict() for stats in self._stats_history]
    
    def is_monitoring(self) -> bool:
        """모니터링 상태 확인"""
        return self._monitoring


if __name__ == "__main__":
    # 검증 함수
    import sys
    
    all_validation_failures = []
    total_tests = 0
    
    # Test 1: MemoryStats 생성
    total_tests += 1
    try:
        stats = MemoryStats(total_memory=1000, used_memory=500, memory_percent=50.0)
        if stats.total_memory != 1000 or stats.memory_percent != 50.0:
            all_validation_failures.append("MemoryStats creation: Invalid values")
    except Exception as e:
        all_validation_failures.append(f"MemoryStats creation: Exception {e}")
    
    # Test 2: CoreMemoryOptimizer 초기화
    total_tests += 1
    try:
        optimizer = CoreMemoryOptimizer(auto_gc=False)
        if optimizer.auto_gc or optimizer.gc_threshold != 80.0:
            all_validation_failures.append("CoreMemoryOptimizer init: Invalid configuration")
    except Exception as e:
        all_validation_failures.append(f"CoreMemoryOptimizer init: Exception {e}")
    
    # Test 3: 메모리 통계 조회
    total_tests += 1
    try:
        optimizer = CoreMemoryOptimizer()
        stats = optimizer.get_memory_stats()
        if not isinstance(stats, MemoryStats):
            all_validation_failures.append("Memory stats retrieval: Invalid return type")
    except Exception as e:
        all_validation_failures.append(f"Memory stats retrieval: Exception {e}")
    
    # Test 4: 메모리 최적화
    total_tests += 1
    try:
        optimizer = CoreMemoryOptimizer()
        result = optimizer.optimize_memory()
        if not isinstance(result, dict) or 'success' not in result:
            all_validation_failures.append("Memory optimization: Invalid result format")
    except Exception as e:
        all_validation_failures.append(f"Memory optimization: Exception {e}")
    
    # 최종 검증 결과
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("CoreMemoryOptimizer and MemoryStats are validated and ready for use")
        sys.exit(0)
