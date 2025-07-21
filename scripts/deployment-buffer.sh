#!/bin/bash
# 배포 버퍼링 및 큐 관리 시스템

set -e

# 설정
DEPLOYMENT_QUEUE="/tmp/blacklist-deployment-queue"
DEPLOYMENT_LOCK="/tmp/blacklist-deployment.lock"
DEPLOYMENT_LOG="/tmp/blacklist-deployment.log"
MAX_CONCURRENT_DEPLOYMENTS=1
DEPLOYMENT_COOLDOWN=60  # 배포 간 최소 대기 시간 (초)
LAST_DEPLOYMENT_FILE="/tmp/blacklist-last-deployment"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 로깅 함수
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date +'%Y-%m-%d %H:%M:%S')
    echo -e "${BLUE}[$timestamp]${NC} ${level}: $message"
    echo "[$timestamp] ${level}: $message" >> "$DEPLOYMENT_LOG"
}

error() {
    log "ERROR" "${RED}$@${NC}"
    exit 1
}

success() {
    log "SUCCESS" "${GREEN}$@${NC}"
}

warning() {
    log "WARNING" "${YELLOW}$@${NC}"
}

info() {
    log "INFO" "$@"
}

# 큐 초기화
init_queue() {
    mkdir -p $(dirname "$DEPLOYMENT_QUEUE")
    touch "$DEPLOYMENT_QUEUE"
    touch "$DEPLOYMENT_LOG"
}

# 배포 잠금 획득
acquire_lock() {
    local timeout=${1:-300}  # 기본 5분 타임아웃
    local elapsed=0
    
    while [ $elapsed -lt $timeout ]; do
        if mkdir "$DEPLOYMENT_LOCK" 2>/dev/null; then
            echo $$ > "$DEPLOYMENT_LOCK/pid"
            info "배포 잠금 획득 (PID: $$)"
            return 0
        fi
        
        # 기존 잠금 확인
        if [ -f "$DEPLOYMENT_LOCK/pid" ]; then
            local lock_pid=$(cat "$DEPLOYMENT_LOCK/pid" 2>/dev/null || echo "unknown")
            if ! kill -0 "$lock_pid" 2>/dev/null; then
                warning "이전 배포 프로세스가 종료됨. 잠금 해제 중..."
                release_lock
                continue
            fi
            info "다른 배포가 진행 중입니다 (PID: $lock_pid). 대기 중..."
        fi
        
        sleep 5
        elapsed=$((elapsed + 5))
    done
    
    error "배포 잠금 획득 실패 (타임아웃)"
}

# 배포 잠금 해제
release_lock() {
    if [ -d "$DEPLOYMENT_LOCK" ]; then
        rm -rf "$DEPLOYMENT_LOCK"
        info "배포 잠금 해제"
    fi
}

# 쿨다운 확인
check_cooldown() {
    if [ -f "$LAST_DEPLOYMENT_FILE" ]; then
        local last_deployment=$(cat "$LAST_DEPLOYMENT_FILE")
        local current_time=$(date +%s)
        local elapsed=$((current_time - last_deployment))
        
        if [ $elapsed -lt $DEPLOYMENT_COOLDOWN ]; then
            local remaining=$((DEPLOYMENT_COOLDOWN - elapsed))
            warning "최근 배포 후 쿨다운 중. ${remaining}초 대기 필요"
            sleep $remaining
        fi
    fi
}

# 배포 큐에 추가
enqueue_deployment() {
    local version=$1
    local environment=$2
    local priority=${3:-normal}
    local deployment_id=$(date +%s)-$$
    
    local entry="${deployment_id}|${version}|${environment}|${priority}|$(date +'%Y-%m-%d %H:%M:%S')"
    echo "$entry" >> "$DEPLOYMENT_QUEUE"
    
    info "배포 큐에 추가됨: ID=$deployment_id, Version=$version, Env=$environment, Priority=$priority"
    echo "$deployment_id"
}

