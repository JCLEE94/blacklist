"""Core Services Mock Classes for Testing"""

import os
import tempfile
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest


class MockUnifiedService:
    """Mock Unified Service for testing"""

    def __init__(self):
        self.enabled = True
        self.last_collection = None
        self.blacklist_data = [
            {
                "ip_address": "192.168.1.1",
                "source": "REGTECH",
                "threat_level": "high",
                "is_active": True,
                "first_seen": "2025-08-01",
            },
            {
                "ip_address": "192.168.1.2",
                "source": "SECUDIUM",
                "threat_level": "medium",
                "is_active": True,
                "first_seen": "2025-08-02",
            },
        ]

    def get_active_ips(self):
        return ["192.168.1.1", "192.168.1.2", "10.0.0.1"]

    def get_blacklist_data(self, include_inactive=False):
        return [
            {
                "ip_address": "192.168.1.1",
                "source": "REGTECH",
                "threat_level": "high",
                "is_active": True,
                "first_seen": "2025-08-01",
            },
            {
                "ip_address": "192.168.1.2",
                "source": "SECUDIUM",
                "threat_level": "medium",
                "is_active": True,
                "first_seen": "2025-08-02",
            },
        ]

    def get_collection_status(self):
        return {
            "enabled": self.enabled,
            "last_collection": self.last_collection,
            "total_entries": len(self.blacklist_data),
            "sources": {
                "REGTECH": {"active": True, "last_sync": "2025-08-15T10:00:00Z"},
                "SECUDIUM": {"active": True, "last_sync": "2025-08-15T10:30:00Z"},
            },
        }

    def enable_collection(self):
        self.enabled = True
        return {"status": "success", "message": "Collection enabled"}

    def disable_collection(self):
        self.enabled = False
        return {"status": "success", "message": "Collection disabled"}

    def trigger_collection(self, source=None):
        if not self.enabled:
            return {"status": "error", "message": "Collection is disabled"}

        self.last_collection = "2025-08-15T12:00:00Z"
        return {
            "status": "success",
            "message": f"Collection triggered for {source or 'all sources'}",
            "timestamp": self.last_collection,
        }

    def get_statistics(self, period="30d"):
        return {
            "total_ips": 1500,
            "active_ips": 1200,
            "sources": {
                "REGTECH": 800,
                "SECUDIUM": 700,
            },
            "period": period,
        }

    def reset_data(self):
        self.blacklist_data = []
        return {"status": "success", "message": "Data reset successfully"}

    def health_check(self):
        return {
            "status": "healthy",
            "services": {
                "database": "ok",
                "cache": "ok",
                "collectors": "ok",
            },
        }

    def get_fortigate_data(self):
        ips = self.get_active_ips()
        return "\n".join(ips)

    def get_enhanced_blacklist(self):
        return self.get_blacklist_data(include_inactive=False)

    def get_ip_details(self, ip_address):
        for entry in self.get_blacklist_data():
            if entry["ip_address"] == ip_address:
                return entry
        return None

    def search_ips(self, query):
        results = []
        for entry in self.get_blacklist_data():
            if query in entry["ip_address"] or query in entry["source"]:
                results.append(entry)
        return results

    def export_data(self, format_type="json"):
        data = self.get_blacklist_data()
        if format_type == "csv":
            return "ip_address,source,threat_level,is_active,first_seen\n" + "\n".join(
                [
                    f"{entry['ip_address']},{entry['source']},{entry['threat_level']},{entry['is_active']},{entry['first_seen']}"
                    for entry in data
                ]
            )
        return data

    def get_analytics_summary(self, period="30d"):
        """Get analytics summary for the specified period"""
        return {
            "total_entries": len(self.blacklist_data),
            "active_entries": len(
                [e for e in self.blacklist_data if e.get("is_active", True)]
            ),
            "sources": {
                "REGTECH": 800,
                "SECUDIUM": 700,
            },
            "threat_levels": {
                "high": 500,
                "medium": 700,
                "low": 300,
            },
            "period": period,
            "last_updated": "2025-08-15T12:00:00Z",
        }

    def get_trends_analysis(self, period="7d"):
        """Get trends analysis for the specified period"""
        return {
            "trend_direction": "increasing",
            "change_percentage": 15.5,
            "period": period,
            "daily_trends": [
                {"date": "2025-08-09", "count": 1450},
                {"date": "2025-08-10", "count": 1470},
                {"date": "2025-08-11", "count": 1490},
                {"date": "2025-08-12", "count": 1500},
                {"date": "2025-08-13", "count": 1520},
                {"date": "2025-08-14", "count": 1540},
                {"date": "2025-08-15", "count": 1500},
            ],
            "sources_trend": {
                "REGTECH": {"change": 10.2, "direction": "increasing"},
                "SECUDIUM": {"change": 8.7, "direction": "increasing"},
            },
        }


