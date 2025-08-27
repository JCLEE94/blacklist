import logging

from flask import Blueprint, render_template

logger = logging.getLogger(__name__)

#!/usr/bin/env python3
"""
Dashboard fix - Working dashboard route with highest priority
"""


# Create blueprint with no prefix for highest priority
dashboard_fix_bp = Blueprint("dashboard_fix", __name__)


@dashboard_fix_bp.route("/dashboard", methods=["GET"])
def fixed_dashboard():
    """Working dashboard using the original dashboard.html template"""
    try:
        # Get current stats for template context
        from datetime import datetime

        from ..services.unified_service_factory import get_unified_service

        service = get_unified_service()
        stats = service.get_system_health()

        # Prepare template context with actual data
        template_data = {
            "total_ips": stats.get("total_ips", 0),
            "active_ips": stats.get("active_ips", 0),
            "regtech_count": stats.get("regtech_count", 0),
            "secudium_count": stats.get("secudium_count", 0),
            "public_count": stats.get("public_count", 0),
            "active_sources": ["REGTECH"] if stats.get("regtech_count", 0) > 0 else [],
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "system_status": stats.get("status", "healthy"),
        }

        # Use the original dashboard.html template with data
        return render_template("dashboard.html", **template_data)
    except Exception as e:
        # Return simple working HTML as fallback
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dashboard - Blacklist Management</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; margin: 40px; background: #0f0f23; color: #cccccc;">
            <h1 style="color: #4a90e2;">🎛️ Blacklist Management Dashboard</h1>
            <p>Dashboard loading error - using fallback</p>
            <div style="margin: 20px 0;">
                <h3>Error Details:</h3>
                <p style="color: #ff6b6b;">❌ Error: {str(e)}</p>
            </div>
            <div style="margin: 20px 0;">
                <h3>Quick Links:</h3>
                <ul>
                    <li><a href="/unified-control" style="color: #4a90e2;">Unified Control Panel</a></li>
                    <li><a href="/api/health" style="color: #4a90e2;">System Health</a></li>
                    <li><a href="/test" style="color: #4a90e2;">Test Page</a></li>
                </ul>
            </div>
        </body>
        </html>
        """


@dashboard_fix_bp.route("/", methods=["GET"])
def fixed_root():
    """Working root route redirect to dashboard"""
    return fixed_dashboard()
