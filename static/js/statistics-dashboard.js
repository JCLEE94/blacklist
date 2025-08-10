/**
 * 통계 대시보드 JavaScript 모듈
 * Statistics Dashboard Module for Blacklist Management System
 */

class StatisticsDashboard {
  constructor(options = {}) {
    this.options = {
      chartColors: {
        primary: "#0d6efd",
        success: "#198754",
        warning: "#ffc107",
        danger: "#dc3545",
        info: "#0dcaf0",
        secondary: "#6c757d",
      },
      updateInterval: options.updateInterval || 30000, // 30 seconds
      ...options,
    };

    this.charts = {};
    this.filters = {
      dateRange: "30d",
      source: "all",
      ipType: "all",
    };

    this.init();
  }

  /**
   * 대시보드 초기화
   */
  init() {
    this.setupFilterControls();
    this.initializeCharts();
    this.loadInitialData();
    this.startAutoUpdate();
  }

  /**
   * 필터 컨트롤 설정
   */
  setupFilterControls() {
    // 날짜 범위 선택
    const dateRangeSelect = document.getElementById("dateRangeFilter");
    if (dateRangeSelect) {
      dateRangeSelect.addEventListener("change", (e) => {
        this.filters.dateRange = e.target.value;
        this.refreshAllCharts();
      });
    }

    // 소스 필터
    const sourceFilter = document.getElementById("sourceFilter");
    if (sourceFilter) {
      sourceFilter.addEventListener("change", (e) => {
        this.filters.source = e.target.value;
        this.refreshAllCharts();
      });
    }

    // IP 타입 필터
    const ipTypeFilter = document.getElementById("ipTypeFilter");
    if (ipTypeFilter) {
      ipTypeFilter.addEventListener("change", (e) => {
        this.filters.ipType = e.target.value;
        this.refreshAllCharts();
      });
    }

    // 내보내기 버튼
    const exportButton = document.getElementById("exportStats");
    if (exportButton) {
      exportButton.addEventListener("click", () => this.exportStatistics());
    }
  }

  /**
   * 차트 초기화
   */
  initializeCharts() {
    // 탐지 트렌드 차트
    this.initDetectionTrendChart();

    // 소스별 분포 차트
    this.initSourceDistributionChart();

    // IP 유형별 분포 차트
    this.initIPTypeChart();

    // 지리적 분포 차트
    this.initGeographicChart();

    // 시간대별 활동 차트
    this.initHourlyActivityChart();

    // 위협 레벨 차트
    this.initThreatLevelChart();
  }

