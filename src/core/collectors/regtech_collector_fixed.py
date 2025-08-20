#!/usr/bin/env python3
"""
Legacy REGTECH Collector - DEPRECATED
This module has been refactored into modular components in the regtech/ package.
This file is kept for backward compatibility only.

New imports should use:
from src.core.collectors.regtech import FixedRegtechCollector

Deprecated: This file will be removed in a future version.
"""

import logging

# Import everything from the new modular regtech package
from .regtech import *

logger = logging.getLogger(__name__)

# Add deprecation warning
logger.warning(
    "src.core.collectors.regtech_collector_fixed.py is deprecated. Use 'from src.core.collectors.regtech import ...' instead. "
    "This legacy module will be removed in a future version."
)

# All functionality now provided by the modular regtech package
# This file serves only as a compatibility layer
