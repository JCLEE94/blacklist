#!/bin/bash

# CI/CD GitOps 파이프라인 전체 상태 확인 스크립트
# 모든 구성 요소의 상태를 종합적으로 점검하고 문제 해결 방안 제시

echo "🔍 CI/CD GitOps 파이프라인 상태 점검"
echo "==================================="
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# 설정값
NAMESPACE="blacklist"
APP_NAME="blacklist"
ARGOCD_SERVER="${ARGOCD_SERVER:-argo.jclee.me}"
REGISTRY="registry.jclee.me"
IMAGE_NAME="jclee94/blacklist"
GITHUB_REPO="JCLEE94/blacklist"

# 전역 상태 변수
declare -A STATUS_CHECKS
declare -A STATUS_MESSAGES
OVERALL_SCORE=0
MAX_SCORE=0

print_header() {
    echo -e "${WHITE}=== $1 ===${NC}"
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

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_argocd() {
    echo -e "${PURPLE}🚀 [ArgoCD] $1${NC}"
}

print_github() {
    echo -e "${CYAN}📦 [GitHub] $1${NC}"
}

add_check() {
    local component="$1"
    local status="$2"  # pass/warn/fail
    local message="$3"
    local weight="${4:-10}"  # 기본 가중치 10
    
    STATUS_CHECKS["$component"]="$status"
    STATUS_MESSAGES["$component"]="$message"
    MAX_SCORE=$((MAX_SCORE + weight))
    
    case $status in
        "pass")
            OVERALL_SCORE=$((OVERALL_SCORE + weight))
            print_success "$component: $message"
            ;;
        "warn")
            OVERALL_SCORE=$((OVERALL_SCORE + weight/2))
            print_warning "$component: $message"
            ;;
        "fail")
            print_error "$component: $message"
            ;;
    esac
}

# 1. GitHub Repository & Actions 상태 확인
check_github_status() {
    print_header "GitHub Repository & Actions 상태"
    
    # GitHub CLI 확인
    if ! command -v gh &> /dev/null; then
        add_check "GitHub CLI" "warn" "GitHub CLI가 설치되지 않았습니다 (일부 기능 제한)" 5
    else
        add_check "GitHub CLI" "pass" "GitHub CLI 사용 가능" 5
        
        # 최근 워크플로우 실행 상태
        if recent_runs=$(gh run list --repo $GITHUB_REPO --limit 5 2>/dev/null); then
            local failed_runs=$(echo "$recent_runs" | grep -c "❌\|✗\|failure" || echo 0)
            local total_runs=$(echo "$recent_runs" | wc -l)
            
            if [ $failed_runs -eq 0 ]; then
                add_check "GitHub Actions" "pass" "최근 5개 워크플로우 모두 성공" 15
            elif [ $failed_runs -le 2 ]; then
                add_check "GitHub Actions" "warn" "$failed_runs/$total_runs 워크플로우 실패" 15
            else
                add_check "GitHub Actions" "fail" "$failed_runs/$total_runs 워크플로우 실패 (심각)" 15
            fi
            
            # 최근 실행 결과 표시
            echo "  최근 워크플로우 실행:"
            echo "$recent_runs" | head -3 | while read -r line; do
                if [[ $line =~ ✓ ]]; then
                    print_success "    $line"
                elif [[ $line =~ ✗ ]]; then
                    print_error "    $line"
                else
                    print_info "    $line"
                fi
            done
        else
            add_check "GitHub Actions" "warn" "워크플로우 상태 조회 불가" 15
        fi
    fi
    
    echo ""
}

# 2. Docker Registry 상태 확인
check_registry_status() {
    print_header "Docker Registry 상태"
    
    # Registry 연결 테스트
    if curl -s --connect-timeout 10 "http://$REGISTRY/v2/" > /dev/null 2>&1; then
        add_check "Registry Connection" "pass" "Registry 연결 성공 ($REGISTRY)" 10
        
        # 최근 이미지 확인
        if latest_tags=$(curl -s "http://$REGISTRY/v2/$IMAGE_NAME/tags/list" 2>/dev/null); then
            local tag_count=$(echo "$latest_tags" | jq '.tags | length' 2>/dev/null || echo 0)
            if [ "$tag_count" -gt 0 ]; then
                add_check "Image Repository" "pass" "$tag_count개 이미지 태그 존재" 10
                
                # latest 태그 확인
                if echo "$latest_tags" | jq -r '.tags[]' | grep -q "latest"; then
                    add_check "Latest Tag" "pass" "latest 태그 존재" 5
                else
                    add_check "Latest Tag" "warn" "latest 태그 없음" 5
                fi
            else
                add_check "Image Repository" "fail" "이미지 태그가 없습니다" 10
            fi
        else
            add_check "Image Repository" "warn" "이미지 목록 조회 실패" 10
        fi
    else
        add_check "Registry Connection" "fail" "Registry 연결 실패 ($REGISTRY)" 10
        add_check "Image Repository" "fail" "Registry 연결 불가로 확인 불가" 10
    fi
    
    echo ""
}

