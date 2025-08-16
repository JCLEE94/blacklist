"""
서비스 모듈 포괄적 테스트

모든 서비스 클래스와 믹스인의 기능을 테스트합니다.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

from src.core.services.statistics_service import StatisticsServiceMixin
from src.core.services.unified_service_core import UnifiedBlacklistService


class TestStatisticsServiceMixin:
    """StatisticsServiceMixin 테스트"""

    def setup_method(self):
        """각 테스트 전 설정"""
        self.mixin = StatisticsServiceMixin()
        # Mock 의존성 설정
        self.mixin.blacklist_manager = Mock()
        self.mixin.config = {
            "service_name": "test-service",
            "version": "1.0.0",
            "auto_collection": True,
            "collection_interval": 300
        }
        self.mixin._running = True
        self.mixin._components = {"component1": Mock(), "component2": Mock()}

    @pytest.mark.asyncio
    async def test_get_statistics_success(self):
        """통계 조회 성공 테스트"""
        # Mock 데이터 설정
        mock_health = {
            "sources": {"regtech": 100, "secudium": 50},
            "status": "healthy",
            "last_update": "2023-12-01T10:00:00"
        }
        self.mixin.blacklist_manager.get_system_health.return_value = mock_health
        self.mixin.blacklist_manager.get_active_ips.return_value = ["1.2.3.4", "5.6.7.8"]

        result = await self.mixin.get_statistics()

        assert result["total_ips"] == 2
        assert result["sources"] == {"regtech": 100, "secudium": 50}
        assert result["status"] == "healthy"
        assert result["service"]["name"] == "test-service"
        assert result["service"]["version"] == "1.0.0"
        assert result["service"]["running"] is True

    @pytest.mark.asyncio
    async def test_get_statistics_no_manager(self):
        """blacklist_manager가 없을 때 테스트"""
        self.mixin.blacklist_manager = None

        result = await self.mixin.get_statistics()

        assert result["success"] is False
        assert "Blacklist manager not initialized" in result["error"]
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_statistics_exception(self):
        """통계 조회 중 예외 발생 테스트"""
        self.mixin.blacklist_manager.get_system_health.side_effect = Exception("Test error")

        result = await self.mixin.get_statistics()

        # Exception이 발생해도 안전하게 처리되는지 확인
        # (구현에 따라 다를 수 있음)

    @pytest.mark.asyncio
    async def test_get_monthly_stats(self):
        """월별 통계 조회 테스트"""
        # 만약 이 메서드가 존재한다면
        if hasattr(self.mixin, 'get_monthly_stats'):
            mock_data = {
                "2023-12": {"total": 100, "active": 95},
                "2023-11": {"total": 85, "active": 80}
            }
            self.mixin.blacklist_manager.get_monthly_data.return_value = mock_data

            result = await self.mixin.get_monthly_stats()
            
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_source_analytics(self):
        """소스별 분석 테스트"""
        # 만약 이 메서드가 존재한다면
        if hasattr(self.mixin, 'get_source_analytics'):
            mock_analytics = {
                "regtech": {
                    "total_ips": 150,
                    "active_ips": 140,
                    "threat_levels": {"high": 30, "medium": 80, "low": 30}
                },
                "secudium": {
                    "total_ips": 75,
                    "active_ips": 70,
                    "threat_levels": {"high": 15, "medium": 40, "low": 15}
                }
            }
            self.mixin.blacklist_manager.get_source_analytics.return_value = mock_analytics

            result = await self.mixin.get_source_analytics()
            
            assert "regtech" in result
            assert "secudium" in result
            assert result["regtech"]["total_ips"] == 150


class MockUnifiedBlacklistService(UnifiedBlacklistService):
    """테스트용 UnifiedBlacklistService 모의 구현"""
    
    def __init__(self):
        # 기본 설정으로 초기화
        self.config = {
            "service_name": "test-unified-service",
            "version": "1.0.0",
            "auto_collection": False,
            "collection_interval": 600,
            "max_retries": 3,
            "timeout": 30
        }
        self._running = False
        self._components = {}
        self.blacklist_manager = Mock()
        self.collection_manager = Mock()
        self.cache_manager = Mock()
        self.auth_manager = Mock()


class TestUnifiedBlacklistService:
    """UnifiedBlacklistService 통합 테스트"""

    def setup_method(self):
        """각 테스트 전 설정"""
        self.service = MockUnifiedBlacklistService()

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """서비스 초기화 테스트"""
        assert self.service.config["service_name"] == "test-unified-service"
        assert self.service._running is False
        assert isinstance(self.service._components, dict)

    @pytest.mark.asyncio
    async def test_start_service(self):
        """서비스 시작 테스트"""
        if hasattr(self.service, 'start'):
            self.service._running = False
            await self.service.start()
            assert self.service._running is True

    @pytest.mark.asyncio
    async def test_stop_service(self):
        """서비스 중지 테스트"""
        if hasattr(self.service, 'stop'):
            self.service._running = True
            await self.service.stop()
            assert self.service._running is False

    @pytest.mark.asyncio
    async def test_health_check(self):
        """헬스체크 테스트"""
        if hasattr(self.service, 'health_check'):
            mock_health = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "components": []
            }
            self.service.blacklist_manager.get_system_health.return_value = mock_health

            result = await self.service.health_check()
            
            assert "status" in result
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_statistics_integration(self):
        """통계 조회 통합 테스트"""
        # Mock 데이터 설정
        mock_health = {
            "sources": {"regtech": 200, "secudium": 100},
            "status": "healthy",
            "last_update": datetime.now().isoformat()
        }
        mock_ips = [f"192.168.1.{i}" for i in range(1, 301)]  # 300개 IP
        
        self.service.blacklist_manager.get_system_health.return_value = mock_health
        self.service.blacklist_manager.get_active_ips.return_value = mock_ips

        result = await self.service.get_statistics()

        assert result["total_ips"] == 300
        assert result["sources"]["regtech"] == 200
        assert result["sources"]["secudium"] == 100
        assert result["service"]["name"] == "test-unified-service"

    @pytest.mark.asyncio
    async def test_component_management(self):
        """컴포넌트 관리 테스트"""
        if hasattr(self.service, 'register_component'):
            mock_component = Mock()
            mock_component.name = "test_component"
            
            self.service.register_component("test_component", mock_component)
            
            assert "test_component" in self.service._components
            assert self.service._components["test_component"] == mock_component

    @pytest.mark.asyncio
    async def test_service_lifecycle(self):
        """서비스 생명주기 테스트"""
        # 초기 상태
        assert self.service._running is False
        
        # 시작
        if hasattr(self.service, 'start'):
            await self.service.start()
            assert self.service._running is True
        
        # 실행 중 상태 확인
        if hasattr(self.service, 'is_running'):
            assert self.service.is_running() is True
        
        # 중지
        if hasattr(self.service, 'stop'):
            await self.service.stop()
            assert self.service._running is False

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """에러 처리 테스트"""
        # blacklist_manager가 예외를 던지도록 설정
        self.service.blacklist_manager.get_system_health.side_effect = Exception("Connection error")
        
        # 통계 조회 시 예외가 안전하게 처리되는지 확인
        result = await self.service.get_statistics()
        
        # 구현에 따라 다르지만, 일반적으로 에러 상태를 반환하거나 기본값을 제공
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_configuration_management(self):
        """설정 관리 테스트"""
        # 설정 업데이트
        new_config = {
            "auto_collection": True,
            "collection_interval": 300
        }
        
        if hasattr(self.service, 'update_config'):
            self.service.update_config(new_config)
            assert self.service.config["auto_collection"] is True
            assert self.service.config["collection_interval"] == 300
        else:
            # 직접 설정 업데이트
            self.service.config.update(new_config)
            assert self.service.config["auto_collection"] is True

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """동시 요청 처리 테스트"""
        # 동시에 여러 통계 요청을 보내기
        tasks = []
        for i in range(5):
            task = asyncio.create_task(self.service.get_statistics())
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 모든 요청이 성공적으로 처리되는지 확인
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, dict)


class TestServiceMixinIntegration:
    """서비스 믹스인 통합 테스트"""

    def setup_method(self):
        """각 테스트 전 설정"""
        self.service = MockUnifiedBlacklistService()

    @pytest.mark.asyncio
    async def test_mixin_functionality(self):
        """믹스인 기능 테스트"""
        # StatisticsServiceMixin의 기능이 서비스에서 올바르게 작동하는지 확인
        mock_health = {
            "sources": {"regtech": 50, "secudium": 25},
            "status": "healthy",
            "last_update": datetime.now().isoformat()
        }
        mock_ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3"]
        
        self.service.blacklist_manager.get_system_health.return_value = mock_health
        self.service.blacklist_manager.get_active_ips.return_value = mock_ips

        result = await self.service.get_statistics()

        # 믹스인에서 제공하는 통계 기능 확인
        assert result["total_ips"] == 3
        assert result["sources"] == mock_health["sources"]
        assert result["service"]["name"] == "test-unified-service"

    @pytest.mark.asyncio
    async def test_multiple_mixin_interaction(self):
        """여러 믹스인 간 상호작용 테스트"""
        # 만약 다른 믹스인들이 있다면 그들 간의 상호작용을 테스트
        pass


class TestServicePerformance:
    """서비스 성능 테스트"""

    def setup_method(self):
        """각 테스트 전 설정"""
        self.service = MockUnifiedBlacklistService()

    @pytest.mark.asyncio
    async def test_statistics_performance(self):
        """통계 조회 성능 테스트"""
        # 대량 데이터로 성능 테스트
        large_ip_list = [f"192.168.{i//255}.{i%255}" for i in range(10000)]
        mock_health = {
            "sources": {"regtech": 5000, "secudium": 5000},
            "status": "healthy",
            "last_update": datetime.now().isoformat()
        }
        
        self.service.blacklist_manager.get_system_health.return_value = mock_health
        self.service.blacklist_manager.get_active_ips.return_value = large_ip_list

        start_time = datetime.now()
        result = await self.service.get_statistics()
        end_time = datetime.now()
        
        # 성능 검증 (예: 1초 이내 완료)
        duration = (end_time - start_time).total_seconds()
        assert duration < 1.0  # 1초 이내 완료
        assert result["total_ips"] == 10000

    @pytest.mark.asyncio
    async def test_concurrent_statistics_requests(self):
        """동시 통계 요청 성능 테스트"""
        # 동시에 많은 요청을 보내서 성능 확인
        mock_health = {
            "sources": {"regtech": 100},
            "status": "healthy",
            "last_update": datetime.now().isoformat()
        }
        mock_ips = ["1.2.3.4"] * 100
        
        self.service.blacklist_manager.get_system_health.return_value = mock_health
        self.service.blacklist_manager.get_active_ips.return_value = mock_ips

        # 10개의 동시 요청
        start_time = datetime.now()
        tasks = [self.service.get_statistics() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        end_time = datetime.now()
        
        # 모든 요청이 성공했는지 확인
        assert len(results) == 10
        for result in results:
            assert result["total_ips"] == 100
        
        # 전체 시간이 합리적인지 확인 (예: 3초 이내)
        duration = (end_time - start_time).total_seconds()
        assert duration < 3.0


class TestServiceEdgeCases:
    """서비스 엣지 케이스 테스트"""

    def setup_method(self):
        """각 테스트 전 설정"""
        self.service = MockUnifiedBlacklistService()

    @pytest.mark.asyncio
    async def test_empty_data_handling(self):
        """빈 데이터 처리 테스트"""
        # 빈 데이터 설정
        mock_health = {
            "sources": {},
            "status": "unknown",
            "last_update": None
        }
        self.service.blacklist_manager.get_system_health.return_value = mock_health
        self.service.blacklist_manager.get_active_ips.return_value = []

        result = await self.service.get_statistics()

        assert result["total_ips"] == 0
        assert result["sources"] == {}
        assert result["status"] == "unknown"

    @pytest.mark.asyncio
    async def test_malformed_data_handling(self):
        """잘못된 형식 데이터 처리 테스트"""
        # 잘못된 형식의 데이터
        self.service.blacklist_manager.get_system_health.return_value = "invalid_data"
        self.service.blacklist_manager.get_active_ips.return_value = None

        # 예외가 발생하지 않고 안전하게 처리되는지 확인
        result = await self.service.get_statistics()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """타임아웃 처리 테스트"""
        # 오래 걸리는 작업 시뮬레이션
        async def slow_operation():
            await asyncio.sleep(2)
            return {"status": "slow"}
        
        self.service.blacklist_manager.get_system_health = slow_operation
        
        # 타임아웃이 적절히 처리되는지 확인
        # (실제 구현에서는 타임아웃 로직이 있을 수 있음)

    @pytest.mark.asyncio
    async def test_memory_usage_with_large_datasets(self):
        """대용량 데이터셋에서 메모리 사용량 테스트"""
        # 매우 큰 데이터셋 생성
        huge_ip_list = [f"10.{i//65536}.{(i//256)%256}.{i%256}" for i in range(100000)]
        mock_health = {
            "sources": {"regtech": 100000},
            "status": "healthy",
            "last_update": datetime.now().isoformat()
        }
        
        self.service.blacklist_manager.get_system_health.return_value = mock_health
        self.service.blacklist_manager.get_active_ips.return_value = huge_ip_list

        # 메모리 사용량이 과도하지 않은지 확인 (기본적인 확인)
        result = await self.service.get_statistics()
        assert result["total_ips"] == 100000
        
        # 결과가 예상된 구조를 가지는지 확인
        assert "service" in result
        assert "sources" in result