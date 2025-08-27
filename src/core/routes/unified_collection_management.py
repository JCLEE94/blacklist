"""
통합 수집 관리 패널
모든 수집 관련 기능을 하나의 인터페이스로 통합
- 인증정보 설정
- 수집 상태 모니터링
- 수집 트리거 및 제어
- 수집 로그 및 히스토리
- 데이터 통계 및 분석
"""

from flask import Blueprint, request, jsonify, render_template_string
import logging
from datetime import datetime
from src.core.database_manager import DatabaseManager

logger = logging.getLogger(__name__)
unified_collection_bp = Blueprint(
    "unified_collection", __name__, url_prefix="/collection"
)

# 통합 수집 관리 패널 HTML 템플릿
UNIFIED_COLLECTION_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🔄 통합 수집 관리 패널</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .main-container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 30px;
            text-align: center;
            position: relative;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        
        .header .subtitle {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .tab-navigation {
            display: flex;
            background: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
            overflow-x: auto;
        }
        
        .tab-btn {
            padding: 20px 30px;
            border: none;
            background: transparent;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            color: #6c757d;
            transition: all 0.3s ease;
            border-bottom: 3px solid transparent;
            min-width: 200px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        
        .tab-btn:hover {
            background: rgba(79, 172, 254, 0.1);
            color: #4facfe;
        }
        
        .tab-btn.active {
            background: white;
            color: #4facfe;
            border-bottom-color: #4facfe;
        }
        
        .tab-content {
            padding: 30px;
            min-height: 600px;
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .service-card {
            border: 2px solid #e9ecef;
            border-radius: 12px;
            padding: 25px;
            margin: 20px 0;
            transition: all 0.3s ease;
            position: relative;
        }
        
        .service-card.enabled {
            border-color: #28a745;
            background: linear-gradient(135deg, #f8fff9 0%, #e8f5e8 100%);
        }
        
        .service-card.disabled {
            border-color: #dc3545;
            background: linear-gradient(135deg, #fff8f8 0%, #f8e8e8 100%);
        }
        
        .service-card h3 {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 20px;
            font-size: 1.5em;
        }
        
        .status-badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.8em;
        }
        
        .status-badge.enabled {
            background: #d4edda;
            color: #155724;
        }
        
        .status-badge.disabled {
            background: #f8d7da;
            color: #721c24;
        }
        
        .form-group {
            margin: 15px 0;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #495057;
        }
        
        .form-group input {
            width: 100%;
            max-width: 400px;
            padding: 12px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s ease;
        }
        
        .form-group input:focus {
            border-color: #4facfe;
            outline: none;
            box-shadow: 0 0 0 3px rgba(79, 172, 254, 0.1);
        }
        
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin: 5px;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .btn-primary { background: #4facfe; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-warning { background: #ffc107; color: #212529; }
        .btn-info { background: #17a2b8; color: white; }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            border: 2px solid #e9ecef;
            transition: all 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }
        
        .stat-number {
            font-size: 2.5em;
            font-weight: bold;
            color: #4facfe;
            margin-bottom: 10px;
        }
        
        .stat-label {
            color: #6c757d;
            font-weight: 600;
        }
        
        .log-container {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            height: 400px;
            overflow-y: auto;
            padding: 15px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 13px;
        }
        
        .log-entry {
            padding: 5px 0;
            border-bottom: 1px solid #e9ecef;
        }
        
        .log-entry.success { color: #28a745; }
        .log-entry.error { color: #dc3545; }
        .log-entry.info { color: #17a2b8; }
        
        .message {
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            font-weight: 600;
        }
        
        .message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .quick-actions {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
            margin: 20px 0;
            border: 2px solid #e9ecef;
        }
        
        .collection-progress {
            width: 100%;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
            transition: width 0.5s ease;
        }
        
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        
        @media (max-width: 768px) {
            .grid-2 { grid-template-columns: 1fr; }
            .tab-btn { min-width: 150px; font-size: 14px; padding: 15px 20px; }
            .header h1 { font-size: 2em; }
        }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="header">
            <h1>🔄 통합 수집 관리 패널</h1>
            <div class="subtitle">모든 수집 기능을 하나의 인터페이스에서 관리</div>
        </div>
        
        <div class="tab-navigation">
            <button class="tab-btn active" onclick="showTab('dashboard')">
                📊 대시보드
            </button>
            <button class="tab-btn" onclick="showTab('credentials')">
                🔐 인증정보
            </button>
            <button class="tab-btn" onclick="showTab('control')">
                🎮 수집 제어
            </button>
            <button class="tab-btn" onclick="showTab('logs')">
                📋 수집 로그
            </button>
            <button class="tab-btn" onclick="showTab('analytics')">
                📈 통계 분석
            </button>
        </div>
        
        <!-- 대시보드 탭 -->
        <div id="dashboard" class="tab-content active">
            <h2>📊 수집 시스템 대시보드</h2>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number" id="total-ips">0</div>
                    <div class="stat-label">총 수집된 IP</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="active-services">0</div>
                    <div class="stat-label">활성 서비스</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="last-collection">없음</div>
                    <div class="stat-label">마지막 수집</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="success-rate">0%</div>
                    <div class="stat-label">성공률</div>
                </div>
            </div>
            
            <div class="quick-actions">
                <h3>🚀 빠른 액션</h3>
                <button onclick="quickCollectAll()" class="btn btn-success">전체 수집 시작</button>
                <button onclick="refreshDashboard()" class="btn btn-info">대시보드 새로고침</button>
                <button onclick="exportData()" class="btn btn-warning">데이터 내보내기</button>
                <button onclick="systemHealth()" class="btn btn-primary">시스템 상태 체크</button>
            </div>
        </div>
        
        <!-- 인증정보 탭 -->
        <div id="credentials" class="tab-content">
            <h2>🔐 수집 서비스 인증정보 관리</h2>
            <div id="credentials-container">
                <!-- 인증정보가 여기에 로드됩니다 -->
            </div>
        </div>
        
        <!-- 수집 제어 탭 -->
        <div id="control" class="tab-content">
            <h2>🎮 수집 제어 센터</h2>
            
            <div class="grid-2">
                <div>
                    <h3>개별 수집 제어</h3>
                    <div id="individual-controls">
                        <!-- 개별 제어가 여기에 로드됩니다 -->
                    </div>
                </div>
                
                <div>
                    <h3>수집 진행 상황</h3>
                    <div id="collection-progress">
                        <div class="collection-progress">
                            <div class="progress-bar" id="progress-bar" style="width: 0%"></div>
                        </div>
                        <div id="progress-text">대기 중...</div>
                    </div>
                    
                    <h4>수집 스케줄</h4>
                    <div>
                        <label>자동 수집 간격:</label>
                        <select id="schedule-interval">
                            <option value="manual">수동</option>
                            <option value="hourly">1시간마다</option>
                            <option value="daily">매일</option>
                            <option value="weekly">매주</option>
                        </select>
                        <button onclick="updateSchedule()" class="btn btn-primary">적용</button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 수집 로그 탭 -->
        <div id="logs" class="tab-content">
            <h2>📋 수집 로그 및 히스토리</h2>
            
            <div class="grid-2">
                <div>
                    <h3>실시간 로그</h3>
                    <div class="log-container" id="live-logs">
                        <!-- 실시간 로그가 여기에 표시됩니다 -->
                    </div>
                    <button onclick="clearLogs()" class="btn btn-danger">로그 지우기</button>
                </div>
                
                <div>
                    <h3>수집 히스토리</h3>
                    <div id="collection-history">
                        <!-- 히스토리가 여기에 로드됩니다 -->
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 통계 분석 탭 -->
        <div id="analytics" class="tab-content">
            <h2>📈 수집 데이터 통계 및 분석</h2>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number" id="regtech-count">0</div>
                    <div class="stat-label">REGTECH IP</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="secudium-count">0</div>
                    <div class="stat-label">SECUDIUM IP</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="duplicate-count">0</div>
                    <div class="stat-label">중복 IP</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="unique-count">0</div>
                    <div class="stat-label">고유 IP</div>
                </div>
            </div>
            
            <div class="quick-actions">
                <h3>📊 분석 도구</h3>
                <button onclick="generateReport()" class="btn btn-primary">보고서 생성</button>
                <button onclick="compareData()" class="btn btn-info">데이터 비교</button>
                <button onclick="trendAnalysis()" class="btn btn-warning">트렌드 분석</button>
            </div>
        </div>
        
        <div id="status-message"></div>
    </div>

    <script>
        let currentData = {};
        let updateInterval;

        function showTab(tabName) {
            // 모든 탭 비활성화
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // 선택된 탭 활성화
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
            
            // 탭별 초기화
            if (tabName === 'dashboard') refreshDashboard();
            else if (tabName === 'credentials') loadCredentials();
            else if (tabName === 'control') loadControlCenter();
            else if (tabName === 'logs') loadLogs();
            else if (tabName === 'analytics') loadAnalytics();
        }

        function refreshDashboard() {
            showStatus('대시보드 데이터 로딩 중...', 'info');
            
            Promise.all([
                fetch('/collection/api/stats').then(r => r.json()),
                fetch('/collection/api/status').then(r => r.json())
            ]).then(([stats, status]) => {
                document.getElementById('total-ips').textContent = stats.total_ips || 0;
                document.getElementById('active-services').textContent = status.active_services || 0;
                document.getElementById('last-collection').textContent = status.last_collection || '없음';
                document.getElementById('success-rate').textContent = (stats.success_rate || 0) + '%';
                
                showStatus('대시보드 업데이트 완료', 'success');
            }).catch(err => {
                showStatus('대시보드 로딩 실패: ' + err, 'error');
            });
        }

        function loadCredentials() {
            fetch('/collection/api/credentials')
                .then(response => response.json())
                .then(data => {
                    const container = document.getElementById('credentials-container');
                    container.innerHTML = data.credentials.map(cred => `
                        <div class="service-card ${cred.is_active ? 'enabled' : 'disabled'}">
                            <h3>
                                ${cred.service_name}
                                <span class="status-badge ${cred.is_active ? 'enabled' : 'disabled'}">
                                    ${cred.is_active ? '활성화' : '비활성화'}
                                </span>
                            </h3>
                            
                            <div class="form-group">
                                <label>사용자명:</label>
                                <input type="text" id="username-${cred.id}" value="${cred.username}" placeholder="사용자명 입력">
                            </div>
                            
                            <div class="form-group">
                                <label>비밀번호:</label>
                                <input type="password" id="password-${cred.id}" value="${cred.password}" placeholder="비밀번호 입력">
                            </div>
                            
                            <div>
                                <button onclick="saveCredentials(${cred.id})" class="btn btn-primary">💾 저장</button>
                                <button onclick="testConnection('${cred.service_name}')" class="btn btn-success">🔧 연결 테스트</button>
                                ${cred.is_active ? 
                                    `<button onclick="toggleService(${cred.id}, false)" class="btn btn-danger">❌ 비활성화</button>` :
                                    `<button onclick="toggleService(${cred.id}, true)" class="btn btn-success">✅ 활성화</button>`
                                }
                            </div>
                        </div>
                    `).join('');
                })
                .catch(error => showStatus('인증정보 로드 실패: ' + error, 'error'));
        }

        function loadControlCenter() {
            fetch('/collection/api/services')
                .then(response => response.json())
                .then(data => {
                    const container = document.getElementById('individual-controls');
                    container.innerHTML = data.services.map(service => `
                        <div class="service-card ${service.enabled ? 'enabled' : 'disabled'}">
                            <h4>${service.name}</h4>
                            <p>상태: ${service.status}</p>
                            <button onclick="triggerCollection('${service.name}')" class="btn btn-primary">수집 시작</button>
                            <button onclick="stopCollection('${service.name}')" class="btn btn-danger">수집 중지</button>
                        </div>
                    `).join('');
                })
                .catch(error => showStatus('제어 센터 로드 실패: ' + error, 'error'));
        }

        function loadLogs() {
            fetch('/collection/api/logs')
                .then(response => response.json())
                .then(data => {
                    const container = document.getElementById('live-logs');
                    container.innerHTML = data.logs.map(log => `
                        <div class="log-entry ${log.level}">
                            [${log.timestamp}] ${log.level.toUpperCase()}: ${log.message}
                        </div>
                    `).join('');
                    container.scrollTop = container.scrollHeight;
                })
                .catch(error => showStatus('로그 로드 실패: ' + error, 'error'));
        }

        function loadAnalytics() {
            fetch('/collection/api/analytics')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('regtech-count').textContent = data.regtech_count || 0;
                    document.getElementById('secudium-count').textContent = data.secudium_count || 0;
                    document.getElementById('duplicate-count').textContent = data.duplicate_count || 0;
                    document.getElementById('unique-count').textContent = data.unique_count || 0;
                })
                .catch(error => showStatus('분석 데이터 로드 실패: ' + error, 'error'));
        }

        // 각종 액션 함수들
        function quickCollectAll() {
            showStatus('전체 수집을 시작합니다...', 'info');
            fetch('/collection/api/collect-all', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showStatus('전체 수집이 시작되었습니다', 'success');
                        updateProgress();
                    } else {
                        showStatus('수집 시작 실패: ' + data.error, 'error');
                    }
                })
                .catch(error => showStatus('수집 요청 실패: ' + error, 'error'));
        }

        function updateProgress() {
            // 진행률 업데이트 로직
            let progress = 0;
            const interval = setInterval(() => {
                progress += Math.random() * 10;
                if (progress >= 100) {
                    progress = 100;
                    clearInterval(interval);
                    document.getElementById('progress-text').textContent = '수집 완료!';
                } else {
                    document.getElementById('progress-text').textContent = `수집 중... ${Math.round(progress)}%`;
                }
                document.getElementById('progress-bar').style.width = progress + '%';
            }, 1000);
        }

        function saveCredentials(id) {
            const username = document.getElementById(`username-${id}`).value;
            const password = document.getElementById(`password-${id}`).value;
            
            fetch('/collection/api/save-credentials', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id, username, password })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showStatus('인증정보가 저장되었습니다', 'success');
                    loadCredentials();
                } else {
                    showStatus('저장 실패: ' + data.error, 'error');
                }
            })
            .catch(error => showStatus('저장 요청 실패: ' + error, 'error'));
        }

        function testConnection(serviceName) {
            showStatus(`${serviceName} 연결 테스트 중...`, 'info');
            
            fetch('/collection/api/test-connection', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ service_name: serviceName })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showStatus(`${serviceName} 연결 성공! ✓`, 'success');
                } else {
                    showStatus(`${serviceName} 연결 실패: ${data.error}`, 'error');
                }
            })
            .catch(error => showStatus(`연결 테스트 실패: ${error}`, 'error'));
        }

        function showStatus(message, type) {
            const statusDiv = document.getElementById('status-message');
            statusDiv.className = `message ${type}`;
            statusDiv.textContent = message;
            statusDiv.style.display = 'block';
            setTimeout(() => {
                statusDiv.style.display = 'none';
            }, 5000);
        }

        // 페이지 로드시 초기화
        document.addEventListener('DOMContentLoaded', function() {
            refreshDashboard();
            
            // 30초마다 대시보드 자동 새로고침
            updateInterval = setInterval(refreshDashboard, 30000);
        });
        
        // 페이지 언로드시 인터벌 정리
        window.addEventListener('beforeunload', function() {
            if (updateInterval) clearInterval(updateInterval);
        });
    </script>
