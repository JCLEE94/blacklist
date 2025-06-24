/**
 * 시스템 상태 모니터링 위젯
 * System Status Monitoring Widget for Blacklist Management
 */

class SystemMonitorWidget {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Container with ID '${containerId}' not found`);
            return;
        }
        
        this.options = {
            updateInterval: options.updateInterval || 10000, // 10초
            showCPU: options.showCPU !== false,
            showMemory: options.showMemory !== false,
            showDisk: options.showDisk !== false,
            showNetwork: options.showNetwork !== false,
            showServices: options.showServices !== false,
            compact: options.compact || false,
            theme: options.theme || 'light',
            ...options
        };
        
        this.charts = {};
        this.data = {
            cpu: [],
            memory: [],
            disk: [],
            network: { in: [], out: [] }
        };
        
        this.maxDataPoints = 30; // 5분간의 데이터
        this.isActive = false;
        
        this.init();
    }
    
    /**
     * 위젯 초기화
     */
    init() {
        this.render();
        this.setupCharts();
        this.startMonitoring();
    }
    
    /**
     * 위젯 렌더링
     */
    render() {
        const widgetHTML = `
            <div class="system-monitor-widget ${this.options.compact ? 'compact' : ''} theme-${this.options.theme}">
                <div class="widget-header">
                    <h5 class="widget-title">
                        <i class="bi bi-activity"></i> 시스템 모니터링
                    </h5>
                    <div class="widget-controls">
                        <button class="btn btn-sm btn-link" onclick="systemMonitor.toggleCompact()">
                            <i class="bi bi-${this.options.compact ? 'arrows-angle-expand' : 'arrows-angle-contract'}"></i>
                        </button>
                        <button class="btn btn-sm btn-link" onclick="systemMonitor.refresh()">
                            <i class="bi bi-arrow-clockwise"></i>
                        </button>
                    </div>
                </div>
                
                <div class="widget-body">
                    ${this.options.showCPU ? this.renderCPUSection() : ''}
                    ${this.options.showMemory ? this.renderMemorySection() : ''}
                    ${this.options.showDisk ? this.renderDiskSection() : ''}
                    ${this.options.showNetwork ? this.renderNetworkSection() : ''}
                    ${this.options.showServices ? this.renderServicesSection() : ''}
                </div>
                
