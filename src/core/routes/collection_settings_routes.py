#!/usr/bin/env python3
"""
수집 설정 관리 라우트
UI에서 수집 소스 설정 및 자격증명을 저장/조회
"""

from flask import Blueprint, jsonify, render_template_string, request

try:
    from ..database.collection_settings import CollectionSettingsDB
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

bp = Blueprint('collection_settings', __name__, url_prefix='/api/collection/settings')


def get_db():
    """DB 인스턴스 반환"""
    if not DB_AVAILABLE:
        return None
    return CollectionSettingsDB()


# 설정 관리 UI
SETTINGS_UI_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>수집 설정 관리</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-control { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        .btn { padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
        .btn-primary { background: #3498db; color: white; }
        .btn-success { background: #27ae60; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-warning { background: #f39c12; color: white; }
        .sources-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .source-card { background: #ecf0f1; padding: 15px; border-radius: 8px; }
        .source-card.enabled { border-left: 4px solid #27ae60; }
        .source-card.disabled { border-left: 4px solid #e74c3c; }
        .toggle-switch { position: relative; display: inline-block; width: 60px; height: 34px; }
        .toggle-switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #ccc; transition: .4s; border-radius: 34px; }
        .slider:before { position: absolute; content: ""; height: 26px; width: 26px; left: 4px; bottom: 4px; background-color: white; transition: .4s; border-radius: 50%; }
        input:checked + .slider { background-color: #2196F3; }
        input:checked + .slider:before { transform: translateX(26px); }
        .status { padding: 5px 10px; border-radius: 4px; font-size: 0.9em; }
        .status.success { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
        .credentials-form { background: #fff3cd; padding: 15px; border-radius: 8px; margin-top: 10px; }
        .json-editor { min-height: 200px; font-family: monospace; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔧 수집 설정 관리</h1>
            <p>수집 소스 설정 및 자격증명을 관리합니다</p>
        </div>
        
        <!-- 새 소스 추가 -->
        <div class="card">
            <h3>새 수집 소스 추가</h3>
            <form id="addSourceForm">
                <div class="form-group">
                    <label>소스 이름:</label>
                    <input type="text" class="form-control" id="sourceName" placeholder="예: regtech">
                </div>
                <div class="form-group">
                    <label>표시 이름:</label>
                    <input type="text" class="form-control" id="displayName" placeholder="예: REGTECH 위협정보">
                </div>
                <div class="form-group">
                    <label>기본 URL:</label>
                    <input type="url" class="form-control" id="baseUrl" placeholder="https://example.com">
                </div>
                <div class="form-group">
                    <label>설정 (JSON):</label>
                    <textarea class="form-control json-editor" id="sourceConfig" placeholder='{"endpoints": {"login": "/login"}, "timeout": 30}'></textarea>
                </div>
                <button type="submit" class="btn btn-primary">소스 추가</button>
            </form>
        </div>
        
        <!-- 기존 소스 목록 -->
        <div class="card">
            <h3>기존 수집 소스</h3>
            <div id="sourcesList" class="sources-list">
                <!-- 동적으로 생성 -->
            </div>
        </div>
        
        <!-- 자격증명 관리 -->
        <div class="card">
            <h3>자격증명 관리</h3>
            <form id="credentialsForm">
                <div class="form-group">
                    <label>소스 선택:</label>
                    <select class="form-control" id="credentialSource">
                        <option value="">선택하세요</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>사용자명:</label>
                    <input type="text" class="form-control" id="username">
                </div>
                <div class="form-group">
                    <label>패스워드:</label>
                    <input type="password" class="form-control" id="password">
                </div>
                <button type="submit" class="btn btn-success">자격증명 저장</button>
                <button type="button" class="btn btn-warning" onclick="testCredentials()">연결 테스트</button>
            </form>
        </div>
        
        <!-- 테스트 결과 -->
        <div class="card">
            <h3>테스트 및 상태</h3>
            <div id="testResults">
                <p>테스트 결과가 여기에 표시됩니다.</p>
            </div>
            <button class="btn btn-primary" onclick="runCollectionTest()">수집 테스트</button>
            <button class="btn btn-success" onclick="loadSources()">목록 새로고침</button>
        </div>
    </div>
    
    <script>
        // 페이지 로드시 소스 목록 로드
        document.addEventListener('DOMContentLoaded', function() {
            loadSources();
        });
        
        // 소스 목록 로드
        async function loadSources() {
            try {
                const response = await fetch('/api/collection/settings/sources');
                const sources = await response.json();
                
                displaySources(sources);
                updateCredentialSourceOptions(sources);
                
            } catch (error) {
                showResult('error', '소스 목록 로드 실패: ' + error.message);
            }
        }
        
        // 소스 목록 표시
        function displaySources(sources) {
            const container = document.getElementById('sourcesList');
            container.innerHTML = '';
            
            if (sources.length === 0) {
                container.innerHTML = '<p>등록된 소스가 없습니다.</p>';
                return;
            }
            
            sources.forEach(source => {
                const card = document.createElement('div');
                card.className = `source-card ${source.enabled ? 'enabled' : 'disabled'}`;
                card.innerHTML = `
                    <h4>${source.display_name} (${source.name})</h4>
                    <p><strong>URL:</strong> ${source.base_url}</p>
                    <p><strong>상태:</strong> 
                        <label class="toggle-switch">
                            <input type="checkbox" ${source.enabled ? 'checked' : ''} 
                                   onchange="toggleSource('${source.name}', this.checked)">
                            <span class="slider"></span>
                        </label>
                        ${source.enabled ? '활성화' : '비활성화'}
                    </p>
                    <p><strong>생성:</strong> ${new Date(source.created_at).toLocaleDateString()}</p>
                    <button class="btn btn-warning" onclick="editSource('${source.name}')">편집</button>
                    <button class="btn btn-danger" onclick="deleteSource('${source.name}')">삭제</button>
                `;
                container.appendChild(card);
            });
        }
        
        // 자격증명 소스 옵션 업데이트
        function updateCredentialSourceOptions(sources) {
            const select = document.getElementById('credentialSource');
            select.innerHTML = '<option value="">선택하세요</option>';
            
            sources.forEach(source => {
                const option = document.createElement('option');
                option.value = source.name;
                option.textContent = source.display_name;
                select.appendChild(option);
            });
        }
        
        // 새 소스 추가
        document.getElementById('addSourceForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = {
                name: document.getElementById('sourceName').value,
                display_name: document.getElementById('displayName').value,
                base_url: document.getElementById('baseUrl').value,
                config: document.getElementById('sourceConfig').value,
                enabled: true
            };
            
            try {
                const response = await fetch('/api/collection/settings/sources', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showResult('success', '소스가 성공적으로 추가되었습니다.');
                    document.getElementById('addSourceForm').reset();
                    loadSources();
                } else {
                    showResult('error', '소스 추가 실패: ' + result.error);
                }
                
            } catch (error) {
                showResult('error', '요청 실패: ' + error.message);
            }
        });
        
        // 자격증명 저장
        document.getElementById('credentialsForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = {
                source_name: document.getElementById('credentialSource').value,
                username: document.getElementById('username').value,
                password: document.getElementById('password').value
            };
            
            if (!formData.source_name || !formData.username || !formData.password) {
                showResult('error', '모든 필드를 입력해주세요.');
                return;
            }
            
            try {
                const response = await fetch('/api/collection/settings/credentials', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showResult('success', '자격증명이 성공적으로 저장되었습니다.');
                    document.getElementById('credentialsForm').reset();
                } else {
                    showResult('error', '자격증명 저장 실패: ' + result.error);
                }
                
            } catch (error) {
                showResult('error', '요청 실패: ' + error.message);
            }
        });
        
        // 소스 토글
        async function toggleSource(sourceName, enabled) {
            try {
                const response = await fetch(`/api/collection/settings/sources/${sourceName}/toggle`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({enabled: enabled})
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showResult('success', `${sourceName} 소스가 ${enabled ? '활성화' : '비활성화'}되었습니다.`);
                    loadSources();
                } else {
                    showResult('error', '소스 상태 변경 실패: ' + result.error);
                }
                
            } catch (error) {
                showResult('error', '요청 실패: ' + error.message);
            }
        }
        
        // 수집 테스트
        async function runCollectionTest() {
            const sourceName = document.getElementById('credentialSource').value;
            if (!sourceName) {
                showResult('error', '테스트할 소스를 선택하세요.');
                return;
            }
            
            showResult('info', '수집 테스트 진행 중...');
            
            try {
                const response = await fetch(`/api/collection/settings/test/${sourceName}`, {
                    method: 'POST'
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showResult('success', `테스트 성공! ${result.count}개 IP 수집됨`);
                } else {
                    showResult('error', '테스트 실패: ' + result.error);
                }
                
            } catch (error) {
                showResult('error', '테스트 요청 실패: ' + error.message);
            }
        }
        
        // 결과 표시
        function showResult(type, message) {
            const container = document.getElementById('testResults');
            container.innerHTML = `<div class="status ${type}">${message}</div>`;
        }
        
        // 연결 테스트
        async function testCredentials() {
            const sourceName = document.getElementById('credentialSource').value;
            if (!sourceName) {
                showResult('error', '테스트할 소스를 선택하세요.');
                return;
            }
            
            showResult('info', '연결 테스트 진행 중...');
            
            try {
                const response = await fetch(`/api/collection/settings/test-connection/${sourceName}`, {
                    method: 'POST'
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showResult('success', '연결 테스트 성공!');
                } else {
                    showResult('error', '연결 테스트 실패: ' + result.error);
                }
                
            } catch (error) {
                showResult('error', '테스트 요청 실패: ' + error.message);
            }
        }
    </script>
</body>
</html>
"""


@bp.route('/ui')
def settings_ui():
    """설정 관리 UI 페이지"""
    return SETTINGS_UI_HTML


@bp.route('/sources', methods=['GET'])
def get_sources():
    """모든 수집 소스 목록 조회"""
    if not DB_AVAILABLE:
        return jsonify({"error": "Database not available"}), 500
    
    try:
        db = get_db()
        sources = db.get_all_sources()
        return jsonify(sources)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/sources', methods=['POST'])
def add_source():
    """새 수집 소스 추가"""
    if not DB_AVAILABLE:
        return jsonify({"error": "Database not available"}), 500
    
    try:
        data = request.get_json() or {}
        
        name = data.get('name', '').strip()
        display_name = data.get('display_name', '').strip()
        base_url = data.get('base_url', '').strip()
        config_str = data.get('config', '{}')
        enabled = data.get('enabled', True)
        
        if not name or not display_name or not base_url:
            return jsonify({"success": False, "error": "필수 필드가 누락되었습니다"}), 400
        
        # JSON 설정 파싱
        try:
            import json
            config = json.loads(config_str) if config_str else {}
        except json.JSONDecodeError:
            return jsonify({"success": False, "error": "설정 JSON 형식이 올바르지 않습니다"}), 400
        
        db = get_db()
        success = db.save_source_config(name, display_name, base_url, config, enabled)
        
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "소스 저장 실패"}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/sources/<source_name>/toggle', methods=['POST'])
def toggle_source(source_name):
    """소스 활성화/비활성화 토글"""
    if not DB_AVAILABLE:
        return jsonify({"error": "Database not available"}), 500
    
    try:
        data = request.get_json() or {}
        enabled = data.get('enabled', True)
        
        db = get_db()
        # 기존 설정 조회
        source_config = db.get_source_config(source_name)
        if not source_config:
            return jsonify({"success": False, "error": "소스를 찾을 수 없습니다"}), 404
        
        # 상태 업데이트
        success = db.save_source_config(
            source_name,
            source_config['display_name'],
            source_config['base_url'],
            source_config['config'],
            enabled
        )
        
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "상태 변경 실패"}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/credentials', methods=['POST'])
def save_credentials():
    """자격증명 저장"""
    if not DB_AVAILABLE:
        return jsonify({"error": "Database not available"}), 500
    
    try:
        data = request.get_json() or {}
        
        source_name = data.get('source_name', '').strip()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not source_name or not username or not password:
            return jsonify({"success": False, "error": "모든 필드가 필요합니다"}), 400
        
        db = get_db()
        success = db.save_credentials(source_name, username, password)
        
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "자격증명 저장 실패"}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/test/<source_name>', methods=['POST'])
def test_collection(source_name):
    """수집 테스트"""
    if not DB_AVAILABLE:
        return jsonify({"error": "Database not available"}), 500
    
    try:
        # 기존 수집기 사용하여 테스트
        from ..collection_db_collector import DatabaseCollectionSystem
        
        collector = DatabaseCollectionSystem()
        result = collector.collect_from_source(source_name)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/test-connection/<source_name>', methods=['POST'])
def test_connection(source_name):
    """연결 테스트"""
    if not DB_AVAILABLE:
        return jsonify({"error": "Database not available"}), 500
    
    try:
        db = get_db()
        
        # 설정 및 자격증명 확인
        source_config = db.get_source_config(source_name)
        credentials = db.get_credentials(source_name)
        
        if not source_config:
            return jsonify({"success": False, "error": "소스 설정이 없습니다"})
        
        if not credentials:
            return jsonify({"success": False, "error": "자격증명이 없습니다"})
        
        # 간단한 연결 테스트 (ping 형태)
        import requests
        
        base_url = source_config["base_url"]
        timeout = source_config.get("config", {}).get("timeout", 10)
        
        response = requests.get(base_url, timeout=timeout)
        
        if response.status_code == 200:
            return jsonify({"success": True, "message": f"연결 성공 ({response.status_code})"})
        else:
            return jsonify({"success": False, "error": f"연결 실패: HTTP {response.status_code}"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500