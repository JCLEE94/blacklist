#!/bin/bash
# Watchtower 모니터링 스크립트
# 작성자: 이재철 (jclee)
# 버전: v1.0.1

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Watchtower 상태 확인
check_watchtower_status() {
    log_info "Watchtower 상태 확인 중..."
    
    if docker ps | grep -q watchtower; then
        log_success "Watchtower 컨테이너가 실행 중입니다"
        
        # 컨테이너 상세 정보
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep watchtower
        
        # 최근 로그 확인
        log_info "최근 Watchtower 로그:"
        docker logs blacklist-watchtower --tail 10 2>/dev/null || \
        docker logs blacklist-watchtower-standalone --tail 10 2>/dev/null || \
        log_warning "Watchtower 로그를 가져올 수 없습니다"
        
    else
        log_error "Watchtower 컨테이너가 실행되지 않고 있습니다"
        return 1
    fi
}

# 애플리케이션 헬스 체크
check_app_health() {
    log_info "애플리케이션 헬스 체크 중..."
    
    if curl -sf http://localhost:32542/health > /dev/null; then
        log_success "애플리케이션이 정상 작동 중입니다"
        
        # 상세 헬스 정보
        local health_info=$(curl -s http://localhost:32542/health | jq -r '.status // "unknown"')
        local version=$(curl -s http://localhost:32542/health | jq -r '.version // "unknown"')
        
        log_info "상태: $health_info"
        log_info "버전: $version"
        
    else
        log_error "애플리케이션 헬스 체크 실패"
        return 1
    fi
}

# 이미지 업데이트 체크
check_image_updates() {
    log_info "이미지 업데이트 확인 중..."
    
    local current_image=$(docker inspect blacklist --format='{{.Config.Image}}' 2>/dev/null || echo "unknown")
    log_info "현재 이미지: $current_image"
    
    # Registry에서 최신 이미지 정보 확인
    if docker pull --quiet registry.jclee.me/blacklist:latest 2>/dev/null; then
        local latest_image_id=$(docker images --format "{{.ID}}" registry.jclee.me/blacklist:latest | head -n1)
        local current_image_id=$(docker inspect blacklist --format='{{.Image}}' 2>/dev/null | cut -d: -f2 | head -c12)
        
        if [ "$latest_image_id" != "$current_image_id" ]; then
            log_warning "새로운 이미지 버전이 사용 가능합니다"
            log_info "현재: $current_image_id"
            log_info "최신: $latest_image_id"
        else
            log_success "최신 이미지를 사용 중입니다"
        fi
    else
        log_warning "Registry에서 이미지를 가져올 수 없습니다 (인증 필요할 수 있음)"
    fi
}

# 전체 시스템 상태 요약
system_summary() {
    log_info "=== 시스템 상태 요약 ==="
    
    echo
    echo "🐳 Docker 컨테이너 상태:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(blacklist|watchtower)" || echo "  관련 컨테이너 없음"
    
    echo
    echo "📊 시스템 리소스:"
    echo "  메모리 사용량: $(free -h | awk 'NR==2{printf "%.1f%%", $3*100/$2 }')"
    echo "  디스크 사용량: $(df -h / | awk 'NR==2{print $5}')"
    
    echo
    echo "🔄 Watchtower 다음 실행:"
    local next_run=$(docker logs blacklist-watchtower 2>/dev/null | grep "Scheduling first run" | tail -1 | grep -o "2025-[0-9-]* [0-9:]*" || echo "알 수 없음")
    echo "  $next_run"
    
    echo
}

# 메인 함수
main() {
    log_info "Watchtower 모니터링 시작"
    
    # 상태 체크들
    check_watchtower_status
    echo
    check_app_health
    echo
    check_image_updates
    echo
    
    # 요약 정보
    system_summary
    
    log_success "모니터링 완료"
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi