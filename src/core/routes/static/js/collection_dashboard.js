/**
 * 수집기 통합 관리패널 JavaScript
 * 일자별 수집 현황 시각화, 실시간 모니터링, 차트 업데이트
 */

// 전역 변수
let collectionChart = null;
let dashboardData = {};
let updateInterval = null;

// Chart.js 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeChart();
    loadDashboardData();
    startAutoUpdate();
    
    // 이벤트 리스너 등록
    document.getElementById('period-selector')?.addEventListener('change', updateChartPeriod);
});

/**
 * 차트 초기화
 */
function initializeChart() {
    const ctx = document.getElementById('collection-chart');
    if (!ctx) return;
    
    collectionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'REGTECH',
                    data: [],
                    borderColor: '#4CAF50',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    fill: true,
                    tension: 0.3
                },
                {
                    label: 'SECUDIUM',
                    data: [],
                    borderColor: '#2196F3',
                    backgroundColor: 'rgba(33, 150, 243, 0.1)',
                    fill: true,
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'IP 수'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: '날짜'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        title: function(context) {
                            return '날짜: ' + context[0].label;
                        },
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y + '개 IP';
                        }
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

/**
 * 대시보드 데이터 로드
 */
async function loadDashboardData() {
    try {
        showLoadingIndicator();
        
        const days = document.getElementById('period-selector')?.value || 30;
        const response = await fetch(`/api/collection/dashboard/data?days=${days}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            dashboardData = result.data;
            updateDashboard(dashboardData);
        } else {
            throw new Error(result.error || '데이터 로드 실패');
        }
        
    } catch (error) {
        console.error('대시보드 데이터 로드 오류:', error);
        showError('대시보드 데이터를 불러올 수 없습니다: ' + error.message);
    } finally {
        hideLoadingIndicator();
    }
}

/**
 * 대시보드 업데이트
 */
function updateDashboard(data) {
    // 기본 통계 업데이트
    updateStats(data.system_health);
    
    // 차트 업데이트
    updateChart(data.chart_data);
    
    // 소스별 통계 업데이트
    updateSourceStats(data.source_stats);
    
    // 기간별 가용성 업데이트
    updatePeriodAvailability(data.period_availability);
    
    // 마지막 업데이트 시간
    document.getElementById('last-updated')?.innerHTML = 
        formatTime(data.last_updated);
}

/**
 * 기본 통계 업데이트
 */
function updateStats(systemHealth) {
    if (!systemHealth) return;
    
    document.getElementById('total-threats')?.innerHTML = 
        formatNumber(systemHealth.total_ips || 0);
    
    document.getElementById('active-sources')?.innerHTML = 
        (systemHealth.regtech_enabled ? 1 : 0) + '/2';
    
    document.getElementById('system-status')?.innerHTML = 
        systemHealth.status === 'healthy' ? '🟢 정상' : '🔴 오류';
}

/**
 * 차트 업데이트
 */
function updateChart(chartData) {
    if (!collectionChart || !chartData) return;
    
    collectionChart.data.labels = chartData.labels;
    collectionChart.data.datasets[0].data = chartData.datasets[0].data;
    collectionChart.data.datasets[1].data = chartData.datasets[1].data;
    
    collectionChart.update('none'); // 애니메이션 없이 업데이트
}

/**
 * 소스별 통계 업데이트
 */
function updateSourceStats(sourceStats) {
    if (!sourceStats) return;
    
    // REGTECH 통계
    const regtech = sourceStats.REGTECH || {};
    document.getElementById('regtech-count')?.innerHTML = 
        formatNumber(regtech.total_ips || 0) + '개';
    document.getElementById('regtech-rate')?.innerHTML = 
        (regtech.success_rate || 0).toFixed(1) + '%';
    
    const regtechProgress = document.getElementById('regtech-progress');
    if (regtechProgress) {
        regtechProgress.style.width = (regtech.success_rate || 0) + '%';
        regtechProgress.className = `progress ${getProgressColor(regtech.success_rate || 0)}`;
    }
    
    // SECUDIUM 통계
    const secudium = sourceStats.SECUDIUM || {};
    document.getElementById('secudium-count')?.innerHTML = 
        formatNumber(secudium.total_ips || 0) + '개';
    document.getElementById('secudium-rate')?.innerHTML = 
        (secudium.success_rate || 0).toFixed(1) + '%';
    
    const secudiumProgress = document.getElementById('secudium-progress');
    if (secudiumProgress) {
        secudiumProgress.style.width = (secudium.success_rate || 0) + '%';
        secudiumProgress.className = `progress ${getProgressColor(secudium.success_rate || 0)}`;
    }
}

/**
 * 기간별 가용성 업데이트
 */
function updatePeriodAvailability(periodData) {
    if (!periodData) return;
    
    const container = document.getElementById('period-availability');
    if (!container) return;
    
    container.innerHTML = '';
    
    Object.entries(periodData).forEach(([period, info]) => {
        const item = document.createElement('div');
        item.className = 'period-item';
        
        const statusClass = info.available ? 'available' : 'unavailable';
        const statusIcon = info.available ? '✅' : '❌';
        const statusText = info.available ? '가능' : '불가';
        const countText = info.available ? ` (${info.ip_count}개)` : '';
        
        item.innerHTML = `
            <span class="period-name">${period}</span>
            <span class="period-status ${statusClass}">
                ${statusIcon} ${statusText}${countText}
            </span>
        `;
        
        container.appendChild(item);
    });
}

/**
 * 차트 기간 업데이트
 */
async function updateChartPeriod() {
    await loadDashboardData();
}

/**
 * 자동 업데이트 시작
 */
function startAutoUpdate() {
    // 기존 인터벌 정리
    if (updateInterval) {
        clearInterval(updateInterval);
    }
    
    // 30초마다 자동 업데이트
    updateInterval = setInterval(async () => {
        try {
            await loadDashboardData();
            updateLastRefresh();
        } catch (error) {
            console.error('자동 업데이트 오류:', error);
        }
    }, 30000);
}

/**
 * 자동 업데이트 중지
 */
function stopAutoUpdate() {
    if (updateInterval) {
        clearInterval(updateInterval);
        updateInterval = null;
    }
}

/**
 * 수동 새로고침
 */
async function refreshDashboard() {
    await loadDashboardData();
    updateLastRefresh();
}

/**
 * 기간별 수집 테스트
 */
async function testPeriodCollection(days) {
    try {
        showLoadingIndicator('기간별 수집 테스트 중...');
        
        const response = await fetch('/api/collection/period/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ days: days })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(`${days}일 기간 테스트 완료: ${result.data.ip_count || 0}개 IP`);
            await loadDashboardData(); // 결과 반영
        } else {
            throw new Error(result.error || '테스트 실패');
        }
        
    } catch (error) {
        console.error('기간별 테스트 오류:', error);
        showError('기간별 수집 테스트 실패: ' + error.message);
    } finally {
        hideLoadingIndicator();
    }
}

/**
 * 유틸리티 함수들
 */

function formatNumber(num) {
    return new Intl.NumberFormat('ko-KR').format(num);
}

function formatTime(isoString) {
    if (!isoString) return '-';
    
    const date = new Date(isoString);
    return date.toLocaleString('ko-KR', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function getProgressColor(rate) {
    if (rate >= 90) return 'excellent';
    if (rate >= 70) return 'good';
    if (rate >= 50) return 'fair';
    return 'poor';
}

function updateLastRefresh() {
    const refreshElement = document.getElementById('last-refresh');
    if (refreshElement) {
        refreshElement.textContent = '마지막 새로고침: ' + new Date().toLocaleTimeString('ko-KR');
    }
}

function showLoadingIndicator(message = '로딩 중...') {
    // 로딩 인디케이터 표시
    const indicator = document.getElementById('loading-indicator');
    if (indicator) {
        indicator.textContent = message;
        indicator.style.display = 'block';
    }
}

function hideLoadingIndicator() {
    const indicator = document.getElementById('loading-indicator');
    if (indicator) {
        indicator.style.display = 'none';
    }
}

function showSuccess(message) {
    console.log('성공:', message);
    // 실제로는 토스트 알림 등으로 구현
}

function showError(message) {
    console.error('오류:', message);
    // 실제로는 토스트 알림 등으로 구현
}

// 페이지 언로드 시 정리
window.addEventListener('beforeunload', function() {
    stopAutoUpdate();
});

// 전역 함수로 노출 (HTML에서 호출용)
window.refreshDashboard = refreshDashboard;
window.testPeriodCollection = testPeriodCollection;
window.updateChartPeriod = updateChartPeriod;