"""
Async to Sync wrapper utility for collectors
"""

import asyncio
from typing import Any, Callable, Dict


def async_to_sync(async_func: Callable) -> Callable:
    """Convert async function to sync function"""

    def wrapper(*args, **kwargs) -> Any:
        loop = None
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # Create new event loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the async function
        return loop.run_until_complete(async_func(*args, **kwargs))

    return wrapper


class SyncCollectorWrapper:
    """Wrapper to make async collectors work in sync context"""

    def __init__(self, async_collector):
        self.async_collector = async_collector

    def collect(self, **kwargs) -> Dict[str, Any]:
        """Synchronous collect method"""
        return async_to_sync(self.async_collector.collect)(**kwargs)

    def __getattr__(self, name):
        """Proxy other attributes to the wrapped collector"""
        return getattr(self.async_collector, name)