                <div class="widget-footer">
                    <small class="text-muted">
                        마지막 업데이트: <span id="system-monitor-last-update">-</span>
                    </small>
                </div>
            </div>
        `;
        
        this.container.innerHTML = widgetHTML;
        this.addStyles();
    }
    
    /**
     * CPU 섹션 렌더링
     */
    renderCPUSection() {
        return `
            <div class="monitor-section cpu-section">
                <div class="section-header">
                    <span class="section-title">CPU 사용률</span>
                    <span class="section-value" id="cpu-value">0%</span>
                </div>
                <div class="chart-container">
                    <canvas id="cpu-chart" height="${this.options.compact ? 50 : 80}"></canvas>
                </div>
                ${!this.options.compact ? `
                    <div class="section-details">
                        <div class="detail-item">
                            <span>코어 수:</span>
                            <span id="cpu-cores">-</span>
                        </div>
                        <div class="detail-item">
                            <span>평균 부하:</span>
                            <span id="cpu-load">-</span>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    /**
     * 메모리 섹션 렌더링
     */
    renderMemorySection() {
        return `
            <div class="monitor-section memory-section">
                <div class="section-header">
                    <span class="section-title">메모리 사용률</span>
                    <span class="section-value" id="memory-value">0%</span>
                </div>
                <div class="chart-container">
                    <canvas id="memory-chart" height="${this.options.compact ? 50 : 80}"></canvas>
                </div>
                ${!this.options.compact ? `
                    <div class="section-details">
                        <div class="detail-item">
                            <span>사용 중:</span>
                            <span id="memory-used">-</span>
                        </div>
                        <div class="detail-item">
                            <span>전체:</span>
                            <span id="memory-total">-</span>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    /**
     * 디스크 섹션 렌더링
     */
    renderDiskSection() {
        return `
            <div class="monitor-section disk-section">
                <div class="section-header">
                    <span class="section-title">디스크 사용률</span>
                    <span class="section-value" id="disk-value">0%</span>
                </div>
                <div class="progress-container">
                    <div class="progress">
                        <div class="progress-bar" id="disk-progress" role="progressbar" style="width: 0%"></div>
                    </div>
                </div>
                ${!this.options.compact ? `
                    <div class="section-details">
                        <div class="detail-item">
                            <span>사용 중:</span>
                            <span id="disk-used">-</span>
                        </div>
                        <div class="detail-item">
                            <span>여유 공간:</span>
                            <span id="disk-free">-</span>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    /**
     * 네트워크 섹션 렌더링
     */
    renderNetworkSection() {
        return `
            <div class="monitor-section network-section">
                <div class="section-header">
                    <span class="section-title">네트워크</span>
                    <span class="section-value">
                        <i class="bi bi-arrow-down"></i> <span id="network-in">0 KB/s</span>
                        <i class="bi bi-arrow-up"></i> <span id="network-out">0 KB/s</span>
                    </span>
                </div>
                ${!this.options.compact ? `
                    <div class="chart-container">
                        <canvas id="network-chart" height="80"></canvas>
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    /**
     * 서비스 섹션 렌더링
     */
    renderServicesSection() {
        return `
            <div class="monitor-section services-section">
                <div class="section-header">
                    <span class="section-title">서비스 상태</span>
                </div>
                <div class="services-grid" id="services-grid">
                    <div class="service-item">
                        <span class="service-indicator" data-service="app"></span>
                        <span class="service-name">애플리케이션</span>
                    </div>
                    <div class="service-item">
                        <span class="service-indicator" data-service="redis"></span>
                        <span class="service-name">Redis</span>
                    </div>
                    <div class="service-item">
                        <span class="service-indicator" data-service="collection"></span>
                        <span class="service-name">수집 서비스</span>
                    </div>
                    <div class="service-item">
                        <span class="service-indicator" data-service="database"></span>
                        <span class="service-name">데이터베이스</span>
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * 차트 설정
     */
    setupCharts() {
        // CPU 차트
        if (this.options.showCPU) {
            this.setupCPUChart();
        }
        
        // 메모리 차트
        if (this.options.showMemory) {
            this.setupMemoryChart();
        }
        
        // 네트워크 차트
        if (this.options.showNetwork && !this.options.compact) {
            this.setupNetworkChart();
        }
    }
    
    /**
     * CPU 차트 설정
     */
    setupCPUChart() {
        const ctx = document.getElementById('cpu-chart');
        if (!ctx) return;
        
        this.charts.cpu = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array(this.maxDataPoints).fill(''),
                datasets: [{
                    label: 'CPU %',
                    data: Array(this.maxDataPoints).fill(0),
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        display: false
                    },
                    y: {
                        display: !this.options.compact,
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: value => value + '%'
                        }
                    }
                },
                elements: {
                    point: {
                        radius: 0
                    }
                }
            }
        });
    }
    
