"""
IP Address Validation Helper
Provides IP address validation and filtering utilities.
"""

import re
from typing import List


class IPValidator:
    """Handles IP address validation and filtering."""

    def __init__(self):
        # IP address regex pattern
        self.ip_pattern = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")

    def is_valid_ip(self, ip_str: str) -> bool:
        """Validate IP address format and exclude private/reserved ranges.

        Args:
            ip_str: IP address string to validate

        Returns:
            True if IP is valid and public
        """
        try:
            parts = ip_str.split(".")
            if len(parts) != 4:
                return False

            # Check each part is valid number
            for part in parts:
                num = int(part)
                if not 0 <= num <= 255:
                    return False

            # Exclude private and reserved ranges
            first_octet = int(parts[0])
            second_octet = int(parts[1])

            # Private ranges
            if first_octet == 10:  # 10.0.0.0/8
                return False
            if first_octet == 172 and 16 <= second_octet <= 31:  # 172.16.0.0/12
                return False
            if first_octet == 192 and second_octet == 168:  # 192.168.0.0/16
                return False

            # Reserved ranges
            reserved_ranges = [
                0,
                127,
                224,
                225,
                226,
                227,
                228,
                229,
                230,
                231,
                232,
                233,
                234,
                235,
                236,
                237,
                238,
                239,
                240,
                241,
                242,
                243,
                244,
                245,
                246,
                247,
                248,
                249,
                250,
                251,
                252,
                253,
                254,
                255,
            ]
            if first_octet in reserved_ranges:
                return False

            return True

        except (ValueError, IndexError):
            return False

    def extract_valid_ips(self, text: str) -> List[str]:
        """Extract all valid public IP addresses from text.

        Args:
            text: Text to search for IP addresses

        Returns:
            List of valid public IP addresses
        """
        found_ips = self.ip_pattern.findall(text)
        return [ip for ip in found_ips if self.is_valid_ip(ip)]

    def filter_unique_ips(self, ip_list: List[str]) -> List[str]:
        """Remove duplicate IPs while preserving order.

        Args:
            ip_list: List of IP addresses

        Returns:
            List of unique IP addresses
        """
        seen = set()
        unique_ips = []
        for ip in ip_list:
            if ip not in seen:
                seen.add(ip)
                unique_ips.append(ip)
        return unique_ips