  /**
   * 탐지 트렌드 차트 초기화
   */
  initDetectionTrendChart() {
    const canvas = document.getElementById("detectionTrendChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    this.charts.detectionTrend = new Chart(ctx, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          {
            label: "신규 탐지",
            data: [],
            borderColor: this.options.chartColors.primary,
            backgroundColor: this.hexToRgba(
              this.options.chartColors.primary,
              0.1,
            ),
            borderWidth: 2,
            fill: true,
            tension: 0.4,
          },
          {
            label: "제거됨",
            data: [],
            borderColor: this.options.chartColors.danger,
            backgroundColor: this.hexToRgba(
              this.options.chartColors.danger,
              0.1,
            ),
            borderWidth: 2,
            fill: true,
            tension: 0.4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "index",
          intersect: false,
        },
        plugins: {
          legend: {
            position: "top",
          },
          tooltip: {
            callbacks: {
              title: (tooltipItems) => {
                return `날짜: ${tooltipItems[0].label}`;
              },
            },
          },
        },
        scales: {
          x: {
            grid: {
              display: false,
            },
          },
          y: {
            beginAtZero: true,
            ticks: {
              callback: (value) => value.toLocaleString(),
            },
          },
        },
      },
    });
  }

  /**
   * 소스별 분포 차트 초기화
   */
  initSourceDistributionChart() {
    const canvas = document.getElementById("sourceDistributionChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    this.charts.sourceDistribution = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: [],
        datasets: [
          {
            data: [],
            backgroundColor: [
              this.options.chartColors.primary,
              this.options.chartColors.success,
              this.options.chartColors.warning,
              this.options.chartColors.info,
            ],
            borderWidth: 2,
            borderColor: "#fff",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              padding: 15,
            },
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                const label = context.label || "";
                const value = context.parsed || 0;
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((value / total) * 100).toFixed(1);
                return `${label}: ${value.toLocaleString()} (${percentage}%)`;
              },
            },
          },
        },
      },
    });
  }

  /**
   * IP 유형별 차트 초기화
   */
  initIPTypeChart() {
    const canvas = document.getElementById("ipTypeChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    this.charts.ipType = new Chart(ctx, {
      type: "bar",
      data: {
        labels: ["IPv4", "IPv6", "CIDR"],
        datasets: [
          {
            label: "IP 수",
            data: [],
            backgroundColor: [
              this.options.chartColors.primary,
              this.options.chartColors.success,
              this.options.chartColors.warning,
            ],
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
        },
        scales: {
          x: {
            grid: {
              display: false,
            },
          },
          y: {
            beginAtZero: true,
            ticks: {
              callback: (value) => value.toLocaleString(),
            },
          },
        },
      },
    });
  }

  /**
   * 지리적 분포 차트 초기화
   */
  initGeographicChart() {
    const canvas = document.getElementById("geographicChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    this.charts.geographic = new Chart(ctx, {
      type: "bar",
      data: {
        labels: [],
        datasets: [
          {
            label: "국가별 IP 수",
            data: [],
            backgroundColor: this.options.chartColors.info,
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: "y",
        plugins: {
          legend: {
            display: false,
          },
        },
        scales: {
          x: {
            beginAtZero: true,
            ticks: {
              callback: (value) => value.toLocaleString(),
            },
          },
          y: {
            grid: {
              display: false,
            },
          },
        },
      },
    });
  }

  /**
   * 시간대별 활동 차트 초기화
   */
  initHourlyActivityChart() {
    const canvas = document.getElementById("hourlyActivityChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    this.charts.hourlyActivity = new Chart(ctx, {
      type: "radar",
      data: {
        labels: Array.from({ length: 24 }, (_, i) => `${i}시`),
        datasets: [
          {
            label: "탐지 활동",
            data: Array(24).fill(0),
            borderColor: this.options.chartColors.primary,
            backgroundColor: this.hexToRgba(
              this.options.chartColors.primary,
              0.2,
            ),
            borderWidth: 2,
            pointBackgroundColor: this.options.chartColors.primary,
            pointBorderColor: "#fff",
            pointHoverBackgroundColor: "#fff",
            pointHoverBorderColor: this.options.chartColors.primary,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
        },
        scales: {
          r: {
            beginAtZero: true,
            ticks: {
              display: false,
            },
          },
        },
      },
    });
  }

  /**
   * 위협 레벨 차트 초기화
   */
  initThreatLevelChart() {
    const canvas = document.getElementById("threatLevelChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    this.charts.threatLevel = new Chart(ctx, {
      type: "polarArea",
      data: {
        labels: ["낮음", "보통", "높음", "매우 높음"],
        datasets: [
          {
            data: [],
            backgroundColor: [
              this.hexToRgba(this.options.chartColors.success, 0.8),
              this.hexToRgba(this.options.chartColors.warning, 0.8),
              this.hexToRgba(this.options.chartColors.danger, 0.8),
              this.hexToRgba("#8b0000", 0.8),
            ],
            borderWidth: 2,
            borderColor: "#fff",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "right",
          },
        },
      },
    });
  }

  /**
   * 초기 데이터 로드
   */
  async loadInitialData() {
    await this.refreshAllCharts();
    await this.loadSummaryStats();
  }

  /**
   * 모든 차트 새로고침
   */
  async refreshAllCharts() {
    try {
      // 로딩 표시
      this.showLoading(true);

      // 각 차트 데이터 로드
      await Promise.all([
        this.updateDetectionTrend(),
        this.updateSourceDistribution(),
        this.updateIPTypeDistribution(),
        this.updateGeographicDistribution(),
        this.updateHourlyActivity(),
        this.updateThreatLevels(),
      ]);

      // 마지막 업데이트 시간 표시
      this.updateLastRefreshTime();
    } catch (error) {
      console.error("차트 새로고침 실패:", error);
      this.showError("데이터를 불러오는 중 오류가 발생했습니다.");
    } finally {
      this.showLoading(false);
    }
  }

  /**
   * 요약 통계 로드
   */
  async loadSummaryStats() {
    try {
      const response = await fetch(
        "/api/v2/analytics/summary-data?" + this.buildQueryString(),
      );
      const data = await response.json();

      if (data.summary) {
        this.updateSummaryCards(data.summary);
      }
    } catch (error) {
      console.error("요약 통계 로드 실패:", error);
    }
  }

  /**
   * 요약 카드 업데이트
   */
  updateSummaryCards(summary) {
    // 총 위협 수
    const totalThreats = document.getElementById("totalThreats");
    if (totalThreats) {
      this.animateValue(totalThreats, summary.total_threats || 0);
    }

    // 활성 위협
    const activeThreats = document.getElementById("activeThreats");
    if (activeThreats) {
      this.animateValue(activeThreats, summary.active_threats || 0);
    }

    // 차단률
    const blockRate = document.getElementById("blockRate");
    if (blockRate) {
      blockRate.textContent = `${(summary.block_rate || 0).toFixed(1)}%`;
    }

    // 평균 대응 시간
    const avgResponseTime = document.getElementById("avgResponseTime");
    if (avgResponseTime) {
      avgResponseTime.textContent = `${summary.avg_response_time || 0}분`;
    }
  }

  /**
   * 탐지 트렌드 업데이트
   */
  async updateDetectionTrend() {
    try {
      const response = await fetch(
        `/api/v2/analytics/detection-trend?${this.buildQueryString()}`,
      );
      const data = await response.json();

      if (data.trend && this.charts.detectionTrend) {
        const labels = data.trend.map((d) => this.formatDate(d.date));
        const newDetections = data.trend.map((d) => d.count || 0);
        const removed = data.trend.map((d) => 0); // V2 API doesn't have removed data

        this.charts.detectionTrend.data.labels = labels;
        this.charts.detectionTrend.data.datasets[0].data = newDetections;
        this.charts.detectionTrend.data.datasets[1].data = removed;
        this.charts.detectionTrend.update();
      }
    } catch (error) {
      console.error("탐지 트렌드 업데이트 실패:", error);
    }
  }

  /**
   * 소스별 분포 업데이트
   */
  async updateSourceDistribution() {
    try {
      const response = await fetch(
        `/api/v2/sources/distribution?${this.buildQueryString()}`,
      );
      const data = await response.json();

      if (data.sources && this.charts.sourceDistribution) {
        const labels = data.sources.map((s) => s.name);
        const values = data.sources.map((s) => s.count);

        this.charts.sourceDistribution.data.labels = labels;
        this.charts.sourceDistribution.data.datasets[0].data = values;
        this.charts.sourceDistribution.update();
      }
    } catch (error) {
      console.error("소스 분포 업데이트 실패:", error);
    }
  }

  /**
   * IP 유형 분포 업데이트
   */
  async updateIPTypeDistribution() {
    try {
      const response = await fetch(
        `/api/v2/analytics/ip-types?${this.buildQueryString()}`,
      );
      const data = await response.json();

      if (data.ip_types && this.charts.ipType) {
        const values = [
          data.ip_types.ipv4 || 0,
          data.ip_types.ipv6 || 0,
          data.ip_types.cidr || 0,
        ];

        this.charts.ipType.data.datasets[0].data = values;
        this.charts.ipType.update();
      }
    } catch (error) {
      console.error("IP 유형 분포 업데이트 실패:", error);
    }
  }

  /**
   * 지리적 분포 업데이트
   */
  async updateGeographicDistribution() {
    try {
      const response = await fetch(
        `/api/v2/analytics/geographic?${this.buildQueryString()}`,
      );
      const data = await response.json();

      if (data.countries && this.charts.geographic) {
        // 상위 10개 국가만 표시
        const topCountries = data.countries.slice(0, 10);
        const labels = topCountries.map((c) => c.country);
        const values = topCountries.map((c) => c.count);

        this.charts.geographic.data.labels = labels;
        this.charts.geographic.data.datasets[0].data = values;
        this.charts.geographic.update();
      }
    } catch (error) {
      console.error("지리적 분포 업데이트 실패:", error);
    }
  }

  /**
   * 시간대별 활동 업데이트
   */
  async updateHourlyActivity() {
    try {
      const response = await fetch(
        `/api/v2/analytics/hourly-activity?${this.buildQueryString()}`,
      );
      const data = await response.json();

      if (data.hourly_activity && this.charts.hourlyActivity) {
        const hourlyData = Array(24).fill(0);
        data.hourly_activity.forEach((item) => {
          hourlyData[item.hour] = item.count;
        });

        this.charts.hourlyActivity.data.datasets[0].data = hourlyData;
        this.charts.hourlyActivity.update();
      }
    } catch (error) {
      console.error("시간대별 활동 업데이트 실패:", error);
    }
  }

  /**
   * 위협 레벨 업데이트
   */
  async updateThreatLevels() {
    try {
      const response = await fetch(
        `/api/v2/analytics/threat-levels?${this.buildQueryString()}`,
      );
      const data = await response.json();

      if (data.threat_levels && this.charts.threatLevel) {
        const values = [
          data.threat_levels.low || 0,
          data.threat_levels.medium || 0,
          data.threat_levels.high || 0,
          data.threat_levels.critical || 0,
        ];

        this.charts.threatLevel.data.datasets[0].data = values;
        this.charts.threatLevel.update();
      }
    } catch (error) {
      console.error("위협 레벨 업데이트 실패:", error);
    }
  }

  /**
   * 쿼리 문자열 생성
   */
  buildQueryString() {
    const params = new URLSearchParams();

    // 날짜 범위
    if (this.filters.dateRange !== "all") {
      params.append("range", this.filters.dateRange);
    }

    // 소스 필터
    if (this.filters.source !== "all") {
      params.append("source", this.filters.source);
    }

    // IP 유형 필터
    if (this.filters.ipType !== "all") {
      params.append("ip_type", this.filters.ipType);
    }

    return params.toString();
  }

  /**
   * 통계 내보내기
   */
  async exportStatistics() {
    try {
      const response = await fetch(
        `/api/v2/analytics/export?${this.buildQueryString()}`,
      );

      if (!response.ok) {
        throw new Error("내보내기 실패");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `blacklist_statistics_${new Date().toISOString().split("T")[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      this.showNotification("통계 데이터를 내보냈습니다.", "success");
    } catch (error) {
      console.error("통계 내보내기 실패:", error);
      this.showNotification("통계 내보내기에 실패했습니다.", "danger");
    }
  }

  /**
   * 자동 업데이트 시작
   */
  startAutoUpdate() {
    this.updateInterval = setInterval(() => {
      this.refreshAllCharts();
    }, this.options.updateInterval);
  }

  /**
   * 자동 업데이트 중지
   */
  stopAutoUpdate() {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = null;
    }
  }

  /**
   * 로딩 표시
   */
  showLoading(show) {
    const loadingOverlay = document.getElementById("statisticsLoading");
    if (loadingOverlay) {
      loadingOverlay.style.display = show ? "flex" : "none";
    }
  }

  /**
   * 에러 표시
   */
  showError(message) {
    this.showNotification(message, "danger");
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
   * 날짜 포맷팅
   */
  formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString("ko-KR", {
      month: "short",
      day: "numeric",
    });
  }

  /**
   * 마지막 새로고침 시간 업데이트
   */
  updateLastRefreshTime() {
    const element = document.getElementById("lastRefreshTime");
    if (element) {
      element.textContent = new Date().toLocaleTimeString("ko-KR");
    }
  }

  /**
   * 숫자 애니메이션
   */
  animateValue(element, endValue) {
    const startValue =
      parseInt(element.textContent.replace(/[^0-9]/g, "")) || 0;
    const duration = 1000;
    const steps = 30;
    const increment = (endValue - startValue) / steps;

    let step = 0;
    const timer = setInterval(() => {
      step++;
      const value = Math.round(startValue + increment * step);
      element.textContent = value.toLocaleString();

      if (step >= steps) {
        clearInterval(timer);
        element.textContent = endValue.toLocaleString();
      }
    }, duration / steps);
  }

  /**
   * HEX to RGBA 변환
   */
  hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  /**
   * 정리
   */
  destroy() {
    this.stopAutoUpdate();

    // 차트 정리
    Object.values(this.charts).forEach((chart) => {
      if (chart) {
        chart.destroy();
      }
    });

    this.charts = {};
  }
}

// 전역 인스턴스
let statisticsDashboard = null;

/**
 * 통계 대시보드 초기화
 */
function initializeStatisticsDashboard(options = {}) {
  if (statisticsDashboard) {
    statisticsDashboard.destroy();
  }

  statisticsDashboard = new StatisticsDashboard(options);
  return statisticsDashboard;
}

// 페이지 로드 시 초기화
document.addEventListener("DOMContentLoaded", function () {
  // 통계 페이지에서만 초기화
  if (
    window.location.pathname === "/statistics" ||
    document.getElementById("statisticsContainer")
  ) {
    initializeStatisticsDashboard();
  }
});

// 모듈 export
if (typeof module !== "undefined" && module.exports) {
  module.exports = { StatisticsDashboard, initializeStatisticsDashboard };
}
