"""
자율 모니터링 시스템 테스트

AI 자동화 플랫폼 v8.3.0의 자율 모니터링 시스템에 대한
종합적인 테스트 및 검증을 수행합니다.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import os
from pathlib import Path

# 테스트 대상 모듈 import
try:
    from src.core.automation.autonomous_monitor import (
        AutonomousMonitor, AlertLevel, SystemMetrics, 
        MetricThreshold, MonitoringAlert, SystemSnapshot
    )
    from src.core.automation.backup_manager import (
        AutomationBackupManager, BackupType, BackupStatus
    )
    from src.core.automation.korean_alert_system import (
        KoreanAlertSystem, AlertPriority, AlertCategory
    )
    from src.core.automation.predictive_engine import (
        PredictiveEngine, PredictionType, RiskLevel
    )
except ImportError as e:
    pytest.skip(f"모니터링 시스템 모듈을 찾을 수 없습니다: {e}", allow_module_level=True)

class TestAutonomousMonitor:
    """자율 모니터링 시스템 테스트"""
    
    @pytest.fixture
    def monitor(self):
        """테스트용 모니터 인스턴스"""
        monitor = AutonomousMonitor()
        yield monitor
        monitor.stop_monitoring()
    
    def test_monitor_initialization(self, monitor):
        """모니터 초기화 테스트"""
        assert monitor is not None
        assert not monitor.is_running
        assert len(monitor.alerts_history) == 0
        assert len(monitor.metrics_history) == 0
        assert monitor.auto_healing_enabled == True
        
        # 임계값 설정 확인
        assert SystemMetrics.GIT_CHANGES in monitor.thresholds
        assert SystemMetrics.TEST_COVERAGE in monitor.thresholds
        assert SystemMetrics.API_PERFORMANCE in monitor.thresholds
    
    @pytest.mark.asyncio
    async def test_system_metrics_collection(self, monitor):
        """시스템 메트릭 수집 테스트"""
        with patch('subprocess.run') as mock_run:
            # Git 명령 모킹
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "M file1.py\nM file2.py\n"
            
            with patch('requests.get') as mock_requests:
                # API 요청 모킹
                mock_response = Mock()
                mock_response.status_code = 200
                mock_requests.return_value = mock_response
                
                with patch('psutil.virtual_memory') as mock_memory:
                    mock_memory.return_value.percent = 50.0
                    
                    with patch('psutil.cpu_percent') as mock_cpu:
                        mock_cpu.return_value = 30.0
                        
                        # 메트릭 수집 실행
                        snapshot = await monitor._collect_system_metrics()
                        
                        assert isinstance(snapshot, SystemSnapshot)
                        assert snapshot.git_changes_count >= 0
                        assert snapshot.memory_usage == 50.0
                        assert snapshot.cpu_usage == 30.0
                        assert isinstance(snapshot.timestamp, datetime)
    
    def test_threshold_checking(self, monitor):
        """임계값 검사 테스트"""
        # 테스트 스냅샷 생성
        snapshot = SystemSnapshot(
            timestamp=datetime.now(),
            git_changes_count=150,  # 임계값 초과
            test_coverage=15.0,     # 임계값 미만 (위험)
            api_response_time=250.0,  # 임계값 초과
            memory_usage=45.0,      # 정상
            cpu_usage=25.0,         # 정상
            file_violations_count=2,  # 정상
            deployment_health="healthy",
            alerts_count=0
        )
        
        alerts = monitor._check_thresholds(snapshot)
        
        # 예상되는 알림 생성 확인
        assert len(alerts) > 0
        
        # Git 변경사항 알림 확인
        git_alert = next((a for a in alerts if a.metric_type == SystemMetrics.GIT_CHANGES), None)
        assert git_alert is not None
        assert git_alert.level in [AlertLevel.WARNING, AlertLevel.CRITICAL, AlertLevel.EMERGENCY]
        
        # 테스트 커버리지 알림 확인 (낮은 값이므로 위험)
        coverage_alert = next((a for a in alerts if a.metric_type == SystemMetrics.TEST_COVERAGE), None)
        assert coverage_alert is not None
        assert coverage_alert.level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]
    
    @pytest.mark.asyncio
    async def test_auto_healing_git_changes(self, monitor):
        """자가 치유 - Git 변경사항 자동 수정 테스트"""
        alert = MonitoringAlert(
            timestamp=datetime.now(),
            level=AlertLevel.WARNING,
            metric_type=SystemMetrics.GIT_CHANGES,
            current_value=120,
            threshold=100,
            message="Git 변경사항 과다"
        )
        
        with patch('subprocess.run') as mock_run:
            # Git 상태 및 커밋 명령 모킹
            mock_run.side_effect = [
                # git status --porcelain
                Mock(returncode=0, stdout="M config/settings.yml\nM README.md\n"),
                # git add 명령들
                Mock(returncode=0),
                Mock(returncode=0),
                # git commit
                Mock(returncode=0)
            ]
            
            success = await monitor._auto_fix_git_changes()
            
            assert success == True
            assert mock_run.call_count >= 3  # status + add 명령들 + commit
    
    def test_alert_message_generation(self, monitor):
        """알림 메시지 생성 테스트"""
        message = monitor._generate_alert_message(
            SystemMetrics.API_PERFORMANCE,
            150.0,
            AlertLevel.WARNING
        )
        
        assert "API 응답시간" in message
        assert "주의" in message
        assert "150" in message
    
    def test_progress_calculation(self, monitor):
        """자동화 진행률 계산 테스트"""
        snapshot = SystemSnapshot(
            timestamp=datetime.now(),
            git_changes_count=66,   # 50% 진행 (133 -> 66)
            test_coverage=57.0,     # 60% 진행 (19 -> 57, 목표 95)
            api_response_time=100.0,  # 75% 진행 (200 -> 100, 목표 50)
            memory_usage=45.0,
            cpu_usage=25.0,
            file_violations_count=0,
            deployment_health="healthy",
            alerts_count=0
        )
        
        progress = monitor._calculate_automation_progress(snapshot)
        
        assert 0 <= progress <= 100
        assert progress > 50  # 전반적으로 개선된 상태

class TestBackupManager:
    """백업 관리자 테스트"""
    
    @pytest.fixture
    def backup_manager(self):
        """테스트용 백업 관리자"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = AutomationBackupManager(backup_root=temp_dir)
            yield manager
    
    def test_backup_manager_initialization(self, backup_manager):
        """백업 관리자 초기화 테스트"""
        assert backup_manager is not None
        assert backup_manager.backup_root.exists()
        assert isinstance(backup_manager.backup_records, list)
        assert backup_manager.max_backups_per_type == 10
        assert backup_manager.retention_days == 7
    
    def test_git_backup_creation(self, backup_manager):
        """Git 백업 생성 테스트"""
        with patch('subprocess.run') as mock_run:
            # Git 명령들 모킹
            mock_run.side_effect = [
                Mock(returncode=0, stdout="M file1.py\nM file2.py\n"),  # git status
                Mock(returncode=0, stdout="diff --git a/file1.py\n+new line\n"),  # git diff
                Mock(returncode=0, stdout="abc123 Initial commit\n"),  # git log
                Mock(returncode=0, stdout="main\n")  # git branch
            ]
            
            backup_record = backup_manager.create_backup(
                BackupType.GIT_CHECKPOINT,
                "테스트 Git 백업"
            )
            
            assert backup_record is not None
            assert backup_record.backup_type == BackupType.GIT_CHECKPOINT
            assert backup_record.status == BackupStatus.VERIFIED
            assert Path(backup_record.file_path).exists()
            assert backup_record.size_bytes > 0
    
    def test_backup_verification(self, backup_manager):
        """백업 검증 테스트"""
        # 임시 백업 파일 생성
        temp_backup = backup_manager.backup_root / "test_backup.tar.gz"
        
        import tarfile
        with tarfile.open(temp_backup, 'w:gz') as tar:
            info = tarfile.TarInfo('test.txt')
            info.size = 4
            tar.addfile(info, fileobj=b"test")
        
        # 백업 레코드 생성
        from src.core.automation.backup_manager import BackupRecord
        backup_record = BackupRecord(
            backup_id="test_backup",
            backup_type=BackupType.CONFIG_BACKUP,
            timestamp=datetime.now(),
            file_path=str(temp_backup),
            description="테스트 백업",
            size_bytes=temp_backup.stat().st_size,
            checksum=backup_manager._calculate_checksum(temp_backup),
            metadata={}
        )
        
        # 검증 실행
        is_valid = backup_manager._verify_backup(backup_record)
        assert is_valid == True
    
    def test_backup_cleanup(self, backup_manager):
        """백업 정리 테스트"""
        # 여러 개의 백업 레코드 생성 (한도 초과)
        for i in range(12):  # max_backups_per_type(10) 초과
            backup_record = backup_manager.create_backup(
                BackupType.AUTOMATION_STATE,
                f"테스트 백업 {i}",
                metadata={"test_index": i}
            )
            
            # 타임스탬프 조정 (시간 순서 확보)
            if backup_record:
                backup_record.timestamp = datetime.now() - timedelta(minutes=i)
        
        # 정리 후 개수 확인
        automation_backups = [r for r in backup_manager.backup_records 
                            if r.backup_type == BackupType.AUTOMATION_STATE]
        
        assert len(automation_backups) <= backup_manager.max_backups_per_type
    
    def test_backup_status_report(self, backup_manager):
        """백업 상태 보고서 테스트"""
        # 몇 개의 백업 생성
        backup_manager.create_backup(BackupType.CONFIG_BACKUP, "설정 백업")
        backup_manager.create_backup(BackupType.AUTOMATION_STATE, "상태 백업")
        
        status = backup_manager.get_backup_status()
        
        assert "total_backups" in status
        assert "total_size_bytes" in status
        assert "status_distribution" in status
        assert "type_distribution" in status
        assert status["total_backups"] >= 2