# 3. Kubernetes 클러스터 상태 확인
check_kubernetes_status() {
    print_header "Kubernetes 클러스터 상태"
    
    # kubectl 연결 확인
    if kubectl cluster-info &> /dev/null; then
        add_check "Kubernetes Connection" "pass" "클러스터 연결 성공" 15
        
        # 네임스페이스 확인
        if kubectl get namespace $NAMESPACE &> /dev/null; then
            add_check "Namespace" "pass" "네임스페이스 '$NAMESPACE' 존재" 5
        else
            add_check "Namespace" "fail" "네임스페이스 '$NAMESPACE' 없음" 5
        fi
        
        # 배포 상태 확인
        if deployment_info=$(kubectl get deployment $APP_NAME -n $NAMESPACE -o json 2>/dev/null); then
            local replicas=$(echo "$deployment_info" | jq -r '.spec.replicas')
            local ready_replicas=$(echo "$deployment_info" | jq -r '.status.readyReplicas // 0')
            local available_replicas=$(echo "$deployment_info" | jq -r '.status.availableReplicas // 0')
            
            if [ "$ready_replicas" -eq "$replicas" ] && [ "$available_replicas" -eq "$replicas" ]; then
                add_check "Deployment Status" "pass" "$ready_replicas/$replicas Pod 정상 실행 중" 15
            elif [ "$ready_replicas" -gt 0 ]; then
                add_check "Deployment Status" "warn" "$ready_replicas/$replicas Pod 실행 중 (일부 문제)" 15
            else
                add_check "Deployment Status" "fail" "실행 중인 Pod 없음" 15
            fi
            
            # 현재 이미지 정보
            local current_image=$(echo "$deployment_info" | jq -r '.spec.template.spec.containers[0].image')
            print_info "  현재 이미지: $current_image"
            
        else
            add_check "Deployment Status" "fail" "배포를 찾을 수 없음" 15
        fi
        
        # 서비스 상태 확인
        if service_info=$(kubectl get service $APP_NAME -n $NAMESPACE -o json 2>/dev/null); then
            local cluster_ip=$(echo "$service_info" | jq -r '.spec.clusterIP')
            local node_port=$(echo "$service_info" | jq -r '.spec.ports[0].nodePort // "N/A"')
            
            add_check "Service" "pass" "서비스 정상 (ClusterIP: $cluster_ip)" 10
            
            if [ "$node_port" != "N/A" ]; then
                print_info "  NodePort: $node_port"
            fi
        else
            add_check "Service" "fail" "서비스를 찾을 수 없음" 10
        fi
        
    else
        add_check "Kubernetes Connection" "fail" "클러스터 연결 실패" 15
        add_check "Namespace" "fail" "클러스터 연결 실패로 확인 불가" 5
        add_check "Deployment Status" "fail" "클러스터 연결 실패로 확인 불가" 15
        add_check "Service" "fail" "클러스터 연결 실패로 확인 불가" 10
    fi
    
    echo ""
}

