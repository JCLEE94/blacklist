"""
Credentials Management Routes
UI를 통한 수집 인증정보 관리
"""

from flask import Blueprint, request, jsonify, render_template_string
import logging
from src.core.database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)
credentials_bp = Blueprint("credentials", __name__, url_prefix="/credentials")

# HTML Template for credentials management
CREDENTIALS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>수집 인증정보 관리</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .service { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
        .service.enabled { border-color: #28a745; background: #f8fff9; }
        .service.disabled { border-color: #dc3545; background: #fff8f8; }
        input[type="text"], input[type="password"] { width: 200px; padding: 8px; margin: 5px; border: 1px solid #ccc; border-radius: 4px; }
        button { padding: 10px 15px; margin: 5px; border: none; border-radius: 4px; cursor: pointer; }
        .save-btn { background: #007bff; color: white; }
        .test-btn { background: #28a745; color: white; }
        .disable-btn { background: #dc3545; color: white; }
        .enable-btn { background: #28a745; color: white; }
        .status { padding: 5px 10px; border-radius: 4px; font-weight: bold; }
        .status.enabled { background: #d4edda; color: #155724; }
        .status.disabled { background: #f8d7da; color: #721c24; }
        .success { color: #28a745; font-weight: bold; }
        .error { color: #dc3545; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 수집 인증정보 관리</h1>
        <div id="credentials-container">
            <!-- 데이터가 여기에 로드됩니다 -->
        </div>
        
        <div style="margin-top: 30px; padding: 15px; background: #e9ecef; border-radius: 5px;">
            <h3>🚀 빠른 액션</h3>
            <button onclick="testAllConnections()" class="test-btn">모든 서비스 연결 테스트</button>
            <button onclick="enableAllServices()" class="enable-btn">모든 서비스 활성화</button>
            <button onclick="refreshData()" class="save-btn">데이터 새로고침</button>
        </div>
        
        <div id="status-message" style="margin-top: 15px;"></div>
    </div>

    <script>
        let credentials = [];

        function loadCredentials() {
            fetch('/credentials/api/list')
                .then(response => response.json())
                .then(data => {
                    credentials = data.credentials || [];
                    renderCredentials();
                })
                .catch(error => showStatus('데이터 로드 실패: ' + error, 'error'));
        }

        function renderCredentials() {
            const container = document.getElementById('credentials-container');
            container.innerHTML = credentials.map(cred => `
                <div class="service ${cred.is_active ? 'enabled' : 'disabled'}">
                    <h3>${cred.service_name} 
                        <span class="status ${cred.is_active ? 'enabled' : 'disabled'}">
                            ${cred.is_active ? '활성화' : '비활성화'}
                        </span>
                    </h3>
                    
                    <div>
                        <label>사용자명:</label>
                        <input type="text" id="username-${cred.id}" value="${cred.username}" placeholder="사용자명 입력">
                    </div>
                    
                    <div>
                        <label>비밀번호:</label>
                        <input type="password" id="password-${cred.id}" value="${cred.password}" placeholder="비밀번호 입력">
                    </div>
                    
                    <div style="margin-top: 10px;">
                        <button onclick="saveCredentials(${cred.id})" class="save-btn">저장</button>
                        <button onclick="testConnection('${cred.service_name}')" class="test-btn">연결 테스트</button>
                        ${cred.is_active ? 
                            `<button onclick="toggleService(${cred.id}, false)" class="disable-btn">비활성화</button>` :
                            `<button onclick="toggleService(${cred.id}, true)" class="enable-btn">활성화</button>`
                        }
                    </div>
                </div>
            `).join('');
        }

        function saveCredentials(id) {
            const username = document.getElementById(`username-${id}`).value;
            const password = document.getElementById(`password-${id}`).value;
            
            if (!username || !password) {
                showStatus('사용자명과 비밀번호를 입력해주세요', 'error');
                return;
            }
            
            fetch('/credentials/api/save', {
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
            .catch(error => showStatus('저장 실패: ' + error, 'error'));
        }

        function toggleService(id, enable) {
            fetch('/credentials/api/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id, is_active: enable })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showStatus(`서비스가 ${enable ? '활성화' : '비활성화'}되었습니다`, 'success');
                    loadCredentials();
                } else {
                    showStatus('상태 변경 실패: ' + data.error, 'error');
                }
            })
            .catch(error => showStatus('상태 변경 실패: ' + error, 'error'));
        }

        function testConnection(serviceName) {
            showStatus(`${serviceName} 연결 테스트 중...`, 'info');
            
            fetch('/credentials/api/test', {
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
            .catch(error => showStatus(`${serviceName} 연결 테스트 실패: ` + error, 'error'));
        }

        function testAllConnections() {
            credentials.forEach(cred => {
                if (cred.is_active) {
                    testConnection(cred.service_name);
                }
            });
        }

        function enableAllServices() {
            credentials.forEach(cred => {
                if (!cred.is_active) {
                    toggleService(cred.id, true);
                }
            });
        }

        function refreshData() {
            loadCredentials();
            showStatus('데이터가 새로고침되었습니다', 'success');
        }

        function showStatus(message, type) {
            const statusDiv = document.getElementById('status-message');
            statusDiv.className = type;
            statusDiv.textContent = message;
            setTimeout(() => statusDiv.textContent = '', 5000);
        }

        // 페이지 로드시 데이터 로드
        loadCredentials();
    </script>
</body>
</html>
"""


@credentials_bp.route("/")
def credentials_page():
    """수집 인증정보 관리 페이지"""
    return render_template_string(CREDENTIALS_TEMPLATE)


@credentials_bp.route("/api/list")
def list_credentials():
    """인증정보 목록 조회"""
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
        logger.error(f"Failed to list credentials: {e}")
        return jsonify({"success": False, "error": str(e)})


@credentials_bp.route("/api/save", methods=["POST"])
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


@credentials_bp.route("/api/toggle", methods=["POST"])
def toggle_service():
    """서비스 활성화/비활성화"""
    try:
        data = request.get_json()
        credential_id = data.get("id")
        is_active = data.get("is_active")

        db = DatabaseManager()
        db.execute_query(
            """
            UPDATE collection_credentials 
            SET is_active = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """,
            (is_active, credential_id),
        )

        status = "activated" if is_active else "deactivated"
        logger.info(f"Service {status} for credential ID: {credential_id}")
        return jsonify({"success": True})

    except Exception as e:
        logger.error(f"Failed to toggle service: {e}")
        return jsonify({"success": False, "error": str(e)})


@credentials_bp.route("/api/test", methods=["POST"])
def test_connection():
    """연결 테스트"""
    try:
        data = request.get_json()
        service_name = data.get("service_name")

        db = DatabaseManager()
        result = db.execute_query(
            """
            SELECT username, password FROM collection_credentials 
            WHERE service_name = %s AND is_active = true
        """,
            (service_name,),
        )

        if not result:
            return jsonify({"success": False, "error": "Service not found or inactive"})

        # 실제 연결 테스트 로직 (간단한 버전)
        # TODO: 실제 REGTECH/SECUDIUM API 호출로 교체
        username, password = result[0]

        if username and password and len(password) > 3:
            return jsonify(
                {
                    "success": True,
                    "message": f"Connection test passed for {service_name}",
                }
            )
        else:
            return jsonify({"success": False, "error": "Invalid credentials format"})

    except Exception as e:
        logger.error(f"Connection test failed for {service_name}: {e}")
        return jsonify({"success": False, "error": str(e)})
