"""
Collection status helper functions.
Provides statistics and availability data for collection management.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def get_source_collection_stats(service) -> Dict[str, Any]:
    """Get collection statistics by source.
    
    Args:
        service: Unified service instance
        
    Returns:
        Dict containing source statistics
    """
    try:
        regtech_status = (
            service.get_regtech_status()
            if hasattr(service, "get_regtech_status")
            else {}
        )

        stats = {
            "REGTECH": {
                "name": "REGTECH",
                "status": regtech_status.get("status", "unknown"),
                "total_ips": regtech_status.get("total_ips", 0),
                "last_collection": regtech_status.get("last_collection_time"),
                "success_rate": calculate_success_rate("REGTECH", 7),
                "enabled": True,
            },
            "SECUDIUM": {
                "name": "SECUDIUM",
                "status": "disabled",
                "total_ips": 0,
                "last_collection": None,
                "success_rate": 0,
                "enabled": False,
            },
        }

        return stats

    except Exception as e:
        logger.error(f"Error getting source stats: {e}")
        return {}


def get_period_availability_cache() -> Dict[str, Dict[str, Any]]:
    """Get cached period availability data.
    
    Returns:
        Dict containing availability data for different time periods
    """
    try:
        # Period availability test results (cached)
        availability = {
            "1일": {"available": False, "ip_count": 0},
            "1주일": {"available": False, "ip_count": 0},
            "2주일": {"available": True, "ip_count": 30},
            "1개월": {"available": True, "ip_count": 930},
            "3개월": {"available": True, "ip_count": 930},
            "6개월": {"available": True, "ip_count": 930},
            "1년": {"available": True, "ip_count": 930},
        }

        return availability

    except Exception as e:
        logger.error(f"Error getting period availability: {e}")
        return {}


def calculate_success_rate(source: str, days: int) -> float:
    """Calculate success rate for a source.
    
    Args:
        source: Source name (REGTECH, SECUDIUM)
        days: Number of days to calculate rate for
        
    Returns:
        Success rate as percentage
    """
    try:
        # TODO: Implement actual log table queries
        if source == "REGTECH":
            return 92.5
        elif source == "SECUDIUM":
            return 0.0
        else:
            return 0.0

    except Exception as e:
        logger.error(f"Error calculating success rate: {e}")
        return 0.0
