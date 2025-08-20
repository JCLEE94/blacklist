#!/usr/bin/env python3
"""
Credentials Management Module

Handles secure storage and retrieval of collection system credentials using Fernet encryption.

Sample input: source="regtech", credentials={"username": "test", "password": "pass"}
Expected output: Encrypted credentials stored securely, retrieved when needed
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class CredentialsManager:
    """Handles secure credentials storage and retrieval"""

    def __init__(
        self, credentials_file: Path, cipher_key_file: Path, security_config: Dict
    ):
        """Initialize credentials manager"""
        self.credentials_file = credentials_file
        self.cipher_key_file = cipher_key_file
        self.security_config = security_config

        # Ensure parent directories exist
        self.credentials_file.parent.mkdir(exist_ok=True)
        self.cipher_key_file.parent.mkdir(exist_ok=True)

        # Initialize encryption
        self.cipher_key = self._get_or_create_cipher_key()
        self.cipher = Fernet(self.cipher_key)

    def _get_or_create_cipher_key(self) -> bytes:
        """Generate or load encryption key"""
        if self.cipher_key_file.exists():
            return self.cipher_key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            self.cipher_key_file.write_bytes(key)
            # Set permissions from security config
            permissions = self.security_config.get("cipher_key_permissions", 0o600)
            self.cipher_key_file.chmod(permissions)
            logger.info(f"Generated new cipher key: {self.cipher_key_file}")
            return key

    def save_credentials(
        self,
        source: str,
        username: str,
        password: str,
        additional_fields: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Save encrypted credentials for a source"""
        try:
            # Load existing credentials
            all_credentials = self._load_all_credentials()

            # Create credential entry
            credentials = {"username": username, "password": password}

            # Add additional fields if provided
            if additional_fields:
                credentials.update(additional_fields)

            # Update credentials for this source
            all_credentials[source] = credentials

            # Encrypt and save
            encrypted_data = self.cipher.encrypt(
                json.dumps(all_credentials).encode("utf-8")
            )

            # Write to file with secure permissions
            self.credentials_file.write_bytes(encrypted_data)
            permissions = self.security_config.get("credentials_permissions", 0o600)
            self.credentials_file.chmod(permissions)

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

            encrypted_data = self.credentials_file.read_bytes()
            decrypted_data = self.cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode("utf-8"))

        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return {}

    def get_credentials(self, source: str = "regtech") -> Optional[Dict[str, str]]:
        """Get credentials for specific source"""
        try:
            all_credentials = self._load_all_credentials()
            credentials = all_credentials.get(source)

            if not credentials:
                logger.warning(f"No credentials found for source: {source}")
                return None

            # Validate required fields
            if "username" not in credentials or "password" not in credentials:
                logger.error(f"Invalid credentials for source: {source}")
                return None

            logger.debug(f"Credentials loaded for source: {source}")
            return credentials

        except Exception as e:
            logger.error(f"Failed to get credentials for {source}: {e}")
            return None

    def delete_credentials(self, source: str) -> bool:
        """Delete credentials for specific source"""
        try:
            all_credentials = self._load_all_credentials()

            if source in all_credentials:
                del all_credentials[source]

                # Save updated credentials
                encrypted_data = self.cipher.encrypt(
                    json.dumps(all_credentials).encode("utf-8")
                )
                self.credentials_file.write_bytes(encrypted_data)

                logger.info(f"Credentials deleted for source: {source}")
                return True
            else:
                logger.warning(f"No credentials to delete for source: {source}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete credentials for {source}: {e}")
            return False

    def list_sources(self) -> list:
        """List all sources with stored credentials"""
        try:
            all_credentials = self._load_all_credentials()
            return list(all_credentials.keys())
        except Exception as e:
            logger.error(f"Failed to list credential sources: {e}")
            return []


if __name__ == "__main__":
    # Validation function
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        creds_file = temp_path / "test_creds.enc"
        key_file = temp_path / "test_key"
        security_config = {"credentials_permissions": 0o600}

        creds_mgr = CredentialsManager(creds_file, key_file, security_config)

        # Test 1: Save and retrieve credentials
        success = creds_mgr.save_credentials("test_source", "test_user", "test_pass")
        assert success, "Failed to save credentials"

        retrieved = creds_mgr.get_credentials("test_source")
        assert retrieved is not None, "Failed to retrieve credentials"
        assert retrieved["username"] == "test_user", "Username mismatch"

        # Test 2: List sources
        sources = creds_mgr.list_sources()
        assert "test_source" in sources, "Source not in list"

        # Test 3: Delete credentials
        deleted = creds_mgr.delete_credentials("test_source")
        assert deleted, "Failed to delete credentials"

        sources_after = creds_mgr.list_sources()
        assert "test_source" not in sources_after, "Source still in list after deletion"

        print("✅ Credentials manager validation complete")
