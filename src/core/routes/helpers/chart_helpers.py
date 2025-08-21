"""
Chart data formatting helpers.
Provides chart data transformation for collection dashboard.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def format_chart_data(daily_stats: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Format daily statistics for chart display.

    Args:
        daily_stats: List of daily statistics

    Returns:
        Formatted chart data with labels and datasets
    """
    try:
        chart_data = {
            "labels": [],
            "datasets": [
                {
                    "label": "REGTECH",
                    "data": [],
                    "borderColor": "#4CAF50",
                    "backgroundColor": "rgba(76, 175, 80, 0.1)",
                },
                {
                    "label": "SECUDIUM",
                    "data": [],
                    "borderColor": "#2196F3",
                    "backgroundColor": "rgba(33, 150, 243, 0.1)",
                },
            ],
        }

        # Generate default data if no stats available
        if not daily_stats:
            return _generate_default_chart_data()

        # Process actual statistics
        for stat in daily_stats:
            chart_data["labels"].append(stat.get("date", ""))

            sources = stat.get("sources", {})
            regtech_count = sources.get("regtech", 0)
            secudium_count = sources.get("secudium", 0)

            chart_data["datasets"][0]["data"].append(regtech_count)
            chart_data["datasets"][1]["data"].append(secudium_count)

        return chart_data

    except Exception as e:
        logger.error(f"Error formatting chart data: {e}")
        return _generate_default_chart_data()


def _generate_default_chart_data() -> Dict[str, Any]:
    """Generate default chart data for last 7 days.

    Returns:
        Default chart data structure
    """
    today = datetime.now()
    default_data = {
        "labels": [
            (today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)
        ],
        "datasets": [
            {
                "label": "REGTECH",
                "data": [0, 0, 0, 0, 0, 0, 0],
                "borderColor": "#4CAF50",
                "backgroundColor": "rgba(76, 175, 80, 0.1)",
            },
            {
                "label": "SECUDIUM",
                "data": [0, 0, 0, 0, 0, 0, 0],
                "borderColor": "#2196F3",
                "backgroundColor": "rgba(33, 150, 243, 0.1)",
            },
        ],
    }
    return default_data
