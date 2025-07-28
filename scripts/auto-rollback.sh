#!/bin/bash

# 자동 롤백 스크립트
# 배포 실패 또는 헬스체크 실패 시 이전 안정 버전으로 자동 롤백

echo "🔄 자동 롤백 시스템"
echo "=================="
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# 설정
NAMESPACE="blacklist"
APP_NAME="blacklist"
ARGOCD_SERVER="${ARGOCD_SERVER:-argo.jclee.me}"
HEALTH_CHECK_RETRIES=3
HEALTH_CHECK_DELAY=30
ROLLBACK_TIMEOUT=300

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_argocd() {
    echo -e "${PURPLE}[ARGOCD]${NC} $1"
}

show_usage() {
    echo "사용법: $0 [options]"
    echo ""
    echo "옵션:"
    echo "  --check-health        현재 배포 상태 헬스체크 수행"
    echo "  --force-rollback      강제 롤백 실행"
    echo "  --to-revision REV     특정 리비전으로 롤백"
    echo "  --dry-run            실제 실행 없이 명령어만 출력"
    echo "  --help               도움말 표시"
    echo ""
    echo "예시:"
    echo "  $0 --check-health              # 헬스체크 후 필요시 롤백"
    echo "  $0 --force-rollback           # 즉시 롤백"
    echo "  $0 --to-revision abc123       # 특정 리비전으로 롤백"
    echo "  $0 --dry-run --force-rollback # 롤백 시뮬레이션"
}

# 현재 배포 정보 수집
get_current_deployment_info() {
    print_step "현재 배포 정보 수집 중..."
    
    # Kubernetes 배포 정보
    local deployment_info
    if deployment_info=$(kubectl get deployment $APP_NAME -n $NAMESPACE -o json 2>/dev/null); then
        CURRENT_IMAGE=$(echo "$deployment_info" | jq -r '.spec.template.spec.containers[0].image')
        CURRENT_REPLICAS=$(echo "$deployment_info" | jq -r '.spec.replicas')
        READY_REPLICAS=$(echo "$deployment_info" | jq -r '.status.readyReplicas // 0')
        
        echo "현재 이미지: $CURRENT_IMAGE"
        echo "레플리카: $READY_REPLICAS/$CURRENT_REPLICAS"
    else
        print_error "배포 정보를 가져올 수 없습니다"
        return 1
    fi
    
    # ArgoCD 애플리케이션 정보
    local app_info
    if app_info=$(argocd app get $APP_NAME --server $ARGOCD_SERVER --grpc-web -o json 2>/dev/null); then
        CURRENT_REVISION=$(echo "$app_info" | jq -r '.status.sync.revision[0:7] // "Unknown"')
        HEALTH_STATUS=$(echo "$app_info" | jq -r '.status.health.status // "Unknown"')
        SYNC_STATUS=$(echo "$app_info" | jq -r '.status.sync.status // "Unknown"')
        
        echo "현재 리비전: $CURRENT_REVISION"
        echo "Health 상태: $HEALTH_STATUS"
        echo "Sync 상태: $SYNC_STATUS"
    else
        print_warning "ArgoCD 애플리케이션 정보를 가져올 수 없습니다"
        CURRENT_REVISION="Unknown"
        HEALTH_STATUS="Unknown"
        SYNC_STATUS="Unknown"
    fi
    
    echo ""
    return 0
}

# 이전 안정 버전 정보 조회
get_previous_stable_version() {
    print_step "이전 안정 버전 조회 중..."
    
    # ArgoCD 이력에서 이전 버전 찾기
    local app_history
    if app_history=$(argocd app history $APP_NAME --server $ARGOCD_SERVER --grpc-web -o json 2>/dev/null); then
        # 현재 리비전이 아닌 가장 최근 리비전 찾기
        PREVIOUS_REVISION=$(echo "$app_history" | jq -r --arg current "$CURRENT_REVISION" \
            '[.[] | select(.revision[0:7] != $current)][0].revision[0:7] // "None"')
        
        if [ "$PREVIOUS_REVISION" != "None" ]; then
            print_success "이전 안정 버전 발견: $PREVIOUS_REVISION"
            
            # 해당 리비전의 상세 정보
            PREVIOUS_DEPLOYED_AT=$(echo "$app_history" | jq -r --arg rev "$PREVIOUS_REVISION" \
                '.[] | select(.revision[0:7] == $rev) | .deployedAt // "Unknown"')
            
            echo "배포 시간: $PREVIOUS_DEPLOYED_AT"
        else
            print_warning "이전 안정 버전을 찾을 수 없습니다"
            return 1
        fi
    else
        print_warning "ArgoCD 이력을 조회할 수 없습니다. Kubernetes 롤백을 시도합니다."
        
        # Kubernetes 롤아웃 이력 확인
        local k8s_history
        if k8s_history=$(kubectl rollout history deployment/$APP_NAME -n $NAMESPACE 2>/dev/null); then
            PREVIOUS_K8S_REVISION=$(echo "$k8s_history" | tail -2 | head -1 | awk '{print $1}')
            if [ -n "$PREVIOUS_K8S_REVISION" ]; then
                print_success "Kubernetes 이전 리비전 발견: $PREVIOUS_K8S_REVISION"
            else
                print_error "롤백 가능한 이전 버전이 없습니다"
                return 1
            fi
        else
            print_error "Kubernetes 배포 이력을 조회할 수 없습니다"
            return 1
        fi
    fi
    
    echo ""
    return 0
}

