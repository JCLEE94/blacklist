#!/usr/bin/env python3
"""
Collection service for managing data collection
"""
import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class CollectionService:
    """Service for managing blacklist data collection"""

    def __init__(self):
        self.status = {
            "enabled": True,
            "sources": {
                "regtech": {
                    "enabled": True,
                    "last_run": None,
                    "status": "ready",
                    "total_collected": 0,
                    "last_error": None,
                },
                "secudium": {
                    "enabled": True,
                    "last_run": None,
                    "status": "ready",
                    "total_collected": 0,
                    "last_error": None,
                },
            },
        }

        # Environment variables for collectors
        self.env = os.environ.copy()
        self.env.update(
            {
                "REGTECH_USERNAME": os.getenv("REGTECH_USERNAME", "nextrade"),
                "REGTECH_PASSWORD": os.getenv("REGTECH_PASSWORD", "Sprtmxm1@3"),
                "SECUDIUM_USERNAME": os.getenv("SECUDIUM_USERNAME", "nextrade"),
                "SECUDIUM_PASSWORD": os.getenv("SECUDIUM_PASSWORD", "Sprtmxm1@3"),
            }
        )

    def get_status(self):
        """Get current collection status"""
        return self.status

    def enable_collection(self):
        """Enable all collection sources"""
        self.status["enabled"] = True
        for source in self.status["sources"]:
            self.status["sources"][source]["enabled"] = True
        return {
            "status": "enabled",
            "message": "Collection enabled successfully",
            "timestamp": datetime.now().isoformat(),
        }

    def disable_collection(self):
        """Disable all collection sources"""
        self.status["enabled"] = False
        for source in self.status["sources"]:
            self.status["sources"][source]["enabled"] = False
        return {
            "status": "disabled",
            "message": "Collection disabled successfully",
            "timestamp": datetime.now().isoformat(),
        }

    def trigger_regtech(self, params=None):
        """Trigger REGTECH collection"""
        if (
            not self.status["enabled"]
            or not self.status["sources"]["regtech"]["enabled"]
        ):
            return {"success": False, "error": "REGTECH collection is disabled"}

        try:
            # Update status
            self.status["sources"]["regtech"]["status"] = "running"
            self.status["sources"]["regtech"]["last_run"] = datetime.now().isoformat()

            # Prepare command
            cmd = ["python3", "/app/scripts/collection/collect_regtech_simple.py"]

            if params:
                if params.get("start_date"):
                    cmd.extend(["--start-date", params["start_date"]])
                if params.get("end_date"):
                    cmd.extend(["--end-date", params["end_date"]])

            # Run collector
            logger.info(f"Running REGTECH collector: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=self.env,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                # Parse output for count
                try:
                    lines = result.stdout.strip().split("\n")
                    for line in lines:
                        if "collected" in line.lower():
                            # Extract number from line
                            import re

                            match = re.search(r"\d+", line)
                            if match:
                                count = int(match.group())
                                self.status["sources"]["regtech"][
                                    "total_collected"
                                ] += count
                except Exception:
                    pass

                self.status["sources"]["regtech"]["status"] = "completed"
                self.status["sources"]["regtech"]["last_error"] = None

                return {
                    "success": True,
                    "message": "REGTECH collection completed",
                    "output": result.stdout[-1000:] if result.stdout else "No output",
                }
            else:
                self.status["sources"]["regtech"]["status"] = "error"
                self.status["sources"]["regtech"]["last_error"] = (
                    result.stderr or "Unknown error"
                )

                return {
                    "success": False,
                    "error": result.stderr or "Collection failed",
                    "output": result.stdout[-1000:] if result.stdout else None,
                }

        except subprocess.TimeoutExpired:
            self.status["sources"]["regtech"]["status"] = "timeout"
            self.status["sources"]["regtech"]["last_error"] = "Collection timeout"
            return {"success": False, "error": "Collection timeout after 5 minutes"}
        except Exception as e:
            self.status["sources"]["regtech"]["status"] = "error"
            self.status["sources"]["regtech"]["last_error"] = str(e)
            logger.error(f"REGTECH collection error: {e}")
            return {"success": False, "error": str(e)}

    def trigger_secudium(self, params=None):
        """Trigger SECUDIUM collection"""
        if (
            not self.status["enabled"]
            or not self.status["sources"]["secudium"]["enabled"]
        ):
            return {"success": False, "error": "SECUDIUM collection is disabled"}

        try:
            # Update status
            self.status["sources"]["secudium"]["status"] = "running"
            self.status["sources"]["secudium"]["last_run"] = datetime.now().isoformat()

            # Prepare command
            cmd = ["python3", "/app/scripts/collection/secudium_api_collector.py"]

            collection_type = "blackip"
            if params:
                collection_type = params.get("collection_type", "blackip")
                cmd.extend(["--type", collection_type])

                if (
                    collection_type == "blackip"
                    and params.get("start_date")
                    and params.get("end_date")
                ):
                    cmd.extend(["--start-date", params["start_date"]])
                    cmd.extend(["--end-date", params["end_date"]])

            # Run collector
            logger.info(f"Running SECUDIUM collector: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=self.env,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                # Parse output for count
                try:
                    if "SUCCESS" in result.stdout:
                        import re

                        match = re.search(r"총 (\d+)개", result.stdout)
                        if match:
                            count = int(match.group(1))
                            self.status["sources"]["secudium"][
                                "total_collected"
                            ] += count
                except Exception:
                    pass

                self.status["sources"]["secudium"]["status"] = "completed"
                self.status["sources"]["secudium"]["last_error"] = None

                return {
                    "success": True,
                    "message": "SECUDIUM collection completed",
                    "output": result.stdout[-1000:] if result.stdout else "No output",
                }
            else:
                self.status["sources"]["secudium"]["status"] = "error"
                self.status["sources"]["secudium"]["last_error"] = (
                    result.stderr or "Unknown error"
                )

                return {
                    "success": False,
                    "error": result.stderr or "Collection failed",
                    "output": result.stdout[-1000:] if result.stdout else None,
                }

        except subprocess.TimeoutExpired:
            self.status["sources"]["secudium"]["status"] = "timeout"
            self.status["sources"]["secudium"]["last_error"] = "Collection timeout"
            return {"success": False, "error": "Collection timeout after 5 minutes"}
        except Exception as e:
            self.status["sources"]["secudium"]["status"] = "error"
            self.status["sources"]["secudium"]["last_error"] = str(e)
            logger.error(f"SECUDIUM collection error: {e}")
            return {"success": False, "error": str(e)}


# Global instance
_collection_service = None


def get_collection_service():
    """Get or create collection service instance"""
    global _collection_service
    if _collection_service is None:
        _collection_service = CollectionService()
    return _collection_service
