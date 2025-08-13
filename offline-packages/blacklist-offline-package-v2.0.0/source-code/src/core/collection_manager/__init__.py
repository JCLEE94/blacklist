"""Modular Collection Manager package"""

from .auth_service import AuthService
from .config_service import CollectionConfigService
from .manager import CollectionManager
from .protection_service import ProtectionService
from .status_service import StatusService

__all__ = [
    "CollectionManager",
    "CollectionConfigService",
    "ProtectionService",
    "AuthService",
    "StatusService",
]
