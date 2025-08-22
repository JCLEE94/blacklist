#!/bin/bash
# Docker Management Script for Blacklist - Optimized v1.0.37
# 통합 Docker 환경 관리 도구

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# 출력 함수들
print_header() { echo -e "${PURPLE}🚀 $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# 환경 변수
COMPOSE_FILES=("docker-compose.yml")
CURRENT_ENV=""
PROFILES=""

# 현재 환경 확인
check_current_env() {
    if [[ -L ".env" ]]; then
        CURRENT_ENV=$(readlink .env | sed 's/\.env\.//')
    else
        CURRENT_ENV="custom"
    fi
}

# 사용법 출력
show_usage() {
    print_header "Blacklist Docker 통합 관리 도구 v1.0.37"
    echo ""
    echo "사용법: $0 [명령] [옵션]"
    echo ""
    echo "🏗️  기본 명령어:"
    echo "  start         - 서비스 시작"
    echo "  stop          - 서비스 중지"
    echo "  restart       - 서비스 재시작"
    echo "  status        - 서비스 상태 확인"
    echo "  logs          - 로그 확인"
    echo "  clean         - 정리 작업"
    echo ""
    echo "🚀 고급 명령어:"
    echo "  deploy        - 전체 배포 (성능 최적화 포함)"
    echo "  monitor       - 모니터링 시작"
    echo "  performance   - 성능 모드로 시작"
    echo "  health        - 전체 헬스체크"
    echo "  backup        - 데이터 백업"
    echo "  restore       - 데이터 복원"
    echo ""
    echo "🔧 관리 명령어:"
    echo "  env [환경]    - 환경 전환 (production/development/local)"
    echo "  volumes       - 볼륨 관리"
    echo "  watchtower    - Watchtower 관리"
    echo "  update        - 이미지 업데이트"
    echo ""
    check_current_env
    echo "현재 환경: $CURRENT_ENV"
    echo ""
    echo "🔥 빠른 시작:"
    echo "  $0 deploy production  # 운영 환경 전체 배포"
    echo "  $0 start development  # 개발 환경 시작"
    echo "  $0 monitor           # 모니터링 포함 시작"
}

# 환경 파일 설정
setup_env_files() {
    local env=${1:-production}
    
    if [[ -f ".env.$env" ]]; then
        COMPOSE_FILES=("docker-compose.yml" "--env-file" ".env.$env")
        print_info "환경 파일 사용: .env.$env"
    else
        print_warning "환경 파일이 없습니다: .env.$env"
        COMPOSE_FILES=("docker-compose.yml")
    fi
}

# Compose 명령 실행
run_compose() {
    local cmd="$1"
    shift
    
    print_info "Docker Compose 명령 실행: $cmd"
    
    if [[ -n "$PROFILES" ]]; then
        docker-compose "${COMPOSE_FILES[@]}" --profile "$PROFILES" "$cmd" "$@"
    else
        docker-compose "${COMPOSE_FILES[@]}" "$cmd" "$@"
    fi
}

# 서비스 시작
start_services() {
    local env=${1:-production}
    local mode=${2:-normal}
    
    print_header "Blacklist 서비스 시작"
    print_info "환경: $env, 모드: $mode"
    
    setup_env_files "$env"
    
    # 환경별 추가 설정
    case $mode in
        "performance"|"prod")
            print_info "성능 최적화 모드로 시작"
            COMPOSE_FILES+=("-f" "docker-compose.performance.yml")
            ;;
        "monitoring")
            print_info "모니터링 포함 모드로 시작"
            PROFILES="monitoring"
            COMPOSE_FILES+=("-f" "docker-compose.performance.yml")
            ;;
        "watchtower")
            print_info "Watchtower 포함 모드로 시작"
            PROFILES="watchtower"
            ;;
    esac
    
    # 네트워크 생성 (존재하지 않을 경우)
    if ! docker network ls | grep -q "blacklist-network"; then
        print_info "blacklist-network 생성 중..."
        docker network create blacklist-network
    fi
    
    # 서비스 시작
    run_compose "up" "-d"
    
    # 시작 확인
    sleep 5
    check_health
    
    print_success "서비스가 성공적으로 시작되었습니다"
    show_access_info "$env"
}

# 서비스 중지
stop_services() {
    print_header "Blacklist 서비스 중지"
    
    # 모든 관련 compose 파일로 중지 시도
    docker-compose down 2>/dev/null || true
    docker-compose -f docker-compose.performance.yml down 2>/dev/null || true
    docker-compose -f docker-compose.watchtower.yml down 2>/dev/null || true
    
    print_success "모든 서비스가 중지되었습니다"
}

# 서비스 상태 확인
check_status() {
    print_header "Blacklist 서비스 상태"
    
    echo "🐳 Docker 컨테이너:"
    docker ps --filter "name=blacklist" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    echo ""
    echo "💾 Docker 볼륨:"
    docker volume ls | grep blacklist | head -10
    
    echo ""
    echo "🌐 Docker 네트워크:"
    docker network ls | grep blacklist
}

# 헬스체크
check_health() {
    print_header "헬스체크 실행"
    
    local services=("blacklist" "blacklist-redis" "blacklist-postgresql")
    local healthy=0
    local total=${#services[@]}
    
    for service in "${services[@]}"; do
        if docker ps --filter "name=$service" --filter "status=running" | grep -q "$service"; then
            local health=$(docker inspect --format='{{.State.Health.Status}}' "$service" 2>/dev/null || echo "unknown")
            case $health in
                "healthy")
                    print_success "$service: 정상"
                    ((healthy++))
                    ;;
                "unhealthy")
                    print_error "$service: 비정상"
                    ;;
                "starting")
                    print_warning "$service: 시작 중"
                    ;;
                *)
                    print_warning "$service: 헬스체크 없음"
                    ((healthy++))  # 헬스체크가 없는 경우 정상으로 간주
                    ;;
            esac
        else
            print_error "$service: 실행되지 않음"
        fi
    done
    
    echo ""
    if [[ $healthy -eq $total ]]; then
        print_success "전체 서비스 정상 ($healthy/$total)"
    else
        print_warning "일부 서비스 이상 ($healthy/$total)"
    fi
}

# 접속 정보 출력
show_access_info() {
    local env=${1:-production}
    
    print_header "접속 정보"
    
    case $env in
        "production")
            echo "🌐 웹 인터페이스: http://localhost:32542"
            echo "🗄️  PostgreSQL: localhost:32543"
            echo "📊 API: http://localhost:32542/api/health"
            ;;
        "development"|"local")
            echo "🌐 웹 인터페이스: http://localhost:2542"
            echo "🗄️  PostgreSQL: localhost:5432"
            echo "📊 API: http://localhost:2542/api/health"
            ;;
    esac
    
    if docker ps --filter "name=blacklist-prometheus" | grep -q "Up"; then
        echo "📈 Prometheus: http://localhost:9090"
    fi
    
    if docker ps --filter "name=blacklist-grafana" | grep -q "Up"; then
        echo "📊 Grafana: http://localhost:3000"
    fi
}

# 로그 확인
show_logs() {
    local service=${1:-blacklist}
    local args=("${@:2}")
    
    print_info "로그 확인: $service"
    
    if [[ ${#args[@]} -eq 0 ]]; then
        args=("--tail=50")
    fi
    
    docker-compose logs "${args[@]}" "$service"
}

# 전체 배포
deploy_full() {
    local env=${1:-production}
    
    print_header "Blacklist 전체 배포 시작"
    
    # 이미지 업데이트
    print_info "최신 이미지 가져오는 중..."
    setup_env_files "$env"
    run_compose "pull"
    
    # 기존 서비스 중지
    stop_services
    
    # 볼륨 정리 (선택적)
    read -p "볼륨을 정리하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ./scripts/cleanup-volumes.sh
    fi
    
    # 성능 모드로 시작
    start_services "$env" "performance"
    
    # Watchtower 시작 (운영 환경)
    if [[ "$env" == "production" ]]; then
        print_info "Watchtower 시작 중..."
        ./scripts/manage-watchtower.sh start
    fi
    
    print_success "전체 배포가 완료되었습니다"
}

# 모니터링 시작
start_monitoring() {
    print_header "모니터링 시스템 시작"
    start_services "production" "monitoring"
}

# 데이터 백업
backup_data() {
    local backup_dir="./backups/$(date +%Y%m%d_%H%M%S)"
    
    print_header "데이터 백업 시작"
    print_info "백업 위치: $backup_dir"
    
    mkdir -p "$backup_dir"
    
    # PostgreSQL 백업
    if docker ps --filter "name=blacklist-postgresql" | grep -q "Up"; then
        print_info "PostgreSQL 백업 중..."
        docker exec blacklist-postgresql pg_dump -U blacklist_user blacklist > "$backup_dir/postgresql_backup.sql"
        print_success "PostgreSQL 백업 완료"
    fi
    
    # Redis 백업
    if docker ps --filter "name=blacklist-redis" | grep -q "Up"; then
        print_info "Redis 백업 중..."
        docker exec blacklist-redis redis-cli BGSAVE
        sleep 5
        docker cp blacklist-redis:/data/dump.rdb "$backup_dir/redis_dump.rdb"
        print_success "Redis 백업 완료"
    fi
    
    # 애플리케이션 데이터 백업
    print_info "애플리케이션 데이터 백업 중..."
    docker run --rm \
        -v blacklist-data:/source \
        -v "$PWD/$backup_dir":/backup \
        alpine:latest \
        tar czf /backup/app_data.tar.gz -C /source .
    
    print_success "데이터 백업이 완료되었습니다: $backup_dir"
}

# 메인 로직
main() {
    case "${1:-}" in
        "start")
            start_services "${2:-production}" "${3:-normal}"
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            stop_services
            sleep 3
            start_services "${2:-production}" "${3:-normal}"
            ;;
        "status")
            check_status
            ;;
        "logs")
            show_logs "${@:2}"
            ;;
        "deploy")
            deploy_full "${2:-production}"
            ;;
        "monitor")
            start_monitoring
            ;;
        "performance")
            start_services "${2:-production}" "performance"
            ;;
        "health")
            check_health
            ;;
        "backup")
            backup_data
            ;;
        "env")
            ./scripts/switch-env.sh "${2:-production}"
            ;;
        "volumes")
            ./scripts/cleanup-volumes.sh
            ;;
        "watchtower")
            ./scripts/manage-watchtower.sh "${@:2}"
            ;;
        "update")
            setup_env_files "${2:-production}"
            run_compose "pull"
            print_success "이미지 업데이트 완료"
            ;;
        "clean")
            stop_services
            docker system prune -f
            docker volume prune -f
            print_success "정리 완료"
            ;;
        *)
            show_usage
            ;;
    esac
}

# 스크립트 실행
main "$@"