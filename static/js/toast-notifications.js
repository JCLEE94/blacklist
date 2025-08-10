/**
 * 토스트 알림 시스템
 * Toast Notification System for Blacklist Management
 */

class ToastNotificationSystem {
  constructor(options = {}) {
    this.options = {
      position: options.position || "top-right",
      duration: options.duration || 5000,
      maxToasts: options.maxToasts || 5,
      animationDuration: options.animationDuration || 300,
      ...options,
    };

    this.toasts = [];
    this.container = null;

    this.init();
  }

  /**
   * 시스템 초기화
   */
  init() {
    this.createContainer();
    this.setupStyles();

    // 전역 함수로 등록
    window.showNotification = this.show.bind(this);
    window.showToast = this.show.bind(this);
  }

  /**
   * 토스트 컨테이너 생성
   */
  createContainer() {
    // 기존 컨테이너 제거
    const existing = document.getElementById("toast-container");
    if (existing) {
      existing.remove();
    }

    // 새 컨테이너 생성
    this.container = document.createElement("div");
    this.container.id = "toast-container";
    this.container.className = `toast-container toast-${this.options.position}`;
    document.body.appendChild(this.container);
  }

  /**
   * 스타일 설정
   */
  setupStyles() {
    // 스타일이 이미 존재하는지 확인
    if (document.getElementById("toast-styles")) {
      return;
    }

    const style = document.createElement("style");
    style.id = "toast-styles";
    style.textContent = `
            .toast-container {
                position: fixed;
                z-index: 9999;
                pointer-events: none;
                display: flex;
                flex-direction: column;
                gap: 10px;
                padding: 20px;
            }
            
            .toast-top-right {
                top: 0;
                right: 0;
                align-items: flex-end;
            }
            
            .toast-top-left {
                top: 0;
                left: 0;
                align-items: flex-start;
            }
            
            .toast-bottom-right {
                bottom: 0;
                right: 0;
                align-items: flex-end;
            }
            
            .toast-bottom-left {
                bottom: 0;
                left: 0;
                align-items: flex-start;
            }
            
            .toast-top-center {
                top: 0;
                left: 50%;
                transform: translateX(-50%);
                align-items: center;
            }
            
            .toast-bottom-center {
                bottom: 0;
                left: 50%;
                transform: translateX(-50%);
                align-items: center;
            }
            
            .toast {
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                padding: 16px 20px;
                min-width: 300px;
                max-width: 500px;
                pointer-events: all;
                display: flex;
                align-items: center;
                gap: 12px;
                animation: slideIn ${this.options.animationDuration}ms ease-out;
                transition: all ${this.options.animationDuration}ms ease-out;
                position: relative;
                overflow: hidden;
            }
            
            .toast.toast-hiding {
                animation: slideOut ${this.options.animationDuration}ms ease-in;
                opacity: 0;
                transform: translateX(100%);
            }
            
            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateX(100%);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }
            
            @keyframes slideOut {
                from {
                    opacity: 1;
                    transform: translateX(0);
                }
                to {
                    opacity: 0;
                    transform: translateX(100%);
                }
            }
            
            .toast-icon {
                font-size: 24px;
                flex-shrink: 0;
            }
            
            .toast-content {
                flex: 1;
            }
            
            .toast-title {
                font-weight: 600;
                margin-bottom: 4px;
                font-size: 16px;
            }
            
            .toast-message {
                font-size: 14px;
                color: #666;
                line-height: 1.4;
            }
            
            .toast-close {
                background: none;
                border: none;
                font-size: 20px;
                color: #999;
                cursor: pointer;
                padding: 0;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 4px;
                transition: all 0.2s;
            }
            
            .toast-close:hover {
                background: rgba(0, 0, 0, 0.1);
                color: #333;
            }
            
            .toast-progress {
                position: absolute;
                bottom: 0;
                left: 0;
                height: 3px;
                background: currentColor;
                opacity: 0.3;
                animation: progress ${this.options.duration}ms linear;
            }
            
            @keyframes progress {
                from {
                    width: 100%;
                }
                to {
                    width: 0%;
                }
            }
            
            /* 타입별 스타일 */
            .toast-success {
                border-left: 4px solid #198754;
            }
            
            .toast-success .toast-icon {
                color: #198754;
            }
            
            .toast-error {
                border-left: 4px solid #dc3545;
            }
            
            .toast-error .toast-icon {
                color: #dc3545;
            }
            
            .toast-warning {
                border-left: 4px solid #ffc107;
            }
            
            .toast-warning .toast-icon {
                color: #ffc107;
            }
            
            .toast-info {
                border-left: 4px solid #0dcaf0;
            }
            
            .toast-info .toast-icon {
                color: #0dcaf0;
            }
            
            /* 다크 모드 지원 */
            @media (prefers-color-scheme: dark) {
                .toast {
                    background: #2b2b2b;
                    color: #fff;
                }
                
                .toast-message {
                    color: #ccc;
                }
                
                .toast-close {
                    color: #666;
                }
                
                .toast-close:hover {
                    background: rgba(255, 255, 255, 0.1);
                    color: #fff;
                }
            }
            
            /* 모바일 반응형 */
            @media (max-width: 576px) {
                .toast-container {
                    padding: 10px;
                }
                
                .toast {
                    min-width: auto;
                    max-width: calc(100vw - 20px);
                }
            }
        `;

    document.head.appendChild(style);
  }

