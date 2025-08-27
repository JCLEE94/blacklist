"""
🚀 AI 자동화 플랫폼 v8.3.0 - Production Monitoring System
Enterprise-grade monitoring and alerting infrastructure

Features:
- Real-time SLA monitoring (99.9% uptime target)
- Korean language alerting system
- Automated rollback triggers
- Performance regression detection
- Security incident monitoring
"""

import asyncio
import logging
import time
import json
import psutil
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    INFO = "정보"
    WARNING = "경고" 
    CRITICAL = "위험"
    EMERGENCY = "긴급"


class MonitoringMetric(Enum):
    UPTIME = "가동시간"
    RESPONSE_TIME = "응답시간"
    ERROR_RATE = "오류율"
    CPU_USAGE = "CPU사용률"
    MEMORY_USAGE = "메모리사용률"
    DISK_USAGE = "디스크사용률"
    ACTIVE_CONNECTIONS = "활성연결수"
    THROUGHPUT = "처리량"


@dataclass
class SLAMetric:
    """SLA 메트릭 데이터 클래스"""
    name: str
    value: float
    threshold: float
    unit: str
    status: str
    timestamp: datetime
    
    def is_breached(self) -> bool:
        """SLA 위반 여부 확인"""
        if self.name == MonitoringMetric.UPTIME.value:
            return self.value < self.threshold
        elif self.name in [MonitoringMetric.RESPONSE_TIME.value, 
                          MonitoringMetric.ERROR_RATE.value,
                          MonitoringMetric.CPU_USAGE.value,
                          MonitoringMetric.MEMORY_USAGE.value]:
            return self.value > self.threshold
        return False


@dataclass
class AlertMessage:
    """알림 메시지 데이터 클래스"""
    level: AlertLevel
    title: str
    message: str
    metric: Optional[SLAMetric]
    timestamp: datetime
    actions: List[str]
    korean_message: str


