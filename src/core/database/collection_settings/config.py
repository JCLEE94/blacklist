#!/usr/bin/env python3
"""
Collection Settings Configuration Module
Provides source configuration and settings management

Third-party packages:
- cryptography: https://cryptography.io/en/latest/
- sqlite3: https://docs.python.org/3/library/sqlite3.html

Sample input: source configurations, settings
Expected output: saved/retrieved configuration data
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet


class ConfigurationManager:
    """Manages collection source configurations and settings"""

    def __init__(self, db_path: str, cipher: Fernet):
        self.db_path = Path(db_path)
        self.cipher = cipher

    def save_source_config(
        self,
        name: str,
        display_name: str,
        base_url: str,
        config: Dict[str, Any],
        enabled: bool = True,
    ) -> bool:
        """Save collection source configuration"""
        try:
            # Encrypt configuration
            config_encrypted = self.cipher.encrypt(json.dumps(config).encode()).decode()

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO collection_sources
                    (name, display_name, enabled, base_url, config_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        name,
                        display_name,
                        enabled,
                        base_url,
                        config_encrypted,
                        datetime.now(),
                    ),
                )
                conn.commit()

            return True

        except Exception as e:
            print(f"Source configuration save failed: {e}")
            return False

    def get_source_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieve collection source configuration"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM collection_sources WHERE name = ? AND enabled = 1
                """,
                    (name,),
                )
                row = cursor.fetchone()

                if row:
                    # Decrypt configuration
                    config_encrypted = row["config_json"]
                    if config_encrypted:
                        config_decrypted = self.cipher.decrypt(
                            config_encrypted.encode()
                        ).decode()
                        config = json.loads(config_decrypted)
                    else:
                        config = {}

                    return {
                        "name": row["name"],
                        "display_name": row["display_name"],
                        "enabled": bool(row["enabled"]),
                        "base_url": row["base_url"],
                        "config": config,
                    }

            return None

        except Exception as e:
            print(f"Source configuration retrieval failed: {e}")
            return None

    def get_all_sources(self) -> List[Dict[str, Any]]:
        """Retrieve all collection sources"""
        sources = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT name, display_name, enabled, base_url, updated_at
                    FROM collection_sources ORDER BY display_name
                """
                )

                for row in cursor.fetchall():
                    sources.append(
                        {
                            "name": row["name"],
                            "display_name": row["display_name"],
                            "enabled": bool(row["enabled"]),
                            "base_url": row["base_url"],
                            "updated_at": row["updated_at"],
                        }
                    )

        except Exception as e:
            print(f"Sources list retrieval failed: {e}")

        return sources

    def save_credentials(self, source_name: str, username: str, password: str) -> bool:
        """Save encrypted credentials for a source"""
        try:
            # Encrypt password
            password_encrypted = self.cipher.encrypt(password.encode()).decode()

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO collection_credentials
                    (source_name, username, password_encrypted, updated_at)
                    VALUES (?, ?, ?, ?)
                """,
                    (source_name, username, password_encrypted, datetime.now()),
                )
                conn.commit()

            return True

        except Exception as e:
            print(f"Credentials save failed: {e}")
            return False

    def get_credentials(self, source_name: str) -> Optional[Dict[str, str]]:
        """Retrieve decrypted credentials for a source"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT username, password_encrypted FROM collection_credentials
                    WHERE source_name = ?
                """,
                    (source_name,),
                )
                row = cursor.fetchone()

                if row and row["username"] and row["password_encrypted"]:
                    # Decrypt password
                    password_decrypted = self.cipher.decrypt(
                        row["password_encrypted"].encode()
                    ).decode()
                    return {"username": row["username"], "password": password_decrypted}

            return None

        except Exception as e:
            print(f"Credentials retrieval failed: {e}")
            return None

    def save_setting(self, key: str, value: Any, description: str = "") -> bool:
        """Save a general setting"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO collection_settings
                    (key, value_json, description, updated_at)
                    VALUES (?, ?, ?, ?)
                """,
                    (key, json.dumps(value), description, datetime.now()),
                )
                conn.commit()

            return True

        except Exception as e:
            print(f"Setting save failed: {e}")
            return False

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Retrieve a general setting"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT value_json FROM collection_settings WHERE key = ?",
                    (key,),
                )
                row = cursor.fetchone()

                if row and row[0]:
                    return json.loads(row[0])

        except Exception as e:
            print(f"Setting retrieval failed: {e}")

        return default

    def get_all_settings(self) -> Dict[str, Any]:
        """Retrieve all settings"""
        settings = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT key, value_json, description FROM collection_settings"
                )

                for row in cursor.fetchall():
                    try:
                        settings[row["key"]] = {
                            "value": (
                                json.loads(row["value_json"])
                                if row["value_json"]
                                else None
                            ),
                            "description": row["description"],
                        }
                    except json.JSONDecodeError:
                        settings[row["key"]] = {
                            "value": row["value_json"],
                            "description": row["description"],
                        }

        except Exception as e:
            print(f"Settings retrieval failed: {e}")

        return settings

    def delete_source(self, name: str) -> bool:
        """Delete a source configuration"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Delete from all related tables
                conn.execute("DELETE FROM collection_sources WHERE name = ?", (name,))
                conn.execute(
                    "DELETE FROM collection_credentials WHERE source_name = ?", (name,)
                )
                conn.execute(
                    "DELETE FROM collection_history WHERE source_name = ?", (name,)
                )
                conn.commit()

            return True

        except Exception as e:
            print(f"Source deletion failed: {e}")
            return False

    def update_source_status(self, name: str, enabled: bool) -> bool:
        """Update source enabled status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE collection_sources SET enabled = ?, updated_at = ? WHERE name = ?",
                    (enabled, datetime.now(), name),
                )
                conn.commit()

            return True

        except Exception as e:
            print(f"Source status update failed: {e}")
            return False


