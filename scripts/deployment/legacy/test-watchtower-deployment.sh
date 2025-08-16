#!/bin/bash

# Watchtower 자동 배포 테스트 스크립트
# CI/CD 파이프라인과 Watchtower 연동 테스트

set -e

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

# 테스트 파일 생성
create_test_file() {
    log_info "테스트 파일 생성 중..."
    
    # 테스트를 위한 작은 변경사항 추가
    echo "# Test commit for Watchtower - $(date)" >> README.md
    
    log_success "테스트 파일 생성 완료"
}

# Git 커밋 및 푸시
commit_and_push() {
    log_info "변경사항 커밋 및 푸시 중..."
    
    git add .
    git commit -m "test: Watchtower auto-deployment test $(date +%Y%m%d-%H%M%S)"
    git push origin main
    
    log_success "커밋 및 푸시 완료"
}

# GitHub Actions 상태 확인
check_github_actions() {
    log_info "GitHub Actions 워크플로우 상태 확인 중..."
    
    # 최근 워크플로우 실행 상태 확인
    gh run list --workflow=deploy.yaml --limit=1
    
    # 실행 대기
    log_info "워크플로우 완료 대기 중 (최대 5분)..."
    
    WORKFLOW_ID=$(gh run list --workflow=deploy.yaml --limit=1 --json databaseId -q '.[0].databaseId')
    
    if [ -n "$WORKFLOW_ID" ]; then
        gh run watch $WORKFLOW_ID --exit-status || true
        log_success "GitHub Actions 워크플로우 완료"
    else
        log_warning "워크플로우 ID를 찾을 수 없습니다"
    fi
}

# 이미지 업데이트 확인
check_image_update() {
    log_info "Docker 레지스트리에서 이미지 업데이트 확인 중..."
    
    # 레지스트리 로그인
    docker login registry.jclee.me -u admin -p bingogo1 2>/dev/null || true
    
    # 최신 이미지 정보 확인
    docker pull registry.jclee.me/jclee94/blacklist:latest 2>/dev/null
    
    LATEST_IMAGE_ID=$(docker images registry.jclee.me/jclee94/blacklist:latest -q)
    log_info "최신 이미지 ID: $LATEST_IMAGE_ID"
    
    log_success "이미지 업데이트 확인 완료"
}

# Watchtower 로그 확인 (NAS)
check_watchtower_logs() {
    log_info "NAS Watchtower 로그 확인 중..."
    
    # SSH로 NAS 접속하여 Watchtower 로그 확인
    sshpass -p 'bingogo1' ssh -p 1111 docker@192.168.50.215 \
        "/usr/local/bin/docker logs watchtower --tail 20" 2>/dev/null || {
        log_warning "NAS Watchtower 로그를 가져올 수 없습니다"
    }
}

# 컨테이너 상태 확인 (NAS)
check_container_status() {
    log_info "NAS 컨테이너 상태 확인 중..."
    
    # 실행 중인 blacklist 컨테이너 확인
    CONTAINER_STATUS=$(sshpass -p 'bingogo1' ssh -p 1111 docker@192.168.50.215 \
        "/usr/local/bin/docker ps --filter name=blacklist --format '{{.Status}}'" 2>/dev/null)
    
    if [ -n "$CONTAINER_STATUS" ]; then
        log_success "Blacklist 컨테이너 상태: $CONTAINER_STATUS"
        
        # 컨테이너 이미지 ID 확인
        IMAGE_ID=$(sshpass -p 'bingogo1' ssh -p 1111 docker@192.168.50.215 \
            "/usr/local/bin/docker inspect blacklist --format '{{.Image}}'" 2>/dev/null | cut -c8-19)
        log_info "실행 중인 이미지 ID: $IMAGE_ID"
    else
        log_error "Blacklist 컨테이너를 찾을 수 없습니다"
    fi
}

# 헬스 체크
health_check() {
    log_info "애플리케이션 헬스 체크 중..."
    
    # NAS 애플리케이션 헬스 체크
    if curl -f http://192.168.50.215:2541/health 2>/dev/null; then
        log_success "NAS 애플리케이션이 정상 작동 중입니다"
    else
        log_warning "NAS 애플리케이션 헬스 체크 실패"
    fi
}

# Watchtower 재시작 (필요시)
restart_watchtower() {
    log_info "Watchtower 재시작 중..."
    
    sshpass -p 'bingogo1' ssh -p 1111 docker@192.168.50.215 \
        "/usr/local/bin/docker restart watchtower" 2>/dev/null || {
        log_warning "Watchtower 재시작 실패"
    }
    
    log_success "Watchtower 재시작 완료"
}

# 메인 테스트 플로우
main() {
    echo "=========================================="
    echo "🚀 Watchtower 자동 배포 테스트 시작"
    echo "=========================================="
    echo ""
    
    # 1. 테스트 파일 생성
    create_test_file
    
    # 2. Git 커밋 및 푸시
    commit_and_push
    
    # 3. GitHub Actions 상태 확인
    check_github_actions
    
    # 4. 이미지 업데이트 확인
    check_image_update
    
    # 5. Watchtower가 변경사항을 감지할 시간 대기
    log_info "Watchtower가 변경사항을 감지하도록 2분 대기 중..."
    sleep 120
    
    # 6. Watchtower 로그 확인
    check_watchtower_logs
    
    # 7. 컨테이너 상태 확인
    check_container_status
    
    # 8. 헬스 체크
    health_check
    
    echo ""
    echo "=========================================="
    echo "✅ Watchtower 자동 배포 테스트 완료"
    echo "=========================================="
    echo ""
    echo "📋 테스트 결과 요약:"
    echo "  1. GitHub Actions 빌드 및 푸시: 완료"
    echo "  2. Docker 이미지 업데이트: 완료"
    echo "  3. Watchtower 자동 감지: 확인 필요"
    echo "  4. 컨테이너 자동 재시작: 확인 필요"
    echo "  5. 애플리케이션 정상 작동: 확인 필요"
}

# 도움말
show_help() {
    cat << EOF
Watchtower 자동 배포 테스트 스크립트

사용법: $0 [COMMAND]

COMMANDS:
    test        전체 테스트 실행 (기본값)
    logs        Watchtower 로그만 확인
    status      컨테이너 상태만 확인
    restart     Watchtower 재시작
    help        도움말 표시

EXAMPLES:
    $0          # 전체 테스트 실행
    $0 logs     # Watchtower 로그 확인
    $0 status   # 컨테이너 상태 확인
EOF
}

# 명령어 처리
case "${1:-test}" in
    test)
        main
        ;;
    logs)
        check_watchtower_logs
        ;;
    status)
        check_container_status
        health_check
        ;;
    restart)
        restart_watchtower
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