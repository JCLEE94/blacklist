#!/usr/bin/env python3
"""
Backward compatibility wrapper for modularized Collection Manager

This file maintains backward compatibility while the actual implementation
has been modularized into the collection_manager/ package.
"""

# Import everything from the modular package
from .collection_manager import (
    CollectionManager,
    CollectionConfigService,
    ProtectionService,
    AuthService,
    StatusService,
)

# Re-export for backward compatibility
__all__ = [
    'CollectionManager',
    'CollectionConfigService',
    'ProtectionService', 
    'AuthService',
    'StatusService',
]

# Preserve the original class name and functionality
# All imports and usage patterns remain the same
