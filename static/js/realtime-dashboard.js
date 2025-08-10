/**
 * 실시간 대시보드 JavaScript 모듈
 * Real-time Dashboard Module for Blacklist Management System
 */

class RealtimeDashboard {
  constructor(options = {}) {
    this.options = {
      updateInterval: options.updateInterval || 5000,
      apiBase: options.apiBase || "/api",
      enableNotifications: options.enableNotifications !== false,
      ...options,
    };

    this.isActive = false;
    this.charts = {};
    this.lastUpdateTime = null;
    this.updateIntervals = new Map();

    this.init();
  }

  /**
   * 대시보드 초기화
   */
  init() {
    this.setupEventListeners();
    this.initializeCharts();
    this.startRealtimeUpdates();

    console.log("실시간 대시보드 초기화 완료");
  }

  /**
   * 이벤트 리스너 설정
   */
  setupEventListeners() {
    // 페이지 가시성 변경 감지
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) {
        this.pauseUpdates();
      } else {
        this.resumeUpdates();
      }
    });

    // 윈도우 포커스 이벤트
    window.addEventListener("focus", () => this.resumeUpdates());
    window.addEventListener("blur", () => this.pauseUpdates());

    // 연결 상태 변경 감지
    window.addEventListener("online", () => {
      this.showNotification("네트워크 연결이 복구되었습니다.", "success");
      this.resumeUpdates();
    });

    window.addEventListener("offline", () => {
      this.showNotification("네트워크 연결이 끊어졌습니다.", "warning");
      this.pauseUpdates();
    });
  }

  /**
   * 차트 초기화
   */
  initializeCharts() {
    // 기존 Chart.js 인스턴스들을 실시간 업데이트 가능하도록 설정
    if (typeof Chart !== "undefined") {
      this.charts.monthly = this.findChartByCanvasId("monthlyChart");
      this.charts.source = this.findChartByCanvasId("sourceChart");
    }
  }

  /**
   * Canvas ID로 Chart.js 인스턴스 찾기
   */
  findChartByCanvasId(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (canvas && Chart.getChart) {
      return Chart.getChart(canvas);
    }
    return null;
  }

  /**
   * 실시간 업데이트 시작
   */
  startRealtimeUpdates() {
    if (this.isActive) return;

    this.isActive = true;

    // 통계 업데이트 (5초마다)
    this.updateIntervals.set(
      "stats",
      setInterval(() => {
        this.updateStats();
      }, this.options.updateInterval),
    );

    // 시스템 모니터링 업데이트 (10초마다)
    this.updateIntervals.set(
      "monitoring",
      setInterval(() => {
        this.updateSystemMonitoring();
      }, this.options.updateInterval * 2),
    );

    // 수집 상태 업데이트 (15초마다)
    this.updateIntervals.set(
      "collection",
      setInterval(() => {
        this.updateCollectionStatus();
      }, this.options.updateInterval * 3),
    );

    // 차트 데이터 업데이트 (30초마다)
    this.updateIntervals.set(
      "charts",
      setInterval(() => {
        this.updateCharts();
      }, this.options.updateInterval * 6),
    );

    console.log("실시간 업데이트 시작");
  }

  /**
   * 실시간 업데이트 중지
   */
  stopRealtimeUpdates() {
    this.isActive = false;

    this.updateIntervals.forEach((interval, key) => {
      clearInterval(interval);
    });
    this.updateIntervals.clear();

    console.log("실시간 업데이트 중지");
  }

  /**
   * 업데이트 일시 중지
   */
  pauseUpdates() {
    if (!this.isActive) return;

    this.updateIntervals.forEach((interval) => {
      clearInterval(interval);
    });
    this.updateIntervals.clear();

    console.log("실시간 업데이트 일시 중지");
  }

  /**
   * 업데이트 재개
   */
  resumeUpdates() {
    if (!this.isActive) return;

    this.startRealtimeUpdates();
    console.log("실시간 업데이트 재개");
  }

  /**
   * 통계 데이터 업데이트
   */
  async updateStats() {
    try {
      const response = await fetch(`${this.options.apiBase}/realtime/stats`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();

      if (data.current_stats) {
        this.updateStatCards(data.current_stats);
      }

      if (data.recent_activity) {
        this.updateActivityFeed(data.recent_activity);
      }

      this.lastUpdateTime = new Date();
      this.updateLastUpdateDisplay();
    } catch (error) {
      console.warn("통계 업데이트 실패:", error);
      this.handleError("통계 데이터 업데이트에 실패했습니다.");
    }
  }

  /**
   * 통계 카드 업데이트
   */
  updateStatCards(stats) {
    // 전체 IP 수 업데이트
    const totalElement = document.querySelector(".stat-card.primary h2");
    if (totalElement && stats.total_ips !== undefined) {
      this.animateNumber(totalElement, stats.total_ips);
    }

    // 활성 IP 수 업데이트
    const activeElement = document.querySelector(".stat-card.success h2");
    if (activeElement && stats.active_ips !== undefined) {
      this.animateNumber(activeElement, stats.active_ips);
    }

    // 시스템 상태 업데이트
    const statusElement = document.querySelector(".stat-card.info h2");
    if (statusElement && stats.system_status) {
      statusElement.textContent = stats.system_status;
    }

    // 데이터 소스 수 업데이트
    const sourceElement = document.querySelector(".stat-card.warning h2");
    if (sourceElement && stats.active_sources !== undefined) {
      sourceElement.textContent = `${stats.active_sources}개`;
    }
  }

  /**
   * 숫자 애니메이션
   */
  animateNumber(element, targetValue) {
    const currentValue =
      parseInt(element.textContent.replace(/[^0-9]/g, "")) || 0;
    const duration = 1000;
    const steps = 30;
    const increment = (targetValue - currentValue) / steps;

    let step = 0;
    const timer = setInterval(() => {
      step++;
      const value = Math.round(currentValue + increment * step);
      element.textContent = this.formatNumber(value);

      if (step >= steps) {
        clearInterval(timer);
        element.textContent = this.formatNumber(targetValue);
      }
    }, duration / steps);
  }

  /**
   * 숫자 포맷팅
   */
  formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  /**
   * 시스템 모니터링 업데이트
   */
  async updateSystemMonitoring() {
    try {
      const response = await fetch(`${this.options.apiBase}/monitoring/system`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();

      if (data.system) {
        this.updateSystemMetrics(data.system);
      }
    } catch (error) {
      console.warn("시스템 모니터링 업데이트 실패:", error);
    }
  }

  /**
   * 시스템 메트릭 업데이트
   */
  updateSystemMetrics(systemData) {
    // CPU 사용률
    if (systemData.cpu_percent !== undefined) {
      this.updateProgressBar("cpu", systemData.cpu_percent);
    }

    // 메모리 사용률
    if (systemData.memory_percent !== undefined) {
      this.updateProgressBar("memory", systemData.memory_percent);
    }

    // 디스크 사용률
    if (systemData.disk_percent !== undefined) {
      this.updateProgressBar("disk", systemData.disk_percent);
    }
  }

  /**
   * 프로그레스 바 업데이트
   */
  updateProgressBar(type, percentage) {
    const progressBar = document.querySelector(
      `.progress-bar.bg-${this.getProgressBarClass(type)}`,
    );
    const percentageElement =
      progressBar?.parentElement?.previousElementSibling?.lastElementChild;

    if (progressBar) {
      // 애니메이션과 함께 업데이트
      progressBar.style.transition = "width 0.5s ease";
      progressBar.style.width = `${percentage}%`;
    }

    if (percentageElement) {
      percentageElement.textContent = `${Math.round(percentage)}%`;
    }
  }

  /**
   * 프로그레스 바 클래스 매핑
   */
  getProgressBarClass(type) {
    const classMap = {
      cpu: "success",
      memory: "info",
      disk: "warning",
    };
    return classMap[type] || "primary";
  }

  /**
   * 수집 상태 업데이트
   */
  async updateCollectionStatus() {
    try {
      const response = await fetch(
        `${this.options.apiBase}/realtime/collection-status`,
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();

      if (data.collections) {
        this.updateCollectionInfo(data.collections);
      }
    } catch (error) {
      console.warn("수집 상태 업데이트 실패:", error);
    }
  }

  /**
   * 수집 정보 업데이트
   */
  updateCollectionInfo(collections) {
    // 데이터 소스 정보 업데이트 로직
    collections.forEach((collection) => {
      console.log(
        `${collection.name}: ${collection.status} (${collection.progress}%)`,
      );
    });
  }

  /**
   * 차트 데이터 업데이트
   */
  async updateCharts() {
    try {
      // 월별 트렌드 차트 업데이트
      await this.updateMonthlyChart();

      // 소스 분포 차트 업데이트
      await this.updateSourceChart();
    } catch (error) {
      console.warn("차트 업데이트 실패:", error);
    }
  }

  /**
   * 월별 차트 업데이트
   */
  async updateMonthlyChart() {
    if (!this.charts.monthly) return;

    try {
      const response = await fetch(
        `${this.options.apiBase}/stats/detection-trends?days=90`,
      );
      if (!response.ok) return;

      const data = await response.json();

      if (data.daily_trends) {
        const labels = data.daily_trends.map((d) => d.date);
        const values = data.daily_trends.map((d) => d.new_detections);

        this.charts.monthly.data.labels = labels;
        this.charts.monthly.data.datasets[0].data = values;
        this.charts.monthly.update("none");
      }
    } catch (error) {
      console.warn("월별 차트 업데이트 실패:", error);
    }
  }

  /**
   * 소스 분포 차트 업데이트
   */
  async updateSourceChart() {
    if (!this.charts.source) return;

    try {
      const response = await fetch(`${this.options.apiBase}/v2/sources/status`);
      if (!response.ok) return;

      const data = await response.json();

      if (data.sources) {
        const values = data.sources.map((s) => s.records_count);
        this.charts.source.data.datasets[0].data = values;
        this.charts.source.update("none");
      }
    } catch (error) {
      console.warn("소스 차트 업데이트 실패:", error);
    }
  }

  /**
   * 활동 피드 업데이트
   */
  updateActivityFeed(activities) {
    let feedArea = document.getElementById("realtime-activity");

    if (!feedArea) {
      feedArea = this.createActivityFeed();
    }

    if (!feedArea) return;

    activities.slice(0, 5).forEach((activity) => {
      const eventElement = document.createElement("div");
      eventElement.className = "activity-item mb-2 fade-in";
      eventElement.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <small class="text-muted">${this.formatTime(activity.time)}</small>
                    <span class="badge bg-${this.getActivityBadgeClass(activity.action)} ms-2">
                        ${activity.action}
                    </span>
                </div>
                <div class="mt-1">
                    <small>${activity.count}개 IP 처리됨</small>
                </div>
            `;

      feedArea.insertBefore(eventElement, feedArea.firstChild);
    });

    // 최대 10개 항목만 유지
    while (feedArea.children.length > 10) {
      feedArea.removeChild(feedArea.lastChild);
    }
  }

  /**
   * 활동 피드 생성
   */
  createActivityFeed() {
    const systemCard = document.querySelector(
      ".col-lg-6:last-child .modern-card .card-body",
    );
    if (!systemCard) return null;

    const feedDiv = document.createElement("div");
    feedDiv.innerHTML = `
            <hr class="my-4">
            <h6 class="mb-3">
                <i class="bi bi-activity text-info"></i> 실시간 활동
            </h6>
            <div id="realtime-activity" class="border rounded p-3" 
                 style="height: 200px; overflow-y: auto; background: rgba(248, 249, 250, 0.5);">
                <div class="text-center text-muted">
                    <small>실시간 데이터를 로드 중...</small>
                </div>
            </div>
        `;

    systemCard.appendChild(feedDiv);
    return document.getElementById("realtime-activity");
  }

  /**
   * 활동 배지 클래스 결정
   */
  getActivityBadgeClass(action) {
    const classMap = {
      ip_added: "success",
      ip_removed: "warning",
      collection_started: "info",
      collection_completed: "primary",
    };
    return classMap[action] || "secondary";
  }

  /**
   * 시간 포맷팅
   */
  formatTime(timeString) {
    const date = new Date(timeString);
    return date.toLocaleTimeString("ko-KR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  /**
   * 마지막 업데이트 시간 표시
   */
  updateLastUpdateDisplay() {
    const updateElement = document.querySelector(".dashboard-header small");
    if (updateElement && this.lastUpdateTime) {
      updateElement.textContent = this.lastUpdateTime.toLocaleString("ko-KR");
    }
  }

  /**
   * 에러 처리
   */
  handleError(message) {
    if (this.options.enableNotifications) {
      this.showNotification(message, "danger");
    }
    console.error("RealtimeDashboard Error:", message);
  }

  /**
   * 알림 표시
   */
  showNotification(message, type = "info") {
    if (typeof showNotification === "function") {
      showNotification(message, type);
    } else {
      console.log(`[${type}] ${message}`);
    }
  }

  /**
   * 대시보드 정리
   */
  destroy() {
    this.stopRealtimeUpdates();
    console.log("실시간 대시보드 정리 완료");
  }
}

// 전역 인스턴스
let realtimeDashboard = null;

/**
 * 대시보드 초기화 함수
 */
function initializeRealtimeDashboard(options = {}) {
  if (realtimeDashboard) {
    realtimeDashboard.destroy();
  }

  realtimeDashboard = new RealtimeDashboard(options);
  return realtimeDashboard;
}

/**
 * 페이지 로드 시 자동 초기화
 */
document.addEventListener("DOMContentLoaded", function () {
  // 대시보드 페이지에서만 초기화
  if (
    window.location.pathname === "/" ||
    window.location.pathname === "/dashboard"
  ) {
    initializeRealtimeDashboard();
  }
});

// 모듈 export (필요한 경우)
if (typeof module !== "undefined" && module.exports) {
  module.exports = { RealtimeDashboard, initializeRealtimeDashboard };
}
