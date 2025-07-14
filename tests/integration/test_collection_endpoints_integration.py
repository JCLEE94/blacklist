"""
Integration tests for collection management endpoints

These tests verify the collection management API endpoints work correctly
in an integrated environment with real services and database interactions.
"""
import pytest
import json
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from src.core.unified_routes import unified_bp


class TestCollectionEndpointsIntegration:
    """Integration tests for collection management endpoints"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app with real configuration"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['WTF_CSRF_ENABLED'] = False
        
        # Register blueprint
        app.register_blueprint(unified_bp)
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    @pytest.fixture
    def mock_service(self):
        """Create mock service with realistic responses"""
        service = Mock()
        
        # Default responses
        service.get_collection_status.return_value = {
            'enabled': True,
            'sources': {
                'regtech': {'enabled': True, 'last_collection': None},
                'secudium': {'enabled': False, 'reason': 'Account issues'}
            },
            'last_updated': datetime.now().isoformat()
        }
        
        service.get_daily_collection_stats.return_value = [
            {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'count': 150,
                'sources': {'regtech': 150}
            },
            {
                'date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                'count': 200,
                'sources': {'regtech': 200}
            }
        ]
        
        service.get_system_health.return_value = {
            'total_ips': 1500,
            'active_ips': 1450,
            'expired_ips': 50,
            'database_status': 'healthy'
        }
        
        service.get_collection_logs.return_value = [
            {
                'timestamp': datetime.now().isoformat(),
                'source': 'regtech',
                'action': 'collection_completed',
                'details': {'ips_collected': 150}
            }
        ]
        
        service.add_collection_log.return_value = None
        
        service.trigger_regtech_collection.return_value = {
            'success': True,
            'collected': 100,
            'message': 'Successfully collected 100 IPs',
            'duration': 5.2
        }
        
        return service
    
    # ===== Collection Status Tests =====
    
    def test_collection_status_returns_always_enabled(self, client, mock_service):
        """Test that collection status always shows enabled state"""
        with patch('src.core.unified_routes.service', mock_service):
            response = client.get('/api/collection/status')
            
            assert response.status_code == 200
            data = response.get_json()
            
            # Verify structure
            assert data['enabled'] is True
            assert data['status'] == 'active'
            assert data['message'] == '수집은 항상 활성화 상태입니다'
            
            # Verify stats
            assert 'stats' in data
            assert data['stats']['total_ips'] == 1500
            assert data['stats']['active_ips'] == 1450
            assert data['stats']['today_collected'] == 150
            
            # Verify daily collection info
            assert 'daily_collection' in data
            assert data['daily_collection']['today'] == 150
            assert len(data['daily_collection']['recent_days']) >= 2
    
    def test_collection_status_handles_service_errors(self, client, mock_service):
        """Test collection status error handling"""
        mock_service.get_collection_status.side_effect = Exception("Database error")
        
        with patch('src.core.unified_routes.service', mock_service):
            response = client.get('/api/collection/status')
            
            assert response.status_code == 500
            data = response.get_json()
            
            assert data['enabled'] is False
            assert data['status'] == 'error'
            assert 'error' in data
            assert data['stats']['total_ips'] == 0
    
    # ===== Collection Enable/Disable Tests =====
    
    def test_collection_enable_is_idempotent(self, client, mock_service):
        """Test that enable endpoint can be called multiple times safely"""
        with patch('src.core.unified_routes.service', mock_service):
            # Call enable multiple times
            for i in range(3):
                response = client.post('/api/collection/enable',
                                     headers={'Content-Type': 'application/json'})
                
                assert response.status_code == 200
                data = response.get_json()
                
                assert data['success'] is True
                assert data['collection_enabled'] is True
                assert data['cleared_data'] is False
                assert data['message'] == '수집은 항상 활성화 상태입니다.'
    
    def test_collection_disable_returns_warning(self, client, mock_service):
        """Test that disable endpoint returns appropriate warning"""
        with patch('src.core.unified_routes.service', mock_service):
            response = client.post('/api/collection/disable',
                                 headers={'Content-Type': 'application/json'})
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['success'] is True
            assert data['collection_enabled'] is True  # Still enabled
            assert data['warning'] == '수집 비활성화는 지원하지 않습니다.'
            assert data['message'] == '수집은 항상 활성화 상태로 유지됩니다. 비활성화할 수 없습니다.'
    
    def test_collection_enable_disable_error_handling(self, client):
        """Test error handling in enable/disable endpoints"""
        # Test without any service (simulates import error)
        response = client.post('/api/collection/enable')
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data
    
    # ===== REGTECH Collection Trigger Tests =====
    
    def test_regtech_trigger_with_date_parameters(self, client, mock_service):
        """Test REGTECH collection trigger with date range"""
        with patch('src.core.unified_routes.service', mock_service):
            # Test with JSON payload
            response = client.post('/api/collection/regtech/trigger',
                                 json={
                                     'start_date': '20250601',
                                     'end_date': '20250630'
                                 })
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['success'] is True
            assert data['source'] == 'regtech'
            assert data['message'] == 'REGTECH 수집이 트리거되었습니다.'
            assert 'data' in data
            assert data['data']['collected'] == 100
            
            # Verify service was called with correct parameters
            mock_service.trigger_regtech_collection.assert_called_with(
                start_date='20250601',
                end_date='20250630'
            )
    
    def test_regtech_trigger_with_form_data(self, client, mock_service):
        """Test REGTECH collection trigger with form data"""
        with patch('src.core.unified_routes.service', mock_service):
            # Test with form data
            response = client.post('/api/collection/regtech/trigger',
                                 data={
                                     'start_date': '20250701',
                                     'end_date': '20250731'
                                 })
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['success'] is True
            assert data['source'] == 'regtech'
            
            # Verify service was called with form data
            mock_service.trigger_regtech_collection.assert_called_with(
                start_date='20250701',
                end_date='20250731'
            )
    
    def test_regtech_trigger_without_dates(self, client, mock_service):
        """Test REGTECH collection trigger without date parameters"""
        with patch('src.core.unified_routes.service', mock_service):
            response = client.post('/api/collection/regtech/trigger')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['success'] is True
            
            # Verify service was called with None dates
            mock_service.trigger_regtech_collection.assert_called_with(
                start_date=None,
                end_date=None
            )
    
    def test_regtech_trigger_handles_collection_failure(self, client, mock_service):
        """Test REGTECH trigger when collection fails"""
        mock_service.trigger_regtech_collection.return_value = {
            'success': False,
            'message': 'Authentication failed',
            'error': 'Invalid credentials'
        }
        
        with patch('src.core.unified_routes.service', mock_service):
            response = client.post('/api/collection/regtech/trigger')
            
            assert response.status_code == 500
            data = response.get_json()
            
            assert data['success'] is False
            assert data['message'] == 'Authentication failed'
            assert data['error'] == 'Invalid credentials'
    
    def test_regtech_trigger_handles_exceptions(self, client, mock_service):
        """Test REGTECH trigger exception handling"""
        mock_service.trigger_regtech_collection.side_effect = Exception("Network error")
        
        with patch('src.core.unified_routes.service', mock_service):
            response = client.post('/api/collection/regtech/trigger')
            
            assert response.status_code == 500
            data = response.get_json()
            
            assert data['success'] is False
            assert 'Network error' in data['error']
            assert data['message'] == 'REGTECH 수집 트리거 중 오류가 발생했습니다.'
    
    # ===== SECUDIUM Collection Trigger Tests =====
    
    def test_secudium_trigger_returns_disabled_status(self, client):
        """Test that SECUDIUM trigger returns disabled status"""
        response = client.post('/api/collection/secudium/trigger',
                             headers={'Content-Type': 'application/json'})
        
        assert response.status_code == 503  # Service Unavailable
        data = response.get_json()
        
        assert data['success'] is False
        assert data['disabled'] is True
        assert data['source'] == 'secudium'
        assert data['message'] == 'SECUDIUM 수집은 현재 비활성화되어 있습니다.'
        assert data['reason'] == '계정 문제로 인해 일시적으로 사용할 수 없습니다.'
    
    def test_secudium_trigger_with_any_payload(self, client):
        """Test SECUDIUM trigger ignores payload and returns disabled"""
        response = client.post('/api/collection/secudium/trigger',
                             json={'force': True, 'test': 'data'})
        
        assert response.status_code == 503
        data = response.get_json()
        assert data['disabled'] is True
    
    # ===== Concurrent Request Tests =====
    
    def test_concurrent_collection_requests(self, client, mock_service):
        """Test handling of concurrent collection trigger requests"""
        results = []
        errors = []
        
        def make_request():
            try:
                with patch('src.core.unified_routes.service', mock_service):
                    response = client.post('/api/collection/regtech/trigger')
                    results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))
        
        # Create and start threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=make_request)
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join(timeout=5)
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10
        assert all(status == 200 for status in results)
    
    # ===== Integration with Service Layer Tests =====
    
    def test_collection_status_with_real_service_calls(self, client, mock_service):
        """Test collection status makes all expected service calls"""
        with patch('src.core.unified_routes.service', mock_service):
            response = client.get('/api/collection/status')
            
            assert response.status_code == 200
            
            # Verify all service methods were called
            mock_service.get_collection_status.assert_called_once()
            mock_service.get_daily_collection_stats.assert_called_once()
            mock_service.get_system_health.assert_called_once()
            mock_service.get_collection_logs.assert_called_once_with(limit=10)
    
    def test_regtech_trigger_logging(self, client, mock_service):
        """Test that REGTECH trigger properly logs actions"""
        with patch('src.core.unified_routes.service', mock_service):
            response = client.post('/api/collection/regtech/trigger')
            
            assert response.status_code == 200
            
            # Verify logging was called
            assert mock_service.add_collection_log.call_count >= 1
            
            # Check log parameters
            call_args = mock_service.add_collection_log.call_args_list[0]
            assert call_args[0][0] == 'regtech'  # source
            assert call_args[0][1] == 'collection_triggered'  # action
            assert 'triggered_by' in call_args[0][2]  # details
            assert call_args[0][2]['triggered_by'] == 'manual'
    
    # ===== Response Format Validation Tests =====
    
    def test_all_endpoints_return_json(self, client, mock_service):
        """Test that all endpoints return valid JSON responses"""
        with patch('src.core.unified_routes.service', mock_service):
            endpoints = [
                ('GET', '/api/collection/status'),
                ('POST', '/api/collection/enable'),
                ('POST', '/api/collection/disable'),
                ('POST', '/api/collection/regtech/trigger'),
                ('POST', '/api/collection/secudium/trigger'),
            ]
            
            for method, endpoint in endpoints:
                if method == 'GET':
                    response = client.get(endpoint)
                else:
                    response = client.post(endpoint)
                
                # Verify JSON response
                assert response.content_type == 'application/json'
                data = response.get_json()
                assert data is not None
                
                # All responses should have either 'success' or 'enabled' field
                assert 'success' in data or 'enabled' in data
    
    # ===== State Consistency Tests =====
    
    def test_collection_state_remains_consistent(self, client, mock_service):
        """Test that collection state remains consistent across operations"""
        with patch('src.core.unified_routes.service', mock_service):
            # Initial state
            response = client.get('/api/collection/status')
            initial_state = response.get_json()
            assert initial_state['enabled'] is True
            
            # Try to disable
            response = client.post('/api/collection/disable')
            assert response.status_code == 200
            
            # Check state hasn't changed
            response = client.get('/api/collection/status')
            current_state = response.get_json()
            assert current_state['enabled'] is True
            
            # Try to enable (should be idempotent)
            response = client.post('/api/collection/enable')
            assert response.status_code == 200
            
            # Final state check
            response = client.get('/api/collection/status')
            final_state = response.get_json()
            assert final_state['enabled'] is True
            assert final_state['status'] == initial_state['status']


# ===== Performance Tests =====

class TestCollectionEndpointsPerformance:
    """Performance tests for collection endpoints"""
    
    @pytest.fixture
    def app(self):
        """Create test app for performance testing"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.register_blueprint(unified_bp)
        return app
    
    @pytest.fixture
    def client(self, app):
        return app.test_client()
    
    def test_collection_status_response_time(self, client):
        """Test that collection status responds within acceptable time"""
        mock_service = Mock()
        mock_service.get_collection_status.return_value = {'enabled': True}
        mock_service.get_daily_collection_stats.return_value = []
        mock_service.get_system_health.return_value = {'total_ips': 0, 'active_ips': 0}
        mock_service.get_collection_logs.return_value = []
        
        with patch('src.core.unified_routes.service', mock_service):
            start_time = time.time()
            response = client.get('/api/collection/status')
            duration = time.time() - start_time
            
            assert response.status_code == 200
            assert duration < 0.1  # Should respond in less than 100ms
    
    def test_multiple_rapid_requests(self, client):
        """Test handling of multiple rapid requests"""
        mock_service = Mock()
        mock_service.trigger_regtech_collection.return_value = {'success': True}
        mock_service.add_collection_log.return_value = None
        
        with patch('src.core.unified_routes.service', mock_service):
            start_time = time.time()
            
            # Send 50 requests rapidly
            for i in range(50):
                response = client.post('/api/collection/regtech/trigger')
                assert response.status_code == 200
            
            duration = time.time() - start_time
            
            # Should handle 50 requests in reasonable time
            assert duration < 5.0  # Less than 5 seconds for 50 requests
            
            # Verify all requests were processed
            assert mock_service.trigger_regtech_collection.call_count == 50


# ===== Edge Case Tests =====

class TestCollectionEndpointsEdgeCases:
    """Edge case tests for collection endpoints"""
    
    @pytest.fixture
    def app(self):
        """Create test app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.register_blueprint(unified_bp)
        return app
    
    @pytest.fixture
    def client(self, app):
        return app.test_client()
    
    def test_malformed_json_handling(self, client):
        """Test handling of malformed JSON in requests"""
        # Send invalid JSON
        response = client.post('/api/collection/regtech/trigger',
                             data='{"invalid": json}',
                             headers={'Content-Type': 'application/json'})
        
        # Should still handle gracefully (form data fallback)
        assert response.status_code in [200, 500]
    
    def test_empty_request_handling(self, client):
        """Test handling of empty requests"""
        mock_service = Mock()
        mock_service.trigger_regtech_collection.return_value = {'success': True}
        mock_service.add_collection_log.return_value = None
        
        with patch('src.core.unified_routes.service', mock_service):
            # Empty POST request
            response = client.post('/api/collection/regtech/trigger',
                                 data='',
                                 headers={'Content-Type': 'application/json'})
            
            assert response.status_code == 200
            
            # Verify called with None values
            mock_service.trigger_regtech_collection.assert_called_with(
                start_date=None,
                end_date=None
            )
    
    def test_large_date_range_handling(self, client):
        """Test handling of very large date ranges"""
        mock_service = Mock()
        mock_service.trigger_regtech_collection.return_value = {'success': True}
        mock_service.add_collection_log.return_value = None
        
        with patch('src.core.unified_routes.service', mock_service):
            # Request 10 years of data
            response = client.post('/api/collection/regtech/trigger',
                                 json={
                                     'start_date': '20150101',
                                     'end_date': '20250101'
                                 })
            
            assert response.status_code == 200
            
            # Service should still be called
            mock_service.trigger_regtech_collection.assert_called_once()
    
    def test_special_characters_in_parameters(self, client):
        """Test handling of special characters in parameters"""
        mock_service = Mock()
        mock_service.trigger_regtech_collection.return_value = {'success': True}
        mock_service.add_collection_log.return_value = None
        
        with patch('src.core.unified_routes.service', mock_service):
            # Special characters in dates
            response = client.post('/api/collection/regtech/trigger',
                                 json={
                                     'start_date': '2025-06-01',  # With dashes
                                     'end_date': '2025/06/30'      # With slashes
                                 })
            
            assert response.status_code == 200
            
            # Verify service received the values as-is
            mock_service.trigger_regtech_collection.assert_called_with(
                start_date='2025-06-01',
                end_date='2025/06/30'
            )


if __name__ == "__main__":
    pytest.main([__file__, '-v'])