"""
Comprehensive tests for src/web/api_routes.py
Tests all API endpoints and functionality with high coverage
"""
import json
import tempfile
import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
from datetime import datetime
from pathlib import Path
from flask import Flask, Blueprint

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.web.api_routes import (
    api_bp,
    get_stats,
    api_search,
    refresh_data,
    get_month_details,
    get_daily_ips,
    download_daily_ips,
    export_data,
    api_stats_simple
)


class TestApiBlueprint:
    """Test the API blueprint creation and structure"""

    def test_blueprint_creation(self):
        """Test that api_bp is properly created"""
        assert isinstance(api_bp, Blueprint)
        assert api_bp.name == 'api'
        assert api_bp.url_prefix == '/api'

    def test_blueprint_routes_registered(self):
        """Test that all expected routes are registered"""
        # Get all registered routes for the blueprint
        routes = []
        for rule in api_bp.url_map.iter_rules():
            routes.append(rule.rule)
        
        # Should have routes registered (though URL map might be empty until app registration)
        assert api_bp.deferred_functions  # Should have deferred route registrations


class TestGetStats:
    """Test the get_stats function"""

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_stats_file_exists(self, mock_file, mock_exists):
        """Test get_stats when stats file exists"""
        mock_exists.return_value = True
        mock_stats_data = {
            "total_ips": 1000,
            "active_ips": 500,
            "sources": {"REGTECH": 600, "SECUDIUM": 400},
            "last_updated": "2024-01-01T12:00:00"
        }
        mock_file.return_value.read.return_value = json.dumps(mock_stats_data)

        with patch('json.load', return_value=mock_stats_data):
            result = get_stats()
            
            assert result == mock_stats_data
            assert result['total_ips'] == 1000
            assert result['active_ips'] == 500

    @patch('pathlib.Path.exists')
    def test_get_stats_file_not_exists(self, mock_exists):
        """Test get_stats when stats file doesn't exist"""
        mock_exists.return_value = False

        result = get_stats()
        
        assert result['total_ips'] == 0
        assert result['active_ips'] == 0
        assert result['sources'] == {}
        assert 'last_updated' in result

    @patch('pathlib.Path.exists')
    @patch('builtins.open', side_effect=IOError("File read error"))
    def test_get_stats_file_read_error(self, mock_file, mock_exists):
        """Test get_stats when file read fails"""
        mock_exists.return_value = True

        result = get_stats()
        
        # Should return default stats on error
        assert result['total_ips'] == 0
        assert result['active_ips'] == 0
        assert result['sources'] == {}

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load', side_effect=json.JSONDecodeError("Invalid JSON", "", 0))
    def test_get_stats_json_decode_error(self, mock_json, mock_file, mock_exists):
        """Test get_stats when JSON parsing fails"""
        mock_exists.return_value = True

        result = get_stats()
        
        # Should return default stats on JSON error
        assert result['total_ips'] == 0
        assert result['active_ips'] == 0


