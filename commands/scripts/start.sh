#!/bin/bash

# Blacklist Management System - 간단한 시작 스크립트
# 단일 Docker Compose 파일로 간소화된 배포

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 도움말
show_help() {
    cat << EOF
Blacklist Management System - 간단한 관리 스크립트

사용법: $0 [COMMAND]

COMMANDS:
    start       서비스 시작 (기본값)
    stop        서비스 종료
    restart     서비스 재시작
    logs        로그 확인
    status      상태 확인
    update      이미지 업데이트
    clean       정리
    help        도움말 표시

EXAMPLES:
    $0 start     # 서비스 시작
    $0 logs      # 로그 확인
    $0 update    # 이미지 업데이트 후 재시작

EOF
}

# 환경 파일 확인
check_env() {
    if [[ ! -f ".env" ]]; then
        log_warning ".env 파일이 없습니다. 예제 파일에서 복사합니다."
        if [[ -f ".env.example" ]]; then
            cp .env.example .env
            log_info ".env 파일을 생성했습니다. 필요에 따라 수정하세요."
        else
            log_error ".env.example 파일을 찾을 수 없습니다."
            exit 1
        fi
    fi
}

# 디렉토리 생성
create_dirs() {
    log_info "필요한 디렉토리 생성 중..."
    mkdir -p instance data logs
}

# 서비스 시작
start_services() {
    log_info "서비스 시작 중..."
    
    check_env
    create_dirs
    
    docker-compose up -d
    
    log_success "서비스가 시작되었습니다."
    log_info "애플리케이션: http://localhost:2541"
    log_info "Redis: localhost:6379"
    
    # 헬스 체크
    log_info "서비스 헬스 체크 중..."
    sleep 5
    
    if curl -f http://localhost:2541/health > /dev/null 2>&1; then
        log_success "애플리케이션이 정상적으로 실행 중입니다."
    else
        log_warning "애플리케이션 헬스 체크 실패. 로그를 확인하세요: $0 logs"
    fi
}

# 서비스 종료
stop_services() {
    log_info "서비스 종료 중..."
    docker-compose down
    log_success "서비스가 종료되었습니다."
}

# 서비스 재시작
restart_services() {
    log_info "서비스 재시작 중..."
    docker-compose restart
    log_success "서비스가 재시작되었습니다."
}

# 로그 확인
show_logs() {
    log_info "로그 확인 중..."
    docker-compose logs -f
}

# 상태 확인
check_status() {
    log_info "서비스 상태 확인 중..."
    docker-compose ps
    
    echo ""
    log_info "헬스 체크:"
    
    # 애플리케이션 체크
    if curl -f http://localhost:2541/health > /dev/null 2>&1; then
        log_success "애플리케이션: 정상 (http://localhost:2541)"
    else
        log_error "애플리케이션: 비정상"
    fi
    
    # Redis 체크
    if docker exec blacklist-redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis: 정상"
    else
        log_error "Redis: 비정상"
    fi
}

# 이미지 업데이트
update_images() {
    log_info "이미지 업데이트 중..."
    docker-compose pull
    docker-compose up -d
    log_success "이미지 업데이트가 완료되었습니다."
}

# 정리
clean_system() {
    log_info "시스템 정리 중..."
    
    # 중지된 컨테이너 제거
    docker container prune -f
    
    # 사용하지 않는 이미지 제거
    docker image prune -f
    
    # 사용하지 않는 볼륨 제거 (주의: 데이터 손실 가능)
    read -p "사용하지 않는 볼륨을 제거하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume prune -f
    fi
    
    log_success "시스템 정리가 완료되었습니다."
}

# 메인 로직
main() {
    case "${1:-start}" in
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        logs)
            show_logs
            ;;
        status)
            check_status
            ;;
        update)
            update_images
            ;;
        clean)
            clean_system
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "알 수 없는 명령어: $1"
            show_help
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"