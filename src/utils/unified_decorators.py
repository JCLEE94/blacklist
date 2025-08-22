"""
Unified Decorators - Backward compatibility wrapper for modularized decorators

This module maintains backward compatibility while delegating to modular
decorator packages
"""

# Import all decorators from the modularized package to maintain backward
# compatibility
from .decorators import (
    DecoratorRegistry,
    admin_endpoint,
    api_endpoint,
    initialize_decorators,
    public_endpoint,
    unified_auth,
    unified_cache,
    unified_monitoring,
    unified_rate_limit,
    unified_validation,
)

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
