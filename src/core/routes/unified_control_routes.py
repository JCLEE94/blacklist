#!/usr/bin/env python3
"""
통합 제어 대시보드 - /unified-control
모든 수집 기능, 시각화, 설정을 하나로 통합
"""

from flask import Blueprint, jsonify, render_template_string, request
from datetime import datetime

try:
    from ..database.collection_settings import CollectionSettingsDB
    from ..collection_db_collector import DatabaseCollectionSystem
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

bp = Blueprint('unified_control', __name__)


# 통합 대시보드 HTML
UNIFIED_DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>통합 제어 대시보드 - Blacklist Management</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f0f23; color: #cccccc; }
        
        /* 헤더 */
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center; }
        .header h1 { color: white; font-size: 2.5em; margin-bottom: 10px; }
        .header p { color: rgba(255,255,255,0.9); font-size: 1.1em; }
        
        /* 컨테이너 */
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        
        /* 탭 네비게이션 */
        .tabs { display: flex; background: #1e1e1e; border-radius: 8px; margin-bottom: 20px; overflow: hidden; }
        .tab { flex: 1; padding: 15px; text-align: center; background: #2d2d2d; cursor: pointer; transition: all 0.3s; }
        .tab:hover { background: #3d3d3d; }
        .tab.active { background: #4a90e2; color: white; }
        
        /* 카드 스타일 */
        .card { background: #1e1e1e; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); }
        .card h3 { color: #4a90e2; margin-bottom: 15px; font-size: 1.3em; }
        
        /* 그리드 */
        .grid { display: grid; gap: 20px; }
        .grid-2 { grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); }
        .grid-3 { grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }
        .grid-4 { grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); }
        
        /* 통계 카드 */
        .stat-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-align: center; border-radius: 12px; padding: 20px; }
        .stat-card .value { font-size: 2.5em; font-weight: bold; margin-bottom: 5px; }
        .stat-card .label { font-size: 0.9em; opacity: 0.9; }
        
        /* 캘린더 */
        .calendar { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; margin: 20px 0; }
        .calendar-day { aspect-ratio: 1; display: flex; align-items: center; justify-content: center; background: #2d2d2d; border-radius: 4px; font-size: 0.8em; transition: all 0.3s; position: relative; }
        .calendar-day:hover { background: #3d3d3d; }
        .calendar-day.header { background: #4a90e2; color: white; font-weight: bold; }
        .calendar-day.collected { background: #27ae60; color: white; }
        .calendar-day.failed { background: #e74c3c; color: white; }
        .calendar-day .count { position: absolute; bottom: 2px; right: 2px; font-size: 0.7em; }
        
        /* 폼 */
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #cccccc; font-weight: 500; }
        .form-control { width: 100%; padding: 10px; background: #2d2d2d; border: 1px solid #3d3d3d; border-radius: 6px; color: #cccccc; }
        .form-control:focus { outline: none; border-color: #4a90e2; box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.2); }
        
        /* 버튼 */
        .btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; transition: all 0.3s; }
        .btn-primary { background: #4a90e2; color: white; }
        .btn-primary:hover { background: #357abd; }
        .btn-success { background: #27ae60; color: white; }
        .btn-success:hover { background: #219a52; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-danger:hover { background: #c0392b; }
        .btn-warning { background: #f39c12; color: white; }
        .btn-warning:hover { background: #d68910; }
        
        /* 토글 스위치 */
        .toggle { position: relative; display: inline-block; width: 50px; height: 24px; }
        .toggle input { opacity: 0; width: 0; height: 0; }
        .toggle .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #3d3d3d; transition: .4s; border-radius: 24px; }
        .toggle .slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; }
        .toggle input:checked + .slider { background-color: #4a90e2; }
        .toggle input:checked + .slider:before { transform: translateX(26px); }
        
        /* 상태 배지 */
        .status { padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
        .status.success { background: #27ae60; color: white; }
        .status.error { background: #e74c3c; color: white; }
        .status.warning { background: #f39c12; color: white; }
        .status.info { background: #3498db; color: white; }
        
        /* 로그 */
        .log-container { background: #0f0f0f; border: 1px solid #3d3d3d; border-radius: 6px; max-height: 300px; overflow-y: auto; padding: 10px; font-family: monospace; font-size: 0.9em; }
        .log-entry { padding: 2px 0; }
        .log-entry.error { color: #e74c3c; }
        .log-entry.success { color: #27ae60; }
        .log-entry.info { color: #3498db; }
        
        /* 숨김/표시 */
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        /* 반응형 */
        @media (max-width: 768px) {
            .container { padding: 10px; }
            .tabs { flex-direction: column; }
            .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎛️ 통합 제어 대시보드</h1>
        <p>수집 관리, 시각화, 설정을 한 곳에서</p>
    </div>
    
    <div class="container">
        <!-- 탭 네비게이션 -->
        <div class="tabs">
            <div class="tab active" onclick="showTab('overview')">📊 개요</div>
            <div class="tab" onclick="showTab('collection')">🔄 수집 관리</div>
            <div class="tab" onclick="showTab('visualization')">📅 시각화</div>
            <div class="tab" onclick="showTab('settings')">⚙️ 설정</div>
            <div class="tab" onclick="showTab('monitoring')">📈 모니터링</div>
        </div>
        
        <!-- 개요 탭 -->
        <div id="overview" class="tab-content active">
            <div class="grid grid-4">
                <div class="stat-card">
                    <div class="value" id="totalCollections">0</div>
                    <div class="label">총 수집</div>
                </div>
                <div class="stat-card">
                    <div class="value" id="successfulCollections">0</div>
                    <div class="label">성공</div>
                </div>
                <div class="stat-card">
                    <div class="value" id="totalIPs">0</div>
                    <div class="label">수집 IP</div>
                </div>
                <div class="stat-card">
                    <div class="value" id="activeSources">0</div>
                    <div class="label">활성 소스</div>
                </div>
            </div>
            
            <div class="grid grid-2">
                <div class="card">
                    <h3>최근 수집 이력</h3>
                    <div id="recentCollections">로딩 중...</div>
                </div>
                <div class="card">
                    <h3>소스별 통계</h3>
                    <div id="sourceStats">로딩 중...</div>
                </div>
            </div>
        </div>
        
        <!-- 수집 관리 탭 -->
        <div id="collection" class="tab-content">
            <div class="grid grid-2">
                <div class="card">
                    <h3>활성 소스</h3>
                    <div id="activeSourcesList">로딩 중...</div>
                </div>
                <div class="card">
                    <h3>수집 제어</h3>
                    <div class="form-group">
                        <label>소스 선택:</label>
                        <select class="form-control" id="collectSourceSelect">
                            <option value="">전체</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>시작 날짜:</label>
                        <input type="date" class="form-control" id="collectStartDate">
                    </div>
                    <div class="form-group">
                        <label>종료 날짜:</label>
                        <input type="date" class="form-control" id="collectEndDate">
                    </div>
                    <button class="btn btn-success" onclick="startCollection()">🚀 수집 시작</button>
                    <button class="btn btn-warning" onclick="testConnection()">🔗 연결 테스트</button>
                </div>
            </div>
            
            <div class="card">
                <h3>수집 로그</h3>
                <div class="log-container" id="collectionLogs">
                    <div class="log-entry info">[INFO] 시스템 준비됨</div>
                </div>
            </div>
        </div>
        
        <!-- 시각화 탭 -->
        <div id="visualization" class="tab-content">
            <div class="card">
                <h3>월별 수집 캘린더</h3>
                <div class="form-group">
                    <select class="form-control" id="calendarMonth" onchange="loadCalendar()">
                        <!-- 동적으로 생성 -->
                    </select>
                </div>
                <div class="calendar" id="collectionCalendar">
                    <!-- 동적으로 생성 -->
                </div>
            </div>
        </div>
        
        <!-- 설정 탭 -->
        <div id="settings" class="tab-content">
            <div class="grid grid-2">
                <div class="card">
                    <h3>수집 소스 관리</h3>
                    <div id="sourcesList">로딩 중...</div>
                    
                    <h4>새 소스 추가</h4>
                    <div class="form-group">
                        <label>소스 이름:</label>
                        <input type="text" class="form-control" id="newSourceName" placeholder="예: regtech">
                    </div>
                    <div class="form-group">
                        <label>표시 이름:</label>
                        <input type="text" class="form-control" id="newSourceDisplayName" placeholder="예: REGTECH 위협정보">
                    </div>
                    <div class="form-group">
                        <label>기본 URL:</label>
                        <input type="url" class="form-control" id="newSourceUrl" placeholder="https://example.com">
                    </div>
                    <button class="btn btn-primary" onclick="addSource()">소스 추가</button>
                </div>
                
                <div class="card">
                    <h3>자격증명 관리</h3>
                    <div class="form-group">
                        <label>소스:</label>
                        <select class="form-control" id="credSourceSelect">
                            <option value="">선택하세요</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>사용자명:</label>
                        <input type="text" class="form-control" id="credUsername">
                    </div>
                    <div class="form-group">
                        <label>패스워드:</label>
                        <input type="password" class="form-control" id="credPassword">
                    </div>
                    <button class="btn btn-success" onclick="saveCredentials()">자격증명 저장</button>
                </div>
            </div>
        </div>
        
        <!-- 모니터링 탭 -->
        <div id="monitoring" class="tab-content">
            <div class="grid grid-2">
                <div class="card">
                    <h3>시스템 상태</h3>
                    <div id="systemStatus">
                        <p>🔄 상태 확인 중...</p>
                    </div>
                </div>
                <div class="card">
                    <h3>성능 메트릭</h3>
                    <div id="performanceMetrics">
                        <p>📊 메트릭 로딩 중...</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // 전역 변수
        let currentStats = {};
        let currentSources = [];
        
        // 초기화
        document.addEventListener('DOMContentLoaded', function() {
            initializeDashboard();
            initializeDateInputs();
            initializeCalendarMonths();
            
            // 주기적 업데이트 (30초마다)
            setInterval(refreshData, 30000);
        });
        
        function initializeDashboard() {
            loadStatistics();
            loadSources();
            loadCalendar();
        }
        
        function initializeDateInputs() {
            const today = new Date().toISOString().split('T')[0];
            const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
            
            document.getElementById('collectStartDate').value = weekAgo;
            document.getElementById('collectEndDate').value = today;
        }
        
        function initializeCalendarMonths() {
            const select = document.getElementById('calendarMonth');
            const now = new Date();
            
            for (let i = -6; i <= 0; i++) {
                const date = new Date(now.getFullYear(), now.getMonth() + i, 1);
                const option = document.createElement('option');
                option.value = `${date.getFullYear()}-${date.getMonth() + 1}`;
                option.text = `${date.getFullYear()}년 ${date.getMonth() + 1}월`;
                if (i === 0) option.selected = true;
                select.appendChild(option);
            }
        }
        
        // 탭 전환
        function showTab(tabName) {
            // 모든 탭 콘텐츠 숨기기
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // 모든 탭 버튼 비활성화
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // 선택된 탭 활성화
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
            
            // 탭별 데이터 로드
            if (tabName === 'visualization') {
                loadCalendar();
            } else if (tabName === 'settings') {
                loadSources();
            }
        }
        
        // 통계 로드
        async function loadStatistics() {
            try {
                const response = await fetch('/api/collection/viz/stats');
                const stats = await response.json();
                currentStats = stats;
                
                updateStatCards(stats);
                updateRecentCollections(stats.recent_collections);
                updateSourceStats(stats.sources);
                
            } catch (error) {
                console.error('통계 로드 실패:', error);
                logMessage('error', '통계 로드 실패: ' + error.message);
            }
        }
        
        function updateStatCards(stats) {
            document.getElementById('totalCollections').textContent = stats.total_collections || 0;
            document.getElementById('successfulCollections').textContent = stats.successful_collections || 0;
            document.getElementById('totalIPs').textContent = (stats.total_ips_collected || 0).toLocaleString();
            document.getElementById('activeSources').textContent = stats.enabled_sources?.length || 0;
        }
        
        function updateRecentCollections(recent) {
            const container = document.getElementById('recentCollections');
            if (!recent || recent.length === 0) {
                container.innerHTML = '<p>최근 수집 이력이 없습니다.</p>';
                return;
            }
            
            container.innerHTML = recent.slice(0, 5).map(item => `
                <div class="log-entry ${item.success ? 'success' : 'error'}">
                    <strong>${item.source}</strong> - ${new Date(item.collected_at).toLocaleString()}<br>
                    ${item.success ? `✅ ${item.count} IPs` : `❌ ${item.error}`}
                </div>
            `).join('');
        }
        
        function updateSourceStats(sources) {
            const container = document.getElementById('sourceStats');
            if (!sources || Object.keys(sources).length === 0) {
                container.innerHTML = '<p>소스별 통계가 없습니다.</p>';
                return;
            }
            
            container.innerHTML = Object.entries(sources).map(([source, stats]) => `
                <div style="margin-bottom: 10px; padding: 10px; background: #2d2d2d; border-radius: 6px;">
                    <strong>${source}</strong><br>
                    <small>시도: ${stats.total}, 성공: ${stats.success}, IP: ${stats.total_ips}</small>
                </div>
            `).join('');
        }
        
        // 소스 로드
        async function loadSources() {
            try {
                const response = await fetch('/api/collection/settings/sources');
                const sources = await response.json();
                currentSources = sources;
                
                updateActiveSourcesList(sources);
                updateSourceSelects(sources);
                updateSourcesManagement(sources);
                
            } catch (error) {
                console.error('소스 로드 실패:', error);
                logMessage('error', '소스 로드 실패: ' + error.message);
            }
        }
        
        function updateActiveSourcesList(sources) {
            const container = document.getElementById('activeSourcesList');
            const activeSources = sources.filter(s => s.enabled);
            
            if (activeSources.length === 0) {
                container.innerHTML = '<p>활성 소스가 없습니다.</p>';
                return;
            }
            
            container.innerHTML = activeSources.map(source => `
                <div style="margin-bottom: 10px; padding: 10px; background: #2d2d2d; border-radius: 6px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong>${source.display_name}</strong><br>
                            <small>${source.base_url}</small>
                        </div>
                        <label class="toggle">
                            <input type="checkbox" ${source.enabled ? 'checked' : ''} 
                                   onchange="toggleSource('${source.name}', this.checked)">
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>
            `).join('');
        }
        
        function updateSourceSelects(sources) {
            const selects = ['collectSourceSelect', 'credSourceSelect'];
            
            selects.forEach(selectId => {
                const select = document.getElementById(selectId);
                if (selectId === 'collectSourceSelect') {
                    select.innerHTML = '<option value="">전체</option>';
                } else {
                    select.innerHTML = '<option value="">선택하세요</option>';
                }
                
                sources.forEach(source => {
                    const option = document.createElement('option');
                    option.value = source.name;
                    option.textContent = source.display_name;
                    select.appendChild(option);
                });
            });
        }
        
        function updateSourcesManagement(sources) {
            const container = document.getElementById('sourcesList');
            if (sources.length === 0) {
                container.innerHTML = '<p>등록된 소스가 없습니다.</p>';
                return;
            }
            
            container.innerHTML = sources.map(source => `
                <div style="margin-bottom: 10px; padding: 10px; background: #2d2d2d; border-radius: 6px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong>${source.display_name}</strong><br>
                            <small>${source.base_url}</small><br>
                            <span class="status ${source.enabled ? 'success' : 'error'}">
                                ${source.enabled ? '활성' : '비활성'}
                            </span>
                        </div>
                        <div>
                            <button class="btn btn-warning" onclick="editSource('${source.name}')">편집</button>
                        </div>
                    </div>
                </div>
            `).join('');
        }
        
        // 캘린더 로드
        async function loadCalendar() {
            const monthSelect = document.getElementById('calendarMonth');
            if (!monthSelect.value) return;
            
            const [year, month] = monthSelect.value.split('-').map(Number);
            
            try {
                const response = await fetch(`/api/collection/viz/calendar?year=${year}&month=${month}`);
                const data = await response.json();
                
                displayCalendar(data);
                
            } catch (error) {
                console.error('캘린더 로드 실패:', error);
                logMessage('error', '캘린더 로드 실패: ' + error.message);
            }
        }
        
        function displayCalendar(data) {
            const container = document.getElementById('collectionCalendar');
            container.innerHTML = '';
            
            // 요일 헤더
            const weekdays = ['일', '월', '화', '수', '목', '금', '토'];
            weekdays.forEach(day => {
                const div = document.createElement('div');
                div.className = 'calendar-day header';
                div.textContent = day;
                container.appendChild(div);
            });
            
            // 첫 날의 요일 계산
            const firstDay = new Date(data.year, data.month - 1, 1).getDay();
            
            // 빈 칸 채우기
            for (let i = 0; i < firstDay; i++) {
                const div = document.createElement('div');
                div.className = 'calendar-day';
                container.appendChild(div);
            }
            
            // 날짜 표시
            Object.entries(data.calendar).forEach(([date, info]) => {
                const day = parseInt(date.split('-')[2]);
                const div = document.createElement('div');
                div.className = 'calendar-day';
                
                if (info.collected) {
                    div.classList.add('collected');
                    div.innerHTML = `${day}<span class="count">${info.count}</span>`;
                } else {
                    div.textContent = day;
                }
                
                div.title = `${date}: ${info.collected ? info.count + ' IPs 수집됨' : '수집 없음'}`;
                container.appendChild(div);
            });
        }
        
        // 수집 시작
        async function startCollection() {
            const source = document.getElementById('collectSourceSelect').value;
            const startDate = document.getElementById('collectStartDate').value;
            const endDate = document.getElementById('collectEndDate').value;
            
            if (!startDate || !endDate) {
                alert('날짜를 입력하세요.');
                return;
            }
            
            logMessage('info', `수집 시작: ${source || '전체'} (${startDate} ~ ${endDate})`);
            
            try {
                const response = await fetch('/api/collection/viz/collect', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        source_name: source,
                        start_date: startDate,
                        end_date: endDate
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    logMessage('success', `수집 성공: ${result.count}개 IP`);
                    refreshData();
                } else {
                    logMessage('error', `수집 실패: ${result.error}`);
                }
                
            } catch (error) {
                logMessage('error', '수집 요청 실패: ' + error.message);
            }
        }
        
        // 연결 테스트
        async function testConnection() {
            const source = document.getElementById('collectSourceSelect').value;
            if (!source) {
                alert('테스트할 소스를 선택하세요.');
                return;
            }
            
            logMessage('info', `연결 테스트: ${source}`);
            
            try {
                const response = await fetch(`/api/collection/settings/test-connection/${source}`, {
                    method: 'POST'
                });
                
                const result = await response.json();
                
                if (result.success) {
                    logMessage('success', `연결 테스트 성공: ${result.message || 'OK'}`);
                } else {
                    logMessage('error', `연결 테스트 실패: ${result.error}`);
                }
                
            } catch (error) {
                logMessage('error', '연결 테스트 요청 실패: ' + error.message);
            }
        }
        
        // 소스 추가
        async function addSource() {
            const name = document.getElementById('newSourceName').value.trim();
            const displayName = document.getElementById('newSourceDisplayName').value.trim();
            const url = document.getElementById('newSourceUrl').value.trim();
            
            if (!name || !displayName || !url) {
                alert('모든 필드를 입력하세요.');
                return;
            }
            
            try {
                const response = await fetch('/api/collection/settings/sources', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        name: name,
                        display_name: displayName,
                        base_url: url,
                        config: '{}',
                        enabled: true
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    logMessage('success', '소스가 성공적으로 추가되었습니다.');
                    document.getElementById('newSourceName').value = '';
                    document.getElementById('newSourceDisplayName').value = '';
                    document.getElementById('newSourceUrl').value = '';
                    loadSources();
                } else {
                    logMessage('error', '소스 추가 실패: ' + result.error);
                }
                
            } catch (error) {
                logMessage('error', '소스 추가 요청 실패: ' + error.message);
            }
        }
        
        // 자격증명 저장
        async function saveCredentials() {
            const source = document.getElementById('credSourceSelect').value;
            const username = document.getElementById('credUsername').value.trim();
            const password = document.getElementById('credPassword').value.trim();
            
            if (!source || !username || !password) {
                alert('모든 필드를 입력하세요.');
                return;
            }
            
            try {
                const response = await fetch('/api/collection/settings/credentials', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        source_name: source,
                        username: username,
                        password: password
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    logMessage('success', '자격증명이 성공적으로 저장되었습니다.');
                    document.getElementById('credUsername').value = '';
                    document.getElementById('credPassword').value = '';
                } else {
                    logMessage('error', '자격증명 저장 실패: ' + result.error);
                }
                
            } catch (error) {
                logMessage('error', '자격증명 저장 요청 실패: ' + error.message);
            }
        }
        
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
                    logMessage('success', `${sourceName} 소스가 ${enabled ? '활성화' : '비활성화'}되었습니다.`);
                    loadSources();
                } else {
                    logMessage('error', '소스 상태 변경 실패: ' + result.error);
                }
                
            } catch (error) {
                logMessage('error', '소스 토글 요청 실패: ' + error.message);
            }
        }
        
        // 로그 메시지 추가
        function logMessage(type, message) {
            const container = document.getElementById('collectionLogs');
            const entry = document.createElement('div');
            entry.className = `log-entry ${type}`;
            entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            
            container.appendChild(entry);
            container.scrollTop = container.scrollHeight;
            
            // 최대 100개 항목만 유지
            while (container.children.length > 100) {
                container.removeChild(container.firstChild);
            }
        }
        
        // 데이터 새로고침
        function refreshData() {
            loadStatistics();
            loadSources();
            if (document.getElementById('visualization').classList.contains('active')) {
                loadCalendar();
            }
        }
        
        // 편집 기능 (추후 구현)
        function editSource(sourceName) {
            alert(`${sourceName} 편집 기능은 곧 구현됩니다.`);
        }
    </script>
</body>
</html>
"""


@bp.route('/unified-control')
def unified_control_dashboard():
    """통합 제어 대시보드 메인 페이지"""
    return UNIFIED_DASHBOARD_HTML


@bp.route('/api/unified/status')
def get_unified_status():
    """통합 시스템 상태 조회"""
    if not DB_AVAILABLE:
        return jsonify({"error": "Database not available"}), 500
    
    try:
        db = CollectionSettingsDB()
        collector = DatabaseCollectionSystem()
        
        # 기본 통계
        stats = db.get_collection_statistics()
        
        # 활성 소스
        sources = db.get_all_sources()
        active_sources = [s for s in sources if s['enabled']]
        
        # 최근 상태
        recent_collections = stats.get('recent_collections', [])[:5]
        
        return jsonify({
            "status": "healthy",
            "statistics": {
                "total_collections": stats.get('total_collections', 0),
                "successful_collections": stats.get('successful_collections', 0),
                "failed_collections": stats.get('failed_collections', 0),
                "total_ips": stats.get('total_ips_collected', 0)
            },
            "sources": {
                "total": len(sources),
                "active": len(active_sources),
                "list": active_sources
            },
            "recent_activity": recent_collections,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@bp.route('/api/unified/health')
def health_check():
    """헬스 체크"""
    try:
        if not DB_AVAILABLE:
            return jsonify({
                "status": "degraded",
                "message": "Database not available",
                "components": {
                    "database": "unavailable",
                    "collector": "unavailable"
                }
            }), 503
        
        # DB 연결 테스트
        db = CollectionSettingsDB()
        sources = db.get_all_sources()
        
        return jsonify({
            "status": "healthy",
            "message": "All systems operational",
            "components": {
                "database": "healthy",
                "collector": "healthy"
            },
            "sources_count": len(sources),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500