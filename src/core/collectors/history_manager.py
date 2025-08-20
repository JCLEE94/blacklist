#!/usr/bin/env python3
"""
Collection History Management Module

Handles collection history storage, retrieval, and statistics generation.

Sample input: collection_result={"source": "regtech", "ip_count": 100, "timestamp": "2024-01-01"}
Expected output: History entry stored with metadata and statistics available
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class HistoryManager:
    """Handles collection history management"""

    def __init__(self, history_file: Path):
        """Initialize history manager"""
        self.history_file = history_file
        self.history_file.parent.mkdir(exist_ok=True)
        self.collection_history = self._load_collection_history()

    def _load_collection_history(self) -> List[Dict[str, Any]]:
        """Load collection history from file"""
        try:
            if not self.history_file.exists():
                logger.info(f"No history file found, creating new one: {self.history_file}")
                return []
                
            with open(self.history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
                
            if not isinstance(history, list):
                logger.warning("Invalid history format, resetting to empty list")
                return []
                
            logger.info(f"Loaded {len(history)} history entries")
            return history
            
        except Exception as e:
            logger.error(f"Failed to load collection history: {e}")
            return []

    def _save_collection_history(self, history: Optional[List[Dict[str, Any]]] = None):
        """Save collection history to file"""
        try:
            history_to_save = history if history is not None else self.collection_history
            
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(history_to_save, f, indent=2, ensure_ascii=False)
                
            logger.debug(f"Saved {len(history_to_save)} history entries")
            
        except Exception as e:
            logger.error(f"Failed to save collection history: {e}")

    def add_to_history(self, result: Dict[str, Any]):
        """Add collection result to history"""
        try:
            # Add timestamp if not present
            if "timestamp" not in result:
                result["timestamp"] = datetime.now().isoformat()
                
            # Add to history
            self.collection_history.append(result)
            
            # Keep only last 1000 entries to prevent unlimited growth
            max_entries = 1000
            if len(self.collection_history) > max_entries:
                self.collection_history = self.collection_history[-max_entries:]
                logger.info(f"Trimmed history to {max_entries} entries")
                
            # Save to file
            self._save_collection_history()
            
            logger.info(f"Added history entry for {result.get('source', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Failed to add history entry: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Generate statistics from collection history"""
        try:
            if not self.collection_history:
                return {
                    "total_collections": 0,
                    "sources": {},
                    "last_collection": None,
                    "success_rate": 0.0,
                    "total_ips_collected": 0
                }

            # Basic statistics
            total_collections = len(self.collection_history)
            successful_collections = sum(1 for entry in self.collection_history 
                                       if entry.get("status") == "success")
            success_rate = (successful_collections / total_collections) * 100

            # Source-specific statistics
            sources = {}
            total_ips = 0
            
            for entry in self.collection_history:
                source = entry.get("source", "unknown")
                if source not in sources:
                    sources[source] = {
                        "collections": 0,
                        "successful": 0,
                        "total_ips": 0,
                        "last_collection": None
                    }
                
                sources[source]["collections"] += 1
                if entry.get("status") == "success":
                    sources[source]["successful"] += 1
                    
                ip_count = entry.get("ip_count", 0)
                sources[source]["total_ips"] += ip_count
                total_ips += ip_count
                
                # Update last collection time
                timestamp = entry.get("timestamp")
                if timestamp and (not sources[source]["last_collection"] or 
                                timestamp > sources[source]["last_collection"]):
                    sources[source]["last_collection"] = timestamp

            # Calculate success rates for each source
            for source_stats in sources.values():
                if source_stats["collections"] > 0:
                    source_stats["success_rate"] = (
                        source_stats["successful"] / source_stats["collections"]
                    ) * 100
                else:
                    source_stats["success_rate"] = 0.0

            # Find last collection time
            last_collection = None
            if self.collection_history:
                timestamps = [entry.get("timestamp") for entry in self.collection_history 
                            if entry.get("timestamp")]
                if timestamps:
                    last_collection = max(timestamps)

            return {
                "total_collections": total_collections,
                "successful_collections": successful_collections,
                "success_rate": round(success_rate, 2),
                "sources": sources,
                "last_collection": last_collection,
                "total_ips_collected": total_ips
            }

        except Exception as e:
            logger.error(f"Failed to generate statistics: {e}")
            return {
                "total_collections": 0,
                "sources": {},
                "last_collection": None,
                "success_rate": 0.0,
                "total_ips_collected": 0,
                "error": str(e)
            }

    def get_recent_entries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent history entries"""
        return self.collection_history[-limit:] if self.collection_history else []

    def get_entries_by_source(self, source: str, limit: int = None) -> List[Dict[str, Any]]:
        """Get history entries for specific source"""
        source_entries = [entry for entry in self.collection_history 
                         if entry.get("source") == source]
        
        if limit:
            return source_entries[-limit:]
        return source_entries

    def clear_history(self) -> bool:
        """Clear all history entries"""
        try:
            self.collection_history = []
            self._save_collection_history()
            logger.info("Collection history cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
            return False


if __name__ == "__main__":
    # Validation function
    from tempfile import TemporaryDirectory
    
    with TemporaryDirectory() as temp_dir:
        history_file = Path(temp_dir) / "test_history.json"
        history_mgr = HistoryManager(history_file)
        
        # Test 1: Add history entries
        test_result1 = {
            "source": "regtech",
            "status": "success",
            "ip_count": 100,
            "timestamp": "2024-01-01T10:00:00"
        }
        
        test_result2 = {
            "source": "secudium",
            "status": "success", 
            "ip_count": 50,
            "timestamp": "2024-01-01T11:00:00"
        }
        
        history_mgr.add_to_history(test_result1)
        history_mgr.add_to_history(test_result2)
        
        # Test 2: Get statistics
        stats = history_mgr.get_statistics()
        assert stats["total_collections"] == 2, "Total collections mismatch"
        assert stats["total_ips_collected"] == 150, "Total IPs mismatch"
        assert "regtech" in stats["sources"], "Regtech source missing"
        
        # Test 3: Get recent entries
        recent = history_mgr.get_recent_entries(1)
        assert len(recent) == 1, "Recent entries count mismatch"
        assert recent[0]["source"] == "secudium", "Recent entry source mismatch"
        
        # Test 4: Get entries by source
        regtech_entries = history_mgr.get_entries_by_source("regtech")
        assert len(regtech_entries) == 1, "Source entries count mismatch"
        
        print("✅ History manager validation complete")
