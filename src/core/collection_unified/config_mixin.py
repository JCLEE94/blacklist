#!/usr/bin/env python3
"""
Configuration Management Mixin
Provides configuration loading and credentials management

Third-party packages:
- cryptography: https://cryptography.io/en/latest/

Sample input: configuration files, credentials
Expected output: loaded configurations, encrypted credentials
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class ConfigurationMixin:
    """Mixin for configuration management"""

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if not self.config_path.exists():
                logger.warning(f"Config file not found: {self.config_path}")
                return self._get_default_config()

            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                logger.info(f"Configuration loaded from {self.config_path}")
                return config

        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "sources": {
                "regtech": {
                    "enabled": True,
                    "base_url": "https://regtech.fsec.or.kr",
                    "timeout": 30,
                    "retry_count": 3
                }
            },
            "storage": {
                "credentials_file": "instance/credentials.enc",
                "history_file": "instance/collection_history.json",
                "cipher_key_file": "instance/.cipher_key",
                "reports_dir": "instance/reports"
            },
            "collection": {
                "default_date_range": 7,
                "max_retry_attempts": 3,
                "batch_size": 1000
            }
        }

    def _get_enabled_sources(self) -> List[str]:
        """Get list of enabled sources"""
        sources = []
        for source_name, source_config in self.config.get("sources", {}).items():
            if source_config.get("enabled", False):
                sources.append(source_name)
        return sources

    def _get_source_config(self, source_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific source"""
        return self.config.get("sources", {}).get(source_name)

    def _get_or_create_cipher_key(self) -> bytes:
        """Get or create encryption key"""
        if self.cipher_key_file.exists():
            return self.cipher_key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            self.cipher_key_file.parent.mkdir(exist_ok=True)
            self.cipher_key_file.write_bytes(key)
            self.cipher_key_file.chmod(0o600)
            return key

    def save_credentials(
        self,
        source: str,
        username: str,
        password: str,
        additional_data: Dict[str, Any] = None,
    ) -> bool:
        """Save encrypted credentials"""
        try:
            # Load existing credentials
            credentials = self._load_all_credentials()

            # Add new credentials
            credentials[source] = {
                "username": username,
                "password": password,
                "updated_at": datetime.now().isoformat(),
            }

            if additional_data:
                credentials[source].update(additional_data)

            # Encrypt and save
            encrypted_data = self.cipher.encrypt(
                json.dumps(credentials).encode()
            ).decode()

            self.credentials_file.parent.mkdir(exist_ok=True)
            with open(self.credentials_file, "w") as f:
                f.write(encrypted_data)

            logger.info(f"Credentials saved for source: {source}")
            return True

        except Exception as e:
            logger.error(f"Failed to save credentials for {source}: {e}")
            return False

    def _load_all_credentials(self) -> Dict[str, Dict[str, str]]:
        """Load all encrypted credentials"""
        try:
            if not self.credentials_file.exists():
                return {}

            with open(self.credentials_file, "r") as f:
                encrypted_data = f.read()

            if not encrypted_data.strip():
                return {}

            decrypted_data = self.cipher.decrypt(encrypted_data.encode()).decode()
            return json.loads(decrypted_data)

        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return {}

    def get_credentials(self, source: str = "regtech") -> Optional[Dict[str, str]]:
        """Get credentials for a source"""
        try:
            credentials = self._load_all_credentials()
            source_creds = credentials.get(source)
            
            if not source_creds:
                logger.warning(f"No credentials found for source: {source}")
                return None

            # Validate required fields
            if "username" not in source_creds or "password" not in source_creds:
                logger.error(f"Invalid credentials format for source: {source}")
                return None

            return source_creds

        except Exception as e:
            logger.error(f"Failed to get credentials for {source}: {e}")
            return None

    def update_source_config(self, source_name: str, config_updates: Dict[str, Any]) -> bool:
        """Update configuration for a source"""
        try:
            if "sources" not in self.config:
                self.config["sources"] = {}
            
            if source_name not in self.config["sources"]:
                self.config["sources"][source_name] = {}
            
            self.config["sources"][source_name].update(config_updates)
            
            # Save updated configuration
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Configuration updated for source: {source_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update config for {source_name}: {e}")
            return False

    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration"""
        return self.config.get("storage", {})

    def get_collection_config(self) -> Dict[str, Any]:
        """Get collection configuration"""
        return self.config.get("collection", {})

    def validate_config(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        # Check required sections
        required_sections = ["sources", "storage", "collection"]
        for section in required_sections:
            if section not in self.config:
                issues.append(f"Missing required section: {section}")
        
        # Validate sources
        sources = self.config.get("sources", {})
        if not sources:
            issues.append("No sources configured")
        
        for source_name, source_config in sources.items():
            if not isinstance(source_config, dict):
                issues.append(f"Invalid configuration for source {source_name}")
                continue
            
            # Check required source fields
            required_fields = ["enabled", "base_url"]
            for field in required_fields:
                if field not in source_config:
                    issues.append(f"Missing {field} in source {source_name}")
        
        # Validate storage paths
        storage_config = self.config.get("storage", {})
        for key, path in storage_config.items():
            if key.endswith("_file") or key.endswith("_dir"):
                path_obj = Path(path)
                if key.endswith("_dir"):
                    if not path_obj.parent.exists():
                        issues.append(f"Parent directory for {key} does not exist: {path}")
        
        return issues


if __name__ == "__main__":
    import sys
    import tempfile
    import os
    from datetime import datetime
    
    # Test configuration mixin functionality
    all_validation_failures = []
    total_tests = 0
    
    # Create a test class that uses the mixin
    class TestConfigSystem(ConfigurationMixin):
        def __init__(self, config_path):
            self.config_path = Path(config_path)
            self.config = self._load_config()
            
            # Initialize storage paths
            storage_config = self.config.get("storage", {})
            self.credentials_file = Path(storage_config.get("credentials_file", "test_credentials.enc"))
            self.cipher_key_file = Path(storage_config.get("cipher_key_file", "test_cipher_key"))
            
            # Initialize encryption
            self.cipher_key = self._get_or_create_cipher_key()
            self.cipher = Fernet(self.cipher_key)
    
    # Create temporary files for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_config:
        test_config = {
            "sources": {
                "regtech": {
                    "enabled": True,
                    "base_url": "https://regtech.fsec.or.kr",
                    "timeout": 30
                }
            },
            "storage": {
                "credentials_file": "test_credentials.enc",
                "cipher_key_file": "test_cipher_key"
            }
        }
        json.dump(test_config, tmp_config)
        test_config_path = tmp_config.name
    
    try:
        # Test 1: Configuration loading
        total_tests += 1
        try:
            config_system = TestConfigSystem(test_config_path)
            
            if "sources" not in config_system.config:
                all_validation_failures.append("Config loading: Missing sources section")
            
            enabled_sources = config_system._get_enabled_sources()
            if "regtech" not in enabled_sources:
                all_validation_failures.append("Config loading: REGTECH not in enabled sources")
                
        except Exception as e:
            all_validation_failures.append(f"Config loading: Exception occurred - {e}")
        
        # Test 2: Credentials management
        total_tests += 1
        try:
            config_system = TestConfigSystem(test_config_path)
            
            success = config_system.save_credentials("test_source", "test_user", "test_pass")
            if not success:
                all_validation_failures.append("Credentials: Save failed")
            
            retrieved_creds = config_system.get_credentials("test_source")
            if not retrieved_creds or retrieved_creds["username"] != "test_user":
                all_validation_failures.append("Credentials: Retrieve failed")
                
        except Exception as e:
            all_validation_failures.append(f"Credentials: Exception occurred - {e}")
        
        # Test 3: Configuration validation
        total_tests += 1
        try:
            config_system = TestConfigSystem(test_config_path)
            
            issues = config_system.validate_config()
            # Should have minimal issues with our test config
            if len(issues) > 2:  # Allow for some minor issues
                all_validation_failures.append(f"Config validation: Too many issues found: {len(issues)}")
                
        except Exception as e:
            all_validation_failures.append(f"Config validation: Exception occurred - {e}")
        
    finally:
        # Clean up test files
        try:
            os.unlink(test_config_path)
            if Path("test_credentials.enc").exists():
                os.unlink("test_credentials.enc")
            if Path("test_cipher_key").exists():
                os.unlink("test_cipher_key")
        except OSError:
            pass
    
    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Configuration mixin is validated and formal tests can now be written")
        sys.exit(0)
