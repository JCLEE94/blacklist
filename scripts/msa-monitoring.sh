#!/bin/bash

# MSA 모니터링 도구
# jclee.me 인프라에 최적화된 종합 모니터링 스크립트

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 환경변수 설정
NAMESPACE=${NAMESPACE:-"microservices"}
APP_NAME=${APP_NAME:-"blacklist"}
ARGOCD_SERVER=${ARGOCD_SERVER:-"argo.jclee.me"}

# 유틸리티 함수
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

log_section() {
    echo -e "\n${PURPLE}=== $1 ===${NC}"
}

# 시간 포맷팅
format_age() {
    local age=$1
    if [[ $age =~ ([0-9]+)d ]]; then
        echo "${BASH_REMATCH[1]}일"
    elif [[ $age =~ ([0-9]+)h ]]; then
        echo "${BASH_REMATCH[1]}시간"
    elif [[ $age =~ ([0-9]+)m ]]; then
        echo "${BASH_REMATCH[1]}분"
    else
        echo "$age"
    fi
}

# 상태 아이콘
get_status_icon() {
    local status=$1
    case $status in
        "Running"|"Ready"|"Healthy"|"Synced"|"True")
            echo "✅"
            ;;
        "Pending"|"Progressing"|"OutOfSync")
            echo "⏳"
            ;;
        "Failed"|"Error"|"Unhealthy"|"False")
            echo "❌"
            ;;
        "Unknown"|"Degraded")
            echo "❓"
            ;;
        *)
            echo "ℹ️"
            ;;
    esac
}

# 클러스터 전체 상태
show_cluster_overview() {
    log_section "클러스터 전체 상태"
    
    # 클러스터 정보
    local cluster_info=$(kubectl cluster-info | head -1 | sed 's/^[^:]*: //')
    log_info "클러스터: $cluster_info"
    
    # 노드 상태
    echo -e "\n📦 ${CYAN}노드 상태:${NC}"
    kubectl get nodes -o custom-columns="NAME:.metadata.name,STATUS:.status.conditions[-1].type,ROLES:.metadata.labels.node-role\.kubernetes\.io/master,AGE:.metadata.creationTimestamp,VERSION:.status.nodeInfo.kubeletVersion" | \
    while IFS= read -r line; do
        if [[ $line == NAME* ]]; then
            echo "$line"
        else
            local name=$(echo "$line" | awk '{print $1}')
            local status=$(echo "$line" | awk '{print $2}')
            local icon=$(get_status_icon "$status")
            echo "$icon $line"
        fi
    done
    
    # 네임스페이스 리소스 요약
    echo -e "\n📊 ${CYAN}네임스페이스 리소스:${NC}"
    local pods=$(kubectl get pods -n $NAMESPACE --no-headers 2>/dev/null | wc -l)
    local services=$(kubectl get svc -n $NAMESPACE --no-headers 2>/dev/null | wc -l)
    local deployments=$(kubectl get deployments -n $NAMESPACE --no-headers 2>/dev/null | wc -l)
    echo "  • Pods: $pods"
    echo "  • Services: $services"
    echo "  • Deployments: $deployments"
}

# Pod 상세 상태
show_pod_status() {
    log_section "Pod 상세 상태"
    
    if ! kubectl get pods -n $NAMESPACE &>/dev/null; then
        log_warning "네임스페이스 '$NAMESPACE'를 찾을 수 없습니다"
        return
    fi
    
    echo -e "${CYAN}현재 실행 중인 Pod:${NC}"
    kubectl get pods -n $NAMESPACE -o custom-columns="NAME:.metadata.name,READY:.status.containerStatuses[0].ready,STATUS:.status.phase,RESTARTS:.status.containerStatuses[0].restartCount,AGE:.metadata.creationTimestamp" | \
    while IFS= read -r line; do
        if [[ $line == NAME* ]]; then
            echo "$line"
        else
            local name=$(echo "$line" | awk '{print $1}')
            local ready=$(echo "$line" | awk '{print $2}')
            local status=$(echo "$line" | awk '{print $3}')
            local restarts=$(echo "$line" | awk '{print $4}')
            local age=$(echo "$line" | awk '{print $5}')
            local icon=$(get_status_icon "$status")
            local formatted_age=$(format_age "$age")
            echo "$icon $name $ready $status $restarts $formatted_age"
        fi
    done
    
    # Pod 리소스 사용량
    echo -e "\n📈 ${CYAN}Pod 리소스 사용량:${NC}"
    if command -v kubectl-top &>/dev/null || kubectl top pods --help &>/dev/null 2>&1; then
        kubectl top pods -n $NAMESPACE 2>/dev/null || log_warning "메트릭 서버가 설치되지 않았습니다"
    else
        log_warning "kubectl top 명령을 사용할 수 없습니다"
    fi
}

# 서비스 및 엔드포인트 상태
show_service_status() {
    log_section "서비스 및 엔드포인트 상태"
    
    echo -e "${CYAN}서비스 목록:${NC}"
    kubectl get svc -n $NAMESPACE -o custom-columns="NAME:.metadata.name,TYPE:.spec.type,CLUSTER-IP:.spec.clusterIP,EXTERNAL-IP:.status.loadBalancer.ingress[0].ip,PORT:.spec.ports[0].port,AGE:.metadata.creationTimestamp"
    
    echo -e "\n${CYAN}엔드포인트 상태:${NC}"
    kubectl get endpoints -n $NAMESPACE -o custom-columns="NAME:.metadata.name,ENDPOINTS:.subsets[0].addresses[*].ip,AGE:.metadata.creationTimestamp"
    
    # Ingress 상태 (있는 경우)
    if kubectl get ingress -n $NAMESPACE &>/dev/null; then
        echo -e "\n${CYAN}Ingress 상태:${NC}"
        kubectl get ingress -n $NAMESPACE
    fi
}

# HPA 및 스케일링 상태
show_scaling_status() {
    log_section "오토스케일링 상태"
    
    if kubectl get hpa -n $NAMESPACE &>/dev/null; then
        echo -e "${CYAN}HPA 상태:${NC}"
        kubectl get hpa -n $NAMESPACE -o custom-columns="NAME:.metadata.name,REFERENCE:.spec.scaleTargetRef.name,TARGETS:.status.currentMetrics[0].resource.current.averageUtilization,MINPODS:.spec.minReplicas,MAXPODS:.spec.maxReplicas,REPLICAS:.status.currentReplicas,AGE:.metadata.creationTimestamp"
        
        # HPA 상세 정보
        echo -e "\n${CYAN}HPA 상세 메트릭:${NC}"
        local hpa_name=$(kubectl get hpa -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        if [[ -n "$hpa_name" ]]; then
            kubectl describe hpa "$hpa_name" -n $NAMESPACE | grep -E "(Current|Target)" || true
        fi
    else
        log_warning "HPA를 찾을 수 없습니다"
    fi
    
    # VPA 상태 (있는 경우)
    if kubectl get vpa -n $NAMESPACE &>/dev/null 2>&1; then
        echo -e "\n${CYAN}VPA 상태:${NC}"
        kubectl get vpa -n $NAMESPACE
    fi
}

# 스토리지 상태
show_storage_status() {
    log_section "스토리지 상태"
    
    # PVC 상태
    if kubectl get pvc -n $NAMESPACE &>/dev/null; then
        echo -e "${CYAN}PVC 상태:${NC}"
        kubectl get pvc -n $NAMESPACE -o custom-columns="NAME:.metadata.name,STATUS:.status.phase,VOLUME:.spec.volumeName,CAPACITY:.status.capacity.storage,ACCESS-MODES:.spec.accessModes,AGE:.metadata.creationTimestamp"
    else
        log_info "PVC를 찾을 수 없습니다"
    fi
    
    # PV 상태 (전체)
    echo -e "\n${CYAN}PV 상태 (전체):${NC}"
    kubectl get pv -o custom-columns="NAME:.metadata.name,CAPACITY:.spec.capacity.storage,ACCESS-MODES:.spec.accessModes,RECLAIM-POLICY:.spec.persistentVolumeReclaimPolicy,STATUS:.status.phase,CLAIM:.spec.claimRef.name"
}

# ArgoCD 상태
show_argocd_status() {
    log_section "ArgoCD GitOps 상태"
    
    if ! command -v argocd &>/dev/null; then
        log_warning "ArgoCD CLI가 설치되지 않았습니다"
        return
    fi
    
    # ArgoCD 서버 상태 확인
    if ! argocd version --client &>/dev/null; then
        log_warning "ArgoCD 서버에 연결할 수 없습니다"
        return
    fi
    
    echo -e "${CYAN}ArgoCD 애플리케이션 상태:${NC}"
    
    # 애플리케이션 목록
    local apps=$(argocd app list --grpc-web 2>/dev/null | grep "$APP_NAME" || echo "")
    if [[ -n "$apps" ]]; then
        echo "$apps"
        
        # 특정 앱 상세 정보
        echo -e "\n${CYAN}애플리케이션 상세 정보:${NC}"
        local app_name=$(echo "$apps" | awk '{print $1}' | head -1)
        if [[ -n "$app_name" ]]; then
            argocd app get "$app_name" --grpc-web 2>/dev/null | head -20 || log_warning "애플리케이션 정보를 가져올 수 없습니다"
        fi
    else
        log_warning "ArgoCD 애플리케이션을 찾을 수 없습니다"
    fi
    
    # ArgoCD Image Updater 상태
    echo -e "\n${CYAN}Image Updater 상태:${NC}"
    if kubectl get deployment argocd-image-updater -n argocd &>/dev/null; then
        kubectl get deployment argocd-image-updater -n argocd -o custom-columns="NAME:.metadata.name,READY:.status.readyReplicas,UP-TO-DATE:.status.updatedReplicas,AVAILABLE:.status.availableReplicas"
        
        # 최근 로그 확인
        echo -e "\n${CYAN}Image Updater 최근 로그:${NC}"
        kubectl logs -n argocd deployment/argocd-image-updater --tail=5 2>/dev/null | head -10 || log_warning "로그를 가져올 수 없습니다"
    else
        log_warning "ArgoCD Image Updater를 찾을 수 없습니다"
    fi
}

# 네트워크 상태
show_network_status() {
    log_section "네트워크 상태"
    
    # NetworkPolicy 상태
    if kubectl get networkpolicy -n $NAMESPACE &>/dev/null; then
        echo -e "${CYAN}Network Policy:${NC}"
        kubectl get networkpolicy -n $NAMESPACE
    fi
    
    # 서비스 연결성 테스트
    echo -e "\n${CYAN}서비스 연결성 테스트:${NC}"
    local service_name=$(kubectl get svc -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    local nodeport=$(kubectl get svc -n $NAMESPACE -o jsonpath='{.items[0].spec.ports[0].nodePort}' 2>/dev/null)
    
    if [[ -n "$nodeport" ]]; then
        if curl -f -s --connect-timeout 5 "http://localhost:$nodeport/health" >/dev/null 2>&1; then
            log_success "서비스 연결 성공 (NodePort: $nodeport)"
        else
            log_warning "서비스 연결 실패 (NodePort: $nodeport)"
        fi
    else
        log_info "NodePort를 찾을 수 없습니다"
    fi
    
    # DNS 확인
    echo -e "\n${CYAN}DNS 해상도 테스트:${NC}"
    if [[ -n "$service_name" ]]; then
        if kubectl run dns-test --rm -i --restart=Never --image=busybox -- nslookup "$service_name.$NAMESPACE.svc.cluster.local" &>/dev/null; then
            log_success "DNS 해상도 정상"
        else
            log_warning "DNS 해상도 문제"
        fi
    fi
}

# 이벤트 및 로그
show_events_and_logs() {
    log_section "최근 이벤트 및 로그"
    
    # 최근 이벤트
    echo -e "${CYAN}최근 이벤트 (10개):${NC}"
    kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -10
    
    # 애플리케이션 로그 (최근 20줄)
    echo -e "\n${CYAN}애플리케이션 로그 (최근 20줄):${NC}"
    local pod_name=$(kubectl get pods -n $NAMESPACE -l app.kubernetes.io/name=$APP_NAME -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [[ -n "$pod_name" ]]; then
        kubectl logs "$pod_name" -n $NAMESPACE --tail=20 2>/dev/null || log_warning "로그를 가져올 수 없습니다"
    else
        log_warning "실행 중인 Pod를 찾을 수 없습니다"
    fi
}

# 보안 상태
show_security_status() {
    log_section "보안 상태"
    
    # Secret 상태
    echo -e "${CYAN}Secret 목록:${NC}"
    kubectl get secrets -n $NAMESPACE -o custom-columns="NAME:.metadata.name,TYPE:.type,DATA:.data,AGE:.metadata.creationTimestamp"
    
    # ServiceAccount 상태
    echo -e "\n${CYAN}ServiceAccount:${NC}"
    kubectl get sa -n $NAMESPACE
    
    # RBAC 확인
    echo -e "\n${CYAN}RBAC 권한:${NC}"
    kubectl auth can-i --list --as=system:serviceaccount:$NAMESPACE:default -n $NAMESPACE 2>/dev/null | head -10 || log_warning "RBAC 정보를 가져올 수 없습니다"
}

# 성능 메트릭
show_performance_metrics() {
    log_section "성능 메트릭"
    
    # 노드 리소스 사용량
    echo -e "${CYAN}노드 리소스 사용량:${NC}"
    if command -v kubectl-top &>/dev/null || kubectl top nodes --help &>/dev/null 2>&1; then
        kubectl top nodes 2>/dev/null || log_warning "메트릭 서버가 설치되지 않았습니다"
    fi
    
    # 네임스페이스 리소스 요약
    echo -e "\n${CYAN}네임스페이스 리소스 할당량:${NC}"
    if kubectl get resourcequota -n $NAMESPACE &>/dev/null; then
        kubectl describe resourcequota -n $NAMESPACE 2>/dev/null | grep -E "(Name|Resource|Used|Hard)" || true
    else
        log_info "리소스 할당량이 설정되지 않았습니다"
    fi
    
    # 응답 시간 테스트
    echo -e "\n${CYAN}API 응답 시간 테스트:${NC}"
    local nodeport=$(kubectl get svc -n $NAMESPACE -o jsonpath='{.items[0].spec.ports[0].nodePort}' 2>/dev/null)
    if [[ -n "$nodeport" ]]; then
        local response_time=$(curl -o /dev/null -s -w '%{time_total}' "http://localhost:$nodeport/health" 2>/dev/null || echo "N/A")
        echo "  • 헬스 체크 응답 시간: ${response_time}초"
    fi
}

# 전체 상태 요약
show_summary() {
    log_section "전체 상태 요약"
    
    local total_pods=$(kubectl get pods -n $NAMESPACE --no-headers 2>/dev/null | wc -l)
    local running_pods=$(kubectl get pods -n $NAMESPACE --no-headers 2>/dev/null | grep -c "Running" || echo "0")
    local total_services=$(kubectl get svc -n $NAMESPACE --no-headers 2>/dev/null | wc -l)
    
    echo -e "${CYAN}📊 MSA 상태 요약:${NC}"
    echo "  • 전체 Pod: $total_pods"
    echo "  • 실행 중인 Pod: $running_pods"
    echo "  • 서비스: $total_services"
    
    # 전체 상태 판단
    local health_status="정상"
    local health_icon="✅"
    
    if [[ $running_pods -eq 0 ]]; then
        health_status="심각"
        health_icon="❌"
    elif [[ $running_pods -lt $total_pods ]]; then
        health_status="주의"
        health_icon="⚠️"
    fi
    
    echo -e "\n$health_icon ${CYAN}전체 상태: $health_status${NC}"
    
    # 권장 사항
    if [[ $health_status != "정상" ]]; then
        echo -e "\n${YELLOW}권장 사항:${NC}"
        echo "  • Pod 로그 확인: kubectl logs -f deployment/$APP_NAME -n $NAMESPACE"
        echo "  • 이벤트 확인: kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp'"
        echo "  • ArgoCD 동기화: argocd app sync ${APP_NAME}-msa --grpc-web"
    fi
}

# 실시간 모니터링
watch_mode() {
    log_section "실시간 모니터링 모드"
    log_info "실시간 모니터링을 시작합니다. Ctrl+C로 종료하세요."
    
    while true; do
        clear
        echo -e "${PURPLE}=== MSA 실시간 모니터링 ($(date)) ===${NC}"
        
        # Pod 상태만 간단히 표시
        echo -e "\n${CYAN}Pod 상태:${NC}"
        kubectl get pods -n $NAMESPACE -o wide 2>/dev/null || log_warning "Pod 정보를 가져올 수 없습니다"
        
        # HPA 상태
        echo -e "\n${CYAN}HPA 상태:${NC}"
        kubectl get hpa -n $NAMESPACE 2>/dev/null || log_info "HPA 없음"
        
        # 최근 이벤트 (최근 5개)
        echo -e "\n${CYAN}최근 이벤트:${NC}"
        kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' 2>/dev/null | tail -5
        
        sleep 10
    done
}

# 도움말
show_help() {
    echo "MSA 모니터링 도구 - jclee.me 인프라 최적화"
    echo ""
    echo "사용법: $0 [옵션]"
    echo ""
    echo "옵션:"
    echo "  all, overview          전체 상태 개요 (기본값)"
    echo "  pods                   Pod 상세 상태"
    echo "  services               서비스 및 엔드포인트 상태"
    echo "  scaling, hpa           오토스케일링 상태"
    echo "  storage                스토리지 상태"
    echo "  argocd, gitops         ArgoCD GitOps 상태"
    echo "  network                네트워크 상태"
    echo "  events, logs           이벤트 및 로그"
    echo "  security               보안 상태"
    echo "  performance, metrics   성능 메트릭"
    echo "  summary                전체 상태 요약"
    echo "  watch                  실시간 모니터링"
    echo "  help                   도움말 표시"
    echo ""
    echo "환경변수:"
    echo "  NAMESPACE              대상 네임스페이스 (기본값: microservices)"
    echo "  APP_NAME               애플리케이션 이름 (기본값: blacklist)"
    echo "  ARGOCD_SERVER          ArgoCD 서버 주소"
}

# 메인 실행
main() {
    local option=${1:-"all"}
    
    case $option in
        all|overview)
            show_cluster_overview
            show_pod_status
            show_service_status
            show_scaling_status
            show_argocd_status
            show_summary
            ;;
        pods)
            show_pod_status
            ;;
        services)
            show_service_status
            ;;
        scaling|hpa)
            show_scaling_status
            ;;
        storage)
            show_storage_status
            ;;
        argocd|gitops)
            show_argocd_status
            ;;
        network)
            show_network_status
            ;;
        events|logs)
            show_events_and_logs
            ;;
        security)
            show_security_status
            ;;
        performance|metrics)
            show_performance_metrics
            ;;
        summary)
            show_summary
            ;;
        watch)
            watch_mode
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "알 수 없는 옵션: $option"
            show_help
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"