class TestKoreanAlertSystem:
    """한국어 알림 시스템 테스트"""
    
    @pytest.fixture
    def alert_system(self):
        """테스트용 알림 시스템"""
        system = KoreanAlertSystem()
        yield system
        system.stop()
    
    def test_alert_system_initialization(self, alert_system):
        """알림 시스템 초기화 테스트"""
        assert alert_system is not None
        assert isinstance(alert_system.active_alerts, list)
        assert isinstance(alert_system.alert_history, list)
        assert isinstance(alert_system.subscribers, list)
    
    def test_alert_sending(self, alert_system):
        """알림 전송 테스트"""
        alert_id = alert_system.send_alert(
            title="테스트 알림",
            message="테스트 메시지입니다",
            priority=AlertPriority.INFO,
            category=AlertCategory.SYSTEM
        )
        
        assert alert_id is not None
        assert len(alert_id) > 0
        
        # 큐에서 처리될 때까지 잠시 대기
        time.sleep(0.1)
    
    def test_progress_update_alert(self, alert_system):
        """진행률 업데이트 알림 테스트"""
        # 50% 진행
        alert_id = alert_system.send_progress_update(
            "테스트 작업", 50.0, 
            details="중간 진행 상황",
            estimated_completion=datetime.now() + timedelta(hours=1)
        )
        
        assert alert_id is not None
        
        # 100% 완료
        alert_id = alert_system.send_progress_update(
            "테스트 작업", 100.0,
            details="작업 완료"
        )
        
        assert alert_id is not None
    
    def test_automation_step_alert(self, alert_system):
        """자동화 단계 알림 테스트"""
        alert_id = alert_system.send_automation_step_alert(
            step_number=1,
            step_name="Git 변경사항 분류",
            status="시작",
            details="133개 변경사항 분석 중",
            next_steps=["파일 그룹화", "안전 검증", "커밋 실행"]
        )
        
        assert alert_id is not None
        
        # 완료 상태
        alert_id = alert_system.send_automation_step_alert(
            step_number=1,
            step_name="Git 변경사항 분류",
            status="완료",
            details="Group A 20개 파일 분류 완료"
        )
        
        assert alert_id is not None
    
    def test_system_status_alert(self, alert_system):
        """시스템 상태 알림 테스트"""
        alert_id = alert_system.send_system_status_alert(
            metric_name="메모리 사용률",
            current_value=85.0,
            threshold=70.0,
            unit="%",
            trend="증가"
        )
        
        assert alert_id is not None
    
    def test_alert_statistics(self, alert_system):
        """알림 통계 테스트"""
        # 여러 알림 전송
        alert_system.send_alert("정보1", "메시지1", AlertPriority.INFO)
        alert_system.send_alert("경고1", "메시지2", AlertPriority.WARNING)
        alert_system.send_alert("위험1", "메시지3", AlertPriority.CRITICAL)
        
        time.sleep(0.2)  # 처리 시간 대기
        
        stats = alert_system.get_alert_statistics()
        
        assert "총_알림_수" in stats
        assert "우선순위별_통계" in stats
        assert "카테고리별_통계" in stats
        assert stats["총_알림_수"] >= 3