# 4. ArgoCD 상태 확인
check_argocd_status() {
    print_header "ArgoCD GitOps 상태"
    
    # ArgoCD CLI 확인
    if ! command -v argocd &> /dev/null; then
        add_check "ArgoCD CLI" "warn" "ArgoCD CLI가 설치되지 않았습니다" 5
        add_check "ArgoCD Connection" "fail" "CLI 없음으로 연결 확인 불가" 10
        add_check "App Health" "fail" "CLI 없음으로 확인 불가" 15
        add_check "App Sync" "fail" "CLI 없음으로 확인 불가" 15
        return
    fi
    
    add_check "ArgoCD CLI" "pass" "ArgoCD CLI 사용 가능" 5
    
    # ArgoCD 서버 연결 확인
    if argocd version --server $ARGOCD_SERVER --grpc-web &> /dev/null; then
        add_check "ArgoCD Connection" "pass" "ArgoCD 서버 연결 성공 ($ARGOCD_SERVER)" 10
        
        # 애플리케이션 상태 확인
        if app_info=$(argocd app get $APP_NAME --server $ARGOCD_SERVER --grpc-web -o json 2>/dev/null); then
            local health_status=$(echo "$app_info" | jq -r '.status.health.status // "Unknown"')
            local sync_status=$(echo "$app_info" | jq -r '.status.sync.status // "Unknown"')
            local last_sync=$(echo "$app_info" | jq -r '.status.operationState.finishedAt // "Never"')
            local current_revision=$(echo "$app_info" | jq -r '.status.sync.revision[0:7] // "Unknown"')
            
            # Health Status 평가
            case $health_status in
                "Healthy")
                    add_check "App Health" "pass" "애플리케이션 상태 정상" 15
                    ;;
                "Progressing")
                    add_check "App Health" "warn" "애플리케이션 배포 진행 중" 15
                    ;;
                "Degraded"|"Missing")
                    add_check "App Health" "fail" "애플리케이션 상태 이상 ($health_status)" 15
                    ;;
                *)
                    add_check "App Health" "warn" "애플리케이션 상태 알 수 없음 ($health_status)" 15
                    ;;
            esac
            
            # Sync Status 평가
            case $sync_status in
                "Synced")
                    add_check "App Sync" "pass" "동기화 상태 정상" 15
                    ;;
                "OutOfSync")
                    add_check "App Sync" "warn" "동기화 필요 (OutOfSync)" 15
                    ;;
                *)
                    add_check "App Sync" "warn" "동기화 상태 알 수 없음 ($sync_status)" 15
                    ;;
            esac
            
            print_info "  현재 리비전: $current_revision"
            print_info "  마지막 동기화: $last_sync"
            
        else
            add_check "App Health" "fail" "애플리케이션 정보 조회 실패" 15
            add_check "App Sync" "fail" "애플리케이션 정보 조회 실패" 15
        fi
        
    else
        add_check "ArgoCD Connection" "fail" "ArgoCD 서버 연결 실패" 10
        print_warning "  로그인이 필요할 수 있습니다: argocd login $ARGOCD_SERVER --grpc-web"
        add_check "App Health" "fail" "연결 실패로 확인 불가" 15
        add_check "App Sync" "fail" "연결 실패로 확인 불가" 15
    fi
    
    echo ""
}

# 5. Image Updater 상태 확인
check_image_updater_status() {
    print_header "ArgoCD Image Updater 상태"
    
    # Image Updater Pod 확인
    if kubectl get namespace argocd &> /dev/null; then
        if updater_pods=$(kubectl get pods -n argocd -l app.kubernetes.io/name=argocd-image-updater -o json 2>/dev/null); then
            local pod_count=$(echo "$updater_pods" | jq '.items | length' 2>/dev/null || echo 0)
            
            if [ "$pod_count" -gt 0 ]; then
                local running_pods=$(echo "$updater_pods" | jq '[.items[] | select(.status.phase == "Running")] | length' 2>/dev/null || echo 0)
                
                if [ "$running_pods" -eq "$pod_count" ]; then
                    add_check "Image Updater Pod" "pass" "$running_pods/$pod_count Pod 실행 중" 10
                elif [ "$running_pods" -gt 0 ]; then
                    add_check "Image Updater Pod" "warn" "$running_pods/$pod_count Pod 실행 중" 10
                else
                    add_check "Image Updater Pod" "fail" "실행 중인 Pod 없음" 10
                fi
                
                # 최근 로그 확인 (Image Updater 활동 여부)
                if recent_logs=$(kubectl logs -n argocd -l app.kubernetes.io/name=argocd-image-updater --tail=20 --since=10m 2>/dev/null); then
                    if echo "$recent_logs" | grep -q "Processing application\|Updating image\|Found new image"; then
                        add_check "Image Updater Activity" "pass" "최근 10분 내 활동 감지" 10
                    else
                        add_check "Image Updater Activity" "warn" "최근 활동 없음 (정상일 수 있음)" 10
                    fi
                else
                    add_check "Image Updater Activity" "warn" "로그 조회 실패" 10
                fi
            else
                add_check "Image Updater Pod" "fail" "Image Updater Pod 없음" 10
                add_check "Image Updater Activity" "fail" "Pod 없음으로 확인 불가" 10
            fi
        else
            add_check "Image Updater Pod" "warn" "Image Updater 상태 조회 실패" 10
            add_check "Image Updater Activity" "warn" "상태 조회 실패" 10
        fi
    else
        add_check "Image Updater Pod" "fail" "ArgoCD 네임스페이스 없음" 10
        add_check "Image Updater Activity" "fail" "ArgoCD 네임스페이스 없음" 10
    fi
    
    echo ""
}

