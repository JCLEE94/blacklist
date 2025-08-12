#!/usr/bin/env python3
"""
Serialization Manager for Advanced Cache
"""

import gzip
import json
import logging
import pickle
from typing import Any
from typing import Dict

try:
    import orjson

    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False

logger = logging.getLogger(__name__)


class SerializationManager:
    """Handles serialization and compression for cache data"""

    def __init__(
        self, enable_compression: bool = True, compression_threshold: int = 1024
    ):
        self.enable_compression = enable_compression
        self.compression_threshold = compression_threshold
        self.stats = {
            "serializations": 0,
            "deserializations": 0,
            "compressions": 0,
            "compression_ratio": 0.0,
        }

    def serialize(self, value: Any) -> bytes:
        """Serialize value with optional compression"""
        try:
            # Choose serialization method based on type
            if isinstance(value, (dict, list)):
                if HAS_ORJSON:
                    data = orjson.dumps(value)
                else:
                    data = json.dumps(value, ensure_ascii=False).encode("utf-8")
            else:
                data = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)

            self.stats["serializations"] += 1

            # Apply compression if enabled and data is large enough
            if self.enable_compression and len(data) > self.compression_threshold:
                compressed = gzip.compress(data, compresslevel=6)
                compression_ratio = len(compressed) / len(data)

                if compression_ratio < 0.9:  # Only use if compression is effective
                    self.stats["compressions"] += 1
                    self.stats["compression_ratio"] = (
                        self.stats["compression_ratio"] * 0.9 + compression_ratio * 0.1
                    )
                    return b"compressed:" + compressed

            return data

        except Exception as e:
            logger.error(f"Serialization error for value type {type(value)}: {e}")
            # Fallback to pickle
            return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)

    def deserialize(self, data: bytes) -> Any:
        """Deserialize data with decompression support"""
        try:
            self.stats["deserializations"] += 1

            # Handle compressed data
            if data.startswith(b"compressed:"):
                compressed_data = data[11:]  # Remove "compressed:" prefix
                data = gzip.decompress(compressed_data)

            # Try JSON first (most common for API data)
            try:
                if HAS_ORJSON:
                    return orjson.loads(data)
                else:
                    return json.loads(data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError, orjson.JSONDecodeError):
                pass

            # Fallback to pickle
            return pickle.loads(data)

        except Exception as e:
            logger.error(f"Deserialization error: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get serialization statistics"""
        return {
            "serialization_stats": self.stats.copy(),
            "compression_enabled": self.enable_compression,
            "compression_threshold_bytes": self.compression_threshold,
            "orjson_available": HAS_ORJSON,
        }

    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            "serializations": 0,
            "deserializations": 0,
            "compressions": 0,
            "compression_ratio": 0.0,
        }