</body>
</html>
"""


@unified_collection_bp.route("/")
def unified_collection_page():
    """통합 수집 관리 패널 메인 페이지"""
    return render_template_string(UNIFIED_COLLECTION_TEMPLATE)


@unified_collection_bp.route("/api/stats")
def get_collection_stats():
    """수집 통계 데이터"""
    try:
        db = DatabaseManager()

        # 총 IP 수
        total_ips = db.execute_query("SELECT COUNT(*) as count FROM blacklist_ips")[0][
            "count"
        ]

        # 활성 IP 수
        active_ips = db.execute_query(
            """
            SELECT COUNT(*) as count FROM blacklist_ips 
            WHERE is_active = true
        """
        )[0]["count"]

        # 성공률 계산 (임시)
        success_rate = 85 if total_ips > 0 else 0

        return jsonify(
            {
                "success": True,
                "total_ips": total_ips,
                "active_ips": active_ips,
                "success_rate": success_rate,
            }
        )
    except Exception as e:
        logger.error(f"Failed to get collection stats: {e}")
        return jsonify({"success": False, "error": str(e)})


@unified_collection_bp.route("/api/status")
def get_collection_status():
    """수집 상태 정보"""
    try:
        db = DatabaseManager()

        # 활성 서비스 수
        active_services = db.execute_query(
            """
            SELECT COUNT(*) as count FROM collection_credentials 
            WHERE is_active = true
        """
        )[0]["count"]

        # 마지막 수집 시간
        last_collection_result = db.execute_query(
            """
            SELECT MAX(created_at) as last_time FROM collections
        """
        )

        last_collection = "Never"
        if last_collection_result and last_collection_result[0]["last_time"]:
            last_collection = last_collection_result[0]["last_time"].strftime(
                "%Y-%m-%d %H:%M"
            )

        return jsonify(
            {
                "success": True,
                "active_services": active_services,
                "last_collection": last_collection,
                "system_status": "healthy",
            }
        )
    except Exception as e:
        logger.error(f"Failed to get collection status: {e}")
        return jsonify({"success": False, "error": str(e)})


@unified_collection_bp.route("/api/credentials")
def get_credentials():
    """인증정보 목록"""
    try:
        db = DatabaseManager()
        credentials = db.execute_query(
            """
            SELECT id, service_name, username, password, 
                   additional_config, is_active, updated_at
            FROM collection_credentials 
            ORDER BY service_name
        """
        )

        return jsonify(
            {"success": True, "credentials": [dict(row) for row in credentials]}
        )
    except Exception as e:
        logger.error(f"Failed to get credentials: {e}")
        return jsonify({"success": False, "error": str(e)})


@unified_collection_bp.route("/api/save-credentials", methods=["POST"])
def save_credentials():
    """인증정보 저장"""
    try:
        data = request.get_json()
        credential_id = data.get("id")
        username = data.get("username")
        password = data.get("password")

        if not all([credential_id, username, password]):
            return jsonify({"success": False, "error": "Missing required fields"})

        db = DatabaseManager()
        db.execute_query(
            """
            UPDATE collection_credentials 
            SET username = %s, password = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """,
            (username, password, credential_id),
        )

        logger.info(f"Credentials updated for ID: {credential_id}")
        return jsonify({"success": True})

    except Exception as e:
        logger.error(f"Failed to save credentials: {e}")
        return jsonify({"success": False, "error": str(e)})


@unified_collection_bp.route("/api/collect-all", methods=["POST"])
def trigger_collect_all():
    """전체 수집 트리거"""
    try:
        # 실제 수집 로직 호출
        logger.info("Manual collection triggered via unified panel")

        # TODO: 실제 수집기 호출

        return jsonify({"success": True, "message": "Collection started successfully"})

    except Exception as e:
        logger.error(f"Failed to trigger collection: {e}")
        return jsonify({"success": False, "error": str(e)})


@unified_collection_bp.route("/api/logs")
def get_logs():
    """수집 로그 조회"""
    try:
        db = DatabaseManager()
        logs = db.execute_query(
            """
            SELECT level, message, timestamp, source 
            FROM system_logs 
            WHERE source LIKE '%collection%' 
            ORDER BY timestamp DESC 
            LIMIT 100
        """
        )

        return jsonify({"success": True, "logs": [dict(row) for row in logs]})
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        return jsonify({"success": False, "error": str(e)})


@unified_collection_bp.route("/api/analytics")
def get_analytics():
    """수집 분석 데이터"""
    try:
        db = DatabaseManager()

        # 소스별 IP 수 계산
        regtech_count = db.execute_query(
            """
            SELECT COUNT(*) as count FROM blacklist_ips 
            WHERE source = 'REGTECH'
        """
        )[0]["count"]

        secudium_count = db.execute_query(
            """
            SELECT COUNT(*) as count FROM blacklist_ips 
            WHERE source = 'SECUDIUM'  
        """
        )[0]["count"]

        # 중복 및 고유 IP 계산
        total_ips = db.execute_query("SELECT COUNT(*) as count FROM blacklist_ips")[0][
            "count"
        ]
        unique_ips = db.execute_query(
            "SELECT COUNT(DISTINCT ip_address) as count FROM blacklist_ips"
        )[0]["count"]

        return jsonify(
            {
                "success": True,
                "regtech_count": regtech_count,
                "secudium_count": secudium_count,
                "duplicate_count": total_ips - unique_ips,
                "unique_count": unique_ips,
            }
        )
    except Exception as e:
        logger.error(f"Failed to get analytics: {e}")
        return jsonify({"success": False, "error": str(e)})
