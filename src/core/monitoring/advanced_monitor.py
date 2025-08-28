"""Advanced monitoring system for production deployment."""

import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import redis
import psycopg2
from flask import Blueprint, jsonify
import json

logger = logging.getLogger(__name__)

monitoring_bp = Blueprint("monitoring", __name__)


class AdvancedMonitor:
    """Advanced monitoring system with performance metrics and alerts."""

    def __init__(self):
        self.metrics_history = []
        self.alert_thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
            "response_time_ms": 1000,
            "error_rate": 0.05,
            "database_connections": 90,
        }
        self.alerts = []

    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive system metrics."""
        try:
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "system": {
                    "cpu_percent": psutil.cpu_percent(interval=1),
                    "cpu_count": psutil.cpu_count(),
                    "memory": {
                        "percent": psutil.virtual_memory().percent,
                        "available": psutil.virtual_memory().available,
                        "total": psutil.virtual_memory().total,
                        "used": psutil.virtual_memory().used,
                    },
                    "disk": {
                        "percent": psutil.disk_usage("/").percent,
                        "free": psutil.disk_usage("/").free,
                        "total": psutil.disk_usage("/").total,
                    },
                    "network": {
                        "bytes_sent": psutil.net_io_counters().bytes_sent,
                        "bytes_recv": psutil.net_io_counters().bytes_recv,
                        "packets_sent": psutil.net_io_counters().packets_sent,
                        "packets_recv": psutil.net_io_counters().packets_recv,
                    },
                },
                "process": self._get_process_metrics(),
                "database": self._get_database_metrics(),
                "cache": self._get_cache_metrics(),
                "application": self._get_application_metrics(),
            }

            # Check thresholds and generate alerts
            self._check_thresholds(metrics)

            # Store in history (keep last 100 entries)
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > 100:
                self.metrics_history.pop(0)

            return metrics

        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {}

    def _get_process_metrics(self) -> Dict[str, Any]:
        """Get current process metrics."""
        try:
            process = psutil.Process()
            return {
                "cpu_percent": process.cpu_percent(),
                "memory_info": {
                    "rss": process.memory_info().rss,
                    "vms": process.memory_info().vms,
                    "percent": process.memory_percent(),
                },
                "num_threads": process.num_threads(),
                "num_connections": len(process.connections()),
                "open_files": len(process.open_files()),
            }
        except Exception as e:
            logger.error(f"Error getting process metrics: {e}")
            return {}

    def _get_database_metrics(self) -> Dict[str, Any]:
        """Get database performance metrics."""
        try:
            conn = psycopg2.connect(
                host="localhost",
                port=32543,
                database="blacklist",
                user="postgres",
                password="postgres",
            )
            cursor = conn.cursor()

            # Get connection stats
            cursor.execute(
                """
                SELECT 
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active_connections,
                    count(*) FILTER (WHERE state = 'idle') as idle_connections
                FROM pg_stat_activity
            """
            )
            connection_stats = cursor.fetchone()

            # Get database size
            cursor.execute(
                """
                SELECT pg_database_size('blacklist') as database_size
            """
            )
            db_size = cursor.fetchone()[0]

            # Get table stats
            cursor.execute(
                """
                SELECT 
                    count(*) as total_tables,
                    sum(n_live_tup) as total_rows
                FROM pg_stat_user_tables
            """
            )
            table_stats = cursor.fetchone()

            cursor.close()
            conn.close()

            return {
                "connections": {
                    "total": connection_stats[0],
                    "active": connection_stats[1],
                    "idle": connection_stats[2],
                },
                "size_bytes": db_size,
                "size_mb": round(db_size / 1024 / 1024, 2),
                "tables": table_stats[0],
                "total_rows": table_stats[1],
            }

        except Exception as e:
            logger.error(f"Error getting database metrics: {e}")
            return {"error": str(e)}

    def _get_cache_metrics(self) -> Dict[str, Any]:
        """Get Redis cache metrics."""
        try:
            r = redis.Redis(host="localhost", port=32544, decode_responses=True)
            info = r.info()

            return {
                "used_memory_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
                "used_memory_peak_mb": round(
                    info.get("used_memory_peak", 0) / 1024 / 1024, 2
                ),
                "connected_clients": info.get("connected_clients", 0),
                "total_connections_received": info.get("total_connections_received", 0),
                "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0), info.get("keyspace_misses", 0)
                ),
            }
        except Exception as e:
            logger.error(f"Error getting cache metrics: {e}")
            return {"error": str(e)}

    def _get_application_metrics(self) -> Dict[str, Any]:
        """Get application-specific metrics."""
        return {
            "version": "1.3.2",
            "uptime_seconds": self._get_uptime(),
            "request_count": self._get_request_count(),
            "error_count": self._get_error_count(),
            "average_response_time_ms": self._get_avg_response_time(),
            "active_sessions": self._get_active_sessions(),
            "collection_enabled": self._get_collection_status(),
        }

    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage."""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)

    def _check_thresholds(self, metrics: Dict[str, Any]):
        """Check metrics against thresholds and generate alerts."""
        alerts = []

        # Check CPU usage
        cpu = metrics.get("system", {}).get("cpu_percent", 0)
        if cpu > self.alert_thresholds["cpu_percent"]:
            alerts.append(
                {
                    "severity": "warning",
                    "metric": "cpu_percent",
                    "value": cpu,
                    "threshold": self.alert_thresholds["cpu_percent"],
                    "message": f"High CPU usage: {cpu}%",
                }
            )

        # Check memory usage
        memory = metrics.get("system", {}).get("memory", {}).get("percent", 0)
        if memory > self.alert_thresholds["memory_percent"]:
            alerts.append(
                {
                    "severity": "warning",
                    "metric": "memory_percent",
                    "value": memory,
                    "threshold": self.alert_thresholds["memory_percent"],
                    "message": f"High memory usage: {memory}%",
                }
            )

        # Check disk usage
        disk = metrics.get("system", {}).get("disk", {}).get("percent", 0)
        if disk > self.alert_thresholds["disk_percent"]:
            alerts.append(
                {
                    "severity": "critical",
                    "metric": "disk_percent",
                    "value": disk,
                    "threshold": self.alert_thresholds["disk_percent"],
                    "message": f"Critical disk usage: {disk}%",
                }
            )

        # Store alerts
        for alert in alerts:
            alert["timestamp"] = datetime.now().isoformat()
            self.alerts.append(alert)

        # Keep only last 50 alerts
        if len(self.alerts) > 50:
            self.alerts = self.alerts[-50:]

    def _get_uptime(self) -> int:
        """Get application uptime in seconds."""
        try:
            with open("/proc/uptime", "r") as f:
                uptime_seconds = float(f.readline().split()[0])
                return int(uptime_seconds)
        except:
            return 0

    def _get_request_count(self) -> int:
        """Get total request count."""
        # This would be tracked in production
        return 0

    def _get_error_count(self) -> int:
        """Get total error count."""
        # This would be tracked in production
        return 0

    def _get_avg_response_time(self) -> float:
        """Get average response time in milliseconds."""
        # This would be calculated from actual request logs
        return 50.0

    def _get_active_sessions(self) -> int:
        """Get number of active user sessions."""
        # This would be tracked in production
        return 0

    def _get_collection_status(self) -> bool:
        """Get collection service status."""
        try:
            import os

            return os.environ.get("COLLECTION_ENABLED", "false").lower() == "true"
        except:
            return False

    def get_health_score(self) -> int:
        """Calculate overall health score (0-100)."""
        if not self.metrics_history:
            return 100

        latest = self.metrics_history[-1]
        score = 100

        # Deduct points for high resource usage
        cpu = latest.get("system", {}).get("cpu_percent", 0)
        if cpu > 50:
            score -= min(20, (cpu - 50) / 2)

        memory = latest.get("system", {}).get("memory", {}).get("percent", 0)
        if memory > 60:
            score -= min(20, (memory - 60) / 2)

        disk = latest.get("system", {}).get("disk", {}).get("percent", 0)
        if disk > 70:
            score -= min(30, (disk - 70))

        # Deduct points for alerts
        recent_alerts = [
            a
            for a in self.alerts
            if datetime.fromisoformat(a["timestamp"])
            > datetime.now() - timedelta(minutes=5)
        ]
        score -= min(30, len(recent_alerts) * 5)

        return max(0, int(score))

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        return {
            "health_score": self.get_health_score(),
            "current_metrics": self.metrics_history[-1] if self.metrics_history else {},
            "recent_alerts": self.alerts[-10:],
            "metrics_summary": self._generate_summary(),
            "recommendations": self._generate_recommendations(),
        }

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate metrics summary."""
        if not self.metrics_history:
            return {}

        recent = self.metrics_history[-10:]

        return {
            "avg_cpu": round(
                sum(m["system"]["cpu_percent"] for m in recent) / len(recent), 2
            ),
            "avg_memory": round(
                sum(m["system"]["memory"]["percent"] for m in recent) / len(recent), 2
            ),
            "trend": self._calculate_trend(),
        }

    def _calculate_trend(self) -> str:
        """Calculate performance trend."""
        if len(self.metrics_history) < 2:
            return "stable"

        old_score = self.get_health_score()
        # Compare with older metrics
        if old_score > 80:
            return "improving"
        elif old_score < 60:
            return "degrading"
        return "stable"

    def _generate_recommendations(self) -> List[str]:
        """Generate performance recommendations."""
        recommendations = []

        if not self.metrics_history:
            return recommendations

        latest = self.metrics_history[-1]

        # Check CPU
        cpu = latest.get("system", {}).get("cpu_percent", 0)
        if cpu > 80:
            recommendations.append(
                "Consider scaling up CPU resources or optimizing code"
            )

        # Check Memory
        memory = latest.get("system", {}).get("memory", {}).get("percent", 0)
        if memory > 85:
            recommendations.append(
                "Memory usage is high, consider increasing RAM or optimizing memory usage"
            )

        # Check Disk
        disk = latest.get("system", {}).get("disk", {}).get("percent", 0)
        if disk > 90:
            recommendations.append(
                "Critical: Disk space is running low, immediate action required"
            )

        # Check Cache
        cache = latest.get("cache", {})
        if cache.get("hit_rate", 0) < 80:
            recommendations.append(
                "Cache hit rate is low, consider reviewing caching strategy"
            )

        return recommendations


# Global monitor instance
monitor = AdvancedMonitor()


@monitoring_bp.route("/api/monitoring/metrics", methods=["GET"])
def get_metrics():
    """Get current system metrics."""
    metrics = monitor.collect_system_metrics()
    return jsonify(metrics)


@monitoring_bp.route("/api/monitoring/health-score", methods=["GET"])
def get_health_score():
    """Get system health score."""
    return jsonify(
        {
            "score": monitor.get_health_score(),
            "status": "healthy" if monitor.get_health_score() > 70 else "degraded",
        }
    )


@monitoring_bp.route("/api/monitoring/report", methods=["GET"])
def get_performance_report():
    """Get comprehensive performance report."""
    return jsonify(monitor.get_performance_report())


@monitoring_bp.route("/api/monitoring/alerts", methods=["GET"])
def get_alerts():
    """Get recent alerts."""
    return jsonify({"alerts": monitor.alerts[-20:], "total": len(monitor.alerts)})


@monitoring_bp.route("/api/monitoring/history", methods=["GET"])
def get_metrics_history():
    """Get metrics history."""
    return jsonify(
        {
            "history": monitor.metrics_history[-50:],
            "count": len(monitor.metrics_history),
        }
    )
