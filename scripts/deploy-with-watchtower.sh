#!/bin/bash
# 🚀 Watchtower 자동 배포 스크립트
# GitHub Actions → Docker Build → Registry Push → Watchtower Auto Deploy

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# 설정 변수
REGISTRY="registry.jclee.me"
IMAGE_NAME="jclee94/blacklist"
WATCHTOWER_API_TOKEN="blacklist-watchtower-2024"
WATCHTOWER_API_URL="http://localhost:8080"

# 환경 확인
check_environment() {
    log "환경 설정 확인 중..."
    
    # Docker 확인
    if ! command -v docker &> /dev/null; then
        error "Docker가 설치되지 않음"
        exit 1
    fi
    
    # Docker Compose 확인
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose가 설치되지 않음"
        exit 1
    fi
    
    # 프로젝트 파일 확인
    if [[ ! -f "$PROJECT_ROOT/docker-compose.yml" ]]; then
        error "docker-compose.yml을 찾을 수 없음"
        exit 1
    fi
    
    success "환경 설정 확인 완료"
}

# Git 정보 확인
get_git_info() {
    log "Git 정보 수집 중..."
    
    cd "$PROJECT_ROOT"
    
    GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    GIT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
    BUILD_DATE=$(date +'%Y%m%d-%H%M%S')
    
    success "Git 정보: $GIT_BRANCH@$GIT_COMMIT (빌드: $BUILD_DATE)"
}

# Docker 이미지 빌드
build_image() {
    log "Docker 이미지 빌드 시작..."
    
    cd "$PROJECT_ROOT"
    
    # VERSION 파일에서 버전 읽기 또는 생성
    if [[ -f "VERSION" ]]; then
        VERSION=$(cat VERSION)
    else
        VERSION="1.0.0"
        echo "$VERSION" > VERSION
    fi
    
    log "빌드 중: $REGISTRY/$IMAGE_NAME:$VERSION"
    
    # Docker 이미지 빌드
    docker build \
        --file deployment/Dockerfile \
        --tag "$REGISTRY/$IMAGE_NAME:latest" \
        --tag "$REGISTRY/$IMAGE_NAME:$VERSION" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$GIT_COMMIT" \
        --build-arg VERSION="$VERSION" \
        .
    
    success "Docker 이미지 빌드 완료"
}

# Registry에 푸시
push_image() {
    log "Registry에 이미지 푸시 중..."
    
    # Registry 로그인 확인
    docker login "$REGISTRY" || {
        error "Registry 로그인 실패"
        exit 1
    }
    
    # 이미지 푸시
    docker push "$REGISTRY/$IMAGE_NAME:latest"
    docker push "$REGISTRY/$IMAGE_NAME:$VERSION"
    
    success "이미지 푸시 완료: $REGISTRY/$IMAGE_NAME:latest"
}

# Watchtower 상태 확인
check_watchtower() {
    log "Watchtower 상태 확인 중..."
    
    # Watchtower API 호출 (타임아웃 5초)
    if curl -s --max-time 5 -H "Authorization: Bearer $WATCHTOWER_API_TOKEN" \
       "$WATCHTOWER_API_URL/v1/update" >/dev/null 2>&1; then
        success "Watchtower API 응답 정상"
        return 0
    else
        warning "Watchtower API 응답 없음 - 컨테이너 직접 확인"
        
        # Docker 컨테이너 상태 확인
        if docker ps | grep -q "watchtower-blacklist"; then
            success "Watchtower 컨테이너 실행 중"
            return 0
        else
            error "Watchtower 컨테이너를 찾을 수 없음"
            return 1
        fi
    fi
}

# Watchtower 업데이트 트리거
trigger_update() {
    log "Watchtower 업데이트 트리거 중..."
    
    # API를 통한 업데이트 트리거 시도
    if curl -s --max-time 10 \
       -H "Authorization: Bearer $WATCHTOWER_API_TOKEN" \
       -X POST "$WATCHTOWER_API_URL/v1/update" >/dev/null 2>&1; then
        success "Watchtower 업데이트 API 호출 성공"
    else
        warning "API 호출 실패 - Watchtower가 자동으로 감지할 예정"
    fi
    
    log "Watchtower가 60초 간격으로 새 이미지를 확인합니다"
    log "예상 배포 시간: 1-3분"
}