class MockBlacklistManager:
    """Mock Blacklist Manager for testing"""

    def __init__(self):
        self.active_ips = ["192.168.1.1", "192.168.1.2", "10.0.0.1"]
        self.blacklist_data = [
            {
                "id": 1,
                "ip_address": "192.168.1.1",
                "source": "REGTECH",
                "threat_level": "high",
                "is_active": True,
                "first_seen": "2025-08-01",
                "last_seen": "2025-08-15",
                "detection_count": 5,
            },
            {
                "id": 2,
                "ip_address": "192.168.1.2",
                "source": "SECUDIUM",
                "threat_level": "medium",
                "is_active": True,
                "first_seen": "2025-08-02",
                "last_seen": "2025-08-15",
                "detection_count": 3,
            },
        ]

    def get_active_blacklist_ips(self):
        return self.active_ips

    def get_blacklist_data(self, include_inactive=False):
        if include_inactive:
            return self.blacklist_data
        return [entry for entry in self.blacklist_data if entry["is_active"]]

    def add_ip(self, ip_address, source, threat_level="medium"):
        new_entry = {
            "id": len(self.blacklist_data) + 1,
            "ip_address": ip_address,
            "source": source,
            "threat_level": threat_level,
            "is_active": True,
            "first_seen": "2025-08-15",
            "last_seen": "2025-08-15",
            "detection_count": 1,
        }
        self.blacklist_data.append(new_entry)
        if ip_address not in self.active_ips:
            self.active_ips.append(ip_address)
        return new_entry

    def remove_ip(self, ip_address):
        self.blacklist_data = [
            entry for entry in self.blacklist_data if entry["ip_address"] != ip_address
        ]
        if ip_address in self.active_ips:
            self.active_ips.remove(ip_address)
        return True

    def update_ip_status(self, ip_address, is_active):
        for entry in self.blacklist_data:
            if entry["ip_address"] == ip_address:
                entry["is_active"] = is_active
                if not is_active and ip_address in self.active_ips:
                    self.active_ips.remove(ip_address)
                elif is_active and ip_address not in self.active_ips:
                    self.active_ips.append(ip_address)
                return entry
        return None


class MockCacheManager:
    """Mock Cache Manager for testing"""

    def __init__(self):
        self.cache = {}
        self.hits = 0
        self.misses = 0

    def get(self, key):
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None

    def set(self, key, value, ttl=300):
        self.cache[key] = value
        return True

    def delete(self, key):
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def clear(self):
        self.cache = {}
        self.hits = 0
        self.misses = 0
        return True

    def get_stats(self):
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "cache_size": len(self.cache),
        }

    def flush_expired(self):
        # Mock implementation - in real cache, this would remove expired entries
        expired_count = max(0, len(self.cache) - 100)  # Mock: keep only 100 entries
        if expired_count > 0:
            keys_to_remove = list(self.cache.keys())[:expired_count]
            for key in keys_to_remove:
                del self.cache[key]
        return expired_count


