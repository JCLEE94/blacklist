#!/usr/bin/env python3
"""
Data models and exceptions for Unified Blacklist Manager
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional


class DataProcessingError(Exception):
    """Data processing error with context"""

    def __init__(
        self,
        message: str,
        file_path: str = None,
        operation: str = None,
        cause: Exception = None,
    ):
        super().__init__(message)
        self.file_path = file_path
        self.operation = operation
        self.cause = cause


class ValidationError(Exception):
    """Data validation error"""

    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(message)
        self.field = field
        self.value = value


@dataclass
class SearchResult:
    """Enhanced search result with geolocation and history"""

    ip: str
    found: bool
    sources: List[str] = field(default_factory=list)
    first_detection: Optional[datetime] = None
    last_detection: Optional[datetime] = None
    detection_count: int = 0
    geolocation: Optional[Dict[str, Any]] = None
    threat_intelligence: Optional[Dict[str, Any]] = None
    search_timestamp: datetime = field(default_factory=datetime.now)