# 배포 상태 모니터링
monitor_deployment() {
    log "배포 상태 모니터링 중..."
    
    local max_wait=300  # 5분 최대 대기
    local wait_time=0
    local check_interval=10
    
    while [[ $wait_time -lt $max_wait ]]; do
        # 컨테이너 상태 확인
        if container_status=$(docker inspect blacklist --format='{{.State.Status}}' 2>/dev/null); then
            case $container_status in
                "running")
                    # Health check 확인
                    if health_status=$(docker inspect blacklist --format='{{.State.Health.Status}}' 2>/dev/null); then
                        if [[ $health_status == "healthy" ]]; then
                            success "배포 완료! 컨테이너가 정상 실행 중입니다"
                            return 0
                        else
                            log "Health check 대기 중... ($health_status)"
                        fi
                    else
                        log "컨테이너 실행 중, Health check 설정 없음"
                        success "배포 완료! 컨테이너가 실행 중입니다"
                        return 0
                    fi
                    ;;
                "restarting")
                    log "컨테이너 재시작 중..."
                    ;;
                "exited")
                    error "컨테이너가 종료됨. 로그 확인이 필요합니다"
                    docker logs blacklist --tail=20
                    return 1
                    ;;
                *)
                    log "컨테이너 상태: $container_status"
                    ;;
            esac
        else
            log "컨테이너 상태 확인 중..."
        fi
        
        sleep $check_interval
        wait_time=$((wait_time + check_interval))
        log "대기 중... (${wait_time}s/${max_wait}s)"
    done
    
    warning "모니터링 시간 초과. 수동으로 상태를 확인하세요:"
    echo "  docker logs blacklist"
    echo "  docker ps"
    return 1
}

# 배포 정보 표시
show_deployment_info() {
    log "배포 정보 요약"
    echo "===================="
    echo "📦 이미지: $REGISTRY/$IMAGE_NAME:latest"
    echo "🏷️  버전: $VERSION"
    echo "🔄 커밋: $GIT_BRANCH@$GIT_COMMIT"
    echo "📅 빌드: $BUILD_DATE"
    echo ""
    echo "🔗 접속 URL:"
    echo "  - 애플리케이션: http://localhost:2541"
    echo "  - Watchtower API: http://localhost:8080"
    echo ""
    echo "📋 유용한 명령어:"
    echo "  - 로그 확인: docker logs blacklist -f"
    echo "  - 상태 확인: docker ps"
    echo "  - Health check: curl http://localhost:2541/health"
    echo "===================="
}

# 메인 실행
main() {
    log "🚀 Blacklist Watchtower 자동 배포 시작"
    
    check_environment
    get_git_info
    build_image
    push_image
    
    if check_watchtower; then
        trigger_update
        monitor_deployment
        success "🎉 배포 완료!"
    else
        warning "Watchtower를 찾을 수 없어 수동 재시작이 필요할 수 있습니다"
        log "다음 명령어로 수동 재시작:"
        echo "  cd $PROJECT_ROOT && docker-compose pull && docker-compose up -d"
    fi
    
    show_deployment_info
}

# 스크립트 인자 처리
case "${1:-help}" in
    "deploy")
        main
        ;;
    "build-only")
        check_environment
        get_git_info
        build_image
        success "빌드만 완료됨 (푸시하지 않음)"
        ;;
    "push-only")
        check_environment
        push_image
        success "이미지 푸시 완료"
        ;;
    "status")
        check_watchtower
        docker ps --filter "name=blacklist"
        ;;
    "help"|*)
        echo "사용법: $0 {deploy|build-only|push-only|status}"
        echo ""
        echo "Commands:"
        echo "  deploy     - 전체 배포 프로세스 실행 (빌드 → 푸시 → 배포)"
        echo "  build-only - Docker 이미지 빌드만 수행"
        echo "  push-only  - Registry에 이미지 푸시만 수행"
        echo "  status     - Watchtower 및 컨테이너 상태 확인"
        echo "  help       - 이 도움말 표시"
        exit 0
        ;;
esac