# 6. 애플리케이션 헬스체크
check_application_health() {
    print_header "애플리케이션 헬스체크"
    
    # NodePort 확인
    local node_port=$(kubectl get service $APP_NAME -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null)
    
    if [ -z "$node_port" ]; then
        add_check "Service Endpoint" "fail" "NodePort를 찾을 수 없음" 10
        add_check "Health Endpoint" "fail" "서비스 엔드포인트 없음" 15
        add_check "API Endpoints" "fail" "서비스 엔드포인트 없음" 15
        return
    fi
    
    add_check "Service Endpoint" "pass" "NodePort $node_port 사용 가능" 10
    
    # 기본 헬스체크
    local health_status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 \
                         "http://localhost:$node_port/health" 2>/dev/null)
    
    if [ "$health_status" = "200" ]; then
        add_check "Health Endpoint" "pass" "헬스체크 엔드포인트 정상 (200)" 15
    elif [ "$health_status" = "000" ]; then
        add_check "Health Endpoint" "fail" "헬스체크 엔드포인트 연결 실패" 15
    else
        add_check "Health Endpoint" "warn" "헬스체크 엔드포인트 응답 이상 ($health_status)" 15
    fi
    
    # 핵심 API 엔드포인트 테스트
    local endpoints=(
        "/api/stats:통계 API"
        "/api/collection/status:수집 상태 API"
        "/api/blacklist/active:활성 IP 목록"
    )
    
    local failed_endpoints=0
    local total_endpoints=${#endpoints[@]}
    
    for endpoint_info in "${endpoints[@]}"; do
        local endpoint=$(echo "$endpoint_info" | cut -d':' -f1)
        local description=$(echo "$endpoint_info" | cut -d':' -f2)
        
        local status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 \
                      "http://localhost:$node_port$endpoint" 2>/dev/null)
        
        if [ "$status" != "200" ]; then
            failed_endpoints=$((failed_endpoints + 1))
            print_warning "    $description ($endpoint): $status"
        else
            print_success "    $description ($endpoint): $status"
        fi
    done
    
    if [ $failed_endpoints -eq 0 ]; then
        add_check "API Endpoints" "pass" "모든 API 엔드포인트 정상" 15
    elif [ $failed_endpoints -le 1 ]; then
        add_check "API Endpoints" "warn" "$failed_endpoints/$total_endpoints API 엔드포인트 실패" 15
    else
        add_check "API Endpoints" "fail" "$failed_endpoints/$total_endpoints API 엔드포인트 실패" 15
    fi
    
    # 응답 시간 측정
    local response_time=$(curl -s -o /dev/null -w "%{time_total}" --connect-timeout 5 --max-time 10 \
                         "http://localhost:$node_port/health" 2>/dev/null)
    
    if [ -n "$response_time" ]; then
        print_info "  평균 응답 시간: ${response_time}초"
        
        if (( $(echo "$response_time < 0.5" | bc -l 2>/dev/null || echo 0) )); then
            add_check "Response Time" "pass" "응답 시간 우수 (${response_time}초)" 5
        elif (( $(echo "$response_time < 2.0" | bc -l 2>/dev/null || echo 0) )); then
            add_check "Response Time" "warn" "응답 시간 보통 (${response_time}초)" 5
        else
            add_check "Response Time" "warn" "응답 시간 느림 (${response_time}초)" 5
        fi
    else
        add_check "Response Time" "fail" "응답 시간 측정 불가" 5
    fi
    
    echo ""
}

