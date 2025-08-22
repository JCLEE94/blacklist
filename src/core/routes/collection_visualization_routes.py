#!/usr/bin/env python3
"""
수집 시각화 라우트 - 날짜별 수집 현황 시각화
"""

from ..common.imports import Blueprint, jsonify, request

from datetime import datetime


from ..collection_unified import UnifiedCollectionSystem

bp = Blueprint("collection_viz", __name__, url_prefix="/api/collection/viz")


# HTML 템플릿
COLLECTION_DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>수집 현황 대시보드</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; }
        .calendar { display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px; margin: 20px 0; }
        .day {
            border: 1px solid #ddd;
            padding: 10px;
            min-height: 60px;
            background: white;
            border-radius: 4px;
            position: relative;
        }
        .day-header { font-weight: bold; background: #34495e; color: white; text-align: center; }
        .day-collected { background: #27ae60; color: white; }
        .day-failed { background: #e74c3c; color: white; }
        .day-number { font-weight: bold; margin-bottom: 5px; }
        .ip-count { font-size: 0.9em; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-title { color: #7f8c8d; font-size: 0.9em; }
        .stat-value { font-size: 2em; font-weight: bold; color: #2c3e50; }
        .controls { margin: 20px 0; }
        .btn {
            padding: 10px 20px;
            margin: 5px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        .btn-primary { background: #3498db; color: white; }
        .btn-success { background: #27ae60; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .recent-list {
            background: white;
            padding: 20px;
            border-radius: 8px;
            max-height: 300px;
            overflow-y: auto;
        }
        .recent-item {
            padding: 10px;
            border-bottom: 1px solid #ecf0f1;
        }
        .recent-item.success { border-left: 4px solid #27ae60; }
        .recent-item.failed { border-left: 4px solid #e74c3c; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 블랙리스트 수집 현황 대시보드</h1>
        <p>날짜별 IP 수집 상태를 시각화합니다</p>
    </div>

    <div class="controls">
        <button class="btn btn-primary" onclick="loadCalendar()">📅 캘린더 새로고침</button>
        <button class="btn btn-success" onclick="collectNow()">▶️ 지금 수집</button>
        <button class="btn btn-primary" onclick="showStats()">📊 통계 보기</button>
        <select id="monthSelector" onchange="changeMonth()">
            <!-- 동적으로 생성 -->
        </select>
    </div>

    <div id="calendar" class="calendar">
        <!-- 캘린더가 여기 표시됨 -->
    </div>

    <div id="stats" class="stats">
        <!-- 통계가 여기 표시됨 -->
    </div>

    <div class="recent-list">
        <h3>최근 수집 이력</h3>
        <div id="recentCollections">
            <!-- 최근 수집 이력 표시 -->
        </div>
    </div>

    <script>
        let currentYear = new Date().getFullYear();
        let currentMonth = new Date().getMonth() + 1;

        function initMonthSelector() {
            const selector = document.getElementById('monthSelector');
            const now = new Date();

            for (let i = -6; i <= 0; i++) {
                const date = new Date(now.getFullYear(), now.getMonth() + i, 1);
                const option = document.createElement('option');
                option.value = `${date.getFullYear()}-${date.getMonth() + 1}`;
                option.text = `${date.getFullYear()}년 ${date.getMonth() + 1}월`;
                if (i === 0) option.selected = true;
                selector.appendChild(option);
            }
        }

        async function loadCalendar() {
            try {
                const response = await fetch(`/api/collection/viz/calendar?year=${currentYear}&month=${currentMonth}`);
                const data = await response.json();

                const calendarDiv = document.getElementById('calendar');
                calendarDiv.innerHTML = '';

                // 요일 헤더
                const weekdays = ['일', '월', '화', '수', '목', '금', '토'];
                weekdays.forEach(day => {
                    const div = document.createElement('div');
                    div.className = 'day day-header';
                    div.textContent = day;
                    calendarDiv.appendChild(div);
                });

                // 첫 날의 요일 계산
                const firstDay = new Date(currentYear, currentMonth - 1, 1).getDay();

                // 빈 칸 채우기
                for (let i = 0; i < firstDay; i++) {
                    const div = document.createElement('div');
                    div.className = 'day';
                    calendarDiv.appendChild(div);
                }

                // 날짜 표시
                Object.entries(data.calendar).forEach(([date, info]) => {
                    const day = parseInt(date.split('-')[2]);
                    const div = document.createElement('div');
                    div.className = 'day';

                    if (info.collected) {
                        div.classList.add('day-collected');
                    }

                    div.innerHTML = `
                        <div class="day-number">${day}</div>
                        ${info.collected ? `<div class="ip-count">${info.count} IPs</div>` : ''}
                    `;

                    calendarDiv.appendChild(div);
                });

                // 통계 업데이트
                updateStats(data.summary);

            } catch (error) {
                console.error('캘린더 로드 실패:', error);
            }
        }

        function updateStats(summary) {
            const statsDiv = document.getElementById('stats');
            statsDiv.innerHTML = `
                <div class="stat-card">
                    <div class="stat-title">수집일</div>
                    <div class="stat-value">${summary.collected_days}/${summary.total_days}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">총 수집 IP</div>
                    <div class="stat-value">${summary.total_ips.toLocaleString()}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">수집률</div>
                    <div class="stat-value">${Math.round(summary.collected_days / summary.total_days * 100)}%</div>
                </div>
            `;
        }

        async function collectNow() {
            if (!confirm('지금 수집을 시작하시겠습니까?')) return;

            try {
                const response = await fetch('/api/collection/viz/collect', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                });
                const result = await response.json();

                if (result.success) {
                    alert(`수집 성공! ${result.count}개 IP 수집됨`);
                    loadCalendar();
                    loadRecentCollections();
                } else {
                    alert(`수집 실패: ${result.error}`);
                }
            } catch (error) {
                alert('수집 요청 실패: ' + error);
            }
        }

        async function showStats() {
            try {
                const response = await fetch('/api/collection/viz/stats');
                const stats = await response.json();

                alert(`수집 통계:
- 전체 수집: ${stats.total_collections}회
- 성공: ${stats.successful_collections}회
- 실패: ${stats.failed_collections}회
- 총 IP: ${stats.total_ips_collected}개`);

            } catch (error) {
                console.error('통계 로드 실패:', error);
            }
        }

        async function loadRecentCollections() {
            try {
                const response = await fetch('/api/collection/viz/recent');
                const data = await response.json();

                const recentDiv = document.getElementById('recentCollections');
                recentDiv.innerHTML = '';

                data.recent.forEach(item => {
                    const div = document.createElement('div');
                    div.className = `recent-item ${item.success ? 'success' : 'failed'}`;

                    const date = new Date(item.collected_at);
                    div.innerHTML = `
                        <strong>${item.source}</strong> -
                        ${date.toLocaleDateString()} ${date.toLocaleTimeString()}<br>
                        ${item.success ? `✅ ${item.count} IPs` : `❌ ${item.error}`}
                    `;

                    recentDiv.appendChild(div);
                });

            } catch (error) {
                console.error('최근 수집 로드 실패:', error);
            }
        }

        function changeMonth() {
            const selector = document.getElementById('monthSelector');
            const [year, month] = selector.value.split('-');
            currentYear = parseInt(year);
            currentMonth = parseInt(month);
            loadCalendar();
        }

        // 초기화
        initMonthSelector();
        loadCalendar();
        loadRecentCollections();

        // 주기적 새로고침 (30초마다)
        setInterval(() => {
            loadCalendar();
            loadRecentCollections();
        }, 30000);
    </script>
</body>
</html>
"""


# 통합 시스템 인스턴스
collection_system = None


def get_collection_system():
    """싱글톤 패턴으로 수집 시스템 반환"""
    global collection_system
    if collection_system is None:
        collection_system = UnifiedCollectionSystem()
    return collection_system


# @bp.route('/dashboard') - 중복 제거됨, /unified-control 사용


@bp.route("/calendar")
def get_calendar():
    """특정 월의 수집 캘린더 데이터"""
    year = request.args.get("year", datetime.now().year, type=int)
    month = request.args.get("month", datetime.now().month, type=int)

    system = get_collection_system()
    calendar_data = system.get_collection_calendar(year, month)

    return jsonify(calendar_data)


@bp.route("/stats")
def get_stats():
    """수집 통계"""
    system = get_collection_system()
    stats = system.get_statistics()
    return jsonify(stats)


@bp.route("/recent")
def get_recent():
    """최근 수집 이력"""
    system = get_collection_system()
    recent = system.collection_history[-20:] if system.collection_history else []
    return jsonify({"recent": recent})


@bp.route("/collect", methods=["POST"])
def trigger_collection():
    """수집 트리거"""
    data = request.get_json() or {}

    start_date = data.get("start_date")
    end_date = data.get("end_date")

    system = get_collection_system()
    result = system.collect_regtech(start_date, end_date)

    return jsonify(result)


@bp.route("/credentials", methods=["POST"])
def save_credentials():
    """자격증명 저장"""
    data = request.get_json() or {}

    username = data.get("username")
    password = data.get("password")
    source = data.get("source", "regtech")

    if not username or not password:
        return jsonify({"error": "자격증명 필요"}), 400

    system = get_collection_system()
    saved = system.save_credentials(username, password, source)

    return jsonify({"success": saved})
