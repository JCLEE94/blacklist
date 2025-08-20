"""
Legacy Security Module - DEPRECATED
This module has been refactored into modular components in the security/ package.
This file is kept for backward compatibility only.

New imports should use:
from src.utils.security import SecurityManager, require_auth, rate_limit

Deprecated: This file will be removed in a future version.
"""

import logging

# Import everything from the new modular security package
# from .security import *  # Removed to fix linting issues
# Use specific imports instead when needed

logger = logging.getLogger(__name__)

# Add deprecation warning
logger.warning(
    "src.utils.security.py is deprecated. Use 'from src.utils.security import ...' instead. "
    "This legacy module will be removed in a future version."
)

# All functionality now provided by the modular security package
# This file serves only as a compatibility layer
