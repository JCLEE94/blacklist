#!/usr/bin/env python3
"""
Legacy Collection Settings Module - DEPRECATED
This module has been refactored into modular components in the collection_settings/ package.
This file is kept for backward compatibility only.

New imports should use:
from src.core.database.collection_settings import CollectionSettingsDB

Deprecated: This file will be removed in a future version.
"""

# Import everything from the new modular collection_settings package
from .collection_settings import *

import logging
logger = logging.getLogger(__name__)

# Add deprecation warning
logger.warning(
    "src.core.database.collection_settings.py is deprecated. Use 'from src.core.database.collection_settings import ...' instead. "
    "This legacy module will be removed in a future version."
)

# All functionality now provided by the modular collection_settings package
