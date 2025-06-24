"""
Real-time System Monitoring
Provides system health monitoring, performance metrics, and alerting
"""

import logging
import psutil
import threading
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import deque, defaultdict

logger = logging.getLogger(__name__)

class SystemMonitor:
    """Real-time system monitoring with metrics collection"""
    
    def __init__(self, history_size=100, alert_thresholds=None):
        self.history_size = history_size
        self.metrics_history = defaultdict(lambda: deque(maxlen=history_size))
        self.alert_thresholds = alert_thresholds or {
            'cpu_percent': 80,
            'memory_percent': 85,
            'disk_percent': 90,
            'response_time_ms': 5000
        }
        self.alerts = deque(maxlen=50)
        self.monitoring_active = False
        self.monitor_thread = None
        
    def start_monitoring(self, interval=30):
        """Start background monitoring thread"""
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop, 
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("System monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("System monitoring stopped")
    
    def _monitoring_loop(self, interval):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                metrics = self.collect_metrics()
                self._check_alerts(metrics)
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(interval)
    
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        try:
            timestamp = datetime.now()
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free_gb = disk.free / (1024**3)
            
            # Network metrics (basic)
            network = psutil.net_io_counters()
            
            # Process count
            process_count = len(psutil.pids())
            
            metrics = {
                'timestamp': timestamp.isoformat(),
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count
                },
                'memory': {
                    'percent': memory_percent,
                    'available_gb': round(memory_available_gb, 2),
                    'used_gb': round((memory.total - memory.available) / (1024**3), 2),
                    'total_gb': round(memory.total / (1024**3), 2)
                },
                'disk': {
                    'percent': disk_percent,
                    'free_gb': round(disk_free_gb, 2),
                    'used_gb': round(disk.used / (1024**3), 2),
                    'total_gb': round(disk.total / (1024**3), 2)
                },
                'network': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                },
                'processes': process_count
            }
            
            # Store in history
            for key, value in metrics.items():
                if key != 'timestamp':
                    self.metrics_history[key].append({
                        'timestamp': timestamp,
                        'value': value
                    })
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return {}
    
    def _check_alerts(self, metrics: Dict[str, Any]):
        """Check metrics against alert thresholds"""
        try:
            alerts_triggered = []
            
            # CPU alert
            cpu_percent = metrics.get('cpu', {}).get('percent', 0)
            if cpu_percent > self.alert_thresholds['cpu_percent']:
                alerts_triggered.append({
                    'type': 'cpu_high',
                    'message': f'High CPU usage: {cpu_percent:.1f}%',
                    'severity': 'warning' if cpu_percent < 90 else 'critical',
                    'value': cpu_percent,
                    'threshold': self.alert_thresholds['cpu_percent']
                })
            
            # Memory alert
            memory_percent = metrics.get('memory', {}).get('percent', 0)
            if memory_percent > self.alert_thresholds['memory_percent']:
                alerts_triggered.append({
                    'type': 'memory_high',
                    'message': f'High memory usage: {memory_percent:.1f}%',
                    'severity': 'warning' if memory_percent < 95 else 'critical',
                    'value': memory_percent,
                    'threshold': self.alert_thresholds['memory_percent']
                })
            
            # Disk alert
            disk_percent = metrics.get('disk', {}).get('percent', 0)
            if disk_percent > self.alert_thresholds['disk_percent']:
                alerts_triggered.append({
                    'type': 'disk_high',
                    'message': f'High disk usage: {disk_percent:.1f}%',
                    'severity': 'warning' if disk_percent < 95 else 'critical',
                    'value': disk_percent,
                    'threshold': self.alert_thresholds['disk_percent']
                })
            
            # Store alerts
            for alert in alerts_triggered:
                alert['timestamp'] = datetime.now().isoformat()
                self.alerts.append(alert)
                logger.warning(f"Alert: {alert['message']}")
            
        except Exception as e:
            logger.error(f"Alert checking error: {e}")
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current system status summary"""
        try:
            metrics = self.collect_metrics()
            
            # Calculate status
            cpu_percent = metrics.get('cpu', {}).get('percent', 0)
            memory_percent = metrics.get('memory', {}).get('percent', 0)
            disk_percent = metrics.get('disk', {}).get('percent', 0)
            
            # Determine overall health
            health_score = 100
            issues = []
            
            if cpu_percent > 80:
                health_score -= 20
                issues.append(f"High CPU: {cpu_percent:.1f}%")
            
            if memory_percent > 85:
                health_score -= 25
                issues.append(f"High Memory: {memory_percent:.1f}%")
            
            if disk_percent > 90:
                health_score -= 30
                issues.append(f"High Disk: {disk_percent:.1f}%")
            
            # Determine status
            if health_score >= 80:
                status = "healthy"
            elif health_score >= 60:
                status = "warning"
            else:
                status = "critical"
            
            return {
                'status': status,
                'health_score': max(0, health_score),
                'issues': issues,
                'metrics': metrics,
                'monitoring_active': self.monitoring_active,
                'alert_count': len(self.alerts)
            }
            
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {
                'status': 'error',
                'health_score': 0,
                'issues': [f"Monitoring error: {e}"],
                'metrics': {},
                'monitoring_active': False,
                'alert_count': 0
            }
    
    def get_metrics_history(self, metric_type: str = None, hours: int = 24) -> Dict[str, Any]:
        """Get historical metrics"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            if metric_type and metric_type in self.metrics_history:
                # Get specific metric
                history = [
                    entry for entry in self.metrics_history[metric_type]
                    if entry['timestamp'] >= cutoff_time
                ]
                return {metric_type: history}
            else:
                # Get all metrics
                filtered_history = {}
                for key, entries in self.metrics_history.items():
                    filtered_history[key] = [
                        entry for entry in entries
                        if entry['timestamp'] >= cutoff_time
                    ]
                return filtered_history
                
        except Exception as e:
            logger.error(f"Failed to get metrics history: {e}")
            return {}
    
    def get_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            recent_alerts = [
                alert for alert in self.alerts
                if datetime.fromisoformat(alert['timestamp']) >= cutoff_time
            ]
            
            return sorted(recent_alerts, key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []
    
    def clear_alerts(self):
        """Clear all alerts"""
        self.alerts.clear()
        logger.info("Alerts cleared")

class PerformanceTracker:
    """Track application performance metrics"""
    
    def __init__(self, history_size=1000):
        self.response_times = deque(maxlen=history_size)
        self.request_counts = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.start_time = datetime.now()
    
    def record_request(self, endpoint: str, response_time_ms: float, status_code: int):
        """Record request metrics"""
        try:
            timestamp = datetime.now()
            
            self.response_times.append({
                'timestamp': timestamp,
                'endpoint': endpoint,
                'response_time_ms': response_time_ms,
                'status_code': status_code
            })
            
            # Count requests
            hour_key = timestamp.strftime('%Y-%m-%d-%H')
            self.request_counts[hour_key] += 1
            
            # Count errors
            if status_code >= 400:
                self.error_counts[hour_key] += 1
                
        except Exception as e:
            logger.error(f"Failed to record request: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        try:
            if not self.response_times:
                return {
                    'avg_response_time_ms': 0,
                    'total_requests': 0,
                    'error_rate': 0,
                    'uptime_hours': 0
                }
            
            # Calculate metrics
            recent_responses = [r['response_time_ms'] for r in list(self.response_times)[-100:]]
            avg_response_time = sum(recent_responses) / len(recent_responses)
            
            total_requests = sum(self.request_counts.values())
            total_errors = sum(self.error_counts.values())
            error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
            
            uptime = datetime.now() - self.start_time
            uptime_hours = uptime.total_seconds() / 3600
            
            return {
                'avg_response_time_ms': round(avg_response_time, 2),
                'total_requests': total_requests,
                'error_rate': round(error_rate, 2),
                'uptime_hours': round(uptime_hours, 2),
                'requests_per_hour': round(total_requests / max(uptime_hours, 1), 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            return {}

# Global instances
_system_monitor = None
_performance_tracker = None

def get_system_monitor():
    """Get global system monitor instance"""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor

def get_performance_tracker():
    """Get global performance tracker instance"""
    global _performance_tracker
    if _performance_tracker is None:
        _performance_tracker = PerformanceTracker()
    return _performance_tracker

def start_monitoring():
    """Start global monitoring"""
    monitor = get_system_monitor()
    monitor.start_monitoring()

def stop_monitoring():
    """Stop global monitoring"""
    if _system_monitor:
        _system_monitor.stop_monitoring()

def setup_monitoring(app=None):
    """Setup monitoring for Flask application"""
    try:
        # Start system monitoring
        start_monitoring()
        
        if app:
            # Add request middleware for performance tracking
            @app.before_request
            def before_request():
                from flask import g
                g.start_time = time.time()
            
            @app.after_request
            def after_request(response):
                from flask import g, request
                if hasattr(g, 'start_time'):
                    response_time_ms = (time.time() - g.start_time) * 1000
                    tracker = get_performance_tracker()
                    tracker.record_request(
                        endpoint=request.endpoint or request.path,
                        response_time_ms=response_time_ms,
                        status_code=response.status_code
                    )
                return response
        
        logger.info("Monitoring setup completed")
        return True
        
    except Exception as e:
        logger.error(f"Failed to setup monitoring: {e}")
        return False