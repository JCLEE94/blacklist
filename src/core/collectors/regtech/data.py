#!/usr/bin/env python3
"""
REGTECH Data Collection Module
Provides data collection methods from various REGTECH sources

Third-party packages:
- requests: https://docs.python-requests.org/
- bs4: https://www.crummy.com/software/BeautifulSoup/

Sample input: date ranges, collection parameters
Expected output: collected IP data, threat intelligence
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class DataCollector:
    """Handles data collection from REGTECH sources"""

    def __init__(self, session: requests.Session, base_url: str):
        self.session = session
        self.base_url = base_url
        self.timeout = 30

    def collect_blacklist_data(
        self, start_date: str = None, end_date: str = None
    ) -> List[Dict[str, Any]]:
        """
        Collect blacklist data from REGTECH

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of IP data dictionaries
        """
        # Default date range (last 7 days)
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        logger.info(f"Collecting REGTECH data from {start_date} to {end_date}")

        collected_ips = []

        # Try multiple data collection methods
        methods = [
            self._collect_from_board,
            self._collect_from_excel,
            self._collect_from_api,
        ]

        for method in methods:
            try:
                logger.info(f"Trying collection method: {method.__name__}")
                ips = method(start_date, end_date)
                if ips:
                    collected_ips.extend(ips)
                    logger.info(f"✅ {method.__name__} collected {len(ips)} IPs")
                    break  # Stop on first successful method
                else:
                    logger.info(f"❌ {method.__name__} returned no data")

            except Exception as e:
                logger.error(f"Error in {method.__name__}: {e}")
                continue

        # Remove duplicates
        from .processing import DataProcessor
        processor = DataProcessor()
        unique_ips = processor.remove_duplicates(collected_ips)
        
        logger.info(
            f"🏁 Collection completed: {len(unique_ips)} unique IPs from {len(collected_ips)} total"
        )
        
        return unique_ips

    def _collect_from_board(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Collect data from bulletin board pages"""
        collected_ips = []
        
        try:
            # URLs to check
            board_urls = [
                f"{self.base_url}/board/threat-intelligence",
                f"{self.base_url}/board/blacklist",
                f"{self.base_url}/board/security-alerts",
            ]
            
            for url in board_urls:
                try:
                    response = self.session.get(url, timeout=self.timeout)
                    if response.status_code == 200:
                        from .processing import DataProcessor
                        processor = DataProcessor()
                        ips = processor.parse_board_page(response.text, url)
                        collected_ips.extend(ips)
                        logger.info(f"Collected {len(ips)} IPs from {url}")
                except Exception as e:
                    logger.error(f"Error collecting from {url}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Board collection error: {e}")
            
        return collected_ips

    def _collect_from_excel(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Collect data from Excel downloads"""
        collected_ips = []
        
        try:
            # Excel download URLs
            excel_endpoints = [
                f"{self.base_url}/api/blacklist/export",
                f"{self.base_url}/download/threat-data",
            ]
            
            for endpoint in excel_endpoints:
                try:
                    params = {
                        "start_date": start_date,
                        "end_date": end_date,
                        "format": "excel"
                    }
                    
                    response = self.session.get(
                        endpoint, params=params, timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        # Check if it's actually Excel content
                        content_type = response.headers.get("content-type", "")
                        if "excel" in content_type or "spreadsheet" in content_type:
                            from .processing import DataProcessor
                            processor = DataProcessor()
                            ips = processor.parse_excel_response(response.content, endpoint)
                            collected_ips.extend(ips)
                            logger.info(f"Collected {len(ips)} IPs from Excel at {endpoint}")
                            
                except Exception as e:
                    logger.error(f"Error downloading Excel from {endpoint}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Excel collection error: {e}")
            
        return collected_ips

    def _collect_from_api(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Collect data from API endpoints"""
        collected_ips = []
        
        try:
            # API endpoints to try
            api_endpoints = [
                f"{self.base_url}/api/v1/blacklist",
                f"{self.base_url}/api/threat-intelligence",
                f"{self.base_url}/api/security/ips",
            ]
            
            for endpoint in api_endpoints:
                try:
                    params = {
                        "start_date": start_date,
                        "end_date": end_date,
                        "format": "json"
                    }
                    
                    response = self.session.get(
                        endpoint, params=params, timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        try:
                            json_data = response.json()
                            from .processing import DataProcessor
                            processor = DataProcessor()
                            ips = processor.parse_json_response(json_data, endpoint)
                            collected_ips.extend(ips)
                            logger.info(f"Collected {len(ips)} IPs from API at {endpoint}")
                        except ValueError as e:
                            logger.error(f"Invalid JSON from {endpoint}: {e}")
                            
                except Exception as e:
                    logger.error(f"Error calling API {endpoint}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"API collection error: {e}")
            
        return collected_ips

    def collect_from_web(
        self, target_urls: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Collect data from web pages (general method)"""
        if not target_urls:
            target_urls = [
                f"{self.base_url}/threat-intelligence",
                f"{self.base_url}/security-alerts",
                f"{self.base_url}/blacklist",
            ]
        
        collected_ips = []
        
        for url in target_urls:
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    from .processing import DataProcessor
                    processor = DataProcessor()
                    ips = processor.parse_board_page(response.text, url)
                    collected_ips.extend(ips)
                    logger.info(f"Web collection from {url}: {len(ips)} IPs")
                    
            except Exception as e:
                logger.error(f"Web collection error from {url}: {e}")
                continue
                
        return collected_ips

    def search_threat_data(
        self, query: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search for specific threat data"""
        collected_data = []
        
        try:
            search_endpoints = [
                f"{self.base_url}/search",
                f"{self.base_url}/api/search",
            ]
            
            for endpoint in search_endpoints:
                try:
                    params = {
                        "q": query,
                        "limit": limit,
                        "type": "ip"
                    }
                    
                    response = self.session.get(
                        endpoint, params=params, timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        try:
                            json_data = response.json()
                            from .processing import DataProcessor
                            processor = DataProcessor()
                            data = processor.parse_json_response(json_data, endpoint)
                            collected_data.extend(data)
                            logger.info(f"Search '{query}' from {endpoint}: {len(data)} results")
                        except ValueError:
                            # Try parsing as HTML
                            from .processing import DataProcessor
                            processor = DataProcessor()
                            data = processor.parse_board_page(response.text, endpoint)
                            collected_data.extend(data)
                            
                except Exception as e:
                    logger.error(f"Search error at {endpoint}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Search operation error: {e}")
            
        return collected_data

    def get_latest_threats(self, count: int = 50) -> List[Dict[str, Any]]:
        """Get latest threat intelligence data"""
        try:
            endpoint = f"{self.base_url}/api/latest-threats"
            params = {"count": count}
            
            response = self.session.get(endpoint, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                try:
                    json_data = response.json()
                    from .processing import DataProcessor
                    processor = DataProcessor()
                    return processor.parse_json_response(json_data, endpoint)
                except ValueError:
                    # Fallback to HTML parsing
                    from .processing import DataProcessor
                    processor = DataProcessor()
                    return processor.parse_board_page(response.text, endpoint)
                    
        except Exception as e:
            logger.error(f"Latest threats collection error: {e}")
            
        return []

    def test_endpoints(self) -> Dict[str, bool]:
        """Test various data collection endpoints"""
        endpoints_status = {}
        
        test_endpoints = [
            f"{self.base_url}/api/v1/blacklist",
            f"{self.base_url}/board/threat-intelligence",
            f"{self.base_url}/api/blacklist/export",
            f"{self.base_url}/search",
        ]
        
        for endpoint in test_endpoints:
            try:
                response = self.session.get(endpoint, timeout=10)
                endpoints_status[endpoint] = response.status_code == 200
            except Exception as e:
                endpoints_status[endpoint] = False
                logger.debug(f"Endpoint test failed for {endpoint}: {e}")
                
        return endpoints_status


if __name__ == "__main__":
    import sys
    
    # Test data collection functionality
    all_validation_failures = []
    total_tests = 0
    
    # Mock session for testing
    class MockSession:
        def get(self, url, **kwargs):
            class MockResponse:
                def __init__(self):
                    self.status_code = 200
                    self.text = "<html>Test content with 192.168.1.1</html>"
                    self.headers = {"content-type": "text/html"}
                
                def json(self):
                    return {"ips": ["192.168.1.1"], "count": 1}
                    
            return MockResponse()
    
    # Test 1: Data collector initialization
    total_tests += 1
    try:
        mock_session = MockSession()
        collector = DataCollector(mock_session, "https://test.example.com")
        
        if collector.session != mock_session:
            all_validation_failures.append("Data collector: Session not set correctly")
        
        if collector.base_url != "https://test.example.com":
            all_validation_failures.append("Data collector: Base URL not set correctly")
            
    except Exception as e:
        all_validation_failures.append(f"Data collector: Exception occurred - {e}")
    
    # Test 2: Endpoint testing
    total_tests += 1
    try:
        mock_session = MockSession()
        collector = DataCollector(mock_session, "https://test.example.com")
        
        endpoints_status = collector.test_endpoints()
        
        if not isinstance(endpoints_status, dict):
            all_validation_failures.append("Endpoint test: Result is not a dict")
        
        if len(endpoints_status) == 0:
            all_validation_failures.append("Endpoint test: No endpoints tested")
            
    except Exception as e:
        all_validation_failures.append(f"Endpoint test: Exception occurred - {e}")
    
    # Test 3: Collection method structure
    total_tests += 1
    try:
        mock_session = MockSession()
        collector = DataCollector(mock_session, "https://test.example.com")
        
        # Test method existence
        methods = ["_collect_from_board", "_collect_from_excel", "_collect_from_api"]
        for method in methods:
            if not hasattr(collector, method):
                all_validation_failures.append(f"Collection methods: Missing method '{method}'")
                
    except Exception as e:
        all_validation_failures.append(f"Collection methods: Exception occurred - {e}")
    
    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Data collection module is validated and formal tests can now be written")
        sys.exit(0)
