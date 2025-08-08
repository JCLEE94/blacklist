"""
Mock services for comprehensive testing
Provides realistic mock implementations for external services
"""
import json
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, MagicMock
import pandas as pd


class MockREGTECHCollector:
    """Mock REGTECH data collector with realistic behavior"""
    
    def __init__(self):
        self.session_active = False
        self.login_attempts = 0
        self.max_login_attempts = 3
        self.sample_data = [
            "192.168.1.100", "192.168.1.101", "192.168.1.102",
            "10.0.0.100", "10.0.0.101", "203.0.113.100",
            "198.51.100.100", "198.51.100.101"
        ]
    
    def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """Mock authentication with realistic failure scenarios"""
        self.login_attempts += 1
        
        if self.login_attempts > self.max_login_attempts:
            return {
                "success": False,
                "error": "Too many login attempts",
                "retry_after": 300
            }
        
        if username == "test_regtech" and password == "test_pass":
            self.session_active = True
            return {
                "success": True,
                "session_id": "mock_session_123",
                "expires": datetime.now() + timedelta(hours=1)
            }
        
        return {
            "success": False,
            "error": "Invalid credentials",
            "attempts_remaining": self.max_login_attempts - self.login_attempts
        }
    
    def collect_data(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Mock data collection with realistic response"""
        if not self.session_active:
            return {
                "success": False,
                "error": "Authentication required"
            }
        
        # Simulate collection delay
        import time
        time.sleep(0.1)  # Small delay to simulate network
        
        return {
            "success": True,
            "data": self.sample_data[:5],  # Return subset
            "count": 5,
            "start_date": start_date or "2024-01-01",
            "end_date": end_date or datetime.now().strftime("%Y-%m-%d"),
            "message": "Mock collection successful"
        }
    
    def collect_from_web(self, **kwargs) -> List[str]:
        """Mock web-based collection"""
        if not self.session_active:
            raise Exception("Authentication required")
        
        return self.sample_data[:3]
    
    def logout(self):
        """Mock logout"""
        self.session_active = False
        self.login_attempts = 0


class MockSECUDIUMCollector:
    """Mock SECUDIUM data collector with realistic behavior"""
    
    def __init__(self):
        self.authenticated = False
        self.bearer_token = None
        self.sample_data = [
            "172.16.1.100", "172.16.1.101", "172.16.1.102",
            "192.168.2.100", "192.168.2.101", "10.1.1.100"
        ]
    
    def login(self, username: str, password: str, is_expire: str = 'N') -> Dict[str, Any]:
        """Mock login with bearer token"""
        if username == "test_secudium" and password == "test_pass":
            self.authenticated = True
            self.bearer_token = "mock_bearer_token_456"
            return {
                "success": True,
                "token": self.bearer_token,
                "expires": datetime.now() + timedelta(hours=2)
            }
        
        return {
            "success": False,
            "error": "Invalid credentials"
        }
    
    def collect_data(self, **kwargs) -> Dict[str, Any]:
        """Mock data collection from bulletin board"""
        if not self.authenticated:
            return {
                "success": False,
                "error": "Authentication required"
            }
        
        # Create mock Excel-like data
        mock_df = pd.DataFrame({
            'IP Address': self.sample_data[:4],
            'Detection Date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04'],
            'Severity': ['High', 'Medium', 'Low', 'Critical'],
            'Category': ['Malware', 'Spam', 'Suspicious', 'Botnet']
        })
        
        return {
            "success": True,
            "data": self.sample_data[:4],
            "count": 4,
            "dataframe": mock_df,
            "message": "Mock SECUDIUM collection successful"
        }


class MockCacheManager:
    """Mock cache manager with realistic behavior"""
    
    def __init__(self):
        self.cache = {}
        self.call_log = []
        self.connected = True
    
    def get(self, key: str) -> Any:
        """Get value from cache"""
        self.call_log.append(('get', key))
        if not self.connected:
            raise Exception("Cache connection failed")
        return self.cache.get(key)
    
    def set(self, key: str, value: Any, ttl: int = None, timeout: int = None) -> bool:
        """Set value in cache with TTL support"""
        self.call_log.append(('set', key, value))
        if not self.connected:
            raise Exception("Cache connection failed")
        
        self.cache[key] = {
            'value': value,
            'expires': datetime.now() + timedelta(seconds=ttl or timeout or 300)
        }
        return True
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        self.call_log.append(('delete', key))
        if not self.connected:
            raise Exception("Cache connection failed")
        
        return self.cache.pop(key, None) is not None
    
    def clear(self) -> bool:
        """Clear all cache"""
        self.call_log.append(('clear',))
        self.cache.clear()
        return True
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        return key in self.cache
    
    def disconnect(self):
        """Simulate connection failure"""
        self.connected = False
    
    def reconnect(self):
        """Simulate connection recovery"""
        self.connected = True


class MockDatabaseManager:
    """Mock database manager for testing"""
    
    def __init__(self):
        self.data = {}
        self.tables = {
            'blacklist': [],
            'auth_attempts': [],
            'collection_logs': [],
            'collection_config': []
        }
        self.connected = True
    
    def execute(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute mock query"""
        if not self.connected:
            raise Exception("Database connection failed")
        
        # Simple mock implementation
        if "SELECT" in query.upper():
            table = self._extract_table_name(query)
            return self.tables.get(table, [])
        elif "INSERT" in query.upper():
            table = self._extract_table_name(query)
            if table in self.tables:
                # Mock insert
                record = {"id": len(self.tables[table]) + 1}
                if params:
                    record.update(dict(enumerate(params)))
                self.tables[table].append(record)
        
        return []
    
    def _extract_table_name(self, query: str) -> str:
        """Extract table name from query (simplified)"""
        query_upper = query.upper()
        for table in self.tables.keys():
            if table.upper() in query_upper:
                return table
        return 'unknown'
    
    def disconnect(self):
        """Simulate connection failure"""
        self.connected = False
    
    def reconnect(self):
        """Simulate connection recovery"""
        self.connected = True


class MockFileSystemManager:
    """Mock file system for testing file operations"""
    
    def __init__(self):
        self.files = {}
        self.temp_dir = tempfile.mkdtemp()
    
    def create_temp_file(self, content: str, suffix: str = '.txt') -> str:
        """Create temporary file with content"""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix=suffix, delete=False, dir=self.temp_dir
        )
        temp_file.write(content)
        temp_file.close()
        
        self.files[temp_file.name] = content
        return temp_file.name
    
    def create_excel_file(self, data: List[Dict], filename: str = None) -> str:
        """Create mock Excel file"""
        if not filename:
            filename = tempfile.mktemp(suffix='.xlsx', dir=self.temp_dir)
        
        # Create DataFrame and save as Excel
        df = pd.DataFrame(data)
        df.to_excel(filename, index=False)
        
        self.files[filename] = data
        return filename
    
    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)