class TestApiSearch:
    """Test the api_search endpoint"""

    def test_api_search_with_app(self):
        """Test api_search endpoint with Flask app context"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            # Test valid search
            response = client.post('/api/search', 
                                 json={'ip': '192.168.1.1', 'type': 'exact'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert len(data['results']) > 0
            assert data['results'][0]['ip'] == '192.168.1.1'

    def test_api_search_localhost(self):
        """Test api_search with localhost IP"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.post('/api/search', 
                                 json={'ip': '127.0.0.1', 'type': 'exact'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert len(data['results']) > 0

    def test_api_search_no_results(self):
        """Test api_search with IP that returns no results"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.post('/api/search', 
                                 json={'ip': '10.0.0.1', 'type': 'exact'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert len(data['results']) == 0

    def test_api_search_missing_ip(self):
        """Test api_search without IP parameter"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.post('/api/search', json={})
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['success'] is False
            assert 'required' in data['error']

    def test_api_search_empty_ip(self):
        """Test api_search with empty IP"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.post('/api/search', json={'ip': '   '})
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['success'] is False

    def test_api_search_no_json(self):
        """Test api_search without JSON data"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.post('/api/search')
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['success'] is False

    def test_api_search_form_data(self):
        """Test api_search with form data instead of JSON"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            # When no JSON is provided, get_json() returns None
            response = client.post('/api/search', data={'ip': '192.168.1.1'})
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['success'] is False


class TestRefreshData:
    """Test the refresh_data endpoint"""

    def test_refresh_data_success(self):
        """Test successful data refresh"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.post('/api/refresh-data')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'refresh completed' in data['message']
            assert 'timestamp' in data


class TestGetMonthDetails:
    """Test the get_month_details endpoint"""

    def test_get_month_details_success(self):
        """Test successful month details retrieval"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.get('/api/month/2024-01')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['data']['month'] == '2024-01'
            assert data['data']['total_ips'] == 1500
            assert 'daily_breakdown' in data['data']

    def test_get_month_details_daily_breakdown(self):
        """Test month details daily breakdown structure"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.get('/api/month/2024-02')
            
            data = response.get_json()
            daily_breakdown = data['data']['daily_breakdown']
            
            assert len(daily_breakdown) == 28  # Simplified to 28 days
            assert all('date' in day for day in daily_breakdown)
            assert all('count' in day for day in daily_breakdown)

    @patch('datetime.datetime.strptime', side_effect=ValueError("Invalid date"))
    def test_get_month_details_invalid_date(self, mock_strptime):
        """Test month details with invalid date format"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.get('/api/month/invalid-date')
            
            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False


class TestGetDailyIps:
    """Test the get_daily_ips endpoint"""

    def test_get_daily_ips_success(self):
        """Test successful daily IPs retrieval"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.get('/api/month/2024-01/daily/2024-01-15')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['date'] == '2024-01-15'
            assert data['count'] == 50
            assert len(data['ips']) == 50

    def test_get_daily_ips_structure(self):
        """Test daily IPs data structure"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.get('/api/month/2024-01/daily/2024-01-01')
            
            data = response.get_json()
            ips = data['ips']
            
            # Check structure of first IP entry
            first_ip = ips[0]
            assert 'ip' in first_ip
            assert 'source' in first_ip
            assert 'country' in first_ip
            assert 'attack_type' in first_ip
            assert 'detection_date' in first_ip
            
            # Check variety in sources and attack types
            sources = set(ip['source'] for ip in ips)
            assert 'REGTECH' in sources or 'SECUDIUM' in sources


class TestDownloadDailyIps:
    """Test the download_daily_ips endpoint"""

    @patch('src.web.api_routes.get_daily_ips')
    def test_download_daily_ips_success(self, mock_get_daily):
        """Test successful daily IPs download"""
        # Mock get_daily_ips response
        mock_response = Mock()
        mock_response.get_json.return_value = {
            'success': True,
            'ips': [
                {'ip': '192.168.1.1', 'source': 'REGTECH', 'attack_type': 'Malware'},
                {'ip': '192.168.1.2', 'source': 'SECUDIUM', 'attack_type': 'Phishing'}
            ]
        }
        mock_get_daily.return_value = mock_response

        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.get('/api/month/2024-01/daily/2024-01-01/download')
            
            assert response.status_code == 200
            assert response.mimetype == 'text/plain'
            assert 'attachment' in response.headers['Content-Disposition']

    @patch('src.web.api_routes.get_daily_ips')
    def test_download_daily_ips_get_data_failure(self, mock_get_daily):
        """Test download when getting daily data fails"""
        # Mock failed get_daily_ips response
        mock_response = Mock()
        mock_response.get_json.return_value = {'success': False}
        mock_get_daily.return_value = mock_response

        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.get('/api/month/2024-01/daily/2024-01-01/download')
            
            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False

    @patch('src.web.api_routes.get_daily_ips', side_effect=Exception("Download error"))
    def test_download_daily_ips_exception(self, mock_get_daily):
        """Test download when exception occurs"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.get('/api/month/2024-01/daily/2024-01-01/download')
            
            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False


class TestExportData:
    """Test the export_data endpoint"""

    @patch('src.web.api_routes.get_stats')
    def test_export_data_json(self, mock_get_stats):
        """Test JSON export"""
        mock_stats = {
            'total_ips': 1000,
            'sources': {'REGTECH': 600, 'SECUDIUM': 400}
        }
        mock_get_stats.return_value = mock_stats

        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.get('/api/export/json')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['data'] == mock_stats

    @patch('src.web.api_routes.get_stats')
    def test_export_data_csv(self, mock_get_stats):
        """Test CSV export"""
        mock_stats = {
            'total_ips': 1000,
            'sources': {'REGTECH': 600, 'SECUDIUM': 400}
        }
        mock_get_stats.return_value = mock_stats

        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.get('/api/export/csv')
            
            assert response.status_code == 200
            assert response.mimetype == 'text/csv'
            assert 'attachment' in response.headers['Content-Disposition']
            
            # Check CSV content structure
            content = response.get_data(as_text=True)
            lines = content.strip().split('\n')
            assert 'Source,Count,Percentage' in lines[0]

    @patch('src.web.api_routes.get_stats')
    def test_export_data_csv_zero_total(self, mock_get_stats):
        """Test CSV export with zero total IPs"""
        mock_stats = {
            'total_ips': 0,
            'sources': {'REGTECH': 0, 'SECUDIUM': 0}
        }
        mock_get_stats.return_value = mock_stats

        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.get('/api/export/csv')
            
            assert response.status_code == 200
            content = response.get_data(as_text=True)
            # Should handle division by zero gracefully
            assert '0%' in content

    def test_export_data_unsupported_format(self):
        """Test export with unsupported format"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.get('/api/export/xml')
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['success'] is False
            assert 'Unsupported format' in data['error']

    @patch('src.web.api_routes.get_stats', side_effect=Exception("Export error"))
    def test_export_data_exception(self, mock_get_stats):
        """Test export when exception occurs"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.get('/api/export/json')
            
            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False


class TestApiStatsSimple:
    """Test the api_stats_simple endpoint"""

    @patch('src.web.api_routes.get_stats')
    def test_api_stats_simple_success(self, mock_get_stats):
        """Test successful simple stats retrieval"""
        mock_stats = {
            'total_ips': 1500,
            'active_ips': 800,
            'sources': {'REGTECH': 600, 'SECUDIUM': 400, 'OTHER': 300},
            'last_updated': '2024-01-01T12:00:00'
        }
        mock_get_stats.return_value = mock_stats

        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.get('/api/stats-simple')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['total'] == 1500
            assert data['active'] == 800
            assert data['sources'] == 3  # Number of sources
            assert data['last_update'] == '2024-01-01T12:00:00'

    @patch('src.web.api_routes.get_stats')
    def test_api_stats_simple_empty_stats(self, mock_get_stats):
        """Test simple stats with empty data"""
        mock_stats = {
            'total_ips': 0,
            'active_ips': 0,
            'sources': {},
            'last_updated': None
        }
        mock_get_stats.return_value = mock_stats

        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.get('/api/stats-simple')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['total'] == 0
            assert data['active'] == 0
            assert data['sources'] == 0

    @patch('src.web.api_routes.get_stats', side_effect=Exception("Stats error"))
    def test_api_stats_simple_exception(self, mock_get_stats):
        """Test simple stats when exception occurs"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.get('/api/stats-simple')
            
            assert response.status_code == 500
            data = response.get_json()
            
            assert data['total'] == 0
            assert data['active'] == 0
            assert data['sources'] == 0
            assert 'error' in data


class TestLogging:
    """Test logging functionality in routes"""

    @patch('src.web.api_routes.logger')
    def test_error_logging_in_get_stats(self, mock_logger):
        """Test that errors are logged in get_stats"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', side_effect=IOError("Test error")):
            
            get_stats()
            mock_logger.error.assert_called_once()

    @patch('src.web.api_routes.logger')
    def test_error_logging_in_api_search(self, mock_logger):
        """Test error logging in api_search"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with patch('src.web.api_routes.request') as mock_request:
            mock_request.get_json.side_effect = Exception("Request error")
            
            with app.test_client() as client:
                response = client.post('/api/search')
                
                # Should log error and return 500
                mock_logger.error.assert_called()


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_malformed_json_request(self):
        """Test handling of malformed JSON requests"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.post('/api/search', 
                                 data='{"invalid": json}',
                                 content_type='application/json')
            
            # Should handle malformed JSON gracefully
            assert response.status_code in [400, 500]

    def test_very_long_ip_address(self):
        """Test handling of very long IP address strings"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        long_ip = 'x' * 1000  # Very long string
        
        with app.test_client() as client:
            response = client.post('/api/search', json={'ip': long_ip})
            
            # Should handle gracefully without crashing
            assert response.status_code in [200, 400]

    def test_unicode_in_search(self):
        """Test handling of unicode characters in search"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)
        
        with app.test_client() as client:
            response = client.post('/api/search', json={'ip': '🚀192.168.1.1🚀'})
            
            # Should handle unicode gracefully
            assert response.status_code in [200, 400]


if __name__ == '__main__':
    pytest.main([__file__])