# 7. 최근 배포 이력 확인
check_deployment_history() {
    print_header "최근 배포 이력"
    
    # ArgoCD 배포 이력
    if argocd version --server $ARGOCD_SERVER --grpc-web &> /dev/null 2>&1; then
        if app_history=$(argocd app history $APP_NAME --server $ARGOCD_SERVER --grpc-web -o json 2>/dev/null); then
            local history_count=$(echo "$app_history" | jq '. | length' 2>/dev/null || echo 0)
            
            if [ "$history_count" -gt 0 ]; then
                add_check "Deployment History" "pass" "$history_count개 배포 이력 존재" 5
                
                echo "  최근 ArgoCD 배포 이력 (최근 3개):"
                echo "$app_history" | jq -r '.[] | "\(.deployedAt // "Unknown"): \(.revision[0:7]) - \(.source.path)"' | head -3 | while read -r line; do
                    print_info "    $line"
                done
            else
                add_check "Deployment History" "warn" "ArgoCD 배포 이력 없음" 5
            fi
        else
            add_check "Deployment History" "warn" "ArgoCD 이력 조회 실패" 5
        fi
    else
        add_check "Deployment History" "warn" "ArgoCD 연결 불가" 5
    fi
    
    # Kubernetes 배포 이력
    if kubectl get deployment $APP_NAME -n $NAMESPACE &> /dev/null; then
        echo "  Kubernetes 배포 이력:"
        kubectl rollout history deployment/$APP_NAME -n $NAMESPACE 2>/dev/null | tail -5 | while read -r line; do
            if [[ $line =~ ^[0-9] ]]; then
                print_info "    $line"
            fi
        done
    fi
    
    echo ""
}