    /**
     * 메모리 차트 설정
     */
    setupMemoryChart() {
        const ctx = document.getElementById('memory-chart');
        if (!ctx) return;
        
        this.charts.memory = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array(this.maxDataPoints).fill(''),
                datasets: [{
                    label: '메모리 %',
                    data: Array(this.maxDataPoints).fill(0),
                    borderColor: '#198754',
                    backgroundColor: 'rgba(25, 135, 84, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        display: false
                    },
                    y: {
                        display: !this.options.compact,
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: value => value + '%'
                        }
                    }
                },
                elements: {
                    point: {
                        radius: 0
                    }
                }
            }
        });
    }
    
    /**
     * 네트워크 차트 설정
     */
    setupNetworkChart() {
        const ctx = document.getElementById('network-chart');
        if (!ctx) return;
        
        this.charts.network = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array(this.maxDataPoints).fill(''),
                datasets: [{
                    label: '수신',
                    data: Array(this.maxDataPoints).fill(0),
                    borderColor: '#0dcaf0',
                    backgroundColor: 'rgba(13, 202, 240, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: false
                }, {
                    label: '송신',
                    data: Array(this.maxDataPoints).fill(0),
                    borderColor: '#ffc107',
                    backgroundColor: 'rgba(255, 193, 7, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom',
                        labels: {
                            boxWidth: 12,
                            padding: 10
                        }
                    }
                },
                scales: {
                    x: {
                        display: false
                    },
                    y: {
                        display: true,
                        beginAtZero: true,
                        ticks: {
                            callback: value => this.formatBytes(value) + '/s'
                        }
                    }
                },
                elements: {
                    point: {
                        radius: 0
                    }
                }
            }
        });
    }
    
    /**
     * 모니터링 시작
     */
    startMonitoring() {
        if (this.isActive) return;
        
        this.isActive = true;
        this.updateSystemStatus();
        
        this.updateInterval = setInterval(() => {
            this.updateSystemStatus();
        }, this.options.updateInterval);
    }
    
    /**
     * 모니터링 중지
     */
    stopMonitoring() {
        this.isActive = false;
        
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
    
    /**
     * 시스템 상태 업데이트
     */
    async updateSystemStatus() {
        try {
            const response = await fetch('/api/monitoring/system');
            if (!response.ok) throw new Error('Failed to fetch system status');
            
            const data = await response.json();
            
            // 각 섹션 업데이트
            if (this.options.showCPU) this.updateCPU(data.cpu);
            if (this.options.showMemory) this.updateMemory(data.memory);
            if (this.options.showDisk) this.updateDisk(data.disk);
            if (this.options.showNetwork) this.updateNetwork(data.network);
            if (this.options.showServices) this.updateServices(data.services);
            
            // 마지막 업데이트 시간
            this.updateLastUpdateTime();
            
        } catch (error) {
            console.error('System monitoring error:', error);
            this.handleError();
        }
    }
    
    /**
     * CPU 정보 업데이트
     */
    updateCPU(cpuData) {
        if (!cpuData) return;
        
        // 값 업데이트
        const cpuValue = document.getElementById('cpu-value');
        if (cpuValue) cpuValue.textContent = `${cpuData.usage}%`;
        
        // 상세 정보
        if (!this.options.compact) {
            const cpuCores = document.getElementById('cpu-cores');
            if (cpuCores) cpuCores.textContent = cpuData.cores || '-';
            
            const cpuLoad = document.getElementById('cpu-load');
            if (cpuLoad) cpuLoad.textContent = cpuData.loadAverage?.join(', ') || '-';
        }
        
        // 차트 업데이트
        if (this.charts.cpu) {
            this.data.cpu.push(cpuData.usage);
            if (this.data.cpu.length > this.maxDataPoints) {
                this.data.cpu.shift();
            }
            
            this.charts.cpu.data.datasets[0].data = this.data.cpu;
            this.charts.cpu.update('none');
        }
    }
    
    /**
     * 메모리 정보 업데이트
     */
    updateMemory(memoryData) {
        if (!memoryData) return;
        
        // 값 업데이트
        const memoryValue = document.getElementById('memory-value');
        if (memoryValue) memoryValue.textContent = `${memoryData.usagePercent}%`;
        
        // 상세 정보
        if (!this.options.compact) {
            const memoryUsed = document.getElementById('memory-used');
            if (memoryUsed) memoryUsed.textContent = this.formatBytes(memoryData.used);
            
            const memoryTotal = document.getElementById('memory-total');
            if (memoryTotal) memoryTotal.textContent = this.formatBytes(memoryData.total);
        }
        
        // 차트 업데이트
        if (this.charts.memory) {
            this.data.memory.push(memoryData.usagePercent);
            if (this.data.memory.length > this.maxDataPoints) {
                this.data.memory.shift();
            }
            
            this.charts.memory.data.datasets[0].data = this.data.memory;
            this.charts.memory.update('none');
        }
    }
    
    /**
     * 디스크 정보 업데이트
     */
    updateDisk(diskData) {
        if (!diskData) return;
        
        // 값 업데이트
        const diskValue = document.getElementById('disk-value');
        if (diskValue) diskValue.textContent = `${diskData.usagePercent}%`;
        
        // 프로그레스 바
        const diskProgress = document.getElementById('disk-progress');
        if (diskProgress) {
            diskProgress.style.width = `${diskData.usagePercent}%`;
            
            // 색상 변경 (사용률에 따라)
            if (diskData.usagePercent > 90) {
                diskProgress.className = 'progress-bar bg-danger';
            } else if (diskData.usagePercent > 70) {
                diskProgress.className = 'progress-bar bg-warning';
            } else {
                diskProgress.className = 'progress-bar bg-success';
            }
        }
        
        // 상세 정보
        if (!this.options.compact) {
            const diskUsed = document.getElementById('disk-used');
            if (diskUsed) diskUsed.textContent = this.formatBytes(diskData.used);
            
            const diskFree = document.getElementById('disk-free');
            if (diskFree) diskFree.textContent = this.formatBytes(diskData.free);
        }
    }
    
    /**
     * 네트워크 정보 업데이트
     */
    updateNetwork(networkData) {
        if (!networkData) return;
        
        // 값 업데이트
        const networkIn = document.getElementById('network-in');
        if (networkIn) networkIn.textContent = this.formatBytes(networkData.bytesRecv) + '/s';
        
        const networkOut = document.getElementById('network-out');
        if (networkOut) networkOut.textContent = this.formatBytes(networkData.bytesSent) + '/s';
        
        // 차트 업데이트
        if (this.charts.network) {
            this.data.network.in.push(networkData.bytesRecv);
            this.data.network.out.push(networkData.bytesSent);
            
            if (this.data.network.in.length > this.maxDataPoints) {
                this.data.network.in.shift();
                this.data.network.out.shift();
            }
            
            this.charts.network.data.datasets[0].data = this.data.network.in;
            this.charts.network.data.datasets[1].data = this.data.network.out;
            this.charts.network.update('none');
        }
    }
    
    /**
     * 서비스 상태 업데이트
     */
    updateServices(servicesData) {
        if (!servicesData) return;
        
        Object.entries(servicesData).forEach(([service, status]) => {
            const indicator = document.querySelector(`[data-service="${service}"]`);
            if (indicator) {
                indicator.className = `service-indicator ${status ? 'active' : 'inactive'}`;
                indicator.title = status ? '정상' : '오류';
            }
        });
    }
    
    /**
     * 에러 처리
     */
    handleError() {
        // 서비스 상태를 모두 오류로 표시
        document.querySelectorAll('.service-indicator').forEach(indicator => {
            indicator.className = 'service-indicator error';
        });
    }
    
    /**
     * 마지막 업데이트 시간 표시
     */
    updateLastUpdateTime() {
        const element = document.getElementById('system-monitor-last-update');
        if (element) {
            element.textContent = new Date().toLocaleTimeString('ko-KR');
        }
    }
    
    /**
     * 바이트 포맷팅
     */
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    /**
     * 컴팩트 모드 토글
     */
    toggleCompact() {
        this.options.compact = !this.options.compact;
        this.destroy();
        this.init();
    }
    
    /**
     * 새로고침
     */
    refresh() {
        this.updateSystemStatus();
    }
    
    /**
     * 스타일 추가
     */
    addStyles() {
        if (document.getElementById('system-monitor-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'system-monitor-styles';
        style.textContent = `
            .system-monitor-widget {
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                padding: 20px;
            }
            
            .system-monitor-widget.compact {
                padding: 15px;
            }
            
            .widget-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }
            
            .widget-title {
                margin: 0;
                font-size: 18px;
                color: #333;
            }
            
            .widget-controls {
                display: flex;
                gap: 5px;
            }
            
            .widget-controls button {
                padding: 4px 8px;
                color: #666;
            }
            
            .widget-body {
                display: flex;
                flex-direction: column;
                gap: 20px;
            }
            
            .monitor-section {
                border-bottom: 1px solid #eee;
                padding-bottom: 15px;
            }
            
            .monitor-section:last-child {
                border-bottom: none;
                padding-bottom: 0;
            }
            
            .section-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }
            
            .section-title {
                font-weight: 600;
                color: #555;
            }
            
            .section-value {
                font-weight: 600;
                color: #333;
                font-size: 18px;
            }
            
            .chart-container {
                position: relative;
                height: 80px;
            }
            
            .compact .chart-container {
                height: 50px;
            }
            
            .progress-container {
                margin: 10px 0;
            }
            
            .section-details {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                margin-top: 10px;
                font-size: 14px;
            }
            
            .detail-item {
                display: flex;
                justify-content: space-between;
                color: #666;
            }
            
            .services-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 10px;
                margin-top: 10px;
            }
            
            .service-item {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .service-indicator {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: #ccc;
                transition: background 0.3s;
            }
            
            .service-indicator.active {
                background: #198754;
            }
            
            .service-indicator.inactive {
                background: #dc3545;
            }
            
            .service-indicator.error {
                background: #6c757d;
            }
            
            .service-name {
                font-size: 14px;
                color: #666;
            }
            
            .widget-footer {
                margin-top: 15px;
                padding-top: 15px;
                border-top: 1px solid #eee;
                text-align: center;
            }
            
            /* 다크 테마 */
            .system-monitor-widget.theme-dark {
                background: #2b2b2b;
                color: #fff;
            }
            
            .theme-dark .widget-title,
            .theme-dark .section-value {
                color: #fff;
            }
            
            .theme-dark .section-title,
            .theme-dark .detail-item,
            .theme-dark .service-name {
                color: #ccc;
            }
            
            .theme-dark .monitor-section {
                border-color: #444;
            }
            
            .theme-dark .widget-footer {
                border-color: #444;
            }
        `;
        
        document.head.appendChild(style);
    }
    
    /**
     * 위젯 정리
     */
    destroy() {
        this.stopMonitoring();
        
        // 차트 정리
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        
        this.charts = {};
        this.data = {
            cpu: [],
            memory: [],
            disk: [],
            network: { in: [], out: [] }
        };
        
        // 컨테이너 비우기
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// 전역 인스턴스 생성 함수
function createSystemMonitor(containerId, options) {
    return new SystemMonitorWidget(containerId, options);
}

// 전역 등록
window.SystemMonitorWidget = SystemMonitorWidget;
window.createSystemMonitor = createSystemMonitor;