#!/bin/bash

# CI/CD GitOps 파이프라인 헬스 모니터링 스크립트
# ArgoCD와 전체 배포 파이프라인의 상태를 실시간 모니터링

echo "🔍 CI/CD GitOps 파이프라인 헬스체크"
echo "================================="
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# 설정
NAMESPACE="blacklist"
APP_NAME="blacklist"
ARGOCD_SERVER="${ARGOCD_SERVER:-argo.jclee.me}"
REGISTRY="registry.jclee.me"
IMAGE_NAME="jclee94/blacklist"
HEALTH_ENDPOINT="/health"
STATS_ENDPOINT="/api/stats"
STATUS_ENDPOINT="/api/collection/status"

print_header() {
    echo -e "${CYAN}=== $1 ===${NC}"
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

# 파이프라인 구성 요소 상태 체크
check_pipeline_components() {
    print_header "파이프라인 구성 요소 상태"
    
    local all_healthy=true
    
    # 1. Kubernetes 클러스터 연결
    echo -n "Kubernetes 클러스터 연결: "
    if kubectl cluster-info &> /dev/null; then
        print_success "연결됨"
    else
        print_error "연결 실패"
        all_healthy=false
    fi
    
    # 2. ArgoCD 서버 연결
    echo -n "ArgoCD 서버 연결: "
    if argocd version --server $ARGOCD_SERVER --grpc-web &> /dev/null; then
        print_success "연결됨 ($ARGOCD_SERVER)"
    else
        print_warning "연결 실패 또는 인증 필요 ($ARGOCD_SERVER)"
    fi
    
    # 3. Docker Registry 연결
    echo -n "Docker Registry 연결: "
    if curl -s --connect-timeout 5 "http://$REGISTRY/v2/" &> /dev/null; then
        print_success "연결됨 ($REGISTRY)"
    else
        print_warning "연결 확인 불가 ($REGISTRY)"
    fi
    
    # 4. 네임스페이스 존재 확인
    echo -n "대상 네임스페이스: "
    if kubectl get namespace $NAMESPACE &> /dev/null; then
        print_success "존재함 ($NAMESPACE)"
    else
        print_error "네임스페이스 없음 ($NAMESPACE)"
        all_healthy=false
    fi
    
    echo ""
    return $([ "$all_healthy" = true ] && echo 0 || echo 1)
}

# ArgoCD 애플리케이션 상태 체크
check_argocd_status() {
    print_header "ArgoCD 애플리케이션 상태"
    
    local app_info
    if app_info=$(argocd app get $APP_NAME --server $ARGOCD_SERVER --grpc-web -o json 2>/dev/null); then
        local health_status=$(echo "$app_info" | jq -r '.status.health.status // "Unknown"')
        local sync_status=$(echo "$app_info" | jq -r '.status.sync.status // "Unknown"')
        local last_sync=$(echo "$app_info" | jq -r '.status.operationState.finishedAt // "Never"')
        local revision=$(echo "$app_info" | jq -r '.status.sync.revision[0:7] // "Unknown"')
        
        echo "애플리케이션: $APP_NAME"
        
        # Health Status
        case $health_status in
            "Healthy")
                print_success "Health Status: $health_status"
                ;;
            "Progressing")
                print_info "Health Status: $health_status"
                ;;
            "Degraded"|"Missing")
                print_error "Health Status: $health_status"
                ;;
            *)
                print_warning "Health Status: $health_status"
                ;;
        esac
        
        # Sync Status
        case $sync_status in
            "Synced")
                print_success "Sync Status: $sync_status"
                ;;
            "OutOfSync")
                print_warning "Sync Status: $sync_status"
                ;;
            *)
                print_info "Sync Status: $sync_status"
                ;;
        esac
        
        print_info "Current Revision: $revision"
        print_info "Last Sync: $last_sync"
        
        # Image Updater 상태 확인
        local image_annotations=$(echo "$app_info" | jq -r '.metadata.annotations // {}' | grep -E "argocd-image-updater" || echo "")
        if [ -n "$image_annotations" ]; then
            print_success "Image Updater: 활성화됨"
        else
            print_warning "Image Updater: 비활성화됨"
        fi
        
    else
        print_error "ArgoCD 애플리케이션 정보를 가져올 수 없습니다"
        print_info "다음 명령어로 로그인하세요: argocd login $ARGOCD_SERVER --grpc-web"
        return 1
    fi
    
    echo ""
    return 0
}