  /**
   * 토스트 표시
   */
  show(message, type = "info", options = {}) {
    // 옵션 병합
    const toastOptions = {
      ...this.options,
      ...options,
    };

    // 토스트 생성
    const toast = this.createToast(message, type, toastOptions);

    // 컨테이너에 추가
    this.container.appendChild(toast.element);
    this.toasts.push(toast);

    // 최대 개수 제한
    this.enforceMaxToasts();

    // 자동 제거 타이머
    if (toastOptions.duration > 0) {
      toast.timer = setTimeout(() => {
        this.remove(toast);
      }, toastOptions.duration);
    }

    return toast;
  }

  /**
   * 토스트 요소 생성
   */
  createToast(message, type, options) {
    const toast = {
      id: Date.now() + Math.random(),
      message,
      type,
      options,
    };

    // 토스트 요소
    const element = document.createElement("div");
    element.className = `toast toast-${type}`;
    element.dataset.toastId = toast.id;

    // 아이콘
    const icon = document.createElement("i");
    icon.className = `toast-icon bi ${this.getIconClass(type)}`;
    element.appendChild(icon);

    // 컨텐츠
    const content = document.createElement("div");
    content.className = "toast-content";

    // 제목과 메시지 파싱
    if (typeof message === "object" && message.title) {
      const title = document.createElement("div");
      title.className = "toast-title";
      title.textContent = message.title;
      content.appendChild(title);

      const msg = document.createElement("div");
      msg.className = "toast-message";
      msg.textContent = message.message || "";
      content.appendChild(msg);
    } else {
      const msg = document.createElement("div");
      msg.className = "toast-message";
      msg.textContent = message;
      content.appendChild(msg);
    }

    element.appendChild(content);

    // 닫기 버튼
    if (options.closable !== false) {
      const closeBtn = document.createElement("button");
      closeBtn.className = "toast-close";
      closeBtn.innerHTML = "&times;";
      closeBtn.onclick = () => this.remove(toast);
      element.appendChild(closeBtn);
    }

    // 진행 표시
    if (options.showProgress && options.duration > 0) {
      const progress = document.createElement("div");
      progress.className = "toast-progress";
      progress.style.animationDuration = `${options.duration}ms`;
      element.appendChild(progress);
    }

    // 클릭 이벤트
    if (options.onClick) {
      element.style.cursor = "pointer";
      element.onclick = (e) => {
        if (!e.target.classList.contains("toast-close")) {
          options.onClick(toast);
        }
      };
    }

    toast.element = element;
    return toast;
  }

  /**
   * 아이콘 클래스 반환
   */
  getIconClass(type) {
    const icons = {
      success: "bi-check-circle-fill",
      error: "bi-x-circle-fill",
      warning: "bi-exclamation-triangle-fill",
      info: "bi-info-circle-fill",
      default: "bi-bell-fill",
    };

    return icons[type] || icons.default;
  }

  /**
   * 토스트 제거
   */
  remove(toast) {
    // 타이머 제거
    if (toast.timer) {
      clearTimeout(toast.timer);
    }

    // 애니메이션 추가
    toast.element.classList.add("toast-hiding");

    // 애니메이션 후 제거
    setTimeout(() => {
      if (toast.element.parentNode) {
        toast.element.remove();
      }

      // 배열에서 제거
      const index = this.toasts.indexOf(toast);
      if (index > -1) {
        this.toasts.splice(index, 1);
      }
    }, this.options.animationDuration);
  }

  /**
   * 최대 토스트 개수 제한
   */
  enforceMaxToasts() {
    while (this.toasts.length > this.options.maxToasts) {
      const oldest = this.toasts.shift();
      this.remove(oldest);
    }
  }

  /**
   * 모든 토스트 제거
   */
  clear() {
    this.toasts.forEach((toast) => this.remove(toast));
  }

  /**
   * 특정 타입의 토스트 제거
   */
  clearType(type) {
    this.toasts
      .filter((toast) => toast.type === type)
      .forEach((toast) => this.remove(toast));
  }

  /**
   * 성공 메시지 표시
   */
  success(message, options) {
    return this.show(message, "success", options);
  }

  /**
   * 에러 메시지 표시
   */
  error(message, options) {
    return this.show(message, "error", {
      duration: 10000, // 에러는 더 오래 표시
      ...options,
    });
  }

  /**
   * 경고 메시지 표시
   */
  warning(message, options) {
    return this.show(message, "warning", options);
  }

  /**
   * 정보 메시지 표시
   */
  info(message, options) {
    return this.show(message, "info", options);
  }

  /**
   * 로딩 토스트 표시
   */
  loading(message, options) {
    const loadingIcon = document.createElement("div");
    loadingIcon.className = "spinner-border spinner-border-sm text-primary";

    return this.show(message, "info", {
      duration: 0, // 수동으로 닫아야 함
      closable: false,
      ...options,
      customIcon: loadingIcon,
    });
  }

  /**
   * Promise 기반 토스트
   */
  async promise(promise, messages) {
    const loading = this.loading(messages.loading || "처리 중...");

    try {
      const result = await promise;
      this.remove(loading);
      this.success(messages.success || "완료되었습니다!");
      return result;
    } catch (error) {
      this.remove(loading);
      this.error(messages.error || "오류가 발생했습니다.");
      throw error;
    }
  }
}

// 전역 인스턴스 생성
const toastSystem = new ToastNotificationSystem();

// 편의 함수들
const toast = {
  show: (message, type, options) => toastSystem.show(message, type, options),
  success: (message, options) => toastSystem.success(message, options),
  error: (message, options) => toastSystem.error(message, options),
  warning: (message, options) => toastSystem.warning(message, options),
  info: (message, options) => toastSystem.info(message, options),
  loading: (message, options) => toastSystem.loading(message, options),
  promise: (promise, messages) => toastSystem.promise(promise, messages),
  clear: () => toastSystem.clear(),
  clearType: (type) => toastSystem.clearType(type),
};

// 전역 등록
window.toast = toast;

// 페이지 로드 시 자동 초기화
document.addEventListener("DOMContentLoaded", function () {
  console.log("토스트 알림 시스템 초기화 완료");
});
