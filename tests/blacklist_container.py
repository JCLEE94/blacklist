"""
Test container module for BlacklistContainer

테스트용 BlacklistContainer 래퍼 및 유틸리티
"""

import logging

# Import the actual BlacklistContainer from the core module
from src.core.containers.blacklist_container import BlacklistContainer

logger = logging.getLogger(__name__)

# Re-export for tests
__all__ = ["BlacklistContainer"]