# 다음 배포 가져오기
dequeue_deployment() {
    if [ ! -s "$DEPLOYMENT_QUEUE" ]; then
        return 1
    fi
    
    # 우선순위별 정렬 (high > normal > low)
    local next_deployment=$(sort -t'|' -k4,4r -k1,1 "$DEPLOYMENT_QUEUE" | head -n1)
    
    if [ -n "$next_deployment" ]; then
        # 큐에서 제거
        grep -v "^$next_deployment$" "$DEPLOYMENT_QUEUE" > "$DEPLOYMENT_QUEUE.tmp" || true
        mv "$DEPLOYMENT_QUEUE.tmp" "$DEPLOYMENT_QUEUE"
        
        echo "$next_deployment"
        return 0
    fi
    
    return 1
}

# 큐 상태 확인
queue_status() {
    echo "=== 배포 큐 상태 ==="
    
    if [ ! -s "$DEPLOYMENT_QUEUE" ]; then
        echo "큐가 비어있습니다"
        return
    fi
    
    echo "대기 중인 배포:"
    echo "ID | Version | Environment | Priority | Queued Time"
    echo "---|---------|-------------|----------|------------"
    
    while IFS='|' read -r id version env priority time; do
        printf "%-10s | %-10s | %-11s | %-8s | %s\n" \
            "$id" "$version" "$env" "$priority" "$time"
    done < "$DEPLOYMENT_QUEUE"
    
    local count=$(wc -l < "$DEPLOYMENT_QUEUE")
    echo ""
    echo "총 ${count}개의 배포 대기 중"
}

# 실제 배포 실행
execute_deployment() {
    local deployment_info=$1
    IFS='|' read -r id version environment priority queued_time <<< "$deployment_info"
    
    info "배포 시작: ID=$id, Version=$version, Environment=$environment"
    
    # 배포 전 검증
    if ! pre_deployment_check "$version" "$environment"; then
        error "배포 전 검증 실패"
        return 1
    fi
    
    # 실제 배포 명령
    case "$environment" in
        dev)
            deploy_to_dev "$version"
            ;;
        staging)
            deploy_to_staging "$version"
            ;;
        prod|production)
            deploy_to_production "$version"
            ;;
        *)
            error "알 수 없는 환경: $environment"
            return 1
            ;;
    esac
    
    # 배포 후 검증
    if ! post_deployment_check "$version" "$environment"; then
        error "배포 후 검증 실패. 롤백을 고려하세요."
        return 1
    fi
    
    # 마지막 배포 시간 기록
    date +%s > "$LAST_DEPLOYMENT_FILE"
    
    success "배포 완료: ID=$id, Version=$version, Environment=$environment"
    return 0
}

# 배포 전 검증
pre_deployment_check() {
    local version=$1
    local environment=$2
    
    info "배포 전 검증 중..."
    
    # 이미지 존재 확인
    if ! docker manifest inspect "registry.jclee.me/blacklist:$version" &>/dev/null; then
        error "Docker 이미지를 찾을 수 없습니다: $version"
        return 1
    fi
    
    # 환경별 추가 검증
    case "$environment" in
        prod|production)
            # 프로덕션은 추가 검증
            if ! check_production_readiness; then
                return 1
            fi
            ;;
    esac
    
    success "배포 전 검증 통과"
    return 0
}

# 배포 후 검증
post_deployment_check() {
    local version=$1
    local environment=$2
    
    info "배포 후 검증 중..."
    
    # 헬스체크
    local health_endpoint=""
    case "$environment" in
        dev)
            health_endpoint="http://localhost:8541/health"
            ;;
        staging)
            health_endpoint="http://staging.blacklist.local/health"
            ;;
        prod|production)
            health_endpoint="https://blacklist.jclee.me/health"
            ;;
    esac
    
    # 헬스체크 재시도
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        attempt=$((attempt + 1))
        
        if curl -f "$health_endpoint" --connect-timeout 5 --max-time 10 &>/dev/null; then
            success "헬스체크 성공 (시도 $attempt/$max_attempts)"
            return 0
        fi
        
        warning "헬스체크 실패 (시도 $attempt/$max_attempts)"
        sleep 10
    done
    
    error "헬스체크 최종 실패"
    return 1
}

# 환경별 배포 함수
deploy_to_dev() {
    local version=$1
    info "개발 환경 배포: $version"
    
    kubectl set image deployment/blacklist-dev \
        blacklist=registry.jclee.me/blacklist:$version \
        -n blacklist-dev || return 1
    
    kubectl rollout status deployment/blacklist-dev \
        -n blacklist-dev \
        --timeout=300s || return 1
}

