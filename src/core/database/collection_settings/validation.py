#!/usr/bin/env python3
"""
Collection Settings Validation and Initialization Module
Provides encryption, validation, and database initialization

Third-party packages:
- cryptography: https://cryptography.io/en/latest/
- sqlite3: https://docs.python.org/3/library/sqlite3.html

Sample input: configuration data, database schema
Expected output: encrypted data, initialized database
"""

import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet


class ValidationManager:
    """Handles validation, encryption, and database initialization"""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        
        # Initialize encryption
        self.cipher_key = self._get_or_create_cipher_key()
        self.cipher = Fernet(self.cipher_key)
        
        # Initialize database tables
        self._init_tables()

    def _get_or_create_cipher_key(self) -> bytes:
        """Generate or load encryption key"""
        key_file = self.db_path.parent / ".settings_key"
        if key_file.exists():
            return key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            key_file.chmod(0o600)
            return key

    def _init_tables(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            # Collection sources configuration table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_sources (
                    name TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    base_url TEXT,
                    config_json TEXT,  -- encrypted configuration
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Collection credentials table (encrypted)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_credentials (
                    source_name TEXT PRIMARY KEY,
                    credentials_encrypted TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_name) REFERENCES collection_sources(name)
                )
            """
            )

            # General settings table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_settings (
                    key TEXT PRIMARY KEY,
                    value_json TEXT,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Collection history table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_name TEXT NOT NULL,
                    success BOOLEAN DEFAULT 0,
                    collected_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata_json TEXT,  -- additional metadata
                    FOREIGN KEY (source_name) REFERENCES collection_sources(name)
                )
            """
            )

            # Create indexes
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_collection_history_source ON collection_history(source_name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_collection_history_date ON collection_history(collected_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_collection_credentials_source ON collection_credentials(source_name)"
            )

            conn.commit()

    def validate_source_config(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Validate source configuration"""
        errors = {}
        
        # Required fields
        required_fields = ["name", "display_name", "base_url"]
        for field in required_fields:
            if not config.get(field):
                errors[field] = f"{field} is required"
        
        # Validate name format (alphanumeric, underscore, hyphen only)
        name = config.get("name", "")
        if name and not all(c.isalnum() or c in "_-" for c in name):
            errors["name"] = "Name can only contain letters, numbers, underscores, and hyphens"
        
        # Validate URL format (basic check)
        base_url = config.get("base_url", "")
        if base_url and not (base_url.startswith("http://") or base_url.startswith("https://")):
            errors["base_url"] = "Base URL must start with http:// or https://"
        
        return errors

    def validate_credentials(self, credentials: Dict[str, str]) -> Dict[str, str]:
        """Validate credentials"""
        errors = {}
        
        # Check required fields
        if not credentials.get("username"):
            errors["username"] = "Username is required"
        
        if not credentials.get("password"):
            errors["password"] = "Password is required"
        
        # Basic security checks
        username = credentials.get("username", "")
        if len(username) < 3:
            errors["username"] = "Username must be at least 3 characters"
        
        password = credentials.get("password", "")
        if len(password) < 6:
            errors["password"] = "Password must be at least 6 characters"
        
        return errors

    def validate_setting(self, key: str, value: Any) -> Optional[str]:
        """Validate a setting key-value pair"""
        if not key or not isinstance(key, str):
            return "Setting key must be a non-empty string"
        
        if not key.replace("_", "").replace("-", "").isalnum():
            return "Setting key can only contain letters, numbers, underscores, and hyphens"
        
        # Value can be any JSON-serializable type, so no specific validation needed
        return None

    def encrypt_data(self, data: str) -> str:
        """Encrypt string data"""
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt string data"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()

    def get_cipher(self) -> Fernet:
        """Get the Fernet cipher instance"""
        return self.cipher

    def verify_database_integrity(self) -> Dict[str, Any]:
        """Verify database integrity and return status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if all required tables exist
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                tables = {row[0] for row in cursor.fetchall()}
                
                required_tables = {
                    "collection_sources",
                    "collection_credentials", 
                    "collection_settings",
                    "collection_history"
                }
                
                missing_tables = required_tables - tables
                
                # Check indexes
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                )
                indexes = {row[0] for row in cursor.fetchall()}
                
                required_indexes = {
                    "idx_collection_history_source",
                    "idx_collection_history_date",
                    "idx_collection_credentials_source"
                }
                
                missing_indexes = required_indexes - indexes
                
                # Count records
                record_counts = {}
                for table in required_tables:
                    if table in tables:
                        cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                        record_counts[table] = cursor.fetchone()[0]
                
                return {
                    "valid": len(missing_tables) == 0,
                    "missing_tables": list(missing_tables),
                    "missing_indexes": list(missing_indexes),
                    "record_counts": record_counts,
                    "database_file_exists": self.db_path.exists(),
                    "database_size_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0,
                }

        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "database_file_exists": self.db_path.exists(),
            }

    def reset_database(self) -> bool:
        """Reset database by dropping and recreating all tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Drop all tables
                tables = ["collection_history", "collection_credentials", "collection_settings", "collection_sources"]
                for table in tables:
                    conn.execute(f"DROP TABLE IF EXISTS {table}")
                conn.commit()
                
                # Recreate tables
                self._init_tables()
                
            return True
            
        except Exception as e:
            print(f"Database reset failed: {e}")
            return False

    def backup_database(self, backup_path: str) -> bool:
        """Create a backup of the database"""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            return True
            
        except Exception as e:
            print(f"Database backup failed: {e}")
            return False

    def restore_database(self, backup_path: str) -> bool:
        """Restore database from backup"""
        try:
            import shutil
            if not Path(backup_path).exists():
                print(f"Backup file does not exist: {backup_path}")
                return False
                
            shutil.copy2(backup_path, self.db_path)
            return True
            
        except Exception as e:
            print(f"Database restore failed: {e}")
            return False


if __name__ == "__main__":
    import sys
    import tempfile
    import os
    
    # Test validation and initialization functionality
    all_validation_failures = []
    total_tests = 0
    
    # Create temporary database for testing
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        test_db_path = tmp_db.name
    
    try:
        validation_mgr = ValidationManager(test_db_path)
        
        # Test 1: Database integrity verification
        total_tests += 1
        try:
            integrity = validation_mgr.verify_database_integrity()
            if not integrity["valid"]:
                all_validation_failures.append("Database integrity: Database not valid after initialization")
            if integrity["missing_tables"]:
                all_validation_failures.append(f"Database integrity: Missing tables: {integrity['missing_tables']}")
        except Exception as e:
            all_validation_failures.append(f"Database integrity: Exception occurred - {e}")
        
        # Test 2: Source configuration validation
        total_tests += 1
        try:
            valid_config = {
                "name": "test_source",
                "display_name": "Test Source",
                "base_url": "https://test.example.com"
            }
            invalid_config = {
                "name": "invalid name!",  # Invalid characters
                "display_name": "",  # Empty
                "base_url": "not-a-url"  # Invalid URL
            }
            
            valid_errors = validation_mgr.validate_source_config(valid_config)
            invalid_errors = validation_mgr.validate_source_config(invalid_config)
            
            if valid_errors:
                all_validation_failures.append(f"Source validation: Valid config rejected: {valid_errors}")
            if not invalid_errors:
                all_validation_failures.append("Source validation: Invalid config accepted")
        except Exception as e:
            all_validation_failures.append(f"Source validation: Exception occurred - {e}")
        
        # Test 3: Encryption and decryption
        total_tests += 1
        try:
            test_data = "This is sensitive test data"
            encrypted = validation_mgr.encrypt_data(test_data)
            decrypted = validation_mgr.decrypt_data(encrypted)
            
            if encrypted == test_data:
                all_validation_failures.append("Encryption: Data not encrypted (same as original)")
            if decrypted != test_data:
                all_validation_failures.append("Encryption: Decrypted data does not match original")
        except Exception as e:
            all_validation_failures.append(f"Encryption: Exception occurred - {e}")
        
        # Test 4: Credentials validation
        total_tests += 1
        try:
            valid_creds = {"username": "testuser", "password": "testpass123"}
            invalid_creds = {"username": "ab", "password": "123"}  # Too short
            
            valid_errors = validation_mgr.validate_credentials(valid_creds)
            invalid_errors = validation_mgr.validate_credentials(invalid_creds)
            
            if valid_errors:
                all_validation_failures.append(f"Credentials validation: Valid credentials rejected: {valid_errors}")
            if not invalid_errors:
                all_validation_failures.append("Credentials validation: Invalid credentials accepted")
        except Exception as e:
            all_validation_failures.append(f"Credentials validation: Exception occurred - {e}")
        
    finally:
        # Clean up test database and key file
        try:
            os.unlink(test_db_path)
            key_file = Path(test_db_path).parent / ".settings_key"
            if key_file.exists():
                os.unlink(key_file)
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
        print("Validation and initialization module is validated and formal tests can now be written")
        sys.exit(0)
