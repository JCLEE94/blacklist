#!/usr/bin/env python3
"""
Collection Settings Module
Provides a unified interface for collection settings management

This module consolidates configuration, database operations, and validation
into a single, easy-to-use interface while maintaining modularity.
"""

from .config import ConfigurationManager
from .operations import DatabaseOperations
from .validation import ValidationManager


# For backward compatibility - preserve the original CollectionSettingsDB
# interface
class CollectionSettingsDB:
    """Unified collection settings database - backward compatibility wrapper"""

    def __init__(self, db_path: str = "instance/blacklist.db"):
        # Initialize validation manager (which also initializes the database)
        self.validation_mgr = ValidationManager(db_path)

        # Initialize other managers with the database path and cipher
        self.config_mgr = ConfigurationManager(
            db_path, self.validation_mgr.get_cipher()
        )
        self.db_ops = DatabaseOperations(db_path)

        # Store references for compatibility
        self.db_path = self.validation_mgr.db_path
        self.cipher_key = self.validation_mgr.cipher_key
        self.cipher = self.validation_mgr.cipher

    # Configuration management methods
    def save_source_config(
        self, name: str, display_name: str, base_url: str, config, enabled: bool = True
    ) -> bool:
        return self.config_mgr.save_source_config(
            name, display_name, base_url, config, enabled
        )

    def get_source_config(self, name: str):
        return self.config_mgr.get_source_config(name)

    def get_all_sources(self):
        return self.config_mgr.get_all_sources()

    def save_credentials(self, source_name: str, username: str, password: str) -> bool:
        return self.config_mgr.save_credentials(source_name, username, password)

    def get_credentials(self, source_name: str):
        return self.config_mgr.get_credentials(source_name)

    def save_setting(self, key: str, value, description: str = "") -> bool:
        return self.config_mgr.save_setting(key, value, description)

    def get_setting(self, key: str, default=None):
        return self.config_mgr.get_setting(key, default)

    # Database operations methods
    def save_collection_result(
        self,
        source_name: str,
        success: bool,
        collected_count: int = 0,
        error_message: str = None,
        metadata=None,
    ) -> bool:
        return self.db_ops.save_collection_result(
            source_name, success, collected_count, error_message, metadata
        )

    def get_collection_statistics(self):
        return self.db_ops.get_collection_statistics()

    def get_collection_calendar(self, year: int, month: int):
        return self.db_ops.get_collection_calendar(year, month)

    def get_collection_history(
        self, source_name: str = None, limit: int = 100, offset: int = 0
    ):
        return self.db_ops.get_collection_history(source_name, limit, offset)

    # Validation and utility methods
    def validate_source_config(self, config):
        return self.validation_mgr.validate_source_config(config)

    def validate_credentials(self, credentials):
        return self.validation_mgr.validate_credentials(credentials)

    def verify_database_integrity(self):
        return self.validation_mgr.verify_database_integrity()

    def reset_database(self) -> bool:
        return self.validation_mgr.reset_database()

    # Private methods for backward compatibility
    def _get_or_create_cipher_key(self):
        return self.validation_mgr._get_or_create_cipher_key()

    def _init_tables(self):
        return self.validation_mgr._init_tables()


__all__ = [
    "CollectionSettingsDB",
    "ConfigurationManager",
    "DatabaseOperations",
    "ValidationManager",
]
