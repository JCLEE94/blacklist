"""Recent detections API for PostgreSQL database."""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import os

logger = logging.getLogger(__name__)

recent_detections_bp = Blueprint("recent_detections", __name__)


def get_db_connection():
    """Get PostgreSQL database connection."""
    try:
        # Docker environment
        if os.getenv("FLASK_ENV") == "production" or os.path.exists("/.dockerenv"):
            conn = psycopg2.connect(
                host="postgresql",  # Docker service name
                port=5432,
                database=os.getenv("POSTGRES_DB", "blacklist"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "postgres"),
                cursor_factory=RealDictCursor,
            )
        else:
            # Local development
            conn = psycopg2.connect(
                host="localhost",
                port=32544,  # External PostgreSQL port
                database="blacklist",
                user="postgres",
                password="postgres",
                cursor_factory=RealDictCursor,
            )
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None


@recent_detections_bp.route("/api/blacklist/recent", methods=["GET"])
def get_recent_detections():
    """Get recent IP detections from PostgreSQL."""
    try:
        conn = get_db_connection()
        if not conn:
            # Fallback to SQLite if PostgreSQL not available
            return get_sqlite_detections()

        cursor = conn.cursor()

        # Query recent blacklist entries
        query = """
            SELECT 
                ip_address,
                threat_level,
                source,
                detected_at,
                description,
                category
            FROM blacklist_entries
            WHERE detected_at >= NOW() - INTERVAL '7 days'
            ORDER BY detected_at DESC
            LIMIT 20
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        if not rows:
            # Try simpler query
            query = """
                SELECT 
                    ip_address,
                    'HIGH' as threat_level,
                    COALESCE(source, 'SYSTEM') as source,
                    COALESCE(created_at, NOW()) as detected_at
                FROM blacklist_entries
                ORDER BY created_at DESC
                LIMIT 20
            """
            cursor.execute(query)
            rows = cursor.fetchall()

        cursor.close()
        conn.close()

        # Format response
        detections = []
        for row in rows:
            detections.append(
                {
                    "ip_address": row.get("ip_address", ""),
                    "threat_level": row.get("threat_level", "HIGH"),
                    "source": row.get("source", "SYSTEM"),
                    "detected_at": row.get("detected_at", datetime.now()).isoformat()
                    if isinstance(row.get("detected_at"), datetime)
                    else str(row.get("detected_at")),
                    "description": row.get("description", ""),
                    "category": row.get("category", "malicious"),
                }
            )

        return jsonify(
            {
                "success": True,
                "recent_detections": detections,
                "total": len(detections),
                "database": "postgresql",
            }
        )

    except Exception as e:
        logger.error(f"Error getting recent detections: {e}")
        return get_sqlite_detections()


def get_sqlite_detections():
    """Fallback to SQLite database."""
    try:
        import sqlite3

        # Try to get data from SQLite
        db_path = "instance/blacklist.db"
        if not os.path.exists(db_path):
            return jsonify(
                {
                    "success": False,
                    "recent_detections": [],
                    "message": "No database available",
                }
            )

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query blacklist table
        cursor.execute(
            """
            SELECT 
                ip_address,
                threat_level,
                source,
                detection_date as detected_at
            FROM blacklist
            ORDER BY detection_date DESC
            LIMIT 20
        """
        )

        rows = cursor.fetchall()

        detections = []
        for row in rows:
            detections.append(
                {
                    "ip_address": row["ip_address"],
                    "threat_level": row.get("threat_level", "HIGH"),
                    "source": row.get("source", "BLACKLIST"),
                    "detected_at": row.get("detected_at", datetime.now().isoformat()),
                }
            )

        cursor.close()
        conn.close()

        return jsonify(
            {
                "success": True,
                "recent_detections": detections,
                "total": len(detections),
                "database": "sqlite",
            }
        )

    except Exception as e:
        logger.error(f"SQLite fallback failed: {e}")
        return jsonify({"success": False, "recent_detections": [], "message": str(e)})


@recent_detections_bp.route("/api/blacklist/stats", methods=["GET"])
def get_blacklist_stats():
    """Get blacklist statistics from PostgreSQL."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = conn.cursor()

        # Get statistics
        stats = {}

        # Total IPs
        cursor.execute("SELECT COUNT(*) as total FROM blacklist_entries")
        stats["total_ips"] = cursor.fetchone()["total"]

        # IPs by source
        cursor.execute(
            """
            SELECT source, COUNT(*) as count 
            FROM blacklist_entries 
            GROUP BY source
        """
        )
        stats["by_source"] = {row["source"]: row["count"] for row in cursor.fetchall()}

        # IPs by threat level
        cursor.execute(
            """
            SELECT threat_level, COUNT(*) as count 
            FROM blacklist_entries 
            WHERE threat_level IS NOT NULL
            GROUP BY threat_level
        """
        )
        stats["by_threat_level"] = {
            row["threat_level"]: row["count"] for row in cursor.fetchall()
        }

        # Recent 24h additions
        cursor.execute(
            """
            SELECT COUNT(*) as count 
            FROM blacklist_entries 
            WHERE detected_at >= NOW() - INTERVAL '24 hours'
        """
        )
        stats["last_24h"] = cursor.fetchone()["count"]

        cursor.close()
        conn.close()

        return jsonify(
            {"success": True, "stats": stats, "timestamp": datetime.now().isoformat()}
        )

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"error": str(e)}), 500
