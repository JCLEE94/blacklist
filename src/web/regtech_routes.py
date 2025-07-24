#!/usr/bin/env python3
"""
REGTECH 데이터 분석 웹 라우트
"""

import json
import os
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, render_template, request

# pandas는 선택적으로 import (호환성 문제시 None으로 설정)
try:
    import pandas as pd
except ImportError:
    pd = None

regtech_bp = Blueprint("regtech", __name__, url_prefix="/regtech")


class RegtechAnalyzer:
    def __init__(self, db_path=None):
        if db_path is None:
            # Try multiple possible paths
            possible_paths = [
                "instance/blacklist.db",
                "../instance/blacklist.db",
                "../../instance/blacklist.db",
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    self.db_path = path
                    break
            else:
                self.db_path = "instance/blacklist.db"  # fallback
        else:
            self.db_path = db_path

    def get_regtech_stats(self):
        """REGTECH 기본 통계"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 기본 통계
            cursor.execute("SELECT COUNT(*) FROM blacklist_ip WHERE source = 'REGTECH'")
            total_ips = cursor.fetchone()[0]

            # 최근 업데이트 시간
            cursor.execute(
                """
                SELECT MAX(created_at) FROM blacklist_ip
                WHERE source = 'REGTECH'
            """
            )
            last_updated = cursor.fetchone()[0]

            # 위험도별 분포 (메타데이터에서 추출)
            cursor.execute(
                """
                SELECT metadata FROM blacklist_ip
                WHERE source = 'REGTECH' AND metadata IS NOT NULL
                LIMIT 1000
            """
            )

            risk_distribution = {"high": 0, "medium": 0, "low": 0}
            region_distribution = defaultdict(int)

            for row in cursor.fetchall():
                try:
                    metadata = json.loads(row[0])
                    if "ip_analysis" in metadata:
                        risk = metadata["ip_analysis"].get("risk_level", "low")
                        region = metadata["ip_analysis"].get(
                            "estimated_region", "Unknown"
                        )
                        risk_distribution[risk] += 1
                        region_distribution[region] += 1
                except:
                    risk_distribution["low"] += 1

            conn.close()

            return {
                "total_ips": total_ips,
                "last_updated": last_updated,
                "risk_distribution": dict(risk_distribution),
                "region_distribution": dict(region_distribution),
            }

        except Exception as e:
            return {"error": str(e)}

    def get_ip_trends(self, days=30):
        """일자별 IP 추이 분석"""
        try:
            conn = sqlite3.connect(self.db_path)

            # 날짜별 데이터 (created_at 기준)
            query = """
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM blacklist_ip
                WHERE source = 'REGTECH'
                AND created_at >= datetime('now', '-{} days')
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            """.format(
                days
            )

            if pd is not None:
                df = pd.read_sql_query(query, conn)
                conn.close()

                # 데이터 변환
                trends = []
                for _, row in df.iterrows():
                    trends.append({"date": row["date"], "count": row["count"]})
            else:
                # pandas 없이 직접 처리
                cursor = conn.cursor()
                cursor.execute(query)
                trends = []
                for row in cursor.fetchall():
                    trends.append({"date": row[0], "count": row[1]})
                conn.close()

            return trends

        except Exception as e:
            return []

    def get_top_ip_ranges(self, limit=20):
        """상위 IP 대역 분석"""
        try:
            conn = sqlite3.connect(self.db_path)

            query = """
                SELECT
                    SUBSTR(ip, 1, INSTR(ip, '.') - 1) as first_octet,
                    COUNT(*) as count
                FROM blacklist_ip
                WHERE source = 'REGTECH'
                GROUP BY first_octet
                ORDER BY count DESC
                LIMIT ?
            """

            cursor = conn.cursor()
            cursor.execute(query, (limit,))

            ranges = []
            for row in cursor.fetchall():
                ranges.append({"range": f"{row[0]}.x.x.x", "count": row[1]})

            conn.close()
            return ranges

        except Exception as e:
            return []

    def search_ips(self, search_term, limit=100):
        """IP 검색"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if search_term:
                query = """
                    SELECT ip, attack_type, detection_date, metadata
                    FROM blacklist_ip
                    WHERE source = 'REGTECH' AND ip LIKE ?
                    ORDER BY ip ASC
                    LIMIT ?
                """
                cursor.execute(query, (f"%{search_term}%", limit))
            else:
                query = """
                    SELECT ip, attack_type, detection_date, metadata
                    FROM blacklist_ip
                    WHERE source = 'REGTECH'
                    ORDER BY ip ASC
                    LIMIT ?
                """
                cursor.execute(query, (limit,))

            results = []
            for row in cursor.fetchall():
                # 메타데이터에서 추가 정보 추출
                metadata = {}
                try:
                    metadata = json.loads(row[3]) if row[3] else {}
                except:
                    pass

                ip_analysis = metadata.get("ip_analysis", {})

                results.append(
                    {
                        "ip": row[0],
                        "attack_type": row[1],
                        "detection_date": row[2],
                        "risk_level": ip_analysis.get("risk_level", "unknown"),
                        "region": ip_analysis.get("estimated_region", "unknown"),
                        "first_octet": ip_analysis.get("first_octet", 0),
                    }
                )

            conn.close()
            return results

        except Exception as e:
            return []

    def get_collection_history(self):
        """수집 이력 분석"""
        try:
            # 백업 파일들에서 수집 이력 추출
            backup_dir = "data/raw_backup/regtech"
            history = []

            if os.path.exists(backup_dir):
                for filename in os.listdir(backup_dir):
                    if filename.startswith("regtech_mass_final_"):
                        filepath = os.path.join(backup_dir, filename)
                        try:
                            with open(filepath, "r", encoding="utf-8") as f:
                                data = json.load(f)
                                history.append(
                                    {
                                        "timestamp": data.get("timestamp", ""),
                                        "total_ips": data.get("total_ips", 0),
                                        "method": data.get("collection_method", ""),
                                        "filename": filename,
                                    }
                                )
                        except:
                            continue

            # 시간순 정렬
            history.sort(key=lambda x: x["timestamp"], reverse=True)
            return history[:10]  # 최근 10개

        except Exception as e:
            return []


# 라우트 정의
@regtech_bp.route("/")
def dashboard():
    """REGTECH 대시보드"""
    analyzer = RegtechAnalyzer()
    stats = analyzer.get_regtech_stats()
    return render_template("regtech/dashboard.html", stats=stats)


@regtech_bp.route("/api/stats")
def api_stats():
    """기본 통계 API"""
    analyzer = RegtechAnalyzer()
    return jsonify(analyzer.get_regtech_stats())


@regtech_bp.route("/api/trends")
def api_trends():
    """추이 분석 API"""
    days = request.args.get("days", 30, type=int)
    analyzer = RegtechAnalyzer()
    return jsonify(analyzer.get_ip_trends(days))


@regtech_bp.route("/api/top-ranges")
def api_top_ranges():
    """상위 IP 대역 API"""
    limit = request.args.get("limit", 20, type=int)
    analyzer = RegtechAnalyzer()
    return jsonify(analyzer.get_top_ip_ranges(limit))


@regtech_bp.route("/api/search")
def api_search():
    """IP 검색 API"""
    search_term = request.args.get("q", "")
    limit = request.args.get("limit", 100, type=int)
    analyzer = RegtechAnalyzer()
    return jsonify(analyzer.search_ips(search_term, limit))


@regtech_bp.route("/api/collection-history")
def api_collection_history():
    """수집 이력 API"""
    analyzer = RegtechAnalyzer()
    return jsonify(analyzer.get_collection_history())


@regtech_bp.route("/analysis")
def analysis():
    """상세 분석 페이지"""
    return render_template("regtech/analysis.html")


@regtech_bp.route("/search")
def search():
    """검색 페이지"""
    return render_template("regtech/search.html")


@regtech_bp.route("/trends")
def trends():
    """추이 분석 페이지"""
    return render_template("regtech/trends.html")
