"""
시스템 메트릭 수집기
"""

import psutil
import time
from datetime import datetime
from typing import List

from .health_models import HealthMetric, get_status_from_thresholds


class SystemMetricsCollector:
    """시스템 메트릭 수집 클래스"""
    
    def collect_system_metrics(self) -> List[HealthMetric]:
        """시스템 메트릭 수집"""
        metrics = []
        now = datetime.now()
        
        # CPU 사용률
        cpu_percent = psutil.cpu_percent(interval=1)
        metrics.append(HealthMetric(
            name="cpu_usage",
            value=cpu_percent,
            status=get_status_from_thresholds(cpu_percent, 70, 90),
            timestamp=now,
            unit="%",
            threshold_warning=70,
            threshold_critical=90,
            description="CPU 사용률"
        ))
        
        # 메모리 사용률
        memory = psutil.virtual_memory()
        metrics.append(HealthMetric(
            name="memory_usage",
            value=memory.percent,
            status=get_status_from_thresholds(memory.percent, 80, 95),
            timestamp=now,
            unit="%",
            threshold_warning=80,
            threshold_critical=95,
            description="메모리 사용률"
        ))
        
        # 디스크 사용률
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        metrics.append(HealthMetric(
            name="disk_usage",
            value=disk_percent,
            status=get_status_from_thresholds(disk_percent, 85, 95),
            timestamp=now,
            unit="%",
            threshold_warning=85,
            threshold_critical=95,
            description="디스크 사용률"
        ))
        
        # 네트워크 연결 수
        try:
            connections = len(psutil.net_connections())
            metrics.append(HealthMetric(
                name="network_connections",
                value=connections,
                status="healthy" if connections < 1000 else "warning",
                timestamp=now,
                unit="개",
                description="네트워크 연결 수"
            ))
        except:
            pass  # 권한 없음 등의 경우 무시
        
        # 프로세스 수
        process_count = len(psutil.pids())
        metrics.append(HealthMetric(
            name="process_count",
            value=process_count,
            status="healthy" if process_count < 500 else "warning",
            timestamp=now,
            unit="개",
            description="실행 중인 프로세스 수"
        ))
        
        return metrics


class ApplicationMetricsCollector:
    """애플리케이션 메트릭 수집 클래스"""
    
    def __init__(self, blacklist_manager=None):
        self.blacklist_manager = blacklist_manager
    
    def collect_application_metrics(self) -> List[HealthMetric]:
        """애플리케이션 메트릭 수집"""
        metrics = []
        now = datetime.now()
        
        if not self.blacklist_manager:
            return metrics
        
        try:
            # 시스템 상태 조회
            health = self.blacklist_manager.get_system_health()
            
            # 활성 IP 수
            active_ips = health.get("database", {}).get("active_ips", 0)
            metrics.append(HealthMetric(
                name="active_ips",
                value=active_ips,
                status="healthy" if active_ips > 0 else "warning",
                timestamp=now,
                unit="개",
                description="활성 IP 수"
            ))
            
            # 총 레코드 수
            total_records = health.get("database", {}).get("total_records", 0)
            metrics.append(HealthMetric(
                name="total_records",
                value=total_records,
                status="healthy" if total_records > 0 else "warning",
                timestamp=now,
                unit="개",
                description="총 레코드 수"
            ))
            
            # 데이터베이스 상태
            db_status = health.get("status", "unknown")
            metrics.append(HealthMetric(
                name="database_status",
                value=db_status,
                status="healthy" if db_status == "healthy" else "warning",
                timestamp=now,
                description="데이터베이스 상태"
            ))
            
        except Exception as e:
            # 애플리케이션 메트릭 수집 실패
            metrics.append(HealthMetric(
                name="app_metrics_error",
                value=str(e),
                status="critical",
                timestamp=now,
                description="애플리케이션 메트릭 수집 오류"
            ))
        
        return metrics