if __name__ == "__main__":
    import os
    import sys
    import tempfile

    # Test configuration management functionality
    all_validation_failures = []
    total_tests = 0

    # Create temporary database for testing
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        test_db_path = tmp_db.name

    try:
        # Create cipher for testing
        cipher_key = Fernet.generate_key()
        cipher = Fernet(cipher_key)

        # Initialize database tables first
        with sqlite3.connect(test_db_path) as conn:
            conn.execute(
                """
                CREATE TABLE collection_sources (
                    name TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    base_url TEXT,
                    config_json TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE collection_credentials (
                    source_name TEXT PRIMARY KEY,
                    credentials_encrypted TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE collection_settings (
                    key TEXT PRIMARY KEY,
                    value_json TEXT,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.commit()

        config_mgr = ConfigurationManager(test_db_path, cipher)

        # Test 1: Source configuration save and retrieve
        total_tests += 1
        try:
            test_config = {"timeout": 30, "retry_count": 3}
            success = config_mgr.save_source_config(
                "test_source", "Test Source", "https://test.example.com", test_config
            )
            if not success:
                all_validation_failures.append("Source config: Save failed")

            retrieved_config = config_mgr.get_source_config("test_source")
            if not retrieved_config:
                all_validation_failures.append("Source config: Retrieve failed")
            elif retrieved_config["config"]["timeout"] != 30:
                all_validation_failures.append(
                    "Source config: Data mismatch after retrieve"
                )

        except Exception as e:
            all_validation_failures.append(f"Source config: Exception occurred - {e}")

        # Test 2: Credentials save and retrieve
        total_tests += 1
        try:
            success = config_mgr.save_credentials("test_source", "testuser", "testpass")
            if not success:
                all_validation_failures.append("Credentials: Save failed")

            retrieved_creds = config_mgr.get_credentials("test_source")
            if not retrieved_creds:
                all_validation_failures.append("Credentials: Retrieve failed")
            elif retrieved_creds["username"] != "testuser":
                all_validation_failures.append(
                    "Credentials: Username mismatch after retrieve"
                )
            elif retrieved_creds["password"] != "testpass":
                all_validation_failures.append(
                    "Credentials: Password mismatch after retrieve"
                )

        except Exception as e:
            all_validation_failures.append(f"Credentials: Exception occurred - {e}")

        # Test 3: Settings save and retrieve
        total_tests += 1
        try:
            test_setting_value = {"enabled": True, "interval": 3600}
            success = config_mgr.save_setting(
                "test_setting", test_setting_value, "Test setting"
            )
            if not success:
                all_validation_failures.append("Settings: Save failed")

            retrieved_setting = config_mgr.get_setting("test_setting")
            if not retrieved_setting:
                all_validation_failures.append("Settings: Retrieve failed")
            elif not retrieved_setting["enabled"]:
                all_validation_failures.append("Settings: Data mismatch after retrieve")

        except Exception as e:
            all_validation_failures.append(f"Settings: Exception occurred - {e}")

    finally:
        # Clean up test database
        try:
            os.unlink(test_db_path)
        except OSError:
            pass

    # Final validation result
    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print(
            "Configuration management module is validated and formal tests can now be written"
        )
        sys.exit(0)
