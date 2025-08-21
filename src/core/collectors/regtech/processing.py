#!/usr/bin/env python3
"""
REGTECH Data Processing Module
Provides data parsing and processing for collected threat intelligence

Third-party packages:
- bs4: https://www.crummy.com/software/BeautifulSoup/
- pandas: https://pandas.pydata.org/docs/

Sample input: HTML content, JSON data, Excel files
Expected output: parsed IP data, processed threat intelligence
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from bs4 import BeautifulSoup

from .helpers import IPValidator, PatternMatcher

logger = logging.getLogger(__name__)


class DataProcessor:
    """Handles processing and parsing of collected data"""

    def __init__(self):
        # Initialize helper classes
        self.ip_validator = IPValidator()
        self.pattern_matcher = PatternMatcher()

    def parse_board_page(self, html_content: str, source: str) -> List[Dict[str, Any]]:
        """Parse HTML content from board pages"""
        ips_data = []

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Extract text content
            text_content = soup.get_text()

            # Find IP addresses using pattern matcher
            found_ips = self.pattern_matcher.extract_ips_from_text(text_content)

            # Also try extracting from tables and lists
            table_ips = self.pattern_matcher.extract_ips_from_html_table(soup)
            list_ips = self.pattern_matcher.extract_ips_from_lists(soup)
            found_ips.update(table_ips)
            found_ips.update(list_ips)

            # Process each found IP
            for ip in found_ips:
                if self.ip_validator.is_valid_ip(ip):
                    ip_data = {
                        "ip": ip,
                        "source": source,
                        "detection_date": datetime.now().strftime("%Y-%m-%d"),
                        "threat_type": "unknown",
                        "confidence": 0.7,
                        "raw_data": self._extract_context(text_content, ip),
                    }
                    ips_data.append(ip_data)

            logger.info(f"Parsed {len(ips_data)} IPs from board page")

        except Exception as e:
            logger.error(f"Board page parsing error: {e}")

        return ips_data

    def parse_excel_response(
        self, excel_content: bytes, source: str
    ) -> List[Dict[str, Any]]:
        """Parse Excel file content"""
        ips_data = []

        try:
            # Try reading as Excel file
            try:
                df = pd.read_excel(excel_content, engine="openpyxl")
            except Exception:
                # Try with xlrd engine
                df = pd.read_excel(excel_content, engine="xlrd")

            logger.info(f"Excel file has {len(df)} rows and {len(df.columns)} columns")

            # Look for IP addresses in all columns
            for _, row in df.iterrows():
                for col_name, cell_value in row.items():
                    if pd.isna(cell_value):
                        continue

                    cell_str = str(cell_value)
                    ips = self.ip_pattern.findall(cell_str)

                    for ip in ips:
                        if self.ip_validator.is_valid_ip(ip):
                            # Try to extract additional data from the row
                            detection_date = self._extract_date_from_row(row)
                            threat_type = self._extract_threat_type_from_row(row)

                            ip_data = {
                                "ip": ip,
                                "source": source,
                                "detection_date": detection_date,
                                "threat_type": threat_type,
                                "confidence": 0.8,
                                "raw_data": row.to_dict(),
                            }
                            ips_data.append(ip_data)

            logger.info(f"Parsed {len(ips_data)} IPs from Excel file")

        except Exception as e:
            logger.error(f"Excel parsing error: {e}")

        return ips_data

    def parse_json_response(
        self, json_data: Dict[str, Any], source: str
    ) -> List[Dict[str, Any]]:
        """Parse JSON response data"""
        ips_data = []

        try:
            # Handle different JSON structures
            if isinstance(json_data, list):
                # Direct list of items
                items = json_data
            elif "data" in json_data:
                # Wrapped in data field
                items = json_data["data"]
            elif "results" in json_data:
                # Wrapped in results field
                items = json_data["results"]
            elif "ips" in json_data:
                # Direct IP list
                items = json_data["ips"]
            else:
                # Try to extract from any field
                items = []
                for key, value in json_data.items():
                    if isinstance(value, list):
                        items.extend(value)

            # Process each item
            for item in items:
                if isinstance(item, str):
                    # Simple string - check if it's an IP
                    if self.ip_validator.is_valid_ip(item):
                        ip_data = {
                            "ip": item,
                            "source": source,
                            "detection_date": datetime.now().strftime("%Y-%m-%d"),
                            "threat_type": "unknown",
                            "confidence": 0.6,
                            "raw_data": item,
                        }
                        ips_data.append(ip_data)

                elif isinstance(item, dict):
                    # Dictionary - extract IP and other data
                    ip = self._extract_ip_from_dict(item)
                    if ip and self.ip_validator.is_valid_ip(ip):
                        ip_data = {
                            "ip": ip,
                            "source": source,
                            "detection_date": self._extract_date_from_dict(item),
                            "threat_type": self._extract_threat_type_from_dict(item),
                            "confidence": self._extract_confidence_from_dict(item),
                            "raw_data": item,
                        }
                        ips_data.append(ip_data)

            logger.info(f"Parsed {len(ips_data)} IPs from JSON response")

        except Exception as e:
            logger.error(f"JSON parsing error: {e}")

        return ips_data

    def _extract_ip_from_dict(self, data: Dict) -> Optional[str]:
        """Extract IP address from dictionary"""
        # Common field names for IP addresses
        ip_fields = ["ip", "ip_address", "address", "host", "target"]

        for field in ip_fields:
            if field in data and data[field]:
                ip = str(data[field])
                if self.ip_validator.is_valid_ip(ip):
                    return ip

        # Search in all fields
        for key, value in data.items():
            if value and isinstance(value, str):
                ips = self.ip_pattern.findall(value)
                for ip in ips:
                    if self.ip_validator.is_valid_ip(ip):
                        return ip

        return None

    # IP validation moved to IPValidator helper class

    def remove_duplicates(self, ips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate IP entries"""
        seen_ips = set()
        unique_ips = []

        for ip_data in ips:
            ip = ip_data.get("ip")
            if ip and ip not in seen_ips:
                seen_ips.add(ip)
                unique_ips.append(ip_data)

        logger.info(f"Removed {len(ips) - len(unique_ips)} duplicate IPs")
        return unique_ips

    def _extract_context(self, text: str, ip: str) -> str:
        """Extract context around IP address"""
        try:
            # Find IP in text and extract surrounding context
            ip_index = text.find(ip)
            if ip_index == -1:
                return ""

            # Extract 100 characters before and after
            start = max(0, ip_index - 100)
            end = min(len(text), ip_index + len(ip) + 100)

            return text[start:end].strip()

        except Exception:
            return ""

    def _extract_date_from_row(self, row: pd.Series) -> str:
        """Extract date from pandas row"""
        # Look for date-like columns
        date_columns = ["date", "timestamp", "detected", "created", "updated"]

        for col in date_columns:
            if col in row.index and not pd.isna(row[col]):
                try:
                    date_value = pd.to_datetime(row[col])
                    return date_value.strftime("%Y-%m-%d")
                except Exception:
                    continue

        return datetime.now().strftime("%Y-%m-%d")

    def _extract_threat_type_from_row(self, row: pd.Series) -> str:
        """Extract threat type from pandas row"""
        # Look for threat type columns
        type_columns = ["type", "threat_type", "category", "classification"]

        for col in type_columns:
            if col in row.index and not pd.isna(row[col]):
                return str(row[col]).lower()

        return "unknown"

    def _extract_date_from_dict(self, data: Dict) -> str:
        """Extract date from dictionary"""
        date_fields = ["date", "timestamp", "detected_at", "created_at", "updated_at"]

        for field in date_fields:
            if field in data and data[field]:
                try:
                    date_value = pd.to_datetime(data[field])
                    return date_value.strftime("%Y-%m-%d")
                except Exception:
                    continue

        return datetime.now().strftime("%Y-%m-%d")

    def _extract_threat_type_from_dict(self, data: Dict) -> str:
        """Extract threat type from dictionary"""
        type_fields = ["type", "threat_type", "category", "classification"]

        for field in type_fields:
            if field in data and data[field]:
                return str(data[field]).lower()

        return "unknown"

    def _extract_confidence_from_dict(self, data: Dict) -> float:
        """Extract confidence score from dictionary"""
        confidence_fields = ["confidence", "score", "probability", "certainty"]

        for field in confidence_fields:
            if field in data and data[field] is not None:
                try:
                    confidence = float(data[field])
                    return max(0.0, min(1.0, confidence))  # Clamp to 0-1 range
                except (ValueError, TypeError):
                    continue

        return 0.6  # Default confidence

    def validate_ip_data(self, ip_data: Dict[str, Any]) -> bool:
        """Validate IP data structure"""
        required_fields = ["ip", "source", "detection_date"]

        for field in required_fields:
            if field not in ip_data or not ip_data[field]:
                return False

        # Validate IP format
        if not self.ip_validator.is_valid_ip(ip_data["ip"]):
            return False

        return True

    def standardize_ip_data(
        self, ip_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Standardize IP data format"""
        standardized = []

        for data in ip_data:
            if not self.validate_ip_data(data):
                continue

            # Ensure all required fields exist
            standard_data = {
                "ip": data["ip"].strip(),
                "source": data.get("source", "unknown"),
                "detection_date": data.get(
                    "detection_date", datetime.now().strftime("%Y-%m-%d")
                ),
                "threat_type": data.get("threat_type", "unknown").lower(),
                "confidence": float(data.get("confidence", 0.6)),
                "raw_data": data.get("raw_data", {}),
                "processed_at": datetime.now().isoformat(),
            }

            standardized.append(standard_data)

        return standardized


if __name__ == "__main__":
    import sys

    # Test data processing functionality
    all_validation_failures = []
    total_tests = 0

    processor = DataProcessor()

    # Test 1: IP validation
    total_tests += 1
    try:
        valid_ips = ["8.8.8.8", "1.2.2.1", "208.67.222.222"]
        invalid_ips = ["192.168.1.1", "10.0.0.1", "256.256.256.256", "invalid"]

        for ip in valid_ips:
            if not processor._is_valid_ip(ip):
                all_validation_failures.append(f"IP validation: Valid IP {ip} rejected")

        for ip in invalid_ips:
            if processor._is_valid_ip(ip):
                all_validation_failures.append(
                    f"IP validation: Invalid IP {ip} accepted"
                )

    except Exception as e:
        all_validation_failures.append(f"IP validation: Exception occurred - {e}")

    # Test 2: HTML parsing
    total_tests += 1
    try:
        test_html = (
            "<html><body>Detected malicious IP: 8.8.8.8 at location</body></html>"
        )
        parsed_data = processor.parse_board_page(test_html, "test_source")

        if len(parsed_data) != 1:
            all_validation_failures.append(
                f"HTML parsing: Expected 1 IP, got {len(parsed_data)}"
            )
        elif parsed_data[0]["ip"] != "8.8.8.8":
            all_validation_failures.append(
                f"HTML parsing: Wrong IP extracted: {parsed_data[0]['ip']}"
            )

    except Exception as e:
        all_validation_failures.append(f"HTML parsing: Exception occurred - {e}")

    # Test 3: JSON parsing
    total_tests += 1
    try:
        test_json = {"ips": ["8.8.8.8", "1.2.2.1"], "count": 2}
        parsed_data = processor.parse_json_response(test_json, "test_api")

        if len(parsed_data) != 2:
            all_validation_failures.append(
                f"JSON parsing: Expected 2 IPs, got {len(parsed_data)}"
            )

    except Exception as e:
        all_validation_failures.append(f"JSON parsing: Exception occurred - {e}")

    # Test 4: Duplicate removal
    total_tests += 1
    try:
        test_data = [
            {"ip": "8.8.8.8", "source": "test1"},
            {"ip": "8.8.8.8", "source": "test2"},
            {"ip": "1.2.2.1", "source": "test1"},
        ]
        unique_data = processor.remove_duplicates(test_data)

        if len(unique_data) != 2:
            all_validation_failures.append(
                f"Duplicate removal: Expected 2 unique IPs, got {len(unique_data)}"
            )

    except Exception as e:
        all_validation_failures.append(f"Duplicate removal: Exception occurred - {e}")

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
        print("Data processing module is validated and formal tests can now be written")
        sys.exit(0)