# 전체 상태 요약 및 권장사항
generate_summary() {
    print_header "파이프라인 상태 요약"
    
    local percentage=0
    if [ $MAX_SCORE -gt 0 ]; then
        percentage=$((OVERALL_SCORE * 100 / MAX_SCORE))
    fi
    
    echo "전체 헬스 스코어: $OVERALL_SCORE/$MAX_SCORE ($percentage%)"
    echo ""
    
    # 상태별 등급 설정
    if [ $percentage -ge 90 ]; then
        print_success "🟢 파이프라인 상태: 매우 양호"
        echo "  모든 구성 요소가 정상적으로 작동하고 있습니다."
    elif [ $percentage -ge 75 ]; then
        print_warning "🟡 파이프라인 상태: 양호"
        echo "  대부분의 구성 요소가 정상이나 일부 개선이 필요합니다."
    elif [ $percentage -ge 50 ]; then
        print_warning "🟠 파이프라인 상태: 주의 필요"
        echo "  여러 구성 요소에서 문제가 발견되었습니다."
    else
        print_error "🔴 파이프라인 상태: 심각한 문제"
        echo "  즉시 조치가 필요한 문제들이 있습니다."
    fi
    
    echo ""
    
    # 실패한 검사들 나열
    local failed_checks=()
    local warning_checks=()
    
    for component in "${!STATUS_CHECKS[@]}"; do
        case "${STATUS_CHECKS[$component]}" in
            "fail")
                failed_checks+=("$component: ${STATUS_MESSAGES[$component]}")
                ;;
            "warn")
                warning_checks+=("$component: ${STATUS_MESSAGES[$component]}")
                ;;
        esac
    done
    
    if [ ${#failed_checks[@]} -gt 0 ]; then
        echo "❌ 실패한 검사들:"
        for check in "${failed_checks[@]}"; do
            echo "   • $check"
        done
        echo ""
    fi
    
    if [ ${#warning_checks[@]} -gt 0 ]; then
        echo "⚠️  경고 사항들:"
        for check in "${warning_checks[@]}"; do
            echo "   • $check"
        done
        echo ""
    fi
}

# 문제 해결 권장사항
provide_recommendations() {
    print_header "문제 해결 권장사항"
    
    local has_recommendations=false
    
    # 구체적인 문제별 해결 방안
    for component in "${!STATUS_CHECKS[@]}"; do
        if [ "${STATUS_CHECKS[$component]}" = "fail" ]; then
            has_recommendations=true
            case $component in
                "GitHub Actions")
                    echo "🔧 GitHub Actions 문제 해결:"
                    echo "   • 최근 워크플로우 실행 결과 확인: gh run list --repo $GITHUB_REPO"
                    echo "   • 실패한 워크플로우 로그 확인: gh run view <run-id> --log-failed"
                    echo "   • 워크플로우 파일 문법 검사: .github/workflows/ 디렉토리 확인"
                    ;;
                "Registry Connection")
                    echo "🔧 Docker Registry 연결 문제 해결:"
                    echo "   • Registry 서버 상태 확인: curl -I http://$REGISTRY/v2/"
                    echo "   • 네트워크 연결 확인: ping $REGISTRY"
                    echo "   • Registry 인증 정보 확인"
                    ;;
                "Kubernetes Connection")
                    echo "🔧 Kubernetes 연결 문제 해결:"
                    echo "   • kubectl 설정 확인: kubectl config current-context"
                    echo "   • 클러스터 상태 확인: kubectl cluster-info"
                    echo "   • kubeconfig 파일 확인: ~/.kube/config"
                    ;;
                "Deployment Status")
                    echo "🔧 배포 상태 문제 해결:"
                    echo "   • Pod 상태 확인: kubectl get pods -n $NAMESPACE"
                    echo "   • 배포 상태 확인: kubectl rollout status deployment/$APP_NAME -n $NAMESPACE"
                    echo "   • Pod 로그 확인: kubectl logs -f deployment/$APP_NAME -n $NAMESPACE"
                    echo "   • 이벤트 확인: kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp'"
                    ;;
                "ArgoCD Connection")
                    echo "🔧 ArgoCD 연결 문제 해결:"
                    echo "   • ArgoCD 로그인: argocd login $ARGOCD_SERVER --grpc-web"
                    echo "   • ArgoCD 서버 상태 확인: curl -k https://$ARGOCD_SERVER/healthz"
                    echo "   • ArgoCD CLI 버전 확인: argocd version"
                    ;;
                "App Health"|"App Sync")
                    echo "🔧 ArgoCD 애플리케이션 문제 해결:"
                    echo "   • 애플리케이션 동기화: argocd app sync $APP_NAME --grpc-web"
                    echo "   • 애플리케이션 상태 확인: argocd app get $APP_NAME --grpc-web"
                    echo "   • 수동 새로고침: argocd app refresh $APP_NAME --grpc-web"
                    ;;
                "Health Endpoint"|"API Endpoints")
                    echo "🔧 애플리케이션 엔드포인트 문제 해결:"
                    echo "   • Pod 재시작: kubectl rollout restart deployment/$APP_NAME -n $NAMESPACE"
                    echo "   • 서비스 상태 확인: kubectl get svc $APP_NAME -n $NAMESPACE"
                    echo "   • 엔드포인트 확인: kubectl get endpoints $APP_NAME -n $NAMESPACE"
                    ;;
            esac
            echo ""
        fi
    done
    
    if [ "$has_recommendations" = false ]; then
        print_success "모든 구성 요소가 정상 작동 중입니다!"
        echo ""
        echo "정기 유지보수 권장사항:"
        echo "   • 정기적인 상태 점검: $0"
        echo "   • 로그 모니터링: scripts/pipeline-health-monitor.sh"
        echo "   • 보안 업데이트 확인"
        echo "   • 백업 상태 점검"
    fi
    
    echo ""
    echo "추가 도움말 명령어:"
    echo "   • 전체 파이프라인 헬스체크: scripts/pipeline-health-monitor.sh"
    echo "   • ArgoCD 관리: scripts/k8s-management.sh [init|deploy|status|logs|rollback]"
    echo "   • 자동 롤백: scripts/auto-rollback.sh --check-health"
    echo "   • CI/CD 상태 확인: $0"
    echo ""
}

# 메인 실행 함수
main() {
    echo "점검 시작 시간: $(date)"
    echo "점검 대상:"
    echo "  • 네임스페이스: $NAMESPACE"
    echo "  • 애플리케이션: $APP_NAME"
    echo "  • ArgoCD 서버: $ARGOCD_SERVER"
    echo "  • Docker Registry: $REGISTRY"
    echo "  • GitHub Repository: $GITHUB_REPO"
    echo ""
    
    # 각 구성 요소 점검 실행
    check_github_status
    check_registry_status
    check_kubernetes_status
    check_argocd_status
    check_image_updater_status
    check_application_health
    check_deployment_history
    
    # 결과 요약 및 권장사항
    generate_summary
    provide_recommendations
    
    echo "점검 완료 시간: $(date)"
    
    # 종료 코드 설정
    local percentage=0
    if [ $MAX_SCORE -gt 0 ]; then
        percentage=$((OVERALL_SCORE * 100 / MAX_SCORE))
    fi
    
    if [ $percentage -ge 75 ]; then
        exit 0  # 정상
    elif [ $percentage -ge 50 ]; then
        exit 1  # 경고
    else
        exit 2  # 심각
    fi
}

# 스크립트 실행
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi