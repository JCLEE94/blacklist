#!/usr/bin/env python3
"""
Configurable Collection System - Refactored Modular Version

Main orchestrator using extracted modular components to stay under 500-line limit.

Sample input: config_path="config/collection_config.json"
Expected output: Collection system with modular architecture
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

try:
    from .config_manager import ConfigManager
    from .credentials_manager import CredentialsManager
    from .history_manager import HistoryManager
except ImportError:
    # Fallback for standalone execution
    from config_manager import ConfigManager
    from credentials_manager import CredentialsManager
    from history_manager import HistoryManager

logger = logging.getLogger(__name__)


class ConfigurableCollectionSystem:
    """Modular collection system orchestrator"""

    def __init__(self, config_path: str = "config/collection_config.json"):
        """Initialize with modular components"""
        # Initialize component managers
        self.config_manager = ConfigManager(config_path)

        # Get configurations
        storage_config = self.config_manager.get_storage_config()
        security_config = self.config_manager.get_security_config()

        # Initialize managers with appropriate file paths
        from pathlib import Path

        credentials_file = Path(
            storage_config.get("credentials_file", "instance/credentials.enc")
        )
        history_file = Path(
            storage_config.get("history_file", "instance/collection_history.json")
        )
        cipher_key_file = Path(
            storage_config.get("cipher_key_file", "instance/.cipher_key")
        )

        self.credentials_manager = CredentialsManager(
            credentials_file, cipher_key_file, security_config
        )
        self.history_manager = HistoryManager(history_file)

        # Reports directory
        self.reports_dir = Path(storage_config.get("reports_dir", "instance/reports"))
        self.reports_dir.mkdir(exist_ok=True)

        enabled_sources = self.config_manager.get_enabled_sources()
        logger.info(
            f"Collection system initialized: {len(enabled_sources)} sources enabled"
        )

    # Delegation methods for backwards compatibility
    def save_credentials(
        self,
        source: str,
        username: str,
        password: str,
        additional_fields: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Save credentials via credentials manager"""
        return self.credentials_manager.save_credentials(
            source, username, password, additional_fields
        )

    def get_credentials(self, source: str = "regtech") -> Optional[Dict[str, str]]:
        """Get credentials via credentials manager"""
        return self.credentials_manager.get_credentials(source)

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics via history manager"""
        return self.history_manager.get_statistics()

    def collect_from_source(
        self,
        source_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Collect data from specific source"""
        # Get source configuration
        source_config = self.config_manager.get_source_config(source_name)
        if not source_config:
            return {
                "source": source_name,
                "success": False,
                "error": f"Source configuration not found: {source_name}",
                "collected_at": datetime.now().isoformat(),
            }

        if not source_config.get("enabled", False):
            return {
                "source": source_name,
                "success": False,
                "error": f"Source disabled: {source_name}",
                "collected_at": datetime.now().isoformat(),
            }

        # Set up date range
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            collection_config = self.config_manager.get_collection_config()
            default_range = collection_config.get("default_date_range", 7)
            start_date = (datetime.now() - timedelta(days=default_range)).strftime(
                "%Y-%m-%d"
            )

        result = {
            "source": source_name,
            "start_date": start_date,
            "end_date": end_date,
            "collected_at": datetime.now().isoformat(),
            "success": False,
            "count": 0,
            "ips": [],
            "error": None,
        }

        try:
            if source_name == "regtech":
                result = self._collect_regtech(
                    source_config, start_date, end_date, result
                )
            else:
                result["error"] = f"Unsupported source: {source_name}"

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"{source_name} collection failed: {e}")

        # Add to history
        self.history_manager.add_to_history(result)
        return result

    def _collect_regtech(
        self,
        config: Dict[str, Any],
        start_date: str,
        end_date: str,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Collect REGTECH data"""
        # Get credentials
        creds = self.get_credentials("regtech")
        if not creds:
            result["error"] = "No credentials available"
            return result

        base_url = config["base_url"]
        endpoints = config["endpoints"]
        headers = config.get("headers", {})
        timeout = config.get("timeout", 30)

        # Create session
        session = requests.Session()
        session.headers.update(headers)

        try:
            # 1. Access login page
            login_url = f"{base_url}{endpoints['login']}"
            login_resp = session.get(login_url, timeout=timeout)

            if login_resp.status_code != 200:
                result["error"] = f"Login page access failed: {login_resp.status_code}"
                return result

            # 2. Perform login
            login_action_url = f"{base_url}{endpoints['login_action']}"
            login_data = {"userId": creds["username"], "userPw": creds["password"]}

            login_action_resp = session.post(
                login_action_url, data=login_data, timeout=timeout
            )

            if login_action_resp.status_code != 200:
                result["error"] = f"Login failed: {login_action_resp.status_code}"
                return result

            # Check login success
            if (
                "로그인" in login_action_resp.text
                or "login" in login_action_resp.text.lower()
            ):
                result["error"] = "Login failed: Invalid credentials"
                return result

            # 3. Search for data
            search_url = f"{base_url}{endpoints['search']}"
            search_data = {
                "pageNum": "1",
                "searchFlag": "1",
                "searchStDt": start_date.replace("-", ""),
                "searchEdDt": end_date.replace("-", ""),
                "searchType": "ALL",
                "searchWord": "",
            }

            search_resp = session.post(search_url, data=search_data, timeout=timeout)

            if search_resp.status_code == 200:
                # Parse HTML and extract IPs
                soup = BeautifulSoup(search_resp.text, "html.parser")
                ip_list = self._extract_ips_from_html(soup)

                result["success"] = True
                result["count"] = len(ip_list)
                result["ips"] = ip_list
                result["status"] = "success"
                result["ip_count"] = len(ip_list)

                logger.info(f"REGTECH collection successful: {len(ip_list)} IPs")
            else:
                result["error"] = f"Data search failed: {search_resp.status_code}"

        except requests.exceptions.Timeout:
            result["error"] = "Request timeout"
        except requests.exceptions.ConnectionError:
            result["error"] = "Connection failed"
        except Exception as e:
            result["error"] = f"Collection error: {str(e)}"

        return result

    def _extract_ips_from_html(self, soup: BeautifulSoup) -> List[str]:
        """Extract IP addresses from HTML"""
        ip_list = []
        ip_pattern = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")

        # Find IPs in tables
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                for cell in row.find_all(["td", "th"]):
                    text = cell.get_text().strip()
                    ips = ip_pattern.findall(text)
                    for ip in ips:
                        if self._is_valid_ip(ip) and ip not in ip_list:
                            ip_list.append(ip)

        return ip_list

    def _is_valid_ip(self, ip: str) -> bool:
        """Validate IP address"""
        try:
            parts = ip.split(".")
            if len(parts) != 4:
                return False

            for part in parts:
                num = int(part)
                if not (0 <= num <= 255):
                    return False

            # Exclude private and special IPs
            if ip.startswith(("127.", "10.", "192.168.", "172.")):
                return False
            if ip.startswith("0.") or ip.endswith(".0"):
                return False

            return True
        except ValueError:
            return False

    def get_collection_calendar(self, year: int, month: int) -> Dict[str, Any]:
        """Generate collection calendar for given month"""
        try:
            from calendar import monthrange

            # Get days in month
            _, days_in_month = monthrange(year, month)

            # Get history entries for the month
            history_entries = self.history_manager.collection_history

            # Filter entries for the specific month
            calendar_data = {}
            for day in range(1, days_in_month + 1):
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                calendar_data[date_str] = {
                    "collections": [],
                    "total_ips": 0,
                    "sources": set(),
                }

                # Find entries for this date
                for entry in history_entries:
                    collected_at = entry.get("collected_at", "")
                    if collected_at.startswith(date_str):
                        calendar_data[date_str]["collections"].append(entry)
                        calendar_data[date_str]["total_ips"] += entry.get("count", 0)
                        calendar_data[date_str]["sources"].add(
                            entry.get("source", "unknown")
                        )

                # Convert set to list for JSON serialization
                calendar_data[date_str]["sources"] = list(
                    calendar_data[date_str]["sources"]
                )

            return {
                "year": year,
                "month": month,
                "calendar": calendar_data,
                "summary": {
                    "total_collection_days": sum(
                        1 for data in calendar_data.values() if data["collections"]
                    ),
                    "total_ips": sum(
                        data["total_ips"] for data in calendar_data.values()
                    ),
                    "active_sources": list(
                        set().union(
                            *[data["sources"] for data in calendar_data.values()]
                        )
                    ),
                },
            }
        except Exception as e:
            logger.error(f"Calendar generation failed: {e}")
            return {"error": str(e)}


if __name__ == "__main__":
    # Validation function
    import sys
    from pathlib import Path
    from tempfile import TemporaryDirectory

    # Set up temporary test environment
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create minimal test config
        config_file = temp_path / "test_config.json"
        test_config = {
            "sources": {
                "regtech": {
                    "enabled": True,
                    "base_url": "https://test.example.com",
                    "endpoints": {
                        "login": "/login",
                        "login_action": "/login_action",
                        "search": "/search",
                    },
                }
            },
            "storage": {
                "credentials_file": str(temp_path / "creds.enc"),
                "history_file": str(temp_path / "history.json"),
                "cipher_key_file": str(temp_path / "cipher.key"),
            },
            "security": {},
            "collection": {"default_date_range": 7},
        }

        import json

        with open(config_file, "w") as f:
            json.dump(test_config, f)

        # Test system initialization
        try:
            system = ConfigurableCollectionSystem(str(config_file))

            # Test 1: Configuration loading
            enabled_sources = system.config_manager.get_enabled_sources()
            assert "regtech" in enabled_sources, "Regtech source not enabled"

            # Test 2: Credentials management
            creds_saved = system.save_credentials("test", "user", "pass")
            assert creds_saved, "Failed to save credentials"

            retrieved_creds = system.get_credentials("test")
            assert retrieved_creds is not None, "Failed to retrieve credentials"
            assert retrieved_creds["username"] == "user", "Username mismatch"

            # Test 3: Statistics
            stats = system.get_statistics()
            assert "total_collections" in stats, "Statistics missing total_collections"

            print("✅ Configurable collection system validation complete")
            sys.exit(0)

        except Exception as e:
            print(f"❌ Validation failed: {e}")
            sys.exit(1)
