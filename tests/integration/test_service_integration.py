"""
Integration tests for service layer interactions

These tests verify that the unified service layer correctly integrates
with all dependencies including database, cache, and collectors.
"""
import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from src.core.unified_service import UnifiedBlacklistService
from src.core.container import BlacklistContainer


class TestServiceLayerIntegration:
    """Test UnifiedBlacklistService integration with all components"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        db_path = temp_file.name
        temp_file.close()
        
        # Initialize database schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blacklist_ip (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address VARCHAR(45) NOT NULL,
                source VARCHAR(50) NOT NULL,
                detection_date TIMESTAMP,
                reason TEXT,
                threat_level VARCHAR(20),
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        
        yield db_path
        
        # Cleanup
        try:
            os.unlink(db_path)
        except:
            pass
    
    @pytest.fixture
    def mock_container(self, temp_db):
        """Create mock container with test dependencies"""
        container = Mock(spec=BlacklistContainer)
        
        # Mock blacklist manager
        blacklist_manager = Mock()
        blacklist_manager.get_active_ips.return_value = (['1.1.1.1', '2.2.2.2'], 2)
        blacklist_manager.add_ip.return_value = True
        blacklist_manager.get_all_ips.return_value = [
            {
                'ip': '1.1.1.1',
                'source': 'regtech',
                'detection_date': datetime.now().isoformat(),
                'is_active': True
            }
        ]
        
        # Mock cache manager
        cache_manager = Mock()
        cache_manager.get.return_value = None
        cache_manager.set.return_value = True
        cache_manager.delete.return_value = True
        cache_manager.clear.return_value = True
        
        # Mock collection manager
        collection_manager = Mock()
        collection_manager.is_collection_enabled.return_value = True
        collection_manager.get_status.return_value = {
            'enabled': True,
            'sources': {'regtech': {'enabled': True}}
        }
        
        # Mock REGTECH collector
        regtech_collector = Mock()
        regtech_collector.collect_from_web.return_value = [
            {
                'ip': '3.3.3.3',
                'source': 'regtech',
                'detection_date': datetime.now(),
                'reason': 'Malicious activity'
            }
        ]
        
        # Configure container to return mocks
        container.get.side_effect = lambda key: {
            'blacklist_manager': blacklist_manager,
            'cache_manager': cache_manager,
            'collection_manager': collection_manager,
            'regtech_collector': regtech_collector,
            'db_path': temp_db
        }.get(key)
        
        container.resolve.side_effect = container.get
        
        return container
    
    @pytest.fixture
    def service(self, mock_container):
        """Create service instance with mock container"""
        with patch('src.core.unified_service.get_container', return_value=mock_container):
            service = UnifiedBlacklistService()
            service.container = mock_container
            service.blacklist_manager = mock_container.get('blacklist_manager')
            service.cache = mock_container.get('cache_manager')
            service.collection_manager = mock_container.get('collection_manager')
            service.regtech_collector = mock_container.get('regtech_collector')
            return service
    
    # ===== Service Initialization Tests =====
    
    def test_service_initialization(self, mock_container):
        """Test service initializes with all dependencies"""
        with patch('src.core.unified_service.get_container', return_value=mock_container):
            service = UnifiedBlacklistService()
            
            # Verify all components initialized
            assert service.container is not None
            assert service.blacklist_manager is not None
            assert service.cache is not None
            assert service.collection_manager is not None
    
    def test_service_handles_missing_dependencies(self):
        """Test service handles missing dependencies gracefully"""
        mock_container = Mock()
        mock_container.get.return_value = None
        
        with patch('src.core.unified_service.get_container', return_value=mock_container):
            service = UnifiedBlacklistService()
            
            # Should still initialize but with None values
            assert service.container is not None
    
    # ===== Collection Integration Tests =====
    
    def test_get_collection_status_integration(self, service):
        """Test collection status retrieves data from multiple sources"""
        status = service.get_collection_status()
        
        assert status['enabled'] is True
        assert 'sources' in status
        assert status['sources']['regtech']['enabled'] is True
        
        # Verify manager was called
        service.collection_manager.get_status.assert_called_once()
    
    def test_trigger_regtech_collection_full_flow(self, service):
        """Test complete REGTECH collection flow"""
        # Mock successful collection
        service.regtech_collector.collect_from_web.return_value = [
            {
                'ip': '10.0.0.1',
                'source': 'regtech',
                'detection_date': datetime.now(),
                'reason': 'Threat detected'
            },
            {
                'ip': '10.0.0.2',
                'source': 'regtech',
                'detection_date': datetime.now(),
                'reason': 'Malicious'
            }
        ]
        
        # Trigger collection
        result = service.trigger_regtech_collection(
            start_date='20250601',
            end_date='20250630'
        )
        
        # Verify success
        assert result['success'] is True
        assert result['collected'] == 2
        assert 'Collection completed' in result['message']
        
        # Verify collector was called with dates
        service.regtech_collector.collect_from_web.assert_called_with(
            start_date='20250601',
            end_date='20250630'
        )
        
        # Verify IPs were added to blacklist
        assert service.blacklist_manager.add_ip.call_count == 2
        
        # Verify cache was cleared
        service.cache.delete.assert_called()
    
    def test_trigger_regtech_collection_with_errors(self, service):
        """Test REGTECH collection error handling"""
        # Mock collection failure
        service.regtech_collector.collect_from_web.side_effect = Exception("Network error")
        
        result = service.trigger_regtech_collection()
        
        assert result['success'] is False
        assert 'error' in result
        assert 'Network error' in result['error']
    
    def test_trigger_regtech_collection_partial_success(self, service):
        """Test handling of partial collection success"""
        # Mock some IPs failing to add
        service.blacklist_manager.add_ip.side_effect = [True, False, True]
        service.regtech_collector.collect_from_web.return_value = [
            {'ip': '1.1.1.1', 'source': 'regtech', 'detection_date': datetime.now()},
            {'ip': '2.2.2.2', 'source': 'regtech', 'detection_date': datetime.now()},
            {'ip': '3.3.3.3', 'source': 'regtech', 'detection_date': datetime.now()},
        ]
        
        result = service.trigger_regtech_collection()
        
        # Should still report success but with correct count
        assert result['success'] is True
        assert result['collected'] == 2  # Only 2 succeeded
    
    # ===== Cache Integration Tests =====
    
    def test_cache_invalidation_on_collection(self, service):
        """Test cache is properly invalidated after collection"""
        # Set some cache values
        service.cache.get.return_value = {'cached': 'data'}
        
        # Trigger collection
        service.trigger_regtech_collection()
        
        # Verify cache operations
        cache_calls = service.cache.delete.call_args_list
        assert len(cache_calls) > 0
        
        # Check specific cache keys were invalidated
        deleted_keys = [call[0][0] for call in cache_calls]
        assert any('active_ips' in key for key in deleted_keys)
        assert any('fortigate' in key for key in deleted_keys)
    
    def test_cache_fallback_behavior(self, service):
        """Test service behavior when cache is unavailable"""
        # Make cache raise errors
        service.cache.get.side_effect = Exception("Redis connection failed")
        service.cache.set.side_effect = Exception("Redis connection failed")
        
        # Service should still function
        status = service.get_system_health()
        assert 'total_ips' in status
        assert 'active_ips' in status
        
        # Data should come from blacklist manager
        service.blacklist_manager.get_all_ips.assert_called()
    
    # ===== Database Integration Tests =====
    
    def test_database_transaction_handling(self, service, temp_db):
        """Test database transaction handling during collection"""
        # Create real database connection
        conn = sqlite3.connect(temp_db)
        
        # Mock blacklist manager to use real DB operations
        def add_ip_to_db(ip_data):
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO blacklist_ip (ip_address, source, detection_date, reason)
                VALUES (?, ?, ?, ?)
            """, (ip_data['ip'], ip_data['source'], ip_data['detection_date'], ip_data.get('reason')))
            conn.commit()
            return True
        
        service.blacklist_manager.add_ip.side_effect = add_ip_to_db
        
        # Trigger collection
        result = service.trigger_regtech_collection()
        
        # Verify data in database
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM blacklist_ip")
        count = cursor.fetchone()[0]
        
        assert count > 0
        assert result['success'] is True
        
        conn.close()
    
    # ===== Health Check Integration Tests =====
    
    def test_system_health_aggregates_all_components(self, service):
        """Test system health check aggregates data from all components"""
        # Mock various component states
        service.blacklist_manager.get_all_ips.return_value = [
            {'ip': '1.1.1.1', 'is_active': True},
            {'ip': '2.2.2.2', 'is_active': True},
            {'ip': '3.3.3.3', 'is_active': False}
        ]
        
        health = service.get_system_health()
        
        assert health['total_ips'] == 3
        assert health['active_ips'] == 2
        assert health['status'] == 'healthy'
        assert 'database' in health
        assert 'cache' in health
        assert 'collection' in health
    
    def test_system_health_reports_unhealthy_state(self, service):
        """Test system health reports issues correctly"""
        # Make database fail
        service.blacklist_manager.get_all_ips.side_effect = Exception("DB Error")
        
        health = service.get_system_health()
        
        assert health['status'] == 'degraded'
        assert health['total_ips'] == 0
        assert 'issues' in health
        assert any('database' in issue for issue in health['issues'])
    
    # ===== Logging Integration Tests =====
    
    def test_collection_logging_integration(self, service):
        """Test collection events are properly logged"""
        # Track log entries
        service.collection_logs = []
        
        # Trigger collection
        service.trigger_regtech_collection()
        
        # Verify logs were created
        assert len(service.collection_logs) > 0
        
        # Check log structure
        log = service.collection_logs[0]
        assert 'timestamp' in log
        assert 'source' in log
        assert log['source'] == 'regtech'
        assert 'action' in log
        assert 'details' in log
    
    def test_error_logging_integration(self, service):
        """Test errors are properly logged"""
        service.collection_logs = []
        
        # Cause an error
        service.regtech_collector.collect_from_web.side_effect = Exception("Test error")
        
        result = service.trigger_regtech_collection()
        
        # Should have error log
        assert len(service.collection_logs) > 0
        error_logs = [log for log in service.collection_logs if 'error' in log.get('details', {})]
        assert len(error_logs) > 0
    
    # ===== Performance Integration Tests =====
    
    def test_bulk_operation_performance(self, service):
        """Test performance of bulk IP operations"""
        # Generate large number of IPs
        large_ip_list = [
            {
                'ip': f'10.0.{i//256}.{i%256}',
                'source': 'regtech',
                'detection_date': datetime.now(),
                'reason': 'Bulk test'
            }
            for i in range(1000)
        ]
        
        service.regtech_collector.collect_from_web.return_value = large_ip_list
        
        import time
        start_time = time.time()
        
        result = service.trigger_regtech_collection()
        
        duration = time.time() - start_time
        
        # Should handle 1000 IPs reasonably fast
        assert duration < 5.0  # Less than 5 seconds
        assert result['success'] is True
        assert result['collected'] == 1000
    
    # ===== Concurrent Access Tests =====
    
    def test_concurrent_service_access(self, service):
        """Test service handles concurrent access correctly"""
        import threading
        
        results = []
        errors = []
        
        def access_service():
            try:
                # Multiple operations
                health = service.get_system_health()
                status = service.get_collection_status()
                results.append({
                    'health': health,
                    'status': status
                })
            except Exception as e:
                errors.append(str(e))
        
        # Create threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=access_service)
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Verify no errors
        assert len(errors) == 0
        assert len(results) == 10
        
        # All results should be consistent
        assert all(r['status']['enabled'] for r in results)