# 애플리케이션 헬스체크
check_application_health() {
    print_step "애플리케이션 헬스체크 실행 중..."
    
    # NodePort 확인
    local node_port
    node_port=$(kubectl get service $APP_NAME -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null)
    
    if [ -z "$node_port" ]; then
        print_error "서비스 NodePort를 찾을 수 없습니다"
        return 1
    fi
    
    print_step "헬스체크 대상: localhost:$node_port"
    
    local retry_count=0
    local health_passed=false
    
    while [ $retry_count -lt $HEALTH_CHECK_RETRIES ]; do
        echo "헬스체크 시도 $((retry_count + 1))/$HEALTH_CHECK_RETRIES..."
        
        # Pod 준비 상태 확인
        local ready_pods
        ready_pods=$(kubectl get pods -n $NAMESPACE -l app=$APP_NAME -o json | \
            jq '[.items[] | select(.status.phase == "Running" and .status.conditions[] | select(.type == "Ready" and .status == "True"))] | length')
        
        echo "  - 준비된 Pod: $ready_pods개"
        
        # HTTP 헬스체크
        local http_status
        http_status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 --max-time 30 \
            "http://localhost:$node_port/health" 2>/dev/null || echo "000")
        
        echo "  - HTTP 상태: $http_status"
        
        # 핵심 API 테스트
        local api_status
        api_status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 --max-time 30 \
            "http://localhost:$node_port/api/stats" 2>/dev/null || echo "000")
        
        echo "  - API 상태: $api_status"
        
        # 헬스체크 통과 조건
        if [ "$ready_pods" -ge 1 ] && [ "$http_status" = "200" ] && [ "$api_status" = "200" ]; then
            print_success "헬스체크 통과!"
            health_passed=true
            break
        fi
        
        # 다음 시도 전 대기
        if [ $retry_count -lt $((HEALTH_CHECK_RETRIES - 1)) ]; then
            print_warning "헬스체크 실패. ${HEALTH_CHECK_DELAY}초 후 재시도..."
            sleep $HEALTH_CHECK_DELAY
        fi
        
        retry_count=$((retry_count + 1))
    done
    
    if [ "$health_passed" = false ]; then
        print_error "헬스체크 최종 실패"
        return 1
    fi
    
    echo ""
    return 0
}

# 롤백 실행
execute_rollback() {
    local target_revision="$1"
    
    print_step "롤백 실행 중..."
    
    if [ "$DRY_RUN" = "true" ]; then
        echo "DRY RUN - 실행될 명령어들:"
        if [ -n "$target_revision" ]; then
            echo "  argocd app rollback $APP_NAME $target_revision --server $ARGOCD_SERVER --grpc-web"
        else
            echo "  argocd app rollback $APP_NAME --server $ARGOCD_SERVER --grpc-web"
            echo "  kubectl rollout undo deployment/$APP_NAME -n $NAMESPACE"
        fi
        return 0
    fi
    
    local rollback_success=false
    
    # ArgoCD 롤백 시도
    if [ -n "$target_revision" ] && [ "$target_revision" != "Unknown" ] && [ "$target_revision" != "None" ]; then
        print_argocd "ArgoCD를 통한 리비전 $target_revision 롤백 시도..."
        
        if argocd app rollback $APP_NAME "$target_revision" --server $ARGOCD_SERVER --grpc-web --timeout $ROLLBACK_TIMEOUT; then
            print_success "ArgoCD 롤백 명령 성공"
            rollback_success=true
        else
            print_warning "ArgoCD 롤백 실패"
        fi
    fi
    
    # ArgoCD 롤백 실패 시 Kubernetes 직접 롤백
    if [ "$rollback_success" = false ]; then
        print_step "Kubernetes 직접 롤백 시도..."
        
        if kubectl rollout undo deployment/$APP_NAME -n $NAMESPACE; then
            print_success "Kubernetes 롤백 명령 성공"
            rollback_success=true
        else
            print_error "Kubernetes 롤백도 실패"
            return 1
        fi
    fi
    
    if [ "$rollback_success" = true ]; then
        # 롤백 완료 대기
        print_step "롤백 완료 대기 중..."
        if kubectl rollout status deployment/$APP_NAME -n $NAMESPACE --timeout=${ROLLBACK_TIMEOUT}s; then
            print_success "롤백 완료"
        else
            print_error "롤백 타임아웃"
            return 1
        fi
        
        # 롤백 후 헬스체크
        print_step "롤백 후 헬스체크..."
        sleep 30  # 서비스 안정화 대기
        
        if check_application_health; then
            print_success "롤백 성공 - 서비스 정상화됨"
            return 0
        else
            print_error "롤백 완료되었으나 서비스가 여전히 비정상"
            return 1
        fi
    fi
    
    return 1
}