# Kubernetes 배포 상태 체크
check_k8s_deployment() {
    print_header "Kubernetes 배포 상태"
    
    local deployment_info
    if deployment_info=$(kubectl get deployment $APP_NAME -n $NAMESPACE -o json 2>/dev/null); then
        local replicas=$(echo "$deployment_info" | jq -r '.spec.replicas')
        local ready_replicas=$(echo "$deployment_info" | jq -r '.status.readyReplicas // 0')
        local available_replicas=$(echo "$deployment_info" | jq -r '.status.availableReplicas // 0')
        local current_image=$(echo "$deployment_info" | jq -r '.spec.template.spec.containers[0].image')
        
        echo "배포명: $APP_NAME"
        print_info "현재 이미지: $current_image"
        
        # 레플리카 상태
        if [ "$ready_replicas" -eq "$replicas" ] && [ "$available_replicas" -eq "$replicas" ]; then
            print_success "레플리카 상태: $ready_replicas/$replicas (Ready), $available_replicas/$replicas (Available)"
        else
            print_warning "레플리카 상태: $ready_replicas/$replicas (Ready), $available_replicas/$replicas (Available)"
        fi
        
        # Pod 상태 확인
        local pod_status=$(kubectl get pods -n $NAMESPACE -l app=$APP_NAME -o json | jq -r '.items[] | "\(.metadata.name): \(.status.phase)"')
        echo "Pod 상태:"
        while IFS= read -r line; do
            if [[ $line == *"Running"* ]]; then
                print_success "  $line"
            else
                print_warning "  $line"
            fi
        done <<< "$pod_status"
        
    else
        print_error "배포 정보를 가져올 수 없습니다"
        return 1
    fi
    
    echo ""
    return 0
}

# 서비스 및 네트워킹 상태 체크
check_service_networking() {
    print_header "서비스 및 네트워킹 상태"
    
    # 서비스 상태
    local service_info
    if service_info=$(kubectl get service $APP_NAME -n $NAMESPACE -o json 2>/dev/null); then
        local cluster_ip=$(echo "$service_info" | jq -r '.spec.clusterIP')
        local node_port=$(echo "$service_info" | jq -r '.spec.ports[0].nodePort // "N/A"')
        local target_port=$(echo "$service_info" | jq -r '.spec.ports[0].targetPort')
        
        print_success "서비스: $APP_NAME"
        print_info "ClusterIP: $cluster_ip:$target_port"
        if [ "$node_port" != "N/A" ]; then
            print_info "NodePort: <node-ip>:$node_port"
        fi
        
        # 엔드포인트 확인
        local endpoints=$(kubectl get endpoints $APP_NAME -n $NAMESPACE -o json | jq -r '.subsets[]?.addresses[]?.ip // empty' | wc -l)
        if [ "$endpoints" -gt 0 ]; then
            print_success "엔드포인트: $endpoints개 활성"
        else
            print_error "엔드포인트: 없음"
        fi
        
    else
        print_error "서비스 정보를 가져올 수 없습니다"
        return 1
    fi
    
    echo ""
    return 0
}

