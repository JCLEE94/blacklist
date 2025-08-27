#!/usr/bin/env python3
"""
자율적 체인 모니터링 웹 인터페이스
실시간 웹 대시보드를 통한 체인 실행 상태 모니터링 및 한국어 진행 상황 보고
"""

import json
import os
from datetime import datetime
from pathlib import Path

from flask import Blueprint, Flask, jsonify, render_template_string, request

from .autonomous_chain_monitor import get_chain_monitor, get_korean_status
from .structured_logging import get_logger

# Blueprint 생성
chain_monitor_bp = Blueprint("chain_monitor", __name__, url_prefix="/chain-monitor")
logger = get_logger("chain_monitor_web")


# HTML 템플릿 (간단한 실시간 대시보드)
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 자동화 플랫폼 v8.3.0 - 무한 체인 모니터링</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
            backdrop-filter: blur(4px);
            border: 1px solid rgba(255, 255, 255, 0.18);
            text-align: center;
        }
        
        .header h1 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 2.5em;
            font-weight: 700;
        }
        
        .header .subtitle {
            color: #7f8c8d;
            font-size: 1.2em;
            margin-bottom: 20px;
        }
        
        .status-card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
            backdrop-filter: blur(4px);
            border: 1px solid rgba(255, 255, 255, 0.18);
        }
        
        .status-card h2 {
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 1.8em;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        
        .metric {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            border: 2px solid #e9ecef;
            transition: all 0.3s ease;
        }
        
        .metric:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .metric-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #27ae60;
            margin-bottom: 10px;
        }
        
        .metric-label {
            font-size: 1.1em;
            color: #7f8c8d;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .chain-list {
            list-style: none;
        }
        
        .chain-item {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 5px solid #3498db;
            display: flex;
            justify-content: between;
            align-items: center;
        }
        
        .chain-item.success {
            border-left-color: #27ae60;
        }
        
        .chain-item.running {
            border-left-color: #f39c12;
            animation: pulse 2s infinite;
        }
        
        .chain-item.failed {
            border-left-color: #e74c3c;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }
        
        .chain-name {
            font-weight: bold;
            font-size: 1.1em;
            color: #2c3e50;
            flex-grow: 1;
        }
        
        .chain-status {
            font-size: 0.9em;
            color: #7f8c8d;
        }
        
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #ecf0f1;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(45deg, #3498db, #2ecc71);
            border-radius: 10px;
            transition: width 0.5s ease;
            position: relative;
        }
        
        .progress-text {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: white;
            font-weight: bold;
            font-size: 0.8em;
        }
        
        .korean-report {
            background: #2c3e50;
            color: #ecf0f1;
            border-radius: 15px;
            padding: 25px;
            font-family: 'Courier New', monospace;
            white-space: pre-line;
            line-height: 1.6;
            max-height: 500px;
            overflow-y: auto;
        }
        
        .refresh-btn {
            background: linear-gradient(45deg, #3498db, #2ecc71);
            color: white;
            border: none;
            border-radius: 25px;
            padding: 12px 30px;
            font-size: 1.1em;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 20px;
        }
        
        .refresh-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .auto-refresh {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 15px;
        }
        
        .timestamp {
            color: #7f8c8d;
            font-size: 0.9em;
            text-align: center;
            margin-top: 15px;
        }
        
        .loading {
            text-align: center;
            padding: 50px;
            color: #7f8c8d;
        }
        
        .loading::after {
            content: '';
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            display: inline-block;
            animation: spin 1s linear infinite;
            margin-left: 15px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AI 자동화 플랫폼 v8.3.0</h1>
            <div class="subtitle">Step 6: Infinite Workflow Chaining - 실시간 모니터링</div>
            <div class="auto-refresh">
                <label>
                    <input type="checkbox" id="autoRefresh" checked> 자동 새로고침 (5초)
                </label>
                <button class="refresh-btn" onclick="refreshData()">🔄 새로고침</button>
            </div>
        </div>
        
        <div class="grid">
            <div class="status-card">
                <h2>📊 전체 실행 통계</h2>
                <div class="grid">
                    <div class="metric">
                        <div class="metric-value" id="overallSuccessRate">0%</div>
                        <div class="metric-label">전체 성공률</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value" id="completedChains">0/0</div>
                        <div class="metric-label">완료된 체인</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value" id="activeChains">0</div>
                        <div class="metric-label">실행 중</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value" id="executionTime">0s</div>
                        <div class="metric-label">실행 시간</div>
                    </div>
                </div>
            </div>
            
            <div class="status-card">
                <h2>🔗 체인 실행 상태</h2>
                <ul class="chain-list" id="chainList">
                    <li class="loading">체인 상태 로딩 중...</li>
                </ul>
            </div>
        </div>
        
        <div class="status-card">
            <h2>📋 한국어 진행 상황 보고</h2>
            <div class="korean-report" id="koreanReport">진행 상황 보고서 로딩 중...</div>
            <div class="timestamp" id="lastUpdate">마지막 업데이트: 로딩 중...</div>
        </div>
    </div>

    <script>
        let autoRefreshEnabled = true;
        let refreshInterval;
        
        // 자동 새로고침 설정
        document.getElementById('autoRefresh').addEventListener('change', function() {
            autoRefreshEnabled = this.checked;
            if (autoRefreshEnabled) {
                startAutoRefresh();
            } else {
                clearInterval(refreshInterval);
            }
        });
        
        function startAutoRefresh() {
            refreshInterval = setInterval(refreshData, 5000);
        }
        
        function refreshData() {
            updateSystemStatus();
            updateKoreanReport();
        }
        
        async function updateSystemStatus() {
            try {
                const response = await fetch('/chain-monitor/api/system-status');
                const data = await response.json();
                
                // 전체 통계 업데이트
                document.getElementById('overallSuccessRate').textContent = 
                    data.system_metrics.average_success_rate.toFixed(1) + '%';
                document.getElementById('completedChains').textContent = 
                    data.system_metrics.successful_chains + '/' + data.system_metrics.total_chains_executed;
                document.getElementById('activeChains').textContent = data.active_chains_count;
                
                // 실행 시간 계산
                const startTime = new Date(data.system_metrics.last_update);
                const now = new Date();
                const executionTime = Math.floor((now - startTime) / 1000);
                document.getElementById('executionTime').textContent = executionTime + 's';
                
                // 체인 목록 업데이트
                updateChainList(data.active_chains);
                
            } catch (error) {
                console.error('시스템 상태 업데이트 실패:', error);
            }
        }
        
        function updateChainList(activeChains) {
            const chainList = document.getElementById('chainList');
            
            if (Object.keys(activeChains).length === 0) {
                chainList.innerHTML = '<li class="chain-item"><div class="chain-name">실행 중인 체인이 없습니다</div></li>';
                return;
            }
            
            chainList.innerHTML = '';
            
            for (const [chainId, chainInfo] of Object.entries(activeChains)) {
                const listItem = document.createElement('li');
                listItem.className = `chain-item ${chainInfo.status}`;
                
                listItem.innerHTML = `
                    <div>
                        <div class="chain-name">${chainInfo.name}</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${chainInfo.progress}%">
                                <div class="progress-text">${chainInfo.progress.toFixed(1)}%</div>
                            </div>
                        </div>
                        <div class="chain-status">${chainInfo.korean_message}</div>
                        ${chainInfo.retry_count > 0 ? `<small>재시도: ${chainInfo.retry_count}회</small>` : ''}
                    </div>
                `;
                
                chainList.appendChild(listItem);
            }
        }
        
        async function updateKoreanReport() {
            try {
                const response = await fetch('/chain-monitor/api/korean-report');
                const data = await response.json();
                
                document.getElementById('koreanReport').textContent = data.report;
                document.getElementById('lastUpdate').textContent = 
                    '마지막 업데이트: ' + new Date(data.timestamp).toLocaleString('ko-KR');
                
            } catch (error) {
                console.error('한국어 보고서 업데이트 실패:', error);
                document.getElementById('koreanReport').textContent = 
                    '보고서 업데이트 중 오류가 발생했습니다: ' + error.message;
            }
        }
        
        // 페이지 로드 시 초기 데이터 로드 및 자동 새로고침 시작
        document.addEventListener('DOMContentLoaded', function() {
            refreshData();
            startAutoRefresh();
        });
    </script>
</body>
</html>
"""


@chain_monitor_bp.route("/")
def dashboard():
    """체인 모니터링 대시보드 메인 페이지"""
    return render_template_string(DASHBOARD_HTML)


@chain_monitor_bp.route("/api/system-status")
def api_system_status():
    """시스템 상태 API"""
    try:
        monitor = get_chain_monitor()
        status = monitor.get_system_status()

        return jsonify(
            {"success": True, "timestamp": datetime.now().isoformat(), **status}
        )

    except Exception as e:
        logger.error(f"시스템 상태 API 오류: {e}", exception=e)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@chain_monitor_bp.route("/api/korean-report")
def api_korean_report():
    """한국어 진행 상황 보고 API"""
    try:
        report = get_korean_status()

        return jsonify(
            {"success": True, "report": report, "timestamp": datetime.now().isoformat()}
        )

    except Exception as e:
        logger.error(f"한국어 보고서 API 오류: {e}", exception=e)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "report": f"보고서 생성 중 오류 발생: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@chain_monitor_bp.route("/api/chain-history")
def api_chain_history():
    """체인 실행 히스토리 API"""
    try:
        monitor = get_chain_monitor()

        # 완료된 체인 히스토리 (최근 20개)
        completed_chains = []
        for chain_context in list(monitor.completed_chains):
            completed_chains.append(
                {
                    "chain_id": chain_context.chain_id,
                    "chain_name": chain_context.chain_name,
                    "status": chain_context.status.value,
                    "success_rate": chain_context.metrics.success_rate,
                    "duration": chain_context.metrics.duration_seconds,
                    "start_time": (
                        chain_context.metrics.start_time.isoformat()
                        if chain_context.metrics.start_time
                        else None
                    ),
                    "end_time": (
                        chain_context.metrics.end_time.isoformat()
                        if chain_context.metrics.end_time
                        else None
                    ),
                    "retry_count": chain_context.metrics.retry_count,
                    "korean_message": chain_context.korean_status_message,
                }
            )

        return jsonify(
            {
                "success": True,
                "completed_chains": completed_chains[-20:],  # 최근 20개
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"체인 히스토리 API 오류: {e}", exception=e)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@chain_monitor_bp.route("/api/chain/<chain_id>")
def api_chain_details(chain_id):
    """특정 체인 상세 정보 API"""
    try:
        monitor = get_chain_monitor()

        # 활성 체인에서 찾기
        if chain_id in monitor.active_chains:
            context = monitor.active_chains[chain_id]

            return jsonify(
                {
                    "success": True,
                    "chain": {
                        "chain_id": context.chain_id,
                        "chain_name": context.chain_name,
                        "task_id": context.task_id,
                        "status": context.status.value,
                        "priority": context.priority.value,
                        "progress": context.progress_percentage,
                        "current_step": context.current_step,
                        "korean_message": context.korean_status_message,
                        "error_message": context.error_message,
                        "metrics": {
                            "start_time": (
                                context.metrics.start_time.isoformat()
                                if context.metrics.start_time
                                else None
                            ),
                            "duration": context.metrics.duration_seconds,
                            "retry_count": context.metrics.retry_count,
                            "max_retries": context.metrics.max_retries,
                            "success_rate": context.metrics.success_rate,
                            "memory_usage": context.metrics.memory_usage_mb,
                            "cpu_usage": context.metrics.cpu_usage_percent,
                            "error_count": context.metrics.error_count,
                            "warning_count": context.metrics.warning_count,
                        },
                        "dependencies": context.dependencies,
                    },
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # 완료된 체인에서 찾기
        for completed_chain in monitor.completed_chains:
            if completed_chain.chain_id == chain_id:
                context = completed_chain

                return jsonify(
                    {
                        "success": True,
                        "chain": {
                            "chain_id": context.chain_id,
                            "chain_name": context.chain_name,
                            "task_id": context.task_id,
                            "status": context.status.value,
                            "priority": context.priority.value,
                            "progress": context.progress_percentage,
                            "korean_message": context.korean_status_message,
                            "error_message": context.error_message,
                            "metrics": {
                                "start_time": (
                                    context.metrics.start_time.isoformat()
                                    if context.metrics.start_time
                                    else None
                                ),
                                "end_time": (
                                    context.metrics.end_time.isoformat()
                                    if context.metrics.end_time
                                    else None
                                ),
                                "duration": context.metrics.duration_seconds,
                                "retry_count": context.metrics.retry_count,
                                "success_rate": context.metrics.success_rate,
                                "error_count": context.metrics.error_count,
                                "warning_count": context.metrics.warning_count,
                            },
                            "dependencies": context.dependencies,
                        },
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        # 체인을 찾지 못한 경우
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"체인 '{chain_id}'를 찾을 수 없습니다",
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            404,
        )

    except Exception as e:
        logger.error(f"체인 상세 정보 API 오류: {e}", exception=e)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@chain_monitor_bp.route("/api/metrics")
def api_metrics():
    """성능 메트릭 API"""
    try:
        monitor = get_chain_monitor()

        # 시스템 메트릭
        metrics = {
            "system_metrics": monitor.system_metrics.copy(),
            "active_chains_count": len(monitor.active_chains),
            "completed_chains_count": len(monitor.completed_chains),
            "monitoring_enabled": monitor.monitoring_enabled,
            "korean_reporting_enabled": monitor.korean_reporting_enabled,
            "auto_recovery_enabled": monitor.auto_recovery_enabled,
            "max_concurrent_chains": monitor.max_concurrent_chains,
        }

        # 체인별 성능 통계
        chain_performance = {}
        for context in monitor.completed_chains:
            chain_name = context.chain_name
            if chain_name not in chain_performance:
                chain_performance[chain_name] = {
                    "executions": 0,
                    "successes": 0,
                    "total_duration": 0,
                    "avg_duration": 0,
                    "success_rate": 0,
                }

            stats = chain_performance[chain_name]
            stats["executions"] += 1
            if context.status.value == "success":
                stats["successes"] += 1
            if context.metrics.duration_seconds:
                stats["total_duration"] += context.metrics.duration_seconds

        # 평균 계산
        for stats in chain_performance.values():
            if stats["executions"] > 0:
                stats["avg_duration"] = stats["total_duration"] / stats["executions"]
                stats["success_rate"] = (stats["successes"] / stats["executions"]) * 100

        metrics["chain_performance"] = chain_performance

        return jsonify(
            {
                "success": True,
                "metrics": metrics,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"메트릭 API 오류: {e}", exception=e)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@chain_monitor_bp.route("/api/control/pause/<chain_id>", methods=["POST"])
def api_pause_chain(chain_id):
    """체인 일시 정지 API"""
    try:
        monitor = get_chain_monitor()
        monitor.pause_chain(chain_id)

        return jsonify(
            {
                "success": True,
                "message": f"체인 '{chain_id}' 일시 정지됨",
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"체인 일시 정지 API 오류: {e}", exception=e)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@chain_monitor_bp.route("/api/control/resume/<chain_id>", methods=["POST"])
def api_resume_chain(chain_id):
    """체인 재개 API"""
    try:
        monitor = get_chain_monitor()
        monitor.resume_chain(chain_id)

        return jsonify(
            {
                "success": True,
                "message": f"체인 '{chain_id}' 재개됨",
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"체인 재개 API 오류: {e}", exception=e)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@chain_monitor_bp.route("/api/control/cancel/<chain_id>", methods=["POST"])
def api_cancel_chain(chain_id):
    """체인 취소 API"""
    try:
        monitor = get_chain_monitor()
        monitor.cancel_chain(chain_id)

        return jsonify(
            {
                "success": True,
                "message": f"체인 '{chain_id}' 취소됨",
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"체인 취소 API 오류: {e}", exception=e)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


def create_chain_monitor_app():
    """체인 모니터링 전용 Flask 앱 생성"""
    app = Flask(__name__)
    app.register_blueprint(chain_monitor_bp)

    # 기본 라우트
    @app.route("/")
    def index():
        return chain_monitor_bp.dashboard()

    return app


if __name__ == "__main__":
    # 단독 실행 시 테스트 서버 시작
    app = create_chain_monitor_app()

    # 체인 모니터링 시스템 초기화
    from .autonomous_chain_monitor import initialize_chain_monitoring

    monitor = initialize_chain_monitoring()

    print("🌐 체인 모니터링 웹 서버 시작")
    print("📍 URL: http://localhost:5555/")
    print("🔄 자동 새로고침: 5초마다")
    print("📊 실시간 모니터링 대시보드 제공")

    try:
        app.run(host="0.0.0.0", port=5555, debug=True)
    except KeyboardInterrupt:
        print("\n🛑 웹 서버 중지됨")
    finally:
        from .autonomous_chain_monitor import shutdown_chain_monitoring

        shutdown_chain_monitoring()
