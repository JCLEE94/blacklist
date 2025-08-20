"""
Unified Decorators - Backward compatibility wrapper for modularized decorators

This module maintains backward compatibility while delegating to modular
decorator packages
"""

# Import all decorators from the modularized package to maintain backward compatibility
from .decorators import DecoratorRegistry
from .decorators import admin_endpoint
from .decorators import api_endpoint
from .decorators import initialize_decorators
from .decorators import public_endpoint
from .decorators import unified_auth
from .decorators import unified_cache
from .decorators import unified_monitoring
from .decorators import unified_rate_limit
from .decorators import unified_validation

# Re-export everything for backward compatibility
__all__ = [
    "DecoratorRegistry",
    "unified_cache",
    "unified_rate_limit",
    "unified_auth",
    "unified_monitoring",
    "unified_validation",
    "api_endpoint",
    "admin_endpoint",
    "public_endpoint",
    "initialize_decorators",
]

# Legacy global registry instance for backward compatibility
_registry = DecoratorRegistry()
