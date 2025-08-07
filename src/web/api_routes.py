"""
Web API routes for Blacklist Manager
API endpoints for the web interface
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")


def get_stats() -> Dict[str, Any]:
    """Get system statistics with proper error handling"""
    try:
        stats_path = Path("data/stats.json")
        if stats_path.exists():
            with open(stats_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")

    # Return default stats if file doesn't exist or has errors
    return {
        "total_ips": 0,
        "active_ips": 0,
        "sources": {},
        "last_updated": datetime.now().isoformat(),
    }


@api_bp.route("/search", methods=["POST"])
def api_search():
    """IP search API endpoint"""
    try:
        data = request.get_json() or {}
        search_ip = data.get("ip", "").strip()
        search_type = data.get("type", "exact")  # exact, range, subnet

        if not search_ip:
            return jsonify({"success": False, "error": "IP address is required"}), 400

        # Mock search results
        results = []

        # Simple mock: if IP contains "192.168", return some results
        if "192.168" in search_ip or search_ip == "127.0.0.1":
            results = [
                {
                    "ip": search_ip,
                    "source": "REGTECH",
                    "country": "KR",
                    "attack_type": "Malware",
                    "detection_date": datetime.now().strftime("%Y-%m-%d"),
                    "is_active": True,
                }
            ]

        return jsonify(
            {
                "success": True,
                "results": results,
                "search_params": {
                    "ip": search_ip,
                    "type": search_type,
                },
                "count": len(results),
            }
        )

    except Exception as e:
        logger.error(f"Search API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/refresh-data", methods=["POST"])
def refresh_data():
    """Refresh data API endpoint"""
    try:
        # Mock refresh operation
        return jsonify(
            {
                "success": True,
                "message": "Data refresh completed",
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Refresh data error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/month/<month>")
def get_month_details(month):
    """Get details for a specific month"""
    try:
        # Mock monthly data
        mock_data = {
            "month": month,
            "total_ips": 1500,
            "sources": {
                "REGTECH": 800,
                "SECUDIUM": 700,
            },
            "daily_breakdown": [],
        }

        # Generate daily breakdown for the month
        start_date = datetime.strptime(f"{month}-01", "%Y-%m-%d")
        for day in range(1, 29):  # Simplified to 28 days
            current_date = start_date.replace(day=day)
            mock_data["daily_breakdown"].append(
                {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "count": 50 + (day % 10) * 5,  # Mock varying daily counts
                }
            )

        return jsonify(
            {
                "success": True,
                "data": mock_data,
            }
        )

    except Exception as e:
        logger.error(f"Month details error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/month/<month>/daily/<date>")
def get_daily_ips(month, date):
    """Get IPs for a specific date"""
    try:
        # Mock daily IP data
        mock_ips = []

        # Generate some mock IPs for the date
        for i in range(50):
            mock_ips.append(
                {
                    "ip": f"192.168.{i//10}.{i%10}",
                    "source": "REGTECH" if i % 2 == 0 else "SECUDIUM",
                    "country": "KR" if i % 3 == 0 else "US",
                    "attack_type": "Malware" if i % 2 == 0 else "Phishing",
                    "detection_date": date,
                }
            )

        return jsonify(
            {
                "success": True,
                "date": date,
                "ips": mock_ips,
                "count": len(mock_ips),
            }
        )

    except Exception as e:
        logger.error(f"Daily IPs error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/month/<month>/daily/<date>/download")
def download_daily_ips(month, date):
    """Download daily IPs as text file"""
    try:
        # Get daily IPs data
        daily_data = get_daily_ips(month, date)
        if not daily_data.get_json().get("success"):
            return jsonify({"success": False, "error": "Failed to get daily data"}), 500

        ips_data = daily_data.get_json()["ips"]

        # Create text content
        text_lines = []
        text_lines.append(f"# Blacklist IPs for {date}")
        text_lines.append(
            f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        text_lines.append(f"# Total IPs: {len(ips_data)}")
        text_lines.append("#" + "=" * 50)
        text_lines.append("")

        for ip_info in ips_data:
            text_lines.append(
                f"{ip_info['ip']}  # {ip_info['source']} - {ip_info['attack_type']}"
            )

        content = "\n".join(text_lines)

        from flask import Response

        return Response(
            content,
            mimetype="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename=blacklist_{date}.txt"
            },
        )

    except Exception as e:
        logger.error(f"Download daily IPs error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/export/<format>")
def export_data(format):
    """Export data in various formats"""
    try:
        stats = get_stats()

        if format == "json":
            return jsonify(
                {
                    "success": True,
                    "data": stats,
                    "export_time": datetime.now().isoformat(),
                }
            )
        elif format == "csv":
            # Simple CSV export
            csv_lines = [
                "Source,Count,Percentage",
            ]

            total = stats.get("total_ips", 0)
            for source, count in stats.get("sources", {}).items():
                percentage = round((count / total) * 100, 2) if total > 0 else 0
                csv_lines.append(f"{source},{count},{percentage}%")

            csv_content = "\n".join(csv_lines)

            from flask import Response

            return Response(
                csv_content,
                mimetype="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=blacklist_stats.csv"
                },
            )
        else:
            return jsonify({"success": False, "error": "Unsupported format"}), 400

    except Exception as e:
        logger.error(f"Export error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/stats-simple")
def api_stats_simple():
    """Simple stats API endpoint"""
    try:
        stats = get_stats()

        # Simplified stats format
        simple_stats = {
            "total": stats.get("total_ips", 0),
            "active": stats.get("active_ips", 0),
            "sources": len(stats.get("sources", {})),
            "last_update": stats.get("last_updated", datetime.now().isoformat()),
        }

        return jsonify(simple_stats)

    except Exception as e:
        logger.error(f"Simple stats error: {e}")
        return jsonify({"total": 0, "active": 0, "sources": 0, "error": str(e)}), 500