class TestPredictiveEngine:
    """예측 엔진 테스트"""
    
    @pytest.fixture
    def predictive_engine(self):
        """테스트용 예측 엔진"""
        return PredictiveEngine()
    
    def test_engine_initialization(self, predictive_engine):
        """예측 엔진 초기화 테스트"""
        assert predictive_engine is not None
        assert predictive_engine.time_series_analyzer is not None
        assert predictive_engine.anomaly_detector is not None
        assert predictive_engine.risk_predictor is not None
    
    def test_system_health_analysis(self, predictive_engine):
        """시스템 건강도 분석 테스트"""
        test_metrics = {
            "git_changes": 133,
            "test_coverage": 19.0,
            "api_response_time": 65.0,
            "memory_usage": 45.0,
            "cpu_usage": 25.0,
            "file_violations": 2
        }
        
        analysis = predictive_engine.analyze_system_health(test_metrics)
        
        assert "timestamp" in analysis
        assert "overall_health" in analysis
        assert "predictions" in analysis
        assert "anomalies" in analysis
        assert "recommendations" in analysis
        
        assert analysis["overall_health"] in [
            "excellent", "good", "fair", "poor", "critical", "error"
        ]
    
    def test_anomaly_detection(self, predictive_engine):
        """이상 징후 감지 테스트"""
        # 정상 범위의 값들로 베이스라인 구축
        normal_values = [45, 47, 46, 48, 44, 46, 45, 47]
        for value in normal_values:
            predictive_engine.anomaly_detector.update_baseline("test_metric", value)
        
        # 이상값 테스트
        anomaly_score = predictive_engine.anomaly_detector.detect_anomaly("test_metric", 80)
        
        assert anomaly_score.metric_name == "test_metric"
        assert anomaly_score.value == 80
        assert anomaly_score.anomaly_score > 0
        # 80은 정상 범위(45±3)를 크게 벗어나므로 이상으로 판단되어야 함
        assert anomaly_score.is_anomaly == True
    
    def test_trend_analysis(self, predictive_engine):
        """트렌드 분석 테스트"""
        # 증가 트렌드 데이터
        increasing_values = [10, 15, 20, 25, 30, 35]
        trend, slope = predictive_engine.time_series_analyzer.detect_trend(increasing_values)
        
        assert trend == "increasing"
        assert slope > 0
        
        # 감소 트렌드 데이터
        decreasing_values = [100, 90, 80, 70, 60, 50]
        trend, slope = predictive_engine.time_series_analyzer.detect_trend(decreasing_values)
        
        assert trend == "decreasing"
        assert slope < 0
        
        # 안정 트렌드 데이터
        stable_values = [50, 51, 49, 50, 52, 48]
        trend, slope = predictive_engine.time_series_analyzer.detect_trend(stable_values)
        
        assert trend == "stable"
    
    def test_automation_risk_prediction(self, predictive_engine):
        """자동화 위험 예측 테스트"""
        # 고위험 상황 메트릭
        high_risk_metrics = {
            "git_changes": 150,      # 많은 변경사항
            "test_coverage": 15.0,   # 낮은 커버리지
            "api_response_time": 250, # 느린 응답
            "memory_usage": 85.0,    # 높은 메모리 사용
            "file_violations": 5     # 파일 위반
        }
        
        prediction = predictive_engine.risk_predictor.predict_automation_success(
            high_risk_metrics, {"timestamp": datetime.now()}
        )
        
        assert prediction.prediction_type == PredictionType.AUTOMATION_SUCCESS
        assert 0 <= prediction.predicted_value <= 100
        assert prediction.risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]
        assert len(prediction.factors) > 0
        assert len(prediction.recommendations) > 0
    
    def test_merge_conflict_prediction(self, predictive_engine):
        """머지 충돌 위험 예측 테스트"""
        prediction = predictive_engine.risk_predictor.predict_merge_conflict_risk(
            git_changes=133,
            file_types=["models.py", "main.py", "settings.py"],
            change_complexity={"lines_changed": 500, "concurrent_developers": 2}
        )
        
        assert prediction.prediction_type == PredictionType.MERGE_CONFLICT_RISK
        assert 0 <= prediction.predicted_value <= 100
        assert prediction.risk_level in list(RiskLevel)
        assert len(prediction.factors) >= 0
        assert len(prediction.recommendations) > 0
    
    def test_prediction_summary(self, predictive_engine):
        """예측 요약 테스트"""
        # 몇 가지 메트릭 히스토리 생성
        predictive_engine.metrics_history["test_metric"].extend([
            {"timestamp": datetime.now(), "value": 10},
            {"timestamp": datetime.now(), "value": 15},
            {"timestamp": datetime.now(), "value": 20}
        ])
        
        summary = predictive_engine.get_prediction_summary()
        
        assert "metrics_tracked" in summary
        assert "total_history_points" in summary
        assert "automation_success_rate" in summary
        assert "prediction_capabilities" in summary
        assert summary["metrics_tracked"] >= 1

