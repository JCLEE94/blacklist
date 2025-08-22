"""
Web data routes for Blacklist Manager
Data export, analytics and real-time features
"""

from flask import Flask, Blueprint, jsonify, request, redirect, url_for, render_template
import logging
logger = logging.getLogger(__name__)

from datetime import datetime, timedelta



data_bp = Blueprint("data", __name__, url_prefix="/api")


@data_bp.route("/ips/recent")
def api_ips_recent():
    """Recent IPs API"""
    try:
        limit = request.args.get("limit", 50, type=int)
        limit = min(limit, 200)  # Cap at 200

        # Mock recent IPs data
        recent_ips = []
        for i in range(limit):
            days_ago = i // 10
            recent_ips.append(
                {
                    "ip": "192.168.{i//10}.{i%10}",
                    "source": "REGTECH" if i % 2 == 0 else "SECUDIUM",
                    "country": "KR" if i % 3 == 0 else "US",
                    "attack_type": "Malware" if i % 2 == 0 else "Phishing",
                    "detection_date": (
                        datetime.now() - timedelta(days=days_ago)
                    ).strftime("%Y-%m-%d"),
                    "added_at": (datetime.now() - timedelta(hours=i)).strftime(
                        "%H:%M:%S"
                    ),
                    "is_active": True,
                }
            )

        return jsonify(
            {
                "success": True,
                "ips": recent_ips,
                "count": len(recent_ips),
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Recent IPs error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "ips": [],
                }
            ),
            500,
        )


@data_bp.route("/ips/daily-stats")
def api_daily_stats():
    """Daily statistics API"""
    try:
        days = request.args.get("days", 7, type=int)
        days = min(days, 30)  # Cap at 30 days

        # Mock daily stats
        daily_stats = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            daily_stats.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "new_ips": 50 + (i % 10) * 5,  # Mock varying daily counts
                    "sources": {
                        "REGTECH": 30 + (i % 5) * 3,
                        "SECUDIUM": 20 + (i % 7) * 2,
                    },
                    "countries": {
                        "KR": 25 + (i % 3) * 5,
                        "US": 15 + (i % 4) * 3,
                        "CN": 10 + (i % 2) * 2,
                    },
                }
            )

        # Reverse to show oldest first
        daily_stats.reverse()

        return jsonify(
            {
                "success": True,
                "daily_stats": daily_stats,
                "period_days": days,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Daily stats error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "daily_stats": [],
                }
            ),
            500,
        )


@data_bp.route("/ips/by-date/<date>")
def api_ips_by_date(date):
    """Get IPs by specific date"""
    try:
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Invalid date format. Use YYYY-MM-DD",
                    }
                ),
                400,
            )

        # Mock IPs for the date
        mock_ips = []
        for i in range(75):  # Mock 75 IPs for the date
            mock_ips.append(
                {
                    "ip": "10.0.{i//10}.{i%10}",
                    "source": "REGTECH" if i % 2 == 0 else "SECUDIUM",
                    "country": ["KR", "US", "CN", "JP"][i % 4],
                    "attack_type": ["Malware", "Phishing", "Spam", "Botnet"][i % 4],
                    "detection_date": date,
                    "severity": ["high", "medium", "low"][i % 3],
                }
            )

        return jsonify(
            {
                "success": True,
                "date": date,
                "ips": mock_ips,
                "count": len(mock_ips),
                "summary": {
                    "by_source": {
                        "REGTECH": len(
                            [ip for ip in mock_ips if ip["source"] == "REGTECH"]
                        ),
                        "SECUDIUM": len(
                            [ip for ip in mock_ips if ip["source"] == "SECUDIUM"]
                        ),
                    },
                    "by_country": {
                        country: len(
                            [ip for ip in mock_ips if ip["country"] == country]
                        )
                        for country in ["KR", "US", "CN", "JP"]
                    },
                },
            }
        )

    except Exception as e:
        logger.error(f"IPs by date error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                }
            ),
            500,
        )


@data_bp.route("/realtime/status")
def realtime_status():
    """Real-time system status"""
    try:
        # Mock real-time status
        status = {
            "system": {
                "status": "running",
                "uptime": "2 days, 5 hours",
                "memory_usage": 68.5,
                "cpu_usage": 23.8,
                "active_connections": 5,
            },
            "collections": {
                "regtech": {
                    "status": "idle",
                    "last_run": "2024-01-15 10:30:00",
                    "next_run": "2024-01-16 10:30:00",
                },
                "secudium": {
                    "status": "idle",
                    "last_run": "2024-01-15 09:45:00",
                    "next_run": "2024-01-16 09:45:00",
                },
            },
            "database": {
                "status": "connected",
                "size": "245 MB",
                "records": 2100,
                "last_backup": "2024-01-15 02:00:00",
            },
            "api": {
                "requests_today": 1547,
                "avg_response_time": "142ms",
                "error_rate": 0.2,
            },
        }

        return jsonify(
            {
                "success": True,
                "status": status,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Realtime status error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                }
            ),
            500,
        )


@data_bp.route("/realtime/feed")
def realtime_feed():
    """Real-time activity feed"""
    try:
        # Mock real-time activity feed
        activities = []

        # Generate recent activities
        activity_types = [
            ("ip_added", "New IP added to blacklist"),
            ("collection_completed", "Data collection completed"),
            ("api_request", "API request processed"),
            ("system_check", "System health check"),
            ("data_export", "Data export completed"),
        ]

        for i in range(20):  # Last 20 activities
            activity_type, base_message = activity_types[i % len(activity_types)]
            timestamp = datetime.now() - timedelta(minutes=i * 2)

            activity = {
                "id": i + 1,
                "type": activity_type,
                "message": base_message,
                "timestamp": timestamp.isoformat(),
                "time_ago": "{i*2} minutes ago" if i > 0 else "just now",
            }

            # Add type-specific details
            if activity_type == "ip_added":
                activity["details"] = {
                    "ip": "192.168.1.{i+100}",
                    "source": "REGTECH" if i % 2 == 0 else "SECUDIUM",
                }
            elif activity_type == "collection_completed":
                activity["details"] = {
                    "source": "REGTECH" if i % 2 == 0 else "SECUDIUM",
                    "count": 50 + (i % 10) * 5,
                }

            activities.append(activity)

        return jsonify(
            {
                "success": True,
                "activities": activities,
                "count": len(activities),
                "last_update": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Realtime feed error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "activities": [],
                }
            ),
            500,
        )


@data_bp.route("/blacklist/active-simple")
def api_blacklist_active_simple():
    """Simple active blacklist API"""
    try:
        # Mock active IPs
        active_ips = []
        for i in range(100):  # Mock 100 active IPs
            active_ips.append("10.0.{i//10}.{i%10}")

        return "\n".join(active_ips), 200, {"Content-Type": "text/plain"}

    except Exception as e:
        logger.error(f"Active blacklist simple error: {e}")
        return "Error: {str(e)}", 500


@data_bp.route("/fortigate-simple")
def api_fortigate_simple():
    """Simple FortiGate format API"""
    try:
        # Mock FortiGate format
        active_ips = []
        for i in range(100):
            active_ips.append("10.0.{i//10}.{i%10}")

        fortigate_data = {
            "type": "IP",
            "version": 1,
            "data": active_ips,
        }

        return jsonify(fortigate_data)

    except Exception as e:
        logger.error(f"FortiGate simple error: {e}")
        return jsonify({"error": str(e)}), 500