class MockCollectionManager:
    """Mock Collection Manager for testing"""

    def __init__(self):
        self.enabled = True
        self.last_collection = None
        self.sources = {
            "REGTECH": {"active": True, "last_sync": None, "status": "ready"},
            "SECUDIUM": {"active": True, "last_sync": None, "status": "ready"},
        }
        self.collection_history = []

    def is_enabled(self):
        return self.enabled

    def enable(self):
        self.enabled = True
        return {"status": "success", "message": "Collection enabled"}

    def disable(self):
        self.enabled = False
        return {"status": "success", "message": "Collection disabled"}

    def get_status(self):
        return {
            "enabled": self.enabled,
            "last_collection": self.last_collection,
            "sources": self.sources,
            "history_count": len(self.collection_history),
        }

    def trigger_collection(self, source=None):
        if not self.enabled:
            return {"status": "error", "message": "Collection is disabled"}

        timestamp = "2025-08-15T12:00:00Z"
        self.last_collection = timestamp

        if source:
            if source in self.sources:
                self.sources[source]["last_sync"] = timestamp
                self.sources[source]["status"] = "completed"
                collection_result = {
                    "status": "success",
                    "source": source,
                    "timestamp": timestamp,
                    "collected_count": 50,
                }
            else:
                return {"status": "error", "message": f"Unknown source: {source}"}
        else:
            # Collect from all sources
            for src in self.sources:
                self.sources[src]["last_sync"] = timestamp
                self.sources[src]["status"] = "completed"
            collection_result = {
                "status": "success",
                "source": "all",
                "timestamp": timestamp,
                "collected_count": 100,
            }

        self.collection_history.append(collection_result)
        return collection_result

    def get_collection_history(self, limit=10):
        return self.collection_history[-limit:]

    def get_source_status(self, source):
        return self.sources.get(source, {"status": "unknown"})

    def reset_source_status(self, source):
        if source in self.sources:
            self.sources[source] = {
                "active": True,
                "last_sync": None,
                "status": "ready",
            }
            return True
        return False

    def validate_credentials(self, source):
        if source in self.sources:
            return {"status": "valid", "source": source}
        return {"status": "invalid", "source": source}

    def test_connection(self, source):
        if source in self.sources:
            return {
                "status": "success",
                "source": source,
                "response_time": 150,  # ms
                "message": "Connection successful",
            }
        return {
            "status": "error",
            "source": source,
            "message": "Unknown source",
        }

    def get_collection_logs(self, source=None, limit=50):
        logs = [
            {
                "timestamp": "2025-08-15T10:00:00Z",
                "source": "REGTECH",
                "level": "INFO",
                "message": "Collection started",
            },
            {
                "timestamp": "2025-08-15T10:05:00Z",
                "source": "REGTECH",
                "level": "INFO",
                "message": "Collected 50 IPs",
            },
            {
                "timestamp": "2025-08-15T10:30:00Z",
                "source": "SECUDIUM",
                "level": "INFO",
                "message": "Collection started",
            },
            {
                "timestamp": "2025-08-15T10:35:00Z",
                "source": "SECUDIUM",
                "level": "INFO",
                "message": "Collected 50 IPs",
            },
        ]

        if source:
            logs = [log for log in logs if log["source"] == source]

        return logs[-limit:]

    def collect_from_regtech(self):
        """Mock REGTECH collection method"""
        if not self.enabled:
            return {"status": "error", "message": "Collection is disabled"}

        timestamp = "2025-08-15T12:00:00Z"
        self.sources["REGTECH"]["last_sync"] = timestamp
        self.sources["REGTECH"]["status"] = "completed"

        result = {
            "status": "success",
            "source": "REGTECH",
            "timestamp": timestamp,
            "collected_count": 50,
            "new_ips": 25,
            "updated_ips": 15,
            "errors": 0,
        }

        self.collection_history.append(result)
        return result

    def collect_from_secudium(self):
        """Mock SECUDIUM collection method"""
        if not self.enabled:
            return {"status": "error", "message": "Collection is disabled"}

        timestamp = "2025-08-15T12:00:00Z"
        self.sources["SECUDIUM"]["last_sync"] = timestamp
        self.sources["SECUDIUM"]["status"] = "completed"

        result = {
            "status": "success",
            "source": "SECUDIUM",
            "timestamp": timestamp,
            "collected_count": 50,
            "new_ips": 30,
            "updated_ips": 10,
            "errors": 0,
        }

        self.collection_history.append(result)
        return result
