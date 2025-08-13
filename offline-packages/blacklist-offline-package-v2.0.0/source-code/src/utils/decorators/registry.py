"""
Decorator Registry - Central dependency management for all decorators
"""

import logging

logger = logging.getLogger(__name__)


class DecoratorRegistry:
    """Central registry for all application decorators"""

    def __init__(self):
        self._cache = None
        self._auth_manager = None
        self._rate_limiter = None
        self._metrics = None

    def set_dependencies(
        self, cache=None, auth_manager=None, rate_limiter=None, metrics=None
    ):
        """Set shared dependencies for decorators"""
        self._cache = cache
        self._auth_manager = auth_manager
        self._rate_limiter = rate_limiter
        self._metrics = metrics

    @property
    def cache(self):
        """Get cache instance"""
        return self._cache

    @property
    def auth_manager(self):
        """Get auth manager instance"""
        return self._auth_manager

    @property
    def rate_limiter(self):
        """Get rate limiter instance"""
        return self._rate_limiter

    @property
    def metrics(self):
        """Get metrics instance"""
        return self._metrics


# Global registry instance
_registry = DecoratorRegistry()


def get_registry() -> DecoratorRegistry:
    """Get the global decorator registry instance"""
    return _registry


def initialize_decorators(
    cache=None, auth_manager=None, rate_limiter=None, metrics=None
):
    """Initialize the decorator registry with dependencies"""
    _registry.set_dependencies(cache, auth_manager, rate_limiter, metrics)