class TestServiceErrorRecovery:
    """Test service error recovery and resilience"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        db_path = temp_file.name
        temp_file.close()
        
        # Initialize database schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blacklist_ip (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address VARCHAR(45) NOT NULL,
                source VARCHAR(50) NOT NULL,
                detection_date TIMESTAMP,
                reason TEXT,
                threat_level VARCHAR(20),
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        
        yield db_path
        
        # Cleanup
        try:
            os.unlink(db_path)
        except:
            pass
    
    @pytest.fixture
    def mock_container(self, temp_db):
        """Create mock container with test dependencies"""
        container = Mock(spec=BlacklistContainer)
        
        # Mock blacklist manager
        blacklist_manager = Mock()
        blacklist_manager.get_active_ips.return_value = (['1.1.1.1', '2.2.2.2'], 2)
        blacklist_manager.add_ip.return_value = True
        blacklist_manager.get_all_ips.return_value = [
            {
                'ip': '1.1.1.1',
                'source': 'REGTECH',
                'detection_date': '2025-01-01',
                'is_active': True
            }
        ]
        
        # Mock cache manager
        cache_manager = Mock()
        cache_manager.get.return_value = None
        cache_manager.set.return_value = True
        
        # Mock collection manager
        collection_manager = Mock()
        collection_manager.get_status.return_value = {
            'regtech': {'enabled': True, 'count': 1},
            'secudium': {'enabled': True, 'count': 1}
        }
        
        # Wire up container
        container.get.side_effect = lambda name: {
            'blacklist_manager': blacklist_manager,
            'cache_manager': cache_manager,
            'collection_manager': collection_manager
        }[name]
        
        return container
    
    @pytest.fixture
    def failing_service(self, mock_container):
        """Create service with components that fail intermittently"""
        # Make components fail on first call, succeed on retry
        call_counts = {'blacklist': 0, 'cache': 0}
        
        def blacklist_get_all(*args, **kwargs):
            call_counts['blacklist'] += 1
            if call_counts['blacklist'] == 1:
                raise Exception("Temporary DB error")
            return []
        
        def cache_get(*args, **kwargs):
            call_counts['cache'] += 1
            if call_counts['cache'] == 1:
                raise Exception("Temporary cache error")
            return None
        
        mock_container.get('blacklist_manager').get_all_ips.side_effect = blacklist_get_all
        mock_container.get('cache_manager').get.side_effect = cache_get
        
        with patch('src.core.unified_service.get_container', return_value=mock_container):
            return UnifiedBlacklistService()
    
    def test_service_recovers_from_transient_errors(self, failing_service):
        """Test service recovers from transient errors"""
        # First call might fail
        health1 = failing_service.get_system_health()
        
        # Second call should succeed
        health2 = failing_service.get_system_health()
        
        # At least one should be successful
        assert health1['status'] == 'healthy' or health2['status'] == 'healthy'
    
    def test_service_degrades_gracefully(self, mock_container):
        """Test service degrades gracefully when components fail"""
        # Make all components fail
        mock_container.get('blacklist_manager').get_all_ips.side_effect = Exception("DB down")
        mock_container.get('cache_manager').get.side_effect = Exception("Cache down")
        mock_container.get('collection_manager').get_status.side_effect = Exception("Collection down")
        
        with patch('src.core.unified_service.get_container', return_value=mock_container):
            service = UnifiedBlacklistService()
            
            # Service should still respond
            health = service.get_system_health()
            
            assert health['status'] == 'degraded'
            assert health['total_ips'] == 0
            assert len(health.get('issues', [])) > 0


if __name__ == "__main__":
    pytest.main([__file__, '-v'])