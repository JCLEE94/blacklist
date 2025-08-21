#!/usr/bin/env python3
"""
Backward compatibility wrapper for modularized Unified Blacklist Manager

This file maintains backward compatibility while the actual implementation
has been modularized into the blacklist_unified/ package.
"""

# Import everything from the modular package
from .blacklist_unified import (
    DataProcessingError,
    SearchResult,
    UnifiedBlacklistManager,
    ValidationError,
)

# Re-export for backward compatibility
__all__ = [
    "UnifiedBlacklistManager",
    "SearchResult",
    "DataProcessingError",
    "ValidationError",
]