# 애플리케이션 헬스체크
check_application_health() {
    print_header "애플리케이션 헬스체크"
    
    # NodePort 확인
    local node_port=$(kubectl get service $APP_NAME -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null)
    
    if [ -z "$node_port" ]; then
        print_error "NodePort를 찾을 수 없습니다"
        return 1
    fi
    
    print_info "테스트 대상: localhost:$node_port"
    
    # 기본 헬스체크
    echo -n "기본 헬스체크: "
    local health_response=$(curl -s --connect-timeout 5 --max-time 10 "http://localhost:$node_port$HEALTH_ENDPOINT" 2>/dev/null)
    local health_status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "http://localhost:$node_port$HEALTH_ENDPOINT" 2>/dev/null)
    
    if [ "$health_status" = "200" ]; then
        print_success "OK ($health_status)"
        if echo "$health_response" | grep -q "healthy\|ok" 2>/dev/null; then
            print_info "Response: 서비스 정상"
        fi
    else
        print_error "FAILED ($health_status)"
    fi
    
    # 핵심 API 엔드포인트 테스트
    local endpoints=(
        "$STATS_ENDPOINT:통계 API"
        "$STATUS_ENDPOINT:수집 상태 API"
        "/api/blacklist/active:활성 IP 목록"
    )
    
    echo "핵심 API 엔드포인트 테스트:"
    local failed_endpoints=0
    
    for endpoint_info in "${endpoints[@]}"; do
        local endpoint=$(echo "$endpoint_info" | cut -d':' -f1)
        local description=$(echo "$endpoint_info" | cut -d':' -f2)
        
        local status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 \
                      "http://localhost:$node_port$endpoint" 2>/dev/null)
        
        if [ "$status" = "200" ]; then
            print_success "  $description ($endpoint): OK"
        else
            print_error "  $description ($endpoint): FAILED ($status)"
            failed_endpoints=$((failed_endpoints + 1))
        fi
    done
    
    # 응답 시간 테스트
    echo -n "응답 시간 테스트: "
    local response_time=$(curl -s -o /dev/null -w "%{time_total}" --connect-timeout 5 --max-time 10 \
                         "http://localhost:$node_port$HEALTH_ENDPOINT" 2>/dev/null)
    
    if [ -n "$response_time" ]; then
        if (( $(echo "$response_time < 1.0" | bc -l 2>/dev/null || echo 0) )); then
            print_success "${response_time}초 (우수)"
        elif (( $(echo "$response_time < 2.0" | bc -l 2>/dev/null || echo 0) )); then
            print_info "${response_time}초 (양호)"
        else
            print_warning "${response_time}초 (느림)"
        fi
    else
        print_error "측정 불가"
    fi
    
    echo ""
    
    # 결과 반환
    if [ "$health_status" = "200" ] && [ $failed_endpoints -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

# Image Updater 상태 체크
check_image_updater() {
    print_header "ArgoCD Image Updater 상태"
    
    # Image Updater Pod 상태
    local updater_pods=$(kubectl get pods -n argocd -l app.kubernetes.io/name=argocd-image-updater -o json 2>/dev/null)
    
    if [ -n "$updater_pods" ] && [ "$updater_pods" != "null" ]; then
        local pod_count=$(echo "$updater_pods" | jq '.items | length')
        local running_pods=$(echo "$updater_pods" | jq '[.items[] | select(.status.phase == "Running")] | length')
        
        if [ "$running_pods" -gt 0 ]; then
            print_success "Image Updater Pod: $running_pods/$pod_count 실행 중"
        else
            print_error "Image Updater Pod: 실행 중인 Pod 없음"
        fi
        
        # 최근 로그 확인
        echo "최근 Image Updater 로그 (마지막 5줄):"
        kubectl logs -n argocd -l app.kubernetes.io/name=argocd-image-updater --tail=5 2>/dev/null | while read -r line; do
            print_info "  $line"
        done
        
    else
        print_warning "ArgoCD Image Updater가 설치되지 않았거나 찾을 수 없습니다"
    fi
    
    echo ""
}

# 최근 배포 이력 확인
check_deployment_history() {
    print_header "최근 배포 이력"
    
    # ArgoCD 애플리케이션 이력
    local app_history
    if app_history=$(argocd app history $APP_NAME --server $ARGOCD_SERVER --grpc-web -o json 2>/dev/null); then
        echo "ArgoCD 배포 이력 (최근 3개):"
        echo "$app_history" | jq -r '.[] | "\(.deployedAt // "Unknown"): \(.revision[0:7]) - \(.source.path)"' | head -3 | while read -r line; do
            print_info "  $line"
        done
    else
        print_warning "ArgoCD 배포 이력을 가져올 수 없습니다"
    fi
    
    # Kubernetes 배포 이력
    echo ""
    echo "Kubernetes 배포 이력:"
    kubectl rollout history deployment/$APP_NAME -n $NAMESPACE 2>/dev/null | tail -5 | while read -r line; do
        if [[ $line =~ ^[0-9] ]]; then
            print_info "  $line"
        fi
    done
    
    echo ""
}

# GitHub Actions 워크플로우 상태 (선택적)
check_github_workflow() {
    print_header "GitHub Actions 워크플로우 상태"
    
    if command -v gh &> /dev/null; then
        echo "최근 워크플로우 실행 (최근 3개):"
        gh run list --repo JCLEE94/blacklist --limit 3 2>/dev/null | while read -r line; do
            if [[ $line =~ ✓ ]]; then
                print_success "  $line"
            elif [[ $line =~ ✗ ]]; then
                print_error "  $line"
            elif [[ $line =~ ⋯ ]]; then
                print_info "  $line"
            else
                print_info "  $line"
            fi
        done
    else
        print_warning "GitHub CLI가 설치되지 않았습니다 (선택적)"
    fi
    
    echo ""
}

# 전체 파이프라인 헬스 스코어 계산
calculate_health_score() {
    print_header "파이프라인 헬스 스코어"
    
    local score=0
    local max_score=100
    
    # 각 검사 결과에 따른 점수
    [ $pipeline_components_ok -eq 0 ] && score=$((score + 20))
    [ $argocd_ok -eq 0 ] && score=$((score + 25))
    [ $k8s_deployment_ok -eq 0 ] && score=$((score + 20))
    [ $service_networking_ok -eq 0 ] && score=$((score + 15))
    [ $application_health_ok -eq 0 ] && score=$((score + 20))
    
    local percentage=$((score * 100 / max_score))
    
    echo "총 헬스 스코어: $score/$max_score ($percentage%)"
    
    if [ $percentage -ge 90 ]; then
        print_success "파이프라인 상태: 매우 양호 🟢"
    elif [ $percentage -ge 70 ]; then
        print_warning "파이프라인 상태: 양호 🟡"
    elif [ $percentage -ge 50 ]; then
        print_warning "파이프라인 상태: 주의 필요 🟠"
    else
        print_error "파이프라인 상태: 심각한 문제 🔴"
    fi
    
    echo ""
}

# 개선 권장사항 제공
provide_recommendations() {
    print_header "권장사항 및 다음 단계"
    
    local recommendations=()
    
    [ $pipeline_components_ok -ne 0 ] && recommendations+=("✅ 파이프라인 구성 요소 연결 문제 해결 필요")
    [ $argocd_ok -ne 0 ] && recommendations+=("✅ ArgoCD 연결 및 인증 확인 필요")
    [ $k8s_deployment_ok -ne 0 ] && recommendations+=("✅ Kubernetes 배포 상태 점검 필요")
    [ $service_networking_ok -ne 0 ] && recommendations+=("✅ 서비스 및 네트워킹 설정 확인 필요")
    [ $application_health_ok -ne 0 ] && recommendations+=("✅ 애플리케이션 헬스체크 문제 해결 필요")
    
    if [ ${#recommendations[@]} -eq 0 ]; then
        print_success "모든 구성 요소가 정상 작동 중입니다!"
        echo ""
        echo "정기 점검 명령어:"
        print_info "  - 파이프라인 상태: $0"
        print_info "  - ArgoCD 동기화: argocd app sync $APP_NAME --grpc-web"
        print_info "  - 배포 상태: kubectl get all -n $NAMESPACE"
        print_info "  - 로그 확인: scripts/k8s-management.sh logs"
    else
        echo "해결 필요한 항목들:"
        for recommendation in "${recommendations[@]}"; do
            echo "  $recommendation"
        done
        echo ""
        echo "문제 해결 명령어:"
        print_info "  - 전체 재배포: scripts/k8s-management.sh deploy"
        print_info "  - 상태 재확인: scripts/k8s-management.sh status"
        print_info "  - 롤백: scripts/k8s-management.sh rollback"
        print_info "  - 로그 확인: scripts/k8s-management.sh logs"
    fi
    
    echo ""
}

# 메인 실행 함수
main() {
    echo "시작 시간: $(date)"
    echo ""
    
    # 전역 상태 변수
    pipeline_components_ok=1
    argocd_ok=1
    k8s_deployment_ok=1
    service_networking_ok=1
    application_health_ok=1
    
    # 각 검사 실행
    check_pipeline_components && pipeline_components_ok=0
    check_argocd_status && argocd_ok=0
    check_k8s_deployment && k8s_deployment_ok=0
    check_service_networking && service_networking_ok=0
    check_application_health && application_health_ok=0
    
    # 추가 정보
    check_image_updater
    check_deployment_history
    check_github_workflow
    
    # 결과 분석
    calculate_health_score
    provide_recommendations
    
    echo "완료 시간: $(date)"
    
    # 전체 상태에 따른 종료 코드
    local overall_status=$((pipeline_components_ok + argocd_ok + k8s_deployment_ok + service_networking_ok + application_health_ok))
    
    if [ $overall_status -eq 0 ]; then
        exit 0  # 모든 검사 통과
    elif [ $overall_status -le 2 ]; then
        exit 1  # 경미한 문제
    else
        exit 2  # 심각한 문제
    fi
}

# 스크립트 실행
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi