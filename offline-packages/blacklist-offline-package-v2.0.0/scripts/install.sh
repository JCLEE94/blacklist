#!/bin/bash
# 블랙리스트 시스템 오프라인 설치 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(dirname "$SCRIPT_DIR")"
INSTALL_DIR="/opt/blacklist"
LOG_FILE="/tmp/blacklist-install.log"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
    log "[STEP] $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    log "[SUCCESS] $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    log "[WARNING] $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    log "[ERROR] $1"
}

# 루트 권한 확인
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "이 스크립트는 root 권한으로 실행해야 합니다."
        echo "sudo $0 $@"
        exit 1
    fi
}

# 시스템 요구사항 확인
check_system_requirements() {
    print_step "시스템 요구사항 확인 중..."
    
    # OS 확인
    if [[ ! -f /etc/os-release ]]; then
        print_error "지원되지 않는 운영체제입니다."
        exit 1
    fi
    
    source /etc/os-release
    print_success "OS: $PRETTY_NAME"
    
    # 메모리 확인
    MEMORY_GB=$(free -g | awk '/^Mem:/{print $2}')
    if [[ $MEMORY_GB -lt 4 ]]; then
        print_warning "권장 메모리(4GB) 미만입니다. 현재: ${MEMORY_GB}GB"
    else
        print_success "메모리: ${MEMORY_GB}GB"
    fi
    
    # 디스크 공간 확인
    DISK_FREE_GB=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
    if [[ $DISK_FREE_GB -lt 10 ]]; then
        print_error "디스크 공간이 부족합니다. 최소 10GB 필요, 현재: ${DISK_FREE_GB}GB"
        exit 1
    else
        print_success "디스크 여유공간: ${DISK_FREE_GB}GB"
    fi
}

# Docker 설치 및 확인
setup_docker() {
    print_step "Docker 설치 및 확인 중..."
    
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        print_success "Docker 이미 설치됨: $DOCKER_VERSION"
    else
        print_step "Docker 설치 중..."
        
        # 공식 Docker 설치 스크립트 사용 (오프라인 환경에서는 사전 설치 필요)
        if [[ -f "$PACKAGE_ROOT/tools/docker-install.sh" ]]; then
            bash "$PACKAGE_ROOT/tools/docker-install.sh"
        else
            print_error "Docker가 설치되지 않았습니다. 수동으로 설치하세요."
            exit 1
        fi
    fi
    
    # Docker 서비스 시작
    systemctl enable docker
    systemctl start docker
    
    # Docker Compose 확인
    if ! command -v docker-compose &> /dev/null; then
        print_step "Docker Compose 설치 중..."
        # 바이너리 복사 (패키지에 포함된 경우)
        if [[ -f "$PACKAGE_ROOT/tools/docker-compose" ]]; then
            cp "$PACKAGE_ROOT/tools/docker-compose" /usr/local/bin/
            chmod +x /usr/local/bin/docker-compose
        else
            print_error "Docker Compose가 없습니다."
            exit 1
        fi
    fi
}

# Python 환경 설정
setup_python() {
    print_step "Python 환경 설정 중..."
    
    # Python 3.9+ 확인
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python 설치됨: $PYTHON_VERSION"
    else
        print_error "Python 3.9+ 가 필요합니다."
        exit 1
    fi
    
    # pip 확인 및 업그레이드
    if ! command -v pip3 &> /dev/null; then
        print_error "pip가 설치되지 않았습니다."
        exit 1
    fi
    
    # 오프라인 의존성 설치
    if [[ -d "$PACKAGE_ROOT/dependencies" ]]; then
        bash "$SCRIPT_DIR/install-python-deps.sh"
    fi
}

# 애플리케이션 설치
install_application() {
    print_step "애플리케이션 설치 중..."
    
    # 설치 디렉토리 생성
    mkdir -p "$INSTALL_DIR"
    
    # 소스 코드 복사
    if [[ -d "$PACKAGE_ROOT/source-code" ]]; then
        cp -r "$PACKAGE_ROOT/source-code"/* "$INSTALL_DIR/"
        print_success "소스 코드 복사 완료"
    fi
    
    # 설정 파일 복사
    if [[ -d "$PACKAGE_ROOT/configs" ]]; then
        cp -r "$PACKAGE_ROOT/configs"/* "$INSTALL_DIR/"
        print_success "설정 파일 복사 완료"
    fi
    
    # 권한 설정
    chown -R 1000:1000 "$INSTALL_DIR"
    chmod +x "$INSTALL_DIR"/*.sh 2>/dev/null || true
}

# Docker 이미지 로드
load_docker_images() {
    print_step "Docker 이미지 로드 중..."
    
    if [[ -d "$PACKAGE_ROOT/docker-images" ]]; then
        bash "$SCRIPT_DIR/load-docker-images.sh"
    else
        print_warning "Docker 이미지가 패키지에 포함되지 않았습니다."
    fi
}

# 서비스 설정
setup_services() {
    print_step "시스템 서비스 설정 중..."
    
    # systemd 서비스 파일 설치
    bash "$SCRIPT_DIR/setup-systemd.sh" "$INSTALL_DIR"
    
    # 환경 변수 설정
    if [[ -f "$INSTALL_DIR/.env.template" ]]; then
        if [[ ! -f "$INSTALL_DIR/.env" ]]; then
            cp "$INSTALL_DIR/.env.template" "$INSTALL_DIR/.env"
            print_warning ".env 파일을 수동으로 편집하세요: $INSTALL_DIR/.env"
        fi
    fi
}

# 데이터베이스 초기화
setup_database() {
    print_step "데이터베이스 초기화 중..."
    
    cd "$INSTALL_DIR"
    
    # 데이터베이스 디렉토리 생성
    mkdir -p instance
    
    # 데이터베이스 초기화
    if [[ -f "init_database.py" ]]; then
        python3 init_database.py
        print_success "데이터베이스 초기화 완료"
    fi
}

# 설치 검증
verify_installation() {
    print_step "설치 검증 중..."
    
    if [[ -f "$PACKAGE_ROOT/tools/verify-installation.sh" ]]; then
        bash "$PACKAGE_ROOT/tools/verify-installation.sh"
    else
        # 기본 검증
        if systemctl is-active --quiet blacklist; then
            print_success "블랙리스트 서비스가 실행 중입니다."
        else
            print_warning "블랙리스트 서비스가 실행되지 않았습니다."
        fi
    fi
}

# 설치 완료 메시지
show_completion_message() {
    echo
    print_success "=== 블랙리스트 시스템 설치 완료 ==="
    echo
    echo "설치 위치: $INSTALL_DIR"
    echo "로그 파일: $LOG_FILE"
    echo
    echo "다음 단계:"
    echo "1. 환경 변수 편집: $INSTALL_DIR/.env"
    echo "2. 서비스 시작: systemctl start blacklist"
    echo "3. 상태 확인: systemctl status blacklist"
    echo "4. 웹 대시보드: http://localhost:32542/dashboard"
    echo
    echo "문제가 발생하면 다음을 확인하세요:"
    echo "- 로그 파일: $LOG_FILE"
    echo "- 시스템 로그: journalctl -u blacklist"
    echo "- 문서: $PACKAGE_ROOT/docs/"
    echo
}

# 메인 설치 프로세스
main() {
    echo "🚀 블랙리스트 시스템 오프라인 설치 시작"
    echo "로그 파일: $LOG_FILE"
    echo
    
    check_root
    check_system_requirements
    setup_docker
    setup_python
    load_docker_images
    install_application
    setup_services
    setup_database
    verify_installation
    show_completion_message
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