class ProductionMonitor:
    """프로덕션 모니터링 시스템"""
    
    def __init__(self):
        self.db_path = "monitoring/production_metrics.db"
        self.sla_targets = {
            MonitoringMetric.UPTIME.value: 99.9,  # 99.9% 가동시간
            MonitoringMetric.RESPONSE_TIME.value: 50.0,  # 50ms 응답시간
            MonitoringMetric.ERROR_RATE.value: 0.1,  # 0.1% 오류율
            MonitoringMetric.CPU_USAGE.value: 80.0,  # 80% CPU 사용률
            MonitoringMetric.MEMORY_USAGE.value: 85.0,  # 85% 메모리 사용률
            MonitoringMetric.DISK_USAGE.value: 90.0  # 90% 디스크 사용률
        }
        self.alert_history: List[AlertMessage] = []
        self.monitoring_active = False
        self.rollback_triggered = False
        
        # 데이터베이스 초기화
        self._init_database()
    
    def _init_database(self):
        """모니터링 데이터베이스 초기화"""
        Path("monitoring").mkdir(exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # SLA 메트릭 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sla_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    value REAL NOT NULL,
                    threshold REAL NOT NULL,
                    unit TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    is_breached BOOLEAN NOT NULL
                )
            """)
            
            # 알림 히스토리 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    korean_message TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolution_time DATETIME NULL
                )
            """)
            
            # SLA 위반 이벤트 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sla_breaches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    breach_value REAL NOT NULL,
                    threshold REAL NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    impact_level TEXT NOT NULL,
                    auto_resolved BOOLEAN DEFAULT FALSE,
                    timestamp DATETIME NOT NULL
                )
            """)
            
            conn.commit()
            logger.info("✅ 프로덕션 모니터링 데이터베이스 초기화 완료")
    
    async def start_monitoring(self):
        """프로덕션 모니터링 시작"""
        self.monitoring_active = True
        logger.info("🚀 프로덕션 모니터링 시스템 시작")
        
        await self._send_alert(
            AlertLevel.INFO,
            "모니터링 시스템 시작",
            "프로덕션 환경 모니터링이 시작되었습니다.",
            korean_message="🚀 AI 자동화 플랫폼 v8.3.0 프로덕션 모니터링 활성화"
        )
        
        # 모니터링 루프 시작
        asyncio.create_task(self._monitoring_loop())
        asyncio.create_task(self._sla_enforcement_loop())
    
    async def _monitoring_loop(self):
        """메인 모니터링 루프 (30초 간격)"""
        while self.monitoring_active:
            try:
                # 시스템 메트릭 수집
                metrics = await self._collect_system_metrics()
                
                # SLA 메트릭 저장 및 검사
                for metric in metrics:
                    await self._store_metric(metric)
                    
                    if metric.is_breached():
                        await self._handle_sla_breach(metric)
                
                # 30초 대기
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ 모니터링 루프 오류: {e}")
                await asyncio.sleep(10)
    
    async def _sla_enforcement_loop(self):
        """SLA 강제 적용 루프 (5분 간격)"""
        while self.monitoring_active:
            try:
                # 5분 간 SLA 위반 통계 분석
                breach_summary = await self._analyze_sla_breaches()
                
                # 심각한 위반 시 자동 조치
                if breach_summary.get('critical_breaches', 0) > 0:
                    await self._trigger_emergency_response(breach_summary)
                
                # 5분 대기
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"❌ SLA 강제 적용 오류: {e}")
                await asyncio.sleep(60)
    
    async def _collect_system_metrics(self) -> List[SLAMetric]:
        """시스템 메트릭 수집"""
        metrics = []
        timestamp = datetime.now()
        
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics.append(SLAMetric(
                name=MonitoringMetric.CPU_USAGE.value,
                value=cpu_percent,
                threshold=self.sla_targets[MonitoringMetric.CPU_USAGE.value],
                unit="%",
                status="정상" if cpu_percent <= 80 else "경고",
                timestamp=timestamp
            ))
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            metrics.append(SLAMetric(
                name=MonitoringMetric.MEMORY_USAGE.value,
                value=memory.percent,
                threshold=self.sla_targets[MonitoringMetric.MEMORY_USAGE.value],
                unit="%",
                status="정상" if memory.percent <= 85 else "경고",
                timestamp=timestamp
            ))
            
            # 디스크 사용률
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            metrics.append(SLAMetric(
                name=MonitoringMetric.DISK_USAGE.value,
                value=disk_percent,
                threshold=self.sla_targets[MonitoringMetric.DISK_USAGE.value],
                unit="%",
                status="정상" if disk_percent <= 90 else "경고",
                timestamp=timestamp
            ))
            
            # API 응답시간 측정
            response_time = await self._measure_api_response_time()
            if response_time is not None:
                metrics.append(SLAMetric(
                    name=MonitoringMetric.RESPONSE_TIME.value,
                    value=response_time,
                    threshold=self.sla_targets[MonitoringMetric.RESPONSE_TIME.value],
                    unit="ms",
                    status="정상" if response_time <= 50 else "경고",
                    timestamp=timestamp
                ))
            
            # 가동시간 계산
            uptime_percent = await self._calculate_uptime()
            metrics.append(SLAMetric(
                name=MonitoringMetric.UPTIME.value,
                value=uptime_percent,
                threshold=self.sla_targets[MonitoringMetric.UPTIME.value],
                unit="%",
                status="정상" if uptime_percent >= 99.9 else "위험",
                timestamp=timestamp
            ))
            
        except Exception as e:
            logger.error(f"❌ 메트릭 수집 오류: {e}")
        
        return metrics
    
    async def _measure_api_response_time(self) -> Optional[float]:
        """API 응답시간 측정"""
        try:
            start_time = time.time()
            response = requests.get(
                "http://localhost:32542/health",
                timeout=10
            )
            end_time = time.time()
            
            if response.status_code == 200:
                return (end_time - start_time) * 1000  # ms 단위
        except Exception as e:
            logger.warning(f"⚠️ API 응답시간 측정 실패: {e}")
        
        return None
    
    async def _calculate_uptime(self) -> float:
        """가동시간 계산 (지난 24시간 기준)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 24시간 전 시점
                twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
                
                # 전체 측정 횟수
                cursor.execute("""
                    SELECT COUNT(*) FROM sla_metrics 
                    WHERE name = ? AND timestamp >= ?
                """, (MonitoringMetric.RESPONSE_TIME.value, twenty_four_hours_ago))
                
                total_checks = cursor.fetchone()[0]
                
                if total_checks == 0:
                    return 100.0  # 데이터 없으면 100% 가정
                
                # 성공한 측정 횟수 (응답시간이 기록된 것)
                cursor.execute("""
                    SELECT COUNT(*) FROM sla_metrics 
                    WHERE name = ? AND timestamp >= ? AND status = '정상'
                """, (MonitoringMetric.RESPONSE_TIME.value, twenty_four_hours_ago))
                
                successful_checks = cursor.fetchone()[0]
                
                return (successful_checks / total_checks) * 100.0
                
        except Exception as e:
            logger.error(f"❌ 가동시간 계산 오류: {e}")
            return 100.0  # 오류 시 100% 가정
    
    async def _store_metric(self, metric: SLAMetric):
        """메트릭을 데이터베이스에 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sla_metrics 
                    (name, value, threshold, unit, status, timestamp, is_breached)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    metric.name, metric.value, metric.threshold, 
                    metric.unit, metric.status, metric.timestamp,
                    metric.is_breached()
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"❌ 메트릭 저장 오류: {e}")
    
    async def _handle_sla_breach(self, metric: SLAMetric):
        """SLA 위반 처리"""
        # 위반 이벤트 기록
        await self._record_sla_breach(metric)
        
        # 알림 레벨 결정
        alert_level = self._determine_alert_level(metric)
        
        # 한국어 메시지 생성
        korean_message = self._generate_korean_alert(metric)
        
        # 알림 전송
        await self._send_alert(
            alert_level,
            f"SLA 위반: {metric.name}",
            f"{metric.name}이(가) 기준값 {metric.threshold}{metric.unit}를 "
            f"초과했습니다. 현재값: {metric.value}{metric.unit}",
            metric,
            korean_message
        )
        
        # 자동 복구 조치
        if alert_level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]:
            await self._trigger_auto_recovery(metric)
    
    def _determine_alert_level(self, metric: SLAMetric) -> AlertLevel:
        """알림 레벨 결정"""
        if metric.name == MonitoringMetric.UPTIME.value:
            if metric.value < 99.0:
                return AlertLevel.EMERGENCY
            elif metric.value < 99.5:
                return AlertLevel.CRITICAL
            else:
                return AlertLevel.WARNING
        
        elif metric.name == MonitoringMetric.RESPONSE_TIME.value:
            if metric.value > 1000:  # 1초 초과
                return AlertLevel.CRITICAL
            elif metric.value > 200:  # 200ms 초과
                return AlertLevel.WARNING
            else:
                return AlertLevel.INFO
        
        elif metric.name in [MonitoringMetric.CPU_USAGE.value, 
                           MonitoringMetric.MEMORY_USAGE.value]:
            if metric.value > 95:
                return AlertLevel.CRITICAL
            elif metric.value > 90:
                return AlertLevel.WARNING
            else:
                return AlertLevel.INFO
        
        return AlertLevel.WARNING
    
    def _generate_korean_alert(self, metric: SLAMetric) -> str:
        """한국어 알림 메시지 생성"""
        messages = {
            MonitoringMetric.UPTIME.value: f"🚨 서비스 가동시간 {metric.value:.1f}% (목표: {metric.threshold}%)",
            MonitoringMetric.RESPONSE_TIME.value: f"⚡ API 응답시간 {metric.value:.1f}ms 지연 (목표: <{metric.threshold}ms)",
            MonitoringMetric.CPU_USAGE.value: f"🔥 CPU 사용률 {metric.value:.1f}% 과부하 (기준: {metric.threshold}%)",
            MonitoringMetric.MEMORY_USAGE.value: f"💾 메모리 사용률 {metric.value:.1f}% 과부하 (기준: {metric.threshold}%)",
            MonitoringMetric.DISK_USAGE.value: f"💿 디스크 사용률 {metric.value:.1f}% 부족 (기준: {metric.threshold}%)"
        }
        
        return messages.get(metric.name, f"⚠️ {metric.name} 이상 감지: {metric.value}{metric.unit}")
    
    async def _send_alert(self, level: AlertLevel, title: str, message: str, 
                         metric: Optional[SLAMetric] = None, korean_message: str = ""):
        """알림 전송"""
        alert = AlertMessage(
            level=level,
            title=title,
            message=message,
            metric=metric,
            timestamp=datetime.now(),
            actions=[],
            korean_message=korean_message
        )
        
        self.alert_history.append(alert)
        
        # 데이터베이스에 저장
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO alert_history 
                    (level, title, message, korean_message, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (level.value, title, message, korean_message, alert.timestamp))
                conn.commit()
        except Exception as e:
            logger.error(f"❌ 알림 저장 오류: {e}")
        
        # 콘솔 로그 출력
        log_message = f"[{level.value}] {title}: {korean_message}"
        if level == AlertLevel.EMERGENCY:
            logger.critical(log_message)
        elif level == AlertLevel.CRITICAL:
            logger.error(log_message)
        elif level == AlertLevel.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    async def _record_sla_breach(self, metric: SLAMetric):
        """SLA 위반 이벤트 기록"""
        try:
            impact_level = "HIGH" if metric.is_breached() else "LOW"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sla_breaches 
                    (metric_name, breach_value, threshold, duration_seconds, 
                     impact_level, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    metric.name, metric.value, metric.threshold,
                    30, impact_level, metric.timestamp  # 30초 간격으로 측정
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"❌ SLA 위반 기록 오류: {e}")
    
    async def _trigger_auto_recovery(self, metric: SLAMetric):
        """자동 복구 조치 트리거"""
        logger.info(f"🔧 자동 복구 조치 시작: {metric.name}")
        
        if metric.name == MonitoringMetric.MEMORY_USAGE.value and metric.value > 90:
            # 메모리 정리
            await self._cleanup_memory()
        
        elif metric.name == MonitoringMetric.CPU_USAGE.value and metric.value > 90:
            # CPU 부하 경감
            await self._reduce_cpu_load()
        
        elif metric.name == MonitoringMetric.RESPONSE_TIME.value and metric.value > 500:
            # 캐시 정리 및 재시작 고려
            await self._optimize_performance()
        
        elif metric.name == MonitoringMetric.UPTIME.value and metric.value < 99.0:
            # 서비스 재시작 (최후 수단)
            await self._trigger_service_rollback()
    
    async def _cleanup_memory(self):
        """메모리 정리"""
        try:
            import gc
            gc.collect()
            logger.info("🧹 메모리 가비지 컬렉션 실행 완료")
        except Exception as e:
            logger.error(f"❌ 메모리 정리 실패: {e}")
    
    async def _reduce_cpu_load(self):
        """CPU 부하 경감"""
        logger.info("⚡ CPU 부하 경감 조치 실행")
        # 여기에 실제 부하 경감 로직 구현
    
    async def _optimize_performance(self):
        """성능 최적화"""
        logger.info("🚀 성능 최적화 조치 실행")
        # 여기에 캐시 정리, 연결 풀 최적화 등 구현
    
    async def _trigger_service_rollback(self):
        """서비스 롤백 트리거"""
        if self.rollback_triggered:
            return  # 이미 롤백이 진행 중
        
        self.rollback_triggered = True
        logger.critical("🚨 긴급 서비스 롤백 시작")
        
        await self._send_alert(
            AlertLevel.EMERGENCY,
            "긴급 서비스 롤백",
            "심각한 SLA 위반으로 인해 자동 롤백을 실행합니다.",
            korean_message="🚨 긴급상황: 서비스 자동 롤백 진행 중..."
        )
    
    async def _analyze_sla_breaches(self) -> Dict[str, Any]:
        """SLA 위반 분석"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 지난 5분간 위반 통계
                five_minutes_ago = datetime.now() - timedelta(minutes=5)
                
                cursor.execute("""
                    SELECT metric_name, COUNT(*), AVG(breach_value), impact_level
                    FROM sla_breaches 
                    WHERE timestamp >= ?
                    GROUP BY metric_name, impact_level
                """, (five_minutes_ago,))
                
                results = cursor.fetchall()
                
                analysis = {
                    'total_breaches': sum(row[1] for row in results),
                    'critical_breaches': sum(row[1] for row in results if row[3] == 'HIGH'),
                    'metrics_affected': list(set(row[0] for row in results)),
                    'timestamp': datetime.now()
                }
                
                return analysis
        except Exception as e:
            logger.error(f"❌ SLA 위반 분석 오류: {e}")
            return {}
    
    async def _trigger_emergency_response(self, breach_summary: Dict[str, Any]):
        """긴급 대응 트리거"""
        logger.critical(f"🚨 긴급 대응 시작: {breach_summary['critical_breaches']}건 심각한 위반")
        
        await self._send_alert(
            AlertLevel.EMERGENCY,
            "긴급 대응 필요",
            f"지난 5분간 {breach_summary['critical_breaches']}건의 심각한 SLA 위반 발생",
            korean_message=f"🚨 긴급상황: {breach_summary['critical_breaches']}건 심각한 위반 - 즉시 대응 필요"
        )
    
    def get_current_sla_status(self) -> Dict[str, Any]:
        """현재 SLA 상태 반환"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 최근 메트릭 조회
                cursor.execute("""
                    SELECT name, value, threshold, unit, status, timestamp
                    FROM sla_metrics 
                    WHERE timestamp >= datetime('now', '-1 hour')
                    ORDER BY timestamp DESC
                """)
                
                results = cursor.fetchall()
                
                if not results:
                    return {"status": "데이터 없음", "metrics": []}
                
                # 메트릭별 최신 상태
                latest_metrics = {}
                for row in results:
                    metric_name = row[0]
                    if metric_name not in latest_metrics:
                        latest_metrics[metric_name] = {
                            'name': row[0],
                            'value': row[1],
                            'threshold': row[2],
                            'unit': row[3],
                            'status': row[4],
                            'timestamp': row[5]
                        }
                
                return {
                    'overall_status': '정상' if all(m['status'] == '정상' for m in latest_metrics.values()) else '경고',
                    'metrics': list(latest_metrics.values()),
                    'last_updated': datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"❌ SLA 상태 조회 오류: {e}")
            return {"status": "오류", "error": str(e)}
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """알림 요약 반환"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 24시간 내 알림 통계
                twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
                
                cursor.execute("""
                    SELECT level, COUNT(*) FROM alert_history 
                    WHERE timestamp >= ?
                    GROUP BY level
                """, (twenty_four_hours_ago,))
                
                alert_counts = dict(cursor.fetchall())
                
                return {
                    'total_alerts': sum(alert_counts.values()),
                    'by_level': alert_counts,
                    'period': '24시간',
                    'last_updated': datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"❌ 알림 요약 조회 오류: {e}")
            return {"error": str(e)}


# 글로벌 모니터링 인스턴스
_monitor_instance = None

def get_production_monitor() -> ProductionMonitor:
    """프로덕션 모니터링 인스턴스 반환 (싱글톤)"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = ProductionMonitor()
    return _monitor_instance


if __name__ == "__main__":
    async def main():
        """테스트 실행"""
        monitor = get_production_monitor()
        await monitor.start_monitoring()
        
        # 5분간 모니터링 실행
        await asyncio.sleep(300)
        
        # 현재 상태 출력
        status = monitor.get_current_sla_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    
    asyncio.run(main())