@pytest.mark.integration
class TestIntegratedMonitoringSystem:
    """통합 모니터링 시스템 테스트"""
    
    @pytest.fixture
    def integrated_system(self):
        """통합 시스템 구성"""
        monitor = AutonomousMonitor()
        backup_manager = AutomationBackupManager()
        alert_system = KoreanAlertSystem()
        predictive_engine = PredictiveEngine()
        
        # 시스템들 연동
        def alert_subscriber(alert):
            print(f"통합 테스트 알림: {alert.title}")
        
        alert_system.subscribe(alert_subscriber)
        
        yield {
            "monitor": monitor,
            "backup_manager": backup_manager,
            "alert_system": alert_system,
            "predictive_engine": predictive_engine
        }
        
        # 정리
        monitor.stop_monitoring()
        alert_system.stop()
    
    @pytest.mark.asyncio
    async def test_end_to_end_monitoring_cycle(self, integrated_system):
        """종단간 모니터링 사이클 테스트"""
        monitor = integrated_system["monitor"]
        alert_system = integrated_system["alert_system"]
        predictive_engine = integrated_system["predictive_engine"]
        
        # 테스트 메트릭 정의
        test_metrics = {
            "git_changes": 133,
            "test_coverage": 19.0,
            "api_response_time": 65.0,
            "memory_usage": 45.0,
            "cpu_usage": 25.0,
            "file_violations": 2
        }
        
        # 1. 시스템 건강도 분석
        health_analysis = predictive_engine.analyze_system_health(test_metrics)
        assert health_analysis["overall_health"] in ["excellent", "good", "fair", "poor", "critical"]
        
        # 2. 백업 생성 (위험한 변경 전)
        backup_record = integrated_system["backup_manager"].create_backup(
            BackupType.AUTOMATION_STATE,
            "통합 테스트 백업",
            metadata={"test_context": "integration"}
        )
        assert backup_record is not None
        
        # 3. 알림 전송
        alert_id = alert_system.send_automation_step_alert(
            step_number=5,
            step_name="자율 모니터링 시스템 설정",
            status="진행중",
            details="통합 테스트 실행 중"
        )
        assert alert_id is not None
        
        # 4. 모니터링 사이클 시뮬레이션
        with patch.object(monitor, '_collect_system_metrics') as mock_collect:
            mock_snapshot = Mock()
            mock_snapshot.timestamp = datetime.now()
            mock_snapshot.git_changes_count = 133
            mock_snapshot.test_coverage = 19.0
            mock_snapshot.api_response_time = 65.0
            mock_snapshot.memory_usage = 45.0
            mock_snapshot.cpu_usage = 25.0
            mock_snapshot.file_violations_count = 2
            mock_snapshot.deployment_health = "healthy"
            mock_snapshot.alerts_count = 1
            
            mock_collect.return_value = mock_snapshot
            
            # 한 번의 모니터링 사이클 실행
            await monitor._monitoring_cycle()
            
            # 결과 확인
            assert len(monitor.metrics_history) > 0
        
        # 5. 통합 상태 확인
        monitor_status = monitor.get_current_status()
        alert_stats = alert_system.get_alert_statistics()
        prediction_summary = predictive_engine.get_prediction_summary()
        backup_status = integrated_system["backup_manager"].get_backup_status()
        
        assert monitor_status["auto_healing_enabled"] == True
        assert alert_stats["총_알림_수"] >= 1
        assert prediction_summary["metrics_tracked"] >= 0
        assert backup_status["total_backups"] >= 1
        
        print("✅ 통합 모니터링 시스템 테스트 완료")
        print(f"📊 모니터 상태: {monitor_status['is_running']}")
        print(f"🔔 총 알림: {alert_stats['총_알림_수']}")
        print(f"📈 예측 메트릭: {prediction_summary['metrics_tracked']}")
        print(f"💾 백업 개수: {backup_status['total_backups']}")

