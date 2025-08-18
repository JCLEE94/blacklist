/**
 * Unified Dashboard JavaScript
 * Handles all client-side functionality for the unified control dashboard
 */

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