#!/usr/bin/env python3
"""
Authentication manager for storing and retrieving credentials from file.
Removes dependency on environment variables.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class AuthManager:
    """Manages authentication credentials stored in file system"""
    
    def __init__(self, config_path: str = "instance/auth_config.json"):
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_config_file()
    
    def _ensure_config_file(self):
        """Ensure config file exists with default structure"""
        if not self.config_path.exists():
            default_config = {
                "regtech": {
                    "username": "",
                    "password": "",
                    "enabled": False
                },
                "secudium": {
                    "username": "",
                    "password": "",
                    "enabled": False
                }
            }
            self.save_config(default_config)
    
    def get_config(self) -> Dict:
        """Get current authentication configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                # Mask passwords for security
                masked_config = {
                    "regtech": {
                        "username": config.get("regtech", {}).get("username", ""),
                        "password_set": bool(config.get("regtech", {}).get("password")),
                        "enabled": config.get("regtech", {}).get("enabled", False)
                    },
                    "secudium": {
                        "username": config.get("secudium", {}).get("username", ""),
                        "password_set": bool(config.get("secudium", {}).get("password")),
                        "enabled": config.get("secudium", {}).get("enabled", False)
                    }
                }
                return masked_config
        except Exception as e:
            logger.error(f"Failed to read config: {e}")
            return {
                "regtech": {"username": "", "password_set": False, "enabled": False},
                "secudium": {"username": "", "password_set": False, "enabled": False}
            }
    
    def save_config(self, config: Dict) -> bool:
        """Save authentication configuration"""
        try:
            # Read existing config to preserve passwords if not provided
            existing_config = {}
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    existing_config = json.load(f)
            
            # Update config, preserving passwords if not provided
            updated_config = existing_config.copy()
            
            for source in ["regtech", "secudium"]:
                if source in config:
                    if source not in updated_config:
                        updated_config[source] = {}
                    
                    # Update fields
                    if "username" in config[source]:
                        updated_config[source]["username"] = config[source]["username"]
                    if "password" in config[source] and config[source]["password"]:
                        updated_config[source]["password"] = config[source]["password"]
                    if "enabled" in config[source]:
                        updated_config[source]["enabled"] = config[source]["enabled"]
            
            # Save to file
            with open(self.config_path, 'w') as f:
                json.dump(updated_config, f, indent=2)
            
            logger.info("Auth configuration saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False
    
    def get_credentials(self, source: str) -> Optional[Dict[str, str]]:
        """Get credentials for a specific source"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            source_config = config.get(source, {})
            if source_config.get("enabled") and source_config.get("username") and source_config.get("password"):
                return {
                    "username": source_config["username"],
                    "password": source_config["password"]
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get credentials for {source}: {e}")
            return None
    
    def test_connection(self, source: str) -> Dict:
        """Test connection for a source"""
        credentials = self.get_credentials(source)
        if not credentials:
            return {
                "success": False,
                "message": f"{source} credentials not configured or disabled"
            }
        
        # Here you would actually test the connection
        # For now, just return success if credentials exist
        return {
            "success": True,
            "message": f"{source} credentials configured",
            "username": credentials["username"]
        }

# Global instance
_auth_manager = None

def get_auth_manager() -> AuthManager:
    """Get global auth manager instance"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager