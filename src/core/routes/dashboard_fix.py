#!/usr/bin/env python3
"""
Dashboard fix - Working dashboard route with highest priority
"""

from flask import Blueprint, render_template

# Create blueprint with no prefix for highest priority
dashboard_fix_bp = Blueprint("dashboard_fix", __name__)


@dashboard_fix_bp.route("/dashboard", methods=["GET"])
def fixed_dashboard():
    """Working dashboard using the original dashboard.html template"""
    try:
        # Use the original dashboard.html template
        return render_template("dashboard.html")
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