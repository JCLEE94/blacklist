#!/usr/bin/env python3
"""
Backward compatibility wrapper for modularized Unified Blacklist Manager

This file maintains backward compatibility while the actual implementation
has been modularized into the blacklist_unified/ package.
"""

# Import everything from the modular package
from .blacklist_unified import (
    UnifiedBlacklistManager,
    SearchResult,
    DataProcessingError,
    ValidationError,
)

# Re-export for backward compatibility
__all__ = [
    'UnifiedBlacklistManager',
    'SearchResult',
    'DataProcessingError',
    'ValidationError',
]

# Preserve the original class name and functionality
# All imports and usage patterns remain the same
