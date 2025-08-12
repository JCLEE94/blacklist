#!/usr/bin/env python3
"""
Memory Backend for Advanced Cache
"""

import threading
import time
from collections import OrderedDict
from typing import Any
from typing import Dict
from typing import List
from typing import Optional


class MemoryBackend:
    """In-memory backend for cache operations with LRU eviction"""

    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self.lock = threading.RLock()

        # Use OrderedDict for LRU implementation
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0,
        }

    def get(self, key: str) -> Optional[bytes]:
        """Get value from memory cache"""
        with self.lock:
            if key not in self._cache:
                self.stats["misses"] += 1
                return None

            entry = self._cache[key]

            # Check expiration
            if entry["expires_at"] and time.time() > entry["expires_at"]:
                del self._cache[key]
                self.stats["misses"] += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self.stats["hits"] += 1
            return entry["value"]

    def set(self, key: str, value: bytes, ttl: Optional[int] = None) -> bool:
        """Set value in memory cache"""
        with self.lock:
            expires_at = None
            if ttl is not None:
                expires_at = time.time() + ttl

            # Update existing key or add new one
            self._cache[key] = {
                "value": value,
                "expires_at": expires_at,
                "created_at": time.time(),
            }

            # Move to end (most recently used)
            self._cache.move_to_end(key)

            # Enforce max entries limit
            self._enforce_limit()

            self.stats["sets"] += 1
            return True

    def delete(self, key: str) -> bool:
        """Delete key from memory cache"""
        with self.lock:
            if key in self._cache:
                del self._cache[key]
                self.stats["deletes"] += 1
                return True
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern (simple wildcard support)"""
        with self.lock:
            # Convert shell-style wildcards to simple matching
            if "*" in pattern:
                prefix = pattern.replace("*", "")
                keys_to_delete = [
                    key for key in self._cache.keys() if key.startswith(prefix)
                ]
            else:
                keys_to_delete = [key for key in self._cache.keys() if key == pattern]

            for key in keys_to_delete:
                del self._cache[key]
                self.stats["deletes"] += 1

            return len(keys_to_delete)

    def exists(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        with self.lock:
            if key not in self._cache:
                return False

            entry = self._cache[key]
            if entry["expires_at"] and time.time() > entry["expires_at"]:
                del self._cache[key]
                return False

            return True

    def clear_all(self) -> bool:
        """Clear all keys from memory cache"""
        with self.lock:
            self._cache.clear()
            return True

    def get_keys_by_pattern(self, pattern: str) -> List[str]:
        """Get all keys matching pattern"""
        with self.lock:
            if "*" in pattern:
                prefix = pattern.replace("*", "")
                return [
                    key
                    for key in self._cache.keys()
                    if key.startswith(prefix) and self.exists(key)
                ]
            else:
                return [
                    key
                    for key in self._cache.keys()
                    if key == pattern and self.exists(key)
                ]

    def _enforce_limit(self):
        """Enforce maximum entries limit using LRU eviction"""
        while len(self._cache) > self.max_entries:
            # Remove least recently used item
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self.stats["evictions"] += 1

    def cleanup_expired(self) -> int:
        """Clean up expired entries and return count of removed items"""
        with self.lock:
            current_time = time.time()
            expired_keys = [
                key
                for key, entry in self._cache.items()
                if entry["expires_at"] and current_time > entry["expires_at"]
            ]

            for key in expired_keys:
                del self._cache[key]

            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get memory cache statistics"""
        with self.lock:
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = (
                (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            )

            # Calculate memory usage estimate
            memory_usage = 0
            for entry in self._cache.values():
                memory_usage += len(entry["value"]) if entry["value"] else 0

            return {
                "backend": "memory",
                "status": "connected",
                "entries_count": len(self._cache),
                "max_entries": self.max_entries,
                "memory_usage_bytes": memory_usage,
                "hit_rate_percent": round(hit_rate, 2),
                "total_requests": total_requests,
                "operations": self.stats.copy(),
            }

    def get_info(self) -> Dict[str, Any]:
        """Get backend information"""
        return {
            "backend_type": "memory",
            "max_entries": self.max_entries,
            "current_entries": len(self._cache),
            "thread_safe": True,
            "persistent": False,
        }

    def health_check(self) -> Dict[str, Any]:
        """Perform memory backend health check"""
        try:
            # Test basic operations
            test_key = "health_check_test"
            test_value = b"ok"

            self.set(test_key, test_value, ttl=1)
            retrieved = self.get(test_key)
            self.delete(test_key)

            success = retrieved == test_value

            return {
                "status": "healthy" if success else "unhealthy",
                "available": True,
                "test_passed": success,
                "entries_count": len(self._cache),
                "max_entries": self.max_entries,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "available": False,
                "error": str(e),
            }
