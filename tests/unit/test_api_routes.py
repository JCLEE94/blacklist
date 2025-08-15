#!/usr/bin/env python3
"""
Unit tests for src/core/routes/api_routes.py
Testing core API endpoints: health, blacklist, fortigate
"""
from unittest.mock import Mock, patch, MagicMock
import pytest
from flask import Flask
from datetime import datetime

# Import the module under test
from src.core.routes.api_routes import api_routes_bp


class TestAPIRoutes:
    """Unit tests for API routes"""

    @pytest.fixture
    def app(self):
        """Create test Flask app with api routes blueprint"""
        app = Flask(__name__)
        app.register_blueprint(api_routes_bp)
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    @pytest.fixture
    def mock_service(self):
        """Mock unified service"""
        with patch('src.core.routes.api_routes.service') as mock:
            yield mock

    def test_health_check_healthy(self, client, mock_service):
        """Test health check with healthy service"""
        # Mock healthy service response
        mock_service.get_system_health.return_value = {
            "status": "healthy",
            "total_ips": 100,
            "database": "connected"
        }

        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['status'] == 'healthy'
        assert data['service'] == 'blacklist'
        assert data['version'] == '1.0.35'
        assert 'timestamp' in data
        assert 'components' in data
        assert data['components']['database'] == 'healthy'

    def test_health_check_unhealthy(self, client, mock_service):
        """Test health check with unhealthy service"""
        # Mock service exception
        mock_service.get_system_health.side_effect = Exception("Database connection failed")

        response = client.get('/health')
        
        assert response.status_code == 503
        data = response.get_json()
        
        assert data['status'] == 'unhealthy'
        assert 'error' in data
        assert data['components']['database'] == 'unhealthy'

    def test_health_check_detailed(self, client, mock_service):
        """Test health check with detailed parameter"""
        mock_service.get_system_health.return_value = {
            "status": "healthy",
            "total_ips": 50
        }

        with patch('psutil.Process') as mock_process:
            mock_process.return_value.memory_info.return_value.rss = 1024 * 1024 * 100  # 100MB
            
            response = client.get('/health?detailed=true')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert 'response_time_ms' in data
            assert 'memory_usage_mb' in data
            assert data['memory_usage_mb'] == 100

    def test_healthz_endpoint(self, client, mock_service):
        """Test /healthz endpoint (Kubernetes probe)"""
        mock_service.get_system_health.return_value = {"status": "healthy"}

        response = client.get('/healthz')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'

    def test_ready_endpoint(self, client, mock_service):
        """Test /ready endpoint (Kubernetes probe)"""
        mock_service.get_system_health.return_value = {"status": "healthy"}

        response = client.get('/ready')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'

    def test_service_status_success(self, client, mock_service):
        """Test service status endpoint success"""
        mock_service.get_system_stats.return_value = {
            "total_ips": 150,
            "active_ips": 120
        }

        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['success'] is True
        assert data['data']['service_status'] == 'running'
        assert data['data']['database_connected'] is True
        assert data['data']['total_ips'] == 150
        assert data['data']['active_ips'] == 120

    def test_service_status_error(self, client, mock_service):
        """Test service status endpoint with error"""
        mock_service.get_system_stats.side_effect = Exception("Stats error")

        response = client.get('/api/health')
        
        assert response.status_code == 500
        data = response.get_json()
        
        assert 'error' in data

    def test_api_docs(self, client):
        """Test API documentation endpoint"""
        response = client.get('/api/docs')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['message'] == "API Documentation"
        assert 'api_endpoints' in data
        assert data['api_endpoints']['health'] == '/health'
        assert data['api_endpoints']['blacklist'] == '/api/blacklist/active'

    def test_get_active_blacklist_json(self, client, mock_service):
        """Test active blacklist endpoint with JSON response"""
        mock_service.get_active_blacklist_ips.return_value = ["192.168.1.1", "10.0.0.1"]

        response = client.get('/api/blacklist/active', 
                            headers={'Accept': 'application/json'})
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['success'] is True
        assert data['count'] == 2
        assert data['ips'] == ["192.168.1.1", "10.0.0.1"]
        assert 'timestamp' in data

    def test_get_active_blacklist_text(self, client, mock_service):
        """Test active blacklist endpoint with text response"""
        mock_service.get_active_blacklist_ips.return_value = ["192.168.1.1", "10.0.0.1"]

        response = client.get('/api/blacklist/active')
        
        assert response.status_code == 200
        assert 'text/plain' in response.mimetype
        assert response.get_data(as_text=True) == "192.168.1.1\n10.0.0.1"
        assert response.headers['X-Total-Count'] == '2'

    def test_get_active_blacklist_empty(self, client, mock_service):
        """Test active blacklist endpoint with empty list"""
        mock_service.get_active_blacklist_ips.return_value = []

        response = client.get('/api/blacklist/active')
        
        assert response.status_code == 200
        assert response.get_data(as_text=True) == ""
        assert response.headers['X-Total-Count'] == '0'

    def test_get_active_blacklist_error(self, client, mock_service):
        """Test active blacklist endpoint with service error"""
        mock_service.get_active_blacklist_ips.side_effect = Exception("Service error")

        response = client.get('/api/blacklist/active')
        
        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data

    def test_get_active_blacklist_txt(self, client, mock_service):
        """Test active blacklist txt download endpoint"""
        mock_service.get_active_blacklist_ips.return_value = ["192.168.1.1", "10.0.0.1"]

        response = client.get('/api/blacklist/active-txt')
        
        assert response.status_code == 200
        assert response.mimetype == 'text/plain'
        assert response.get_data(as_text=True) == "192.168.1.1\n10.0.0.1"
        assert 'attachment; filename=blacklist.txt' in response.headers['Content-Disposition']
        assert response.headers['X-Total-Count'] == '2'

    def test_get_active_blacklist_txt_error(self, client, mock_service):
        """Test active blacklist txt endpoint with error"""
        mock_service.get_active_blacklist_ips.side_effect = Exception("Service error")

        response = client.get('/api/blacklist/active-txt')
        
        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data

    def test_get_active_blacklist_simple(self, client, mock_service):
        """Test active blacklist simple endpoint"""
        mock_service.get_active_blacklist_ips.return_value = ["192.168.1.1", "10.0.0.1"]

        response = client.get('/api/blacklist/active-simple')
        
        assert response.status_code == 200
        assert response.mimetype == 'text/plain'
        assert response.get_data(as_text=True) == "192.168.1.1\n10.0.0.1"

    def test_get_active_blacklist_simple_error(self, client, mock_service):
        """Test active blacklist simple endpoint with error"""
        mock_service.get_active_blacklist_ips.side_effect = Exception("Service error")

        response = client.get('/api/blacklist/active-simple')
        
        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data

    def test_get_fortigate_simple(self, client, mock_service):
        """Test FortiGate endpoint"""
        mock_service.get_active_blacklist_ips.return_value = ["192.168.1.1", "10.0.0.1"]

        response = client.get('/api/fortigate')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['status'] == 'success'
        assert data['type'] == 'IP'
        assert data['version'] == 1
        assert data['blacklist'] == ["192.168.1.1", "10.0.0.1"]
        assert data['data'] == ["192.168.1.1", "10.0.0.1"]

    def test_get_fortigate_simple_alternative_route(self, client, mock_service):
        """Test FortiGate endpoint with alternative route"""
        mock_service.get_active_blacklist_ips.return_value = ["192.168.1.1"]

        response = client.get('/api/fortigate-simple')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['status'] == 'success'
        assert data['blacklist'] == ["192.168.1.1"]

    def test_get_fortigate_simple_error(self, client, mock_service):
        """Test FortiGate endpoint with error"""
        mock_service.get_active_blacklist_ips.side_effect = Exception("Service error")

        response = client.get('/api/fortigate')
        
        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data


