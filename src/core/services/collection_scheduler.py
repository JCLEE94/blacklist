#!/usr/bin/env python3
"""
수집 스케줄링 서비스
자동화된 데이터 수집 스케줄링 및 모니터링
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable

logger = logging.getLogger(__name__)


class CollectionScheduler:
    """
    수집 스케줄러 - 주기적 자동 수집 및 모니터링
    """
    
    def __init__(self):
        self.is_running = False
        self.scheduler_thread = None
        self.collection_callbacks = {}
        self.schedules = {
            "regtech": {
                "enabled": True,
                "interval_hours": 24,  # 24시간마다
                "last_run": None,
                "next_run": None,
                "success_count": 0,
                "failure_count": 0
            },
            "secudium": {
                "enabled": False,
                "interval_hours": 72,  # 72시간마다 (3일)
                "last_run": None,
                "next_run": None,
                "success_count": 0,
                "failure_count": 0
            }
        }
        
    def register_collection_callback(self, source: str, callback: Callable):
        """수집 콜백 함수 등록"""
        self.collection_callbacks[source] = callback
        logger.info(f"Collection callback registered for {source}")
        
    def start_scheduler(self):
        """스케줄러 시작"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
            
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        # 다음 실행 시간 계산
        self._calculate_next_runs()
        
        logger.info("Collection scheduler started")
        
    def stop_scheduler(self):
        """스케줄러 중지"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
            
        logger.info("Collection scheduler stopped")
        
    def _scheduler_loop(self):
        """스케줄러 메인 루프"""
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # 각 소스별 스케줄 확인
                for source, schedule in self.schedules.items():
                    if not schedule["enabled"]:
                        continue
                        
                    if schedule["next_run"] and current_time >= schedule["next_run"]:
                        self._execute_collection(source)
                        
                # 1분마다 체크
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                time.sleep(60)  # 오류 시에도 계속 실행
                
    def _execute_collection(self, source: str):
        """수집 실행"""
        try:
            logger.info(f"Executing scheduled collection for {source}")
            
            schedule = self.schedules[source]
            schedule["last_run"] = datetime.now()
            
            # 콜백 함수 호출
            if source in self.collection_callbacks:
                callback = self.collection_callbacks[source]
                result = callback()
                
                if result and result.get("success"):
                    schedule["success_count"] += 1
                    logger.info(f"Scheduled collection successful for {source}: {result.get('stored_count', 0)} IPs")
                else:
                    schedule["failure_count"] += 1
                    logger.error(f"Scheduled collection failed for {source}: {result.get('error', 'Unknown error')}")
            else:
                logger.warning(f"No callback registered for {source}")
                schedule["failure_count"] += 1
                
            # 다음 실행 시간 계산
            self._calculate_next_run(source)
            
        except Exception as e:
            logger.error(f"Collection execution error for {source}: {e}")
            self.schedules[source]["failure_count"] += 1
            self._calculate_next_run(source)
            
    def _calculate_next_runs(self):
        """모든 소스의 다음 실행 시간 계산"""
        for source in self.schedules.keys():
            self._calculate_next_run(source)
            
    def _calculate_next_run(self, source: str):
        """특정 소스의 다음 실행 시간 계산"""
        schedule = self.schedules[source]
        
        if not schedule["enabled"]:
            schedule["next_run"] = None
            return
            
        if schedule["last_run"]:
            next_run = schedule["last_run"] + timedelta(hours=schedule["interval_hours"])
        else:
            # 첫 실행: 즉시 실행
            next_run = datetime.now() + timedelta(minutes=1)
            
        schedule["next_run"] = next_run
        logger.info(f"Next run for {source}: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        
    def get_schedule_status(self) -> Dict:
        """스케줄 상태 조회"""
        status = {
            "is_running": self.is_running,
            "schedules": {}
        }
        
        for source, schedule in self.schedules.items():
            status["schedules"][source] = {
                "enabled": schedule["enabled"],
                "interval_hours": schedule["interval_hours"],
                "last_run": schedule["last_run"].isoformat() if schedule["last_run"] else None,
                "next_run": schedule["next_run"].isoformat() if schedule["next_run"] else None,
                "success_count": schedule["success_count"],
                "failure_count": schedule["failure_count"],
                "success_rate": self._calculate_success_rate(schedule)
            }
            
        return status
        
    def _calculate_success_rate(self, schedule: Dict) -> float:
        """성공률 계산"""
        total = schedule["success_count"] + schedule["failure_count"]
        if total == 0:
            return 0.0
        return (schedule["success_count"] / total) * 100
        
    def update_schedule(self, source: str, enabled: bool = None, interval_hours: int = None):
        """스케줄 설정 업데이트"""
        if source not in self.schedules:
            logger.error(f"Unknown source: {source}")
            return False
            
        schedule = self.schedules[source]
        
        if enabled is not None:
            schedule["enabled"] = enabled
            
        if interval_hours is not None:
            if not (1 <= interval_hours <= 168):  # 1시간 ~ 1주일
                logger.error(f"Invalid interval: {interval_hours}")
                return False
            schedule["interval_hours"] = interval_hours
            
        # 다음 실행 시간 재계산
        self._calculate_next_run(source)
        
        logger.info(f"Schedule updated for {source}: enabled={schedule['enabled']}, interval={schedule['interval_hours']}h")
        return True
        
    def trigger_immediate_collection(self, source: str) -> bool:
        """즉시 수집 트리거"""
        if source not in self.schedules:
            logger.error(f"Unknown source: {source}")
            return False
            
        if not self.schedules[source]["enabled"]:
            logger.warning(f"Source {source} is disabled")
            return False
            
        # 별도 스레드에서 실행
        collection_thread = threading.Thread(
            target=self._execute_collection,
            args=(source,),
            daemon=True
        )
        collection_thread.start()
        
        logger.info(f"Immediate collection triggered for {source}")
        return True
        
    def get_next_collection_time(self, source: str) -> Optional[datetime]:
        """다음 수집 시간 조회"""
        if source not in self.schedules:
            return None
            
        return self.schedules[source]["next_run"]
        
    def get_collection_history(self, source: str, days: int = 7) -> Dict:
        """수집 히스토리 조회 (향후 로그 시스템과 연동)"""
        # 실제 구현에서는 로그 데이터베이스에서 조회
        schedule = self.schedules[source]
        
        return {
            "source": source,
            "period_days": days,
            "total_executions": schedule["success_count"] + schedule["failure_count"],
            "successful_executions": schedule["success_count"],
            "failed_executions": schedule["failure_count"],
            "success_rate": self._calculate_success_rate(schedule),
            "last_execution": schedule["last_run"].isoformat() if schedule["last_run"] else None
        }


# 전역 스케줄러 인스턴스
_scheduler_instance = None

def get_collection_scheduler() -> CollectionScheduler:
    """전역 스케줄러 인스턴스 반환"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = CollectionScheduler()
    return _scheduler_instance


