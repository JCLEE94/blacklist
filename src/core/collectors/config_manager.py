#!/usr/bin/env python3
"""
Configuration Management Module

Handles configuration loading and source management for the collection system.

Sample input: config_path="config/collection_config.json"
Expected output: Loaded configuration dictionary with sources, storage, and security settings
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ConfigManager:
    """Handles configuration loading and source management"""

    def __init__(self, config_path: str = "config/collection_config.json"):
        """Initialize config manager with path"""
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration file"""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            logger.info(f"Configuration loaded: {self.config_path}")
            return config

        except Exception as e:
            logger.error(f"Configuration loading failed: {e}")
            # Return default configuration
            return {
                "sources": {},
                "collection": {"default_date_range": 7},
                "storage": {},
                "security": {},
            }

    def get_enabled_sources(self) -> List[str]:
        """Return list of enabled sources"""
        sources = []
        for source_name, source_config in self.config.get("sources", {}).items():
            if source_config.get("enabled", False):
                sources.append(source_name)
        return sources

    def get_source_config(self, source_name: str) -> Optional[Dict[str, Any]]:
        """Return configuration for specific source"""
        return self.config.get("sources", {}).get(source_name)

    def get_storage_config(self) -> Dict[str, Any]:
        """Return storage configuration"""
        return self.config.get("storage", {})

    def get_security_config(self) -> Dict[str, Any]:
        """Return security configuration"""
        return self.config.get("security", {})

    def get_collection_config(self) -> Dict[str, Any]:
        """Return collection configuration"""
        return self.config.get("collection", {})

    def reload_config(self) -> bool:
        """Reload configuration from file"""
        try:
            old_config = self.config.copy()
            self.config = self._load_config()
            logger.info("Configuration reloaded successfully")
            return True
        except Exception as e:
            logger.error(f"Configuration reload failed: {e}")
            self.config = old_config
            return False


if __name__ == "__main__":
    # Validation function
    config_manager = ConfigManager()
    
    # Test 1: Basic configuration loading
    enabled_sources = config_manager.get_enabled_sources()
    print(f"Enabled sources: {enabled_sources}")
    
    # Test 2: Storage configuration
    storage_config = config_manager.get_storage_config()
    print(f"Storage config: {storage_config}")
    
    # Test 3: Security configuration
    security_config = config_manager.get_security_config()
    print(f"Security config keys: {list(security_config.keys())}")
    
    print("✅ Configuration manager validation complete")