class TestBlueprintConfiguration:
    """Test blueprint configuration and structure"""

    def test_blueprint_name(self):
        """Test blueprint name"""
        assert api_routes_bp.name == 'api_routes'

    def test_blueprint_url_rules(self):
        """Test that blueprint has expected URL rules"""
        # Create a temporary app to register the blueprint
        app = Flask(__name__)
        app.register_blueprint(api_routes_bp)
        
        # Get all routes
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        
        # Check expected routes exist
        expected_routes = [
            '/health',
            '/healthz', 
            '/ready',
            '/api/health',
            '/api/docs',
            '/api/blacklist/active',
            '/api/blacklist/active-txt',
            '/api/blacklist/active-simple',
            '/api/fortigate',
            '/api/fortigate-simple'
        ]
        
        for route in expected_routes:
            assert route in routes

    def test_blueprint_methods(self):
        """Test that routes have correct HTTP methods"""
        app = Flask(__name__)
        app.register_blueprint(api_routes_bp)
        
        # Check that all routes only accept GET
        for rule in app.url_map.iter_rules():
            if rule.rule.startswith('/health') or rule.rule.startswith('/api/'):
                assert 'GET' in rule.methods
                # Should not have POST, PUT, DELETE
                assert 'POST' not in rule.methods
                assert 'PUT' not in rule.methods
                assert 'DELETE' not in rule.methods


class TestServiceIntegration:
    """Test service integration and mocking"""

    @pytest.fixture
    def app(self):
        """Create test Flask app"""
        app = Flask(__name__)
        app.register_blueprint(api_routes_bp)
        app.config['TESTING'] = True
        return app

    @pytest.fixture  
    def client(self, app):
        """Create test client"""
        return app.test_client()

    def test_service_import_and_usage(self, client):
        """Test that service is properly imported and used"""
        with patch('src.core.routes.api_routes.service') as mock_service:
            mock_service.get_system_health.return_value = {"status": "healthy"}
            
            response = client.get('/health')
            
            # Verify service method was called
            mock_service.get_system_health.assert_called_once()
            assert response.status_code == 200

    def test_error_response_creation(self, client):
        """Test error response creation function usage"""
        with patch('src.core.routes.api_routes.service') as mock_service, \
             patch('src.core.routes.api_routes.create_error_response') as mock_error:
            
            mock_service.get_active_blacklist_ips.side_effect = Exception("Test error")
            mock_error.return_value = {"error": "Test error", "status": "error"}
            
            response = client.get('/api/blacklist/active')
            
            # Verify error response function was called
            mock_error.assert_called_once()
            assert response.status_code == 500

    def test_logger_usage(self):
        """Test that logger is properly configured"""
        from src.core.routes.api_routes import logger
        
        assert logger.name == 'src.core.routes.api_routes'
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'debug')