# 롤백 상세 정보 생성
generate_rollback_report() {
    print_step "롤백 보고서 생성 중..."
    
    local report_file="rollback-report-$(date +%Y%m%d-%H%M%S).json"
    
    cat > "$report_file" <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "rollback_trigger": "$ROLLBACK_TRIGGER",
    "previous_state": {
        "image": "$CURRENT_IMAGE",
        "revision": "$CURRENT_REVISION",
        "health_status": "$HEALTH_STATUS",
        "sync_status": "$SYNC_STATUS",
        "ready_replicas": "$READY_REPLICAS",
        "total_replicas": "$CURRENT_REPLICAS"
    },
    "rollback_target": {
        "revision": "$PREVIOUS_REVISION",
        "deployed_at": "$PREVIOUS_DEPLOYED_AT"
    },
    "rollback_result": {
        "success": $ROLLBACK_SUCCESS,
        "method": "$ROLLBACK_METHOD",
        "duration_seconds": $ROLLBACK_DURATION
    },
    "post_rollback_health": {
        "health_check_passed": $POST_ROLLBACK_HEALTH
    }
}
EOF
    
    echo "롤백 보고서: $report_file"
    echo ""
}

# 메인 실행 로직
main() {
    # 인자 파싱
    CHECK_HEALTH="false"
    FORCE_ROLLBACK="false"
    TARGET_REVISION=""
    DRY_RUN="false"
    ROLLBACK_TRIGGER="manual"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --check-health)
                CHECK_HEALTH="true"
                ROLLBACK_TRIGGER="health_check"
                shift
                ;;
            --force-rollback)
                FORCE_ROLLBACK="true"
                ROLLBACK_TRIGGER="forced"
                shift
                ;;
            --to-revision)
                TARGET_REVISION="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                print_error "알 수 없는 옵션: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # 기본 동작 설정
    if [ "$CHECK_HEALTH" = "false" ] && [ "$FORCE_ROLLBACK" = "false" ]; then
        CHECK_HEALTH="true"  # 기본적으로 헬스체크 먼저 수행
    fi
    
    echo "시작 시간: $(date)"
    echo "모드: $([ "$DRY_RUN" = "true" ] && echo "DRY RUN" || echo "실제 실행")"
    echo ""
    
    # 현재 배포 정보 수집
    if ! get_current_deployment_info; then
        print_error "현재 배포 정보를 가져올 수 없습니다"
        exit 1
    fi
    
    local rollback_needed=false
    local rollback_reason=""
    
    # 헬스체크 수행
    if [ "$CHECK_HEALTH" = "true" ]; then
        if check_application_health; then
            print_success "현재 배포가 정상 상태입니다"
            
            if [ "$FORCE_ROLLBACK" = "false" ]; then
                echo "롤백이 필요하지 않습니다."
                exit 0
            fi
        else
            print_error "헬스체크 실패 - 롤백이 필요합니다"
            rollback_needed=true
            rollback_reason="health_check_failed"
        fi
    fi
    
    # 강제 롤백 또는 헬스체크 실패 시 롤백 수행
    if [ "$FORCE_ROLLBACK" = "true" ] || [ "$rollback_needed" = "true" ]; then
        # 타겟 리비전 설정
        if [ -z "$TARGET_REVISION" ]; then
            if ! get_previous_stable_version; then
                print_error "롤백 대상을 찾을 수 없습니다"
                exit 1
            fi
            TARGET_REVISION="$PREVIOUS_REVISION"
        fi
        
        print_step "롤백 실행 준비:"
        echo "  - 현재 상태: $HEALTH_STATUS ($CURRENT_REVISION)"
        echo "  - 롤백 대상: $TARGET_REVISION"
        echo "  - 롤백 이유: $rollback_reason"
        echo ""
        
        # 사용자 확인 (강제 모드가 아닌 경우)
        if [ "$FORCE_ROLLBACK" = "false" ] && [ "$DRY_RUN" = "false" ]; then
            read -p "롤백을 진행하시겠습니까? (y/N): " confirm
            if [[ ! $confirm =~ ^[Yy]$ ]]; then
                echo "롤백이 취소되었습니다."
                exit 0
            fi
        fi
        
        # 롤백 실행
        local start_time=$(date +%s)
        ROLLBACK_SUCCESS=false
        ROLLBACK_METHOD="argocd"
        
        if execute_rollback "$TARGET_REVISION"; then
            ROLLBACK_SUCCESS=true
            POST_ROLLBACK_HEALTH=true
        else
            ROLLBACK_SUCCESS=false
            POST_ROLLBACK_HEALTH=false
        fi
        
        local end_time=$(date +%s)
        ROLLBACK_DURATION=$((end_time - start_time))
        
        # 보고서 생성
        generate_rollback_report
        
        if [ "$ROLLBACK_SUCCESS" = true ]; then
            print_success "롤백 작업 완료"
            exit 0
        else
            print_error "롤백 작업 실패"
            exit 1
        fi
    fi
}

# 스크립트 실행
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi