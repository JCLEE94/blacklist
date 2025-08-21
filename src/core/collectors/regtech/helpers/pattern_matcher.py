"""
Pattern Matching Helper
Provides regex patterns for IP extraction from various sources.
"""

import re
from typing import List, Set


class PatternMatcher:
    """Handles pattern matching for IP extraction."""

    def __init__(self):
        # IP address regex pattern
        self.ip_pattern = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")

        # Common IP extraction patterns
        self.extraction_patterns = [
            r"IP[:\s]+([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})",
            r"\b([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})\b",
            r"Address[:\s]+([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})",
            r"Threat[:\s]+([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})",
            r"Source[:\s]+([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})",
        ]

    def extract_ips_from_text(self, text_content: str) -> Set[str]:
        """Extract IP addresses from text using multiple patterns.

        Args:
            text_content: Text to search for IP addresses

        Returns:
            Set of found IP addresses
        """
        found_ips = set()

        # Try each extraction pattern
        for pattern in self.extraction_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            found_ips.update(matches)

        # Also try simple IP pattern
        simple_matches = self.ip_pattern.findall(text_content)
        found_ips.update(simple_matches)

        return found_ips

    def extract_ips_from_html_table(
        self, soup, table_selectors: List[str] = None
    ) -> Set[str]:
        """Extract IPs from HTML tables.

        Args:
            soup: BeautifulSoup object
            table_selectors: List of CSS selectors for tables

        Returns:
            Set of found IP addresses
        """
        found_ips = set()

        if not table_selectors:
            table_selectors = ["table", ".table", "#data-table"]

        for selector in table_selectors:
            tables = soup.select(selector)
            for table in tables:
                table_text = table.get_text()
                ips = self.extract_ips_from_text(table_text)
                found_ips.update(ips)

        return found_ips

    def extract_ips_from_lists(
        self, soup, list_selectors: List[str] = None
    ) -> Set[str]:
        """Extract IPs from HTML lists.

        Args:
            soup: BeautifulSoup object
            list_selectors: List of CSS selectors for lists

        Returns:
            Set of found IP addresses
        """
        found_ips = set()

        if not list_selectors:
            list_selectors = ["ul", "ol", ".ip-list", ".threat-list"]

        for selector in list_selectors:
            lists = soup.select(selector)
            for list_elem in lists:
                list_text = list_elem.get_text()
                ips = self.extract_ips_from_text(list_text)
                found_ips.update(ips)

        return found_ips