deploy_to_staging() {
    local version=$1
    info "스테이징 환경 배포: $version"
    
    kubectl set image deployment/blacklist-staging \
        blacklist=registry.jclee.me/blacklist:$version \
        -n blacklist-staging || return 1
    
    kubectl rollout status deployment/blacklist-staging \
        -n blacklist-staging \
        --timeout=300s || return 1
}

deploy_to_production() {
    local version=$1
    info "프로덕션 환경 배포: $version"
    
    # ArgoCD를 통한 배포
    if command -v argocd &>/dev/null; then
        argocd app set blacklist-prod \
            -p image.tag=$version \
            --grpc-web || return 1
        
        argocd app sync blacklist-prod \
            --grpc-web \
            --timeout 300 || return 1
    else
        kubectl set image deployment/blacklist \
            blacklist=registry.jclee.me/blacklist:$version \
            -n blacklist || return 1
        
        kubectl rollout status deployment/blacklist \
            -n blacklist \
            --timeout=300s || return 1
    fi
}

# 프로덕션 준비 상태 확인
check_production_readiness() {
    info "프로덕션 배포 준비 상태 확인..."
    
    # CPU/메모리 사용률 확인
    local cpu_usage=$(kubectl top nodes --no-headers | awk '{sum+=$3} END {print sum/NR}' | cut -d'%' -f1)
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        error "CPU 사용률이 너무 높습니다: ${cpu_usage}%"
        return 1
    fi
    
    # 현재 Pod 상태 확인
    local unhealthy_pods=$(kubectl get pods -n blacklist --no-headers | grep -v Running | wc -l)
    if [ $unhealthy_pods -gt 0 ]; then
        error "비정상 Pod가 있습니다: $unhealthy_pods개"
        return 1
    fi
    
    success "프로덕션 배포 준비 완료"
    return 0
}

# 배포 워커 (백그라운드 실행용)
deployment_worker() {
    info "배포 워커 시작 (PID: $$)"
    
    while true; do
        # 큐에서 다음 배포 가져오기
        if deployment=$(dequeue_deployment); then
            # 잠금 획득
            if acquire_lock; then
                # 쿨다운 확인
                check_cooldown
                
                # 배포 실행
                if execute_deployment "$deployment"; then
                    success "배포 작업 완료"
                else
                    error "배포 작업 실패"
                fi
                
                # 잠금 해제
                release_lock
            fi
        else
            # 큐가 비어있으면 대기
            sleep 30
        fi
    done
}

# 메인 함수
main() {
    local command=$1
    shift
    
    init_queue
    
    case "$command" in
        enqueue)
            # 배포 큐에 추가
            if [ $# -lt 2 ]; then
                error "사용법: $0 enqueue <version> <environment> [priority]"
            fi
            enqueue_deployment "$@"
            ;;
        
        status)
            # 큐 상태 확인
            queue_status
            ;;
        
        worker)
            # 배포 워커 시작
            deployment_worker
            ;;
        
        execute)
            # 즉시 배포 (큐 무시)
            if [ $# -lt 2 ]; then
                error "사용법: $0 execute <version> <environment>"
            fi
            
            if acquire_lock; then
                check_cooldown
                execute_deployment "manual|$1|$2|high|$(date +'%Y-%m-%d %H:%M:%S')"
                release_lock
            fi
            ;;
        
        clear)
            # 큐 비우기
            > "$DEPLOYMENT_QUEUE"
            success "배포 큐가 비워졌습니다"
            ;;
        
        *)
            echo "사용법: $0 {enqueue|status|worker|execute|clear} [options]"
            echo ""
            echo "Commands:"
            echo "  enqueue <version> <env> [priority]  - 배포 큐에 추가"
            echo "  status                              - 큐 상태 확인"
            echo "  worker                              - 배포 워커 시작"
            echo "  execute <version> <env>             - 즉시 배포"
            echo "  clear                               - 큐 비우기"
            exit 1
            ;;
    esac
}

# Trap으로 정리 작업 등록
trap 'release_lock' EXIT

# 실행
main "$@"