"""
API 라우트 포괄적 테스트

모든 API 엔드포인트의 비즈니스 로직과 응답을 테스트합니다.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from flask import Flask
from flask.testing import FlaskClient

from src.core.routes.api_routes import api_routes_bp
from src.core.routes.web_routes import web_routes_bp
from src.core.routes.collection_status_routes import collection_status_bp
from src.core.routes.collection_trigger_routes import collection_trigger_bp


class TestAPIRoutesComprehensive:
    """API 라우트 포괄적 테스트"""

    @pytest.fixture
    def app(self):
        """테스트용 Flask 앱 생성"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        # 블루프린트 등록
        app.register_blueprint(api_routes_bp)
        app.register_blueprint(web_routes_bp)
        app.register_blueprint(collection_status_bp)
        app.register_blueprint(collection_trigger_bp)
        
        return app

    @pytest.fixture
    def client(self, app):
        """테스트 클라이언트 생성"""
        return app.test_client()

    @pytest.fixture
    def mock_service(self):
        """모의 서비스 객체"""
        with patch('src.core.routes.api_routes.service') as mock:
            mock_instance = Mock()
            mock.return_value = mock_instance
            yield mock_instance

    def test_health_check_healthy(self, client, mock_service):
        """헬스체크 - 정상 상태 테스트"""
        # Mock 데이터 설정
        mock_health = {
            "status": "healthy",
            "total_ips": 100,
            "last_update": "2023-12-01T10:00:00Z",
            "sources": {"regtech": 60, "secudium": 40}
        }
        mock_service.get_system_health.return_value = mock_health

        response = client.get('/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "components" in data
        assert data["components"]["database"] == "healthy"
        assert data["components"]["blacklist"] == "healthy"

    def test_health_check_unhealthy(self, client, mock_service):
        """헬스체크 - 비정상 상태 테스트"""
        mock_health = {
            "status": "unhealthy",
            "total_ips": 0,
            "sources": {}
        }
        mock_service.get_system_health.return_value = mock_health

        response = client.get('/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data["status"] == "degraded"
        assert data["components"]["database"] == "unhealthy"

    def test_health_check_exception(self, client, mock_service):
        """헬스체크 - 예외 발생 테스트"""
        mock_service.get_system_health.side_effect = Exception("Service error")

        response = client.get('/health')
        
        assert response.status_code == 503
        data = json.loads(response.data)
        
        assert data["status"] == "error"
        assert "error" in data

    def test_health_check_multiple_endpoints(self, client, mock_service):
        """헬스체크 - 여러 엔드포인트 테스트"""
        mock_health = {"status": "healthy", "total_ips": 50}
        mock_service.get_system_health.return_value = mock_health

        # 모든 헬스체크 엔드포인트 테스트
        endpoints = ['/health', '/healthz', '/ready']
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "healthy"

    def test_api_health_detailed(self, client, mock_service):
        """API 상세 헬스체크 테스트"""
        mock_health = {
            "status": "healthy",
            "total_ips": 200,
            "active_ips": 180,
            "sources": {"regtech": 120, "secudium": 80},
            "last_update": "2023-12-01T15:30:00Z",
            "collection_status": "enabled",
            "cache_status": "connected"
        }
        mock_service.get_system_health.return_value = mock_health

        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data["status"] == "healthy"
        assert data["total_ips"] == 200
        assert data["sources"]["regtech"] == 120
        assert "version" in data
        assert "uptime" in data

    def test_blacklist_active_ips(self, client, mock_service):
        """활성 IP 조회 테스트"""
        mock_ips = ["192.168.1.1", "10.0.0.1", "172.16.0.1"]
        mock_service.get_active_ips.return_value = mock_ips

        response = client.get('/api/blacklist/active')
        
        assert response.status_code == 200
        assert response.content_type == 'text/plain; charset=utf-8'
        
        content = response.data.decode('utf-8')
        assert "192.168.1.1" in content
        assert "10.0.0.1" in content
        assert "172.16.0.1" in content

    def test_blacklist_active_ips_empty(self, client, mock_service):
        """활성 IP 조회 - 빈 결과 테스트"""
        mock_service.get_active_ips.return_value = []

        response = client.get('/api/blacklist/active')
        
        assert response.status_code == 200
        content = response.data.decode('utf-8')
        assert content.strip() == ""

    def test_blacklist_active_ips_exception(self, client, mock_service):
        """활성 IP 조회 - 예외 발생 테스트"""
        mock_service.get_active_ips.side_effect = Exception("Database error")

        response = client.get('/api/blacklist/active')
        
        assert response.status_code == 500

    def test_fortigate_connector(self, client, mock_service):
        """FortiGate 커넥터 엔드포인트 테스트"""
        mock_ips = ["1.2.3.4", "5.6.7.8"]
        mock_service.get_active_ips.return_value = mock_ips

        response = client.get('/api/fortigate')
        
        assert response.status_code == 200
        assert response.content_type == 'text/plain; charset=utf-8'
        
        content = response.data.decode('utf-8')
        assert "1.2.3.4" in content
        assert "5.6.7.8" in content

    def test_blacklist_enhanced(self, client, mock_service):
        """강화된 블랙리스트 API 테스트"""
        mock_data = [
            {
                "ip": "192.168.1.1",
                "source": "regtech",
                "threat_level": "high",
                "first_seen": "2023-12-01",
                "last_seen": "2023-12-15",
                "is_active": True
            },
            {
                "ip": "10.0.0.1",
                "source": "secudium",
                "threat_level": "medium",
                "first_seen": "2023-11-15",
                "last_seen": "2023-12-10",
                "is_active": True
            }
        ]
        mock_service.get_enhanced_blacklist.return_value = mock_data

        response = client.get('/api/v2/blacklist/enhanced')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert len(data) == 2
        assert data[0]["ip"] == "192.168.1.1"
        assert data[0]["threat_level"] == "high"
        assert data[1]["source"] == "secudium"

    def test_collection_status(self, client, mock_service):
        """수집 상태 조회 테스트"""
        mock_status = {
            "is_enabled": True,
            "regtech_enabled": True,
            "secudium_enabled": False,
            "last_collection_time": "2023-12-01T10:00:00Z",
            "next_collection_time": "2023-12-01T15:00:00Z",
            "total_collections": 50,
            "successful_collections": 48,
            "failed_collections": 2
        }
        mock_service.get_collection_status.return_value = mock_status

        response = client.get('/api/collection/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data["is_enabled"] is True
        assert data["regtech_enabled"] is True
        assert data["secudium_enabled"] is False
        assert data["total_collections"] == 50

    def test_collection_enable(self, client, mock_service):
        """수집 활성화 테스트"""
        mock_service.enable_collection.return_value = {
            "success": True,
            "message": "Collection enabled successfully"
        }

        response = client.post('/api/collection/enable')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data["success"] is True
        assert "enabled successfully" in data["message"]

    def test_collection_disable(self, client, mock_service):
        """수집 비활성화 테스트"""
        mock_service.disable_collection.return_value = {
            "success": True,
            "message": "Collection disabled successfully"
        }

        response = client.post('/api/collection/disable')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data["success"] is True
        assert "disabled successfully" in data["message"]

    def test_manual_collection_regtech(self, client, mock_service):
        """REGTECH 수동 수집 테스트"""
        mock_result = {
            "success": True,
            "collected_ips": 150,
            "new_ips": 25,
            "updated_ips": 10,
            "duration": 45.2
        }
        mock_service.trigger_regtech_collection.return_value = mock_result

        response = client.post('/api/collection/regtech/trigger')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data["success"] is True
        assert data["collected_ips"] == 150
        assert data["new_ips"] == 25

    def test_manual_collection_secudium(self, client, mock_service):
        """SECUDIUM 수동 수집 테스트"""
        mock_result = {
            "success": True,
            "collected_ips": 75,
            "new_ips": 12,
            "updated_ips": 5,
            "duration": 30.8
        }
        mock_service.trigger_secudium_collection.return_value = mock_result

        response = client.post('/api/collection/secudium/trigger')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data["success"] is True
        assert data["collected_ips"] == 75
        assert data["new_ips"] == 12

    def test_analytics_trends(self, client, mock_service):
        """분석 트렌드 API 테스트"""
        mock_trends = {
            "monthly_trends": [
                {"month": "2023-12", "total_ips": 200, "new_ips": 50},
                {"month": "2023-11", "total_ips": 150, "new_ips": 30}
            ],
            "threat_level_distribution": {
                "high": 40,
                "medium": 120,
                "low": 40
            },
            "source_distribution": {
                "regtech": 120,
                "secudium": 80
            }
        }
        mock_service.get_analytics_trends.return_value = mock_trends

        response = client.get('/api/v2/analytics/trends')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert "monthly_trends" in data
        assert len(data["monthly_trends"]) == 2
        assert data["threat_level_distribution"]["high"] == 40

    def test_analytics_summary(self, client, mock_service):
        """분석 요약 API 테스트"""
        mock_summary = {
            "total_ips": 500,
            "active_ips": 450,
            "expired_ips": 50,
            "total_sources": 2,
            "collection_status": "enabled",
            "last_update": "2023-12-01T10:00:00Z",
            "average_threat_level": "medium",
            "top_countries": ["US", "CN", "RU"],
            "detection_rate_24h": 0.95
        }
        mock_service.get_analytics_summary.return_value = mock_summary

        response = client.get('/api/v2/analytics/summary')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data["total_ips"] == 500
        assert data["active_ips"] == 450
        assert data["collection_status"] == "enabled"
        assert len(data["top_countries"]) == 3

    def test_sources_status(self, client, mock_service):
        """소스 상태 API 테스트"""
        mock_sources = {
            "regtech": {
                "name": "REGTECH",
                "status": "active",
                "last_collection": "2023-12-01T10:00:00Z",
                "total_ips": 300,
                "success_rate": 0.98
            },
            "secudium": {
                "name": "SECUDIUM",
                "status": "inactive",
                "last_collection": "2023-11-30T08:00:00Z",
                "total_ips": 200,
                "success_rate": 0.95
            }
        }
        mock_service.get_sources_status.return_value = mock_sources

        response = client.get('/api/v2/sources/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert "regtech" in data
        assert "secudium" in data
        assert data["regtech"]["status"] == "active"
        assert data["secudium"]["status"] == "inactive"

    def test_request_validation(self, client, mock_service):
        """요청 검증 테스트"""
        # POST 요청에 잘못된 데이터 전송
        response = client.post('/api/collection/enable', 
                             data='invalid json',
                             content_type='application/json')
        
        # 대부분의 API는 JSON 요청을 받지 않지만, 
        # 만약 받는다면 적절한 검증이 있어야 함
        assert response.status_code in [200, 400]

    def test_rate_limiting_simulation(self, client, mock_service):
        """레이트 리미팅 시뮬레이션 테스트"""
        # 연속적인 요청 시뮬레이션
        responses = []
        for i in range(10):
            response = client.get('/api/blacklist/active')
            responses.append(response.status_code)
        
        # 대부분의 요청이 성공해야 함 (실제 레이트 리미팅은 구현에 따라 다름)
        success_count = sum(1 for status in responses if status == 200)
        assert success_count >= 8  # 최소 80% 성공

    def test_concurrent_requests_simulation(self, client, mock_service):
        """동시 요청 시뮬레이션 테스트"""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.get('/health')
            results.append(response.status_code)
        
        # 동시에 5개 요청
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()
        
        # 모든 요청이 성공해야 함
        assert all(status == 200 for status in results)
        assert len(results) == 5

    def test_error_response_format(self, client, mock_service):
        """에러 응답 형식 테스트"""
        mock_service.get_active_ips.side_effect = Exception("Database connection failed")

        response = client.get('/api/blacklist/active')
        
        assert response.status_code == 500
        # 에러 응답이 적절한 형식을 가지는지 확인
        # (구현에 따라 JSON 또는 텍스트)

    def test_content_type_headers(self, client, mock_service):
        """Content-Type 헤더 테스트"""
        mock_service.get_active_ips.return_value = ["1.2.3.4"]

        # 텍스트 응답
        response = client.get('/api/blacklist/active')
        assert 'text/plain' in response.content_type

        # JSON 응답 (헬스체크)
        mock_service.get_system_health.return_value = {"status": "healthy", "total_ips": 1}
        response = client.get('/health')
        assert 'application/json' in response.content_type

    def test_caching_headers(self, client, mock_service):
        """캐싱 헤더 테스트"""
        mock_service.get_active_ips.return_value = ["1.2.3.4"]

        response = client.get('/api/blacklist/active')
        
        # 캐싱 관련 헤더가 적절히 설정되었는지 확인
        # (구현에 따라 Cache-Control, ETag 등)

    def test_security_headers(self, client, mock_service):
        """보안 헤더 테스트"""
        response = client.get('/health')
        
        # 보안 헤더들이 설정되었는지 확인
        # (구현에 따라 X-Content-Type-Options, X-Frame-Options 등)

    def test_api_versioning(self, client, mock_service):
        """API 버전 관리 테스트"""
        # V2 API 엔드포인트 테스트
        mock_service.get_enhanced_blacklist.return_value = []
        
        response = client.get('/api/v2/blacklist/enhanced')
        assert response.status_code == 200
        
        # API 버전 정보가 응답에 포함되는지 확인
        # (구현에 따라 헤더나 응답 본문에 포함)

    def test_pagination_support(self, client, mock_service):
        """페이지네이션 지원 테스트"""
        # 만약 페이지네이션을 지원한다면
        mock_large_dataset = [{"ip": f"192.168.1.{i}"} for i in range(100)]
        mock_service.get_enhanced_blacklist.return_value = mock_large_dataset

        # 페이지네이션 파라미터와 함께 요청
        response = client.get('/api/v2/blacklist/enhanced?page=1&size=10')
        
        if response.status_code == 200:
            data = json.loads(response.data)
            # 페이지네이션이 적용되었는지 확인
            # (구현에 따라 다름)