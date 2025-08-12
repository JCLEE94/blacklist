"""
Unified Decorators Package - Modularized decorator functionality
Maintains backward compatibility with the original unified_decorators module
"""

# Import all decorators to maintain backward compatibility
from .auth import unified_auth
from .cache import unified_cache
from .convenience import admin_endpoint, api_endpoint, public_endpoint
# Monitoring decorator removed for performance optimization
def unified_monitoring(operation_name=None):
    """Dummy monitoring decorator for backward compatibility"""
    def decorator(func):
        return func
    return decorator
from .rate_limit import unified_rate_limit
from .registry import DecoratorRegistry, initialize_decorators
from .validation import unified_validation

# Export all public interfaces
__all__ = [
    # Core decorators
    "unified_cache",
    "unified_auth",
    "unified_monitoring",  # Dummy implementation
    "unified_validation",
    "unified_rate_limit",
    # Convenience decorators
    "api_endpoint",
    "admin_endpoint", 
    "public_endpoint",
    # Registry
    "DecoratorRegistry",
    "initialize_decorators",
]

# Global registry instance for backward compatibility
_registry = None


def get_registry():
    """Get the global decorator registry instance"""
    global _registry
    if _registry is None:
        from .registry import DecoratorRegistry

        _registry = DecoratorRegistry()
    return _registry