def test_monitoring_system_components_exist():
    """모니터링 시스템 컴포넌트 존재 확인"""
    # 핵심 클래스들이 정상적으로 import 되는지 확인
    assert AutonomousMonitor is not None
    assert AutomationBackupManager is not None
    assert KoreanAlertSystem is not None
    assert PredictiveEngine is not None
    
    # 열거형 클래스들 확인
    assert AlertLevel is not None
    assert SystemMetrics is not None
    assert BackupType is not None
    assert AlertPriority is not None
    assert PredictionType is not None
    assert RiskLevel is not None

def test_monitoring_api_endpoints_exist():
    """모니터링 API 엔드포인트 존재 확인"""
    try:
        from src.api.monitoring.autonomous_monitoring_routes import autonomous_monitoring_bp
        assert autonomous_monitoring_bp is not None
        
        # Blueprint에 필요한 라우트들이 등록되어 있는지 확인
        route_names = [rule.rule for rule in autonomous_monitoring_bp.url_map.iter_rules()]
        
        # 주요 엔드포인트들 확인
        expected_routes = [
            '/status',
            '/metrics/current',
            '/alerts/active',
            '/dashboard',
            '/control/start',
            '/control/stop'
        ]
        
        for expected_route in expected_routes:
            # Blueprint prefix를 고려한 전체 경로 확인
            full_route = f"/api/monitoring/autonomous{expected_route}"
            # 실제로는 상대 경로만 확인
            route_found = any(expected_route in rule for rule in route_names)
            assert route_found, f"라우트가 등록되지 않음: {expected_route}"
        
    except ImportError:
        pytest.fail("모니터링 API 라우트 모듈을 찾을 수 없습니다")

if __name__ == "__main__":
    # 개별 테스트 실행
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--disable-warnings"
    ])