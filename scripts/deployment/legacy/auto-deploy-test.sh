#!/bin/bash

# 자동 배포 완전 테스트 스크립트
# Push → Build → Deploy 전체 파이프라인 검증

set -e

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 현재 버전 확인
check_current_version() {
    log_info "현재 배포된 버전 확인 중..."
    CURRENT_VERSION=$(curl -s http://192.168.50.215:2541/health | jq -r '.version')
    log_info "현재 버전: $CURRENT_VERSION"
    echo "$CURRENT_VERSION"
}

# 테스트 변경 생성
create_test_change() {
    log_info "테스트용 버전 변경 생성 중..."
    
    # 타임스탬프 생성
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    NEW_VERSION="2.0.2-auto-${TIMESTAMP}"
    
    # 버전 변경
    sed -i "s/\"version\": \".*\"/\"version\": \"${NEW_VERSION}\"/" \
        src/core/routes/api_routes.py
    
    log_success "새 버전: $NEW_VERSION"
    echo "$NEW_VERSION"
}

# Git 커밋 및 푸시
git_push() {
    log_info "Git 커밋 및 푸시 중..."
    
    git add -A
    git commit -m "test: 자동 배포 테스트 - $(date +%Y%m%d-%H%M%S)

- 자동 배포 파이프라인 검증
- Watchtower 자동 감지 테스트
- 버전: $1

🚀 Automated deployment validation"
    
    git push origin main
    log_success "푸시 완료"
}

# GitHub Actions 모니터링
monitor_github_actions() {
    log_info "GitHub Actions 빌드 모니터링 중..."
    
    # 최신 워크플로우 ID 가져오기
    WORKFLOW_ID=$(gh run list --workflow=deploy.yaml --limit=1 --json databaseId -q '.[0].databaseId')
    
    if [ -n "$WORKFLOW_ID" ]; then
        log_info "워크플로우 ID: $WORKFLOW_ID"
        
        # 빌드 완료 대기 (최대 5분)
        TIMEOUT=300
        ELAPSED=0
        
        while [ $ELAPSED -lt $TIMEOUT ]; do
            STATUS=$(gh run view $WORKFLOW_ID --json status -q '.status')
            
            if [ "$STATUS" == "completed" ]; then
                CONCLUSION=$(gh run view $WORKFLOW_ID --json conclusion -q '.conclusion')
                if [ "$CONCLUSION" == "success" ]; then
                    log_success "GitHub Actions 빌드 성공"
                    return 0
                else
                    log_error "GitHub Actions 빌드 실패: $CONCLUSION"
                    return 1
                fi
            fi
            
            echo -n "."
            sleep 10
            ELAPSED=$((ELAPSED + 10))
        done
        
        log_warning "빌드 타임아웃 (5분)"
        return 1
    else
        log_error "워크플로우 ID를 찾을 수 없습니다"
        return 1
    fi
}

# Watchtower 모니터링
monitor_watchtower() {
    log_info "Watchtower 자동 배포 모니터링 중..."
    
    # 최대 3분 대기
    TIMEOUT=180
    ELAPSED=0
    EXPECTED_VERSION=$1
    
    while [ $ELAPSED -lt $TIMEOUT ]; do
        DEPLOYED_VERSION=$(curl -s http://192.168.50.215:2541/health 2>/dev/null | jq -r '.version')
        
        if [ "$DEPLOYED_VERSION" == "$EXPECTED_VERSION" ]; then
            log_success "자동 배포 성공! 버전: $DEPLOYED_VERSION"
            return 0
        fi
        
        echo -n "."
        sleep 10
        ELAPSED=$((ELAPSED + 10))
    done
    
    log_warning "자동 배포 타임아웃 - 수동 배포 시도"
    return 1
}

# 수동 배포 (폴백)
manual_deploy() {
    log_info "수동 배포 실행 중..."
    
    sshpass -p 'bingogo1' ssh -p 1111 docker@192.168.50.215 \
        "cd /volume1/docker/blacklist && \
         /usr/local/bin/docker compose pull && \
         /usr/local/bin/docker compose up -d" 2>/dev/null
    
    sleep 10
    
    DEPLOYED_VERSION=$(curl -s http://192.168.50.215:2541/health 2>/dev/null | jq -r '.version')
    log_info "배포된 버전: $DEPLOYED_VERSION"
}

# 전체 파이프라인 실행
run_full_pipeline() {
    echo "=========================================="
    echo "🚀 자동 배포 파이프라인 테스트 시작"
    echo "=========================================="
    echo ""
    
    # 1. 현재 버전 확인
    CURRENT_VERSION=$(check_current_version)
    
    # 2. 테스트 변경 생성
    NEW_VERSION=$(create_test_change)
    
    # 3. Git 푸시
    git_push "$NEW_VERSION"
    
    # 4. GitHub Actions 모니터링
    if monitor_github_actions; then
        # 5. Watchtower 자동 배포 모니터링
        if monitor_watchtower "$NEW_VERSION"; then
            echo ""
            echo "=========================================="
            echo "✅ 자동 배포 파이프라인 완전 성공!"
            echo "=========================================="
            echo "  이전 버전: $CURRENT_VERSION"
            echo "  새 버전: $NEW_VERSION"
            echo "  소요 시간: ~3-4분"
            echo ""
            return 0
        else
            # 6. 수동 배포 (폴백)
            manual_deploy
            echo ""
            echo "=========================================="
            echo "⚠️ Watchtower 자동 배포 실패 - 수동 배포 완료"
            echo "=========================================="
            echo "  Watchtower 설정 확인 필요"
            echo ""
            return 1
        fi
    else
        log_error "GitHub Actions 빌드 실패"
        return 1
    fi
}

# 도움말
show_help() {
    cat << EOF
자동 배포 파이프라인 테스트 스크립트

사용법: $0 [COMMAND]

COMMANDS:
    test        전체 파이프라인 테스트 (기본값)
    version     현재 버전 확인
    help        도움말 표시

EXAMPLES:
    $0          # 전체 테스트 실행
    $0 version  # 현재 배포 버전 확인
EOF
}

# 명령어 처리
case "${1:-test}" in
    test)
        run_full_pipeline
        ;;
    version)
        check_current_version
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