def create_mock_container() -> Mock:
    """Create comprehensive mock container with all services"""
    container = Mock()
    
    # Mock services
    mock_regtech = MockREGTECHCollector()
    mock_secudium = MockSECUDIUMCollector()
    mock_cache = MockCacheManager()
    mock_db = MockDatabaseManager()
    mock_fs = MockFileSystemManager()
    
    # Mock unified service
    mock_unified_service = Mock()
    mock_unified_service.collection_enabled = True
    mock_unified_service.daily_collection_enabled = True
    mock_unified_service.get_collection_status.return_value = {
        'enabled': True,
        'collection_enabled': True,
        'last_update': datetime.now().isoformat(),
        'sources': {
            'regtech': {'status': 'active', 'last_success': datetime.now().isoformat()},
            'secudium': {'status': 'active', 'last_success': datetime.now().isoformat()}
        },
        'protection': {'enabled': False, 'bypass_active': True}
    }
    
    # Mock blacklist manager
    mock_blacklist_manager = Mock()
    mock_blacklist_manager.get_active_ips.return_value = mock_regtech.sample_data + mock_secudium.sample_data
    mock_blacklist_manager.add_ip.return_value = True
    mock_blacklist_manager.remove_ip.return_value = True
    
    # Mock collection manager
    mock_collection_manager = Mock()
    mock_collection_manager.collection_enabled = True
    mock_collection_manager.enable_collection.return_value = {
        "success": True,
        "enabled": True,
        "message": "수집이 활성화되었습니다."
    }
    mock_collection_manager.disable_collection.return_value = {
        "success": True,
        "enabled": False,
        "message": "수집이 비활성화되었습니다."
    }
    mock_collection_manager.get_collection_status.return_value = mock_unified_service.get_collection_status.return_value
    
    # Configure container get method
    services = {
        'regtech_collector': mock_regtech,
        'secudium_collector': mock_secudium,
        'cache_manager': mock_cache,
        'cache': mock_cache,
        'database_manager': mock_db,
        'filesystem_manager': mock_fs,
        'unified_service': mock_unified_service,
        'blacklist_manager': mock_blacklist_manager,
        'collection_manager': mock_collection_manager
    }
    
    def mock_get(service_name):
        return services.get(service_name, Mock())
    
    container.get.side_effect = mock_get
    
    # Store references for test access
    container._mock_services = services
    container._mock_regtech = mock_regtech
    container._mock_secudium = mock_secudium
    container._mock_cache = mock_cache
    container._mock_db = mock_db
    container._mock_fs = mock_fs
    
    return container


def create_sample_test_data() -> Dict[str, Any]:
    """Create comprehensive sample test data"""
    return {
        'sample_ips': [
            "192.168.1.100", "192.168.1.101", "192.168.1.102",
            "10.0.0.100", "10.0.0.101", "172.16.1.100",
            "203.0.113.100", "198.51.100.100"
        ],
        'blacklist_data': [
            {
                'ip': '192.168.1.100',
                'source': 'REGTECH',
                'detection_date': '2024-01-01',
                'metadata': {'severity': 'high', 'category': 'malware'}
            },
            {
                'ip': '10.0.0.100',
                'source': 'SECUDIUM',
                'detection_date': '2024-01-02',
                'metadata': {'severity': 'medium', 'category': 'spam'}
            }
        ],
        'collection_logs': [
            {
                'source': 'REGTECH',
                'status': 'success',
                'message': 'Collection completed',
                'data_count': 50,
                'duration_seconds': 30
            },
            {
                'source': 'SECUDIUM',
                'status': 'success',
                'message': 'Collection completed',
                'data_count': 75,
                'duration_seconds': 45
            }
        ],
        'auth_attempts': [
            {
                'source': 'REGTECH',
                'username': 'test_user',
                'success': True,
                'attempt_time': datetime.now(),
                'ip_address': '127.0.0.1'
            },
            {
                'source': 'SECUDIUM',
                'username': 'test_user',
                'success': False,
                'attempt_time': datetime.now(),
                'error_message': 'Invalid credentials',
                'ip_address': '127.0.0.1'
            }
        ]
    }