if __name__ == "__main__":
    # 스케줄러 테스트
    import sys
    
    print("🕐 Collection Scheduler Test")
    print("="*50)
    
    all_validation_failures = []
    total_tests = 0
    
    # Test 1: 스케줄러 생성
    total_tests += 1
    try:
        scheduler = CollectionScheduler()
        if not scheduler:
            all_validation_failures.append("Scheduler creation failed")
        else:
            print("✅ Scheduler created successfully")
    except Exception as e:
        all_validation_failures.append(f"Scheduler creation error: {e}")
    
    # Test 2: 스케줄 상태 조회
    total_tests += 1
    try:
        status = scheduler.get_schedule_status()
        if not status or "schedules" not in status:
            all_validation_failures.append("Schedule status format invalid")
        else:
            print(f"✅ Schedule status: {len(status['schedules'])} sources")
    except Exception as e:
        all_validation_failures.append(f"Schedule status error: {e}")
    
    # Test 3: 콜백 등록
    total_tests += 1
    try:
        def dummy_callback():
            return {"success": True, "stored_count": 10}
        
        scheduler.register_collection_callback("regtech", dummy_callback)
        if "regtech" not in scheduler.collection_callbacks:
            all_validation_failures.append("Callback registration failed")
        else:
            print("✅ Callback registered successfully")
    except Exception as e:
        all_validation_failures.append(f"Callback registration error: {e}")
    
    # Test 4: 스케줄 업데이트
    total_tests += 1
    try:
        result = scheduler.update_schedule("regtech", enabled=True, interval_hours=6)
        if not result:
            all_validation_failures.append("Schedule update failed")
        else:
            print("✅ Schedule updated successfully")
    except Exception as e:
        all_validation_failures.append(f"Schedule update error: {e}")
    
    # Final validation result
    if all_validation_failures:
        print(f"\n❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"\n✅ VALIDATION PASSED - All {total_tests} tests successful")
        print("Collection scheduler is ready for use")
        sys.exit(0)