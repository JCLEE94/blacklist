#!/bin/bash
# Watchtower Management Script for Blacklist
# Version: v1.0.37

set -euo pipefail

WATCHTOWER_COMPOSE="docker-compose.watchtower.yml"
WATCHTOWER_CONTAINER="blacklist-watchtower"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 사용법 출력
show_usage() {
    echo "🔧 Blacklist Watchtower 관리 도구"
    echo ""
    echo "사용법: $0 [명령]"
    echo ""
    echo "명령어:"
    echo "  start     - Watchtower 시작"
    echo "  stop      - Watchtower 중지"
    echo "  restart   - Watchtower 재시작"
    echo "  status    - Watchtower 상태 확인"
    echo "  logs      - Watchtower 로그 확인"
    echo "  update    - 수동 업데이트 트리거"
    echo "  test      - Watchtower 테스트 실행"
    echo "  config    - Watchtower 설정 확인"
    echo ""
    echo "예시:"
    echo "  $0 start      # Watchtower 시작"
    echo "  $0 status     # 현재 상태 확인"
    echo "  $0 logs -f    # 실시간 로그 확인"
}

# Watchtower 상태 확인
check_status() {
    print_status "Watchtower 상태 확인 중..."
    
    if docker ps --filter "name=$WATCHTOWER_CONTAINER" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -q "$WATCHTOWER_CONTAINER"; then
        print_success "Watchtower가 실행 중입니다"
        docker ps --filter "name=$WATCHTOWER_CONTAINER" --format "table {{.Names}}\t{{.Status}}\t{{.CreatedAt}}"
    else
        print_warning "Watchtower가 실행되지 않았습니다"
        return 1
    fi
}

# Watchtower 시작
start_watchtower() {
    print_status "Watchtower 시작 중..."
    
    # 네트워크 존재 확인
    if ! docker network ls | grep -q "blacklist-network"; then
        print_warning "blacklist-network가 존재하지 않습니다. 먼저 메인 서비스를 시작하세요."
        print_status "네트워크 생성 중..."
        docker network create blacklist-network
    fi
    
    # Watchtower 시작
    docker-compose -f "$WATCHTOWER_COMPOSE" up -d
    
    # 시작 확인
    sleep 3
    if check_status; then
        print_success "Watchtower가 성공적으로 시작되었습니다"
        show_config
    else
        print_error "Watchtower 시작에 실패했습니다"
        exit 1
    fi
}

# Watchtower 중지
stop_watchtower() {
    print_status "Watchtower 중지 중..."
    docker-compose -f "$WATCHTOWER_COMPOSE" down
    print_success "Watchtower가 중지되었습니다"
}

# Watchtower 재시작
restart_watchtower() {
    print_status "Watchtower 재시작 중..."
    stop_watchtower
    sleep 2
    start_watchtower
}

# 로그 확인
show_logs() {
    local args="${*:2}"  # 첫 번째 인수($1) 제외한 나머지
    print_status "Watchtower 로그 확인 중..."
    
    if [[ -n "$args" ]]; then
        docker-compose -f "$WATCHTOWER_COMPOSE" logs $args
    else
        docker-compose -f "$WATCHTOWER_COMPOSE" logs --tail=50
    fi
}

# 수동 업데이트 트리거
trigger_update() {
    print_status "수동 업데이트 트리거 실행 중..."
    
    if ! check_status &>/dev/null; then
        print_error "Watchtower가 실행되지 않았습니다. 먼저 시작하세요."
        exit 1
    fi
    
    # Watchtower에 SIGUSR1 신호 전송하여 즉시 업데이트 실행
    print_status "업데이트 신호 전송 중..."
    docker kill --signal=SIGUSR1 "$WATCHTOWER_CONTAINER"
    
    print_success "수동 업데이트가 트리거되었습니다"
    print_status "로그를 확인하여 업데이트 진행 상황을 모니터링하세요:"
    echo "  $0 logs -f"
}

# Watchtower 테스트
test_watchtower() {
    print_status "Watchtower 테스트 실행 중..."
    
    # 테스트용 임시 Watchtower 실행
    print_status "테스트 모드로 Watchtower 실행 중..."
    docker run --rm \
        -v /var/run/docker.sock:/var/run/docker.sock \
        containrrr/watchtower:latest \
        --cleanup \
        --run-once \
        --scope blacklist \
        --debug \
        blacklist blacklist-redis blacklist-postgresql
    
    print_success "Watchtower 테스트 완료"
}

# 설정 확인
show_config() {
    print_status "Watchtower 설정 정보:"
    
    # 환경 변수 확인
    local interval="${WATCHTOWER_INTERVAL:-300}"
    local notifications="${WATCHTOWER_NOTIFICATIONS:-disabled}"
    local debug="${WATCHTOWER_DEBUG:-false}"
    
    echo "  📊 업데이트 간격: ${interval}초 ($(($interval / 60))분)"
    echo "  🔔 알림: $notifications"
    echo "  🐛 디버그 모드: $debug"
    echo "  🏷️  스코프: blacklist"
    echo "  🧹 자동 정리: 활성화"
    echo ""
    
    # Registry 설정 확인
    if [[ -n "${REGISTRY_USERNAME:-}" ]]; then
        echo "  🔐 Registry 인증: 설정됨 (${REGISTRY_USERNAME})"
    else
        print_warning "Registry 인증이 설정되지 않았습니다"
    fi
    
    # 슬랙 알림 설정 확인
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        echo "  💬 Slack 알림: 설정됨"
    else
        echo "  💬 Slack 알림: 비활성화"
    fi
}

# 메인 로직
main() {
    case "${1:-}" in
        "start")
            start_watchtower
            ;;
        "stop")
            stop_watchtower
            ;;
        "restart")
            restart_watchtower
            ;;
        "status")
            check_status
            echo ""
            show_config
            ;;
        "logs")
            show_logs "$@"
            ;;
        "update")
            trigger_update
            ;;
        "test")
            test_watchtower
            ;;
        "config")
            show_config
            ;;
        *)
            show_usage
            exit 0
            ;;
    esac
}

# 스크립트 실행
main "$@"