#!/usr/bin/env python3
"""
REGTECH Collector Module
Provides a unified interface for REGTECH data collection

This module consolidates authentication, data collection, and processing
into a single, easy-to-use interface while maintaining modularity.
"""

from .auth import AuthenticationManager
from .data import DataCollector
from .processing import DataProcessor


# For backward compatibility - preserve the original FixedRegtechCollector interface
class FixedRegtechCollector:
    """Fixed REGTECH collector - backward compatibility wrapper"""

    def __init__(self, username: str = None, password: str = None):
        self.auth_manager = AuthenticationManager(username, password)
        self.data_collector = None
        self.processor = DataProcessor()

        # Properties for compatibility
        self.base_url = self.auth_manager.base_url
        self.username = self.auth_manager.username
        self.password = self.auth_manager.password
        self.timeout = self.auth_manager.timeout

    @property
    def session(self):
        return self.auth_manager.get_session()

    @property
    def authenticated(self):
        return self.auth_manager.is_authenticated()

    def authenticate(self) -> bool:
        """Authenticate with REGTECH system"""
        success = self.auth_manager.authenticate()
        if success:
            # Initialize data collector with authenticated session
            session = self.auth_manager.get_session()
            self.data_collector = DataCollector(session, self.base_url)
        return success

    def collect_blacklist_data(self, start_date: str = None, end_date: str = None):
        """Collect blacklist data from REGTECH"""
        if not self.authenticated:
            if not self.authenticate():
                raise RuntimeError("Cannot collect data - authentication failed")

        if not self.data_collector:
            session = self.auth_manager.get_session()
            self.data_collector = DataCollector(session, self.base_url)

        return self.data_collector.collect_blacklist_data(start_date, end_date)

    def collect_from_web(self, target_urls=None):
        """Collect data from web pages"""
        if not self.authenticated:
            if not self.authenticate():
                raise RuntimeError("Cannot collect data - authentication failed")

        if not self.data_collector:
            session = self.auth_manager.get_session()
            self.data_collector = DataCollector(session, self.base_url)

        return self.data_collector.collect_from_web(target_urls)

    def logout(self) -> bool:
        """Logout from REGTECH system"""
        return self.auth_manager.logout()

    # Private methods for backward compatibility
    def _create_session(self):
        return self.auth_manager.create_session()

    def _check_login_success(self, response):
        return self.auth_manager.check_login_success(response)

    def _collect_from_board(self, start_date, end_date):
        if not self.data_collector:
            session = self.auth_manager.get_session()
            self.data_collector = DataCollector(session, self.base_url)
        return self.data_collector._collect_from_board(start_date, end_date)

    def _collect_from_excel(self, start_date, end_date):
        if not self.data_collector:
            session = self.auth_manager.get_session()
            self.data_collector = DataCollector(session, self.base_url)
        return self.data_collector._collect_from_excel(start_date, end_date)

    def _collect_from_api(self, start_date, end_date):
        if not self.data_collector:
            session = self.auth_manager.get_session()
            self.data_collector = DataCollector(session, self.base_url)
        return self.data_collector._collect_from_api(start_date, end_date)

    def _parse_board_page(self, html_content, source):
        return self.processor.parse_board_page(html_content, source)

    def _parse_excel_response(self, excel_content, source):
        return self.processor.parse_excel_response(excel_content, source)

    def _parse_json_response(self, json_data, source):
        return self.processor.parse_json_response(json_data, source)

    def _extract_ip_from_dict(self, data):
        return self.processor._extract_ip_from_dict(data)

    def _is_valid_ip(self, ip_str):
        return self.processor._is_valid_ip(ip_str)

    def _remove_duplicates(self, ips):
        return self.processor.remove_duplicates(ips)


# Export all important classes and functions
__all__ = [
    "FixedRegtechCollector",
    "AuthenticationManager",
    "DataCollector",
    "DataProcessor",
]
