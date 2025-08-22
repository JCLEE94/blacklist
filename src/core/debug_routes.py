from flask import Flask, Blueprint, jsonify, request, redirect, url_for, render_template
import logging

logger = logging.getLogger(__name__)

# !/usr/bin/env python3
"""Debug routes for API testing"""

import sqlite3

debug_bp = Blueprint("debug", __name__, url_prefix="/api/debug")


@debug_bp.route("/raw-source-check", methods=["GET"])
def raw_source_check():
    """Raw database source check for debugging"""
    try:
        # 데이터베이스 직접 연결
        db_path = "/app/instance/blacklist.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 소스별 통계
        cursor.execute(
            """
            SELECT source, COUNT(*) as count
            FROM blacklist_entries
            WHERE is_active = 1
            GROUP BY source
        """
        )
        source_stats = {row["source"]: row["count"] for row in cursor.fetchall()}

        # 최근 5개 레코드 조회
        cursor.execute(
            """
            SELECT ip_address as ip, source, last_seen as detection_date, created_at, reason as attack_type, country
            FROM blacklist_entries
            WHERE is_active = 1
            ORDER BY created_at DESC
            LIMIT 5
        """
        )
        recent_records = []
        for row in cursor.fetchall():
            recent_records.append(
                {
                    "ip": row["ip"],
                    "source": row["source"],
                    "detection_date": row["detection_date"],
                    "created_at": row["created_at"],
                    "attack_type": row["attack_type"],
                    "country": row["country"],
                }
            )

        # REGTECH 데이터 샘플
        cursor.execute(
            """
            SELECT ip_address as ip, source, last_seen as detection_date
            FROM blacklist_entries
            WHERE source = 'REGTECH' AND is_active = 1
            LIMIT 3
        """
        )
        regtech_samples = []
        for row in cursor.fetchall():
            regtech_samples.append(
                {
                    "ip": row["ip"],
                    "source": row["source"],
                    "detection_date": row["detection_date"],
                }
            )

        # SECUDIUM 데이터 샘플
        cursor.execute(
            """
            SELECT ip_address as ip, source, last_seen as detection_date
            FROM blacklist_entries
            WHERE source = 'SECUDIUM' AND is_active = 1
            LIMIT 3
        """
        )
        secudium_samples = []
        for row in cursor.fetchall():
            secudium_samples.append(
                {
                    "ip": row["ip"],
                    "source": row["source"],
                    "detection_date": row["detection_date"],
                }
            )

        conn.close()

        return jsonify(
            {
                "success": True,
                "database_path": db_path,
                "source_statistics": source_stats,
                "recent_records": recent_records,
                "regtech_samples": regtech_samples,
                "secudium_samples": secudium_samples,
                "timestamp": "2025-07-05T16:30:00",
            }
        )

    except Exception as e:
        logger.error(f"Debug API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
