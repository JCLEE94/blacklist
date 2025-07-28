#!/bin/bash
set -euo pipefail

# Blacklist 시스템 성능 최적화 스크립트
# 성능 모니터링, 자동 스케일링, 최적화 적용을 위한 통합 스크립트

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
NAMESPACE="${BLACKLIST_NAMESPACE:-blacklist}"
MONITORING_INTERVAL="${MONITORING_INTERVAL:-30}"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로깅 함수
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# 성능 최적화 설정 적용
apply_performance_optimizations() {
    log_info "성능 최적화 설정 적용 중..."
    
    # HPA 최적화 적용
    if kubectl get hpa blacklist-hpa-optimized -n "$NAMESPACE" >/dev/null 2>&1; then
        log_info "기존 HPA 업데이트 중..."
        kubectl apply -f "$PROJECT_ROOT/k8s/performance/hpa-optimized.yaml"
    else
        log_info "새로운 최적화된 HPA 생성 중..."
        kubectl apply -f "$PROJECT_ROOT/k8s/performance/hpa-optimized.yaml"
    fi
    
    # ConfigMap 업데이트
    kubectl apply -f "$PROJECT_ROOT/k8s/performance/hpa-optimized.yaml"
    
    # 성능 모니터링 설정
    if command -v helm >/dev/null 2>&1; then
        setup_prometheus_monitoring
    else
        log_warn "Helm이 설치되지 않음. Prometheus 모니터링 설정을 건너뜁니다."
    fi
    
    log_info "성능 최적화 설정 적용 완료"
}

# Prometheus 모니터링 설정
setup_prometheus_monitoring() {
    log_info "Prometheus 모니터링 설정 중..."
    
    # kube-prometheus-stack 설치 확인
    if ! helm list -n monitoring | grep -q kube-prometheus-stack; then
        log_info "Prometheus Stack 설치 중..."
        helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
        helm repo update
        
        kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
        
        helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
            --namespace monitoring \
            --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
            --set prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues=false \
            --set prometheus.prometheusSpec.ruleSelectorNilUsesHelmValues=false
    else
        log_info "Prometheus Stack이 이미 설치되어 있습니다"
    fi
    
    # ServiceMonitor 및 PrometheusRule 적용
    kubectl apply -f "$PROJECT_ROOT/k8s/performance/hpa-optimized.yaml"
    
    log_info "Prometheus 모니터링 설정 완료"
}

# 현재 성능 상태 확인
check_performance_status() {
    log_info "현재 성능 상태 확인 중..."
    
    # Pod 상태 확인
    echo "=== Pod 상태 ==="
    kubectl get pods -n "$NAMESPACE" -l app=blacklist
    echo
    
    # HPA 상태 확인
    echo "=== HPA 상태 ==="
    kubectl get hpa -n "$NAMESPACE"
    echo
    
    # 리소스 사용량 확인
    echo "=== 리소스 사용량 ==="
    kubectl top pods -n "$NAMESPACE" 2>/dev/null || log_warn "metrics-server가 설치되지 않음"
    echo
    
    # 서비스 응답시간 확인
    echo "=== 서비스 응답시간 테스트 ==="
    check_api_response_time
    echo
    
    # 메모리 및 캐시 상태 확인
    echo "=== 캐시 상태 ==="
    check_cache_status
}

# API 응답시간 확인
check_api_response_time() {
    local service_url
    service_url=$(get_service_url)
    
    if [[ -n "$service_url" ]]; then
        log_info "API 응답시간 측정: $service_url"
        
        # 헬스체크 응답시간
        local health_time
        health_time=$(curl -w "%{time_total}\n" -o /dev/null -s "$service_url/health" 2>/dev/null || echo "error")
        
        if [[ "$health_time" != "error" ]]; then
            local health_ms
            health_ms=$(echo "$health_time * 1000" | bc)
            echo "  - 헬스체크: ${health_ms}ms"
            
            # 응답시간 기준 평가
            if (( $(echo "$health_time > 1.0" | bc -l) )); then
                log_warn "응답시간이 느립니다 (>${health_ms}ms). 최적화가 필요합니다."
            elif (( $(echo "$health_time > 0.5" | bc -l) )); then
                log_warn "응답시간이 보통입니다 (${health_ms}ms). 최적화를 고려하세요."
            else
                log_info "응답시간이 우수합니다 (${health_ms}ms)"
            fi
        else
            log_error "API 응답시간 측정 실패"
        fi
        
        # 블랙리스트 API 응답시간
        local blacklist_time
        blacklist_time=$(curl -w "%{time_total}\n" -o /dev/null -s "$service_url/api/blacklist/active" 2>/dev/null || echo "error")
        
        if [[ "$blacklist_time" != "error" ]]; then
            local blacklist_ms
            blacklist_ms=$(echo "$blacklist_time * 1000" | bc)
            echo "  - 블랙리스트 API: ${blacklist_ms}ms"
        fi
    else
        log_error "서비스 URL을 찾을 수 없습니다"
    fi
}

# 캐시 상태 확인
check_cache_status() {
    local service_url
    service_url=$(get_service_url)
    
    if [[ -n "$service_url" ]]; then
        # 시스템 헬스에서 캐시 정보 확인
        local health_response
        health_response=$(curl -s "$service_url/health" 2>/dev/null || echo "{}")
        
        if [[ "$health_response" != "{}" ]]; then
            local cache_available
            cache_available=$(echo "$health_response" | jq -r '.cache_available // false' 2>/dev/null || echo "false")
            
            if [[ "$cache_available" == "true" ]]; then
                log_info "캐시 시스템이 활성화되어 있습니다"
            else
                log_warn "캐시 시스템이 비활성화되어 있습니다. 성능에 영향을 줄 수 있습니다."
            fi
        fi
    fi
}

# 서비스 URL 획득
get_service_url() {
    # NodePort 서비스 URL 구성
    local node_port
    node_port=$(kubectl get svc blacklist-service -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "")
    
    if [[ -n "$node_port" ]]; then
        echo "http://localhost:$node_port"
    else
        # 포트 포워딩 활용
        local pod_name
        pod_name=$(kubectl get pods -n "$NAMESPACE" -l app=blacklist -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
        
        if [[ -n "$pod_name" ]]; then
            echo "http://localhost:8080"  # 포트 포워딩 가정
        fi
    fi
}

# 성능 최적화 제안 생성
generate_optimization_recommendations() {
    log_info "성능 최적화 제안 생성 중..."
    
    local recommendations=()
    
    # Pod 수 확인
    local current_replicas
    current_replicas=$(kubectl get deployment blacklist -n "$NAMESPACE" -o jsonpath='{.status.replicas}' 2>/dev/null || echo "0")
    
    if [[ "$current_replicas" -lt 2 ]]; then
        recommendations+=("🔄 최소 2개의 복제본으로 고가용성을 확보하세요")
    fi
    
    # HPA 설정 확인
    if ! kubectl get hpa -n "$NAMESPACE" | grep -q blacklist; then
        recommendations+=("📈 HorizontalPodAutoscaler를 설정하여 자동 스케일링을 활성화하세요")
    fi
    
    # 리소스 제한 확인
    local cpu_limit
    cpu_limit=$(kubectl get deployment blacklist -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].resources.limits.cpu}' 2>/dev/null || echo "")
    
    if [[ -z "$cpu_limit" ]]; then
        recommendations+=("⚙️ CPU 및 메모리 제한을 설정하여 리소스 사용량을 최적화하세요")
    fi
    
    # 모니터링 설정 확인
    if ! kubectl get servicemonitor -n "$NAMESPACE" blacklist-performance-monitor 2>/dev/null; then
        recommendations+=("📊 Prometheus ServiceMonitor를 설정하여 상세 모니터링을 활성화하세요")
    fi
    
    # 추천사항 출력
    if [[ ${#recommendations[@]} -gt 0 ]]; then
        echo "=== 성능 최적화 제안 ==="
        for rec in "${recommendations[@]}"; do
            echo "$rec"
        done
        echo
    else
        log_info "✅ 시스템이 최적화된 상태입니다"
    fi
}

# 실시간 성능 모니터링
start_performance_monitoring() {
    log_info "실시간 성능 모니터링 시작 (${MONITORING_INTERVAL}초 간격)"
    log_info "모니터링을 중지하려면 Ctrl+C를 누르세요"
    
    while true; do
        clear
        echo "=================================="
        echo "Blacklist 성능 모니터링 대시보드"
        echo "$(date)"
        echo "=================================="
        echo
        
        check_performance_status
        
        echo "=================================="
        echo "다음 업데이트: ${MONITORING_INTERVAL}초 후"
        echo "=================================="
        
        sleep "$MONITORING_INTERVAL"
    done
}

# 부하 테스트 실행
run_load_test() {
    log_info "부하 테스트 실행 중..."
    
    local service_url
    service_url=$(get_service_url)
    
    if [[ -z "$service_url" ]]; then
        log_error "서비스 URL을 찾을 수 없습니다"
        return 1
    fi
    
    # Apache Bench를 사용한 부하 테스트
    if command -v ab >/dev/null 2>&1; then
        log_info "Apache Bench를 사용한 부하 테스트..."
        ab -n 100 -c 10 "$service_url/health"
    elif command -v curl >/dev/null 2>&1; then
        log_info "curl을 사용한 간단한 부하 테스트..."
        for i in {1..20}; do
            echo -n "."
            curl -s "$service_url/health" >/dev/null &
        done
        wait
        echo " 완료"
    else
        log_warn "부하 테스트 도구를 찾을 수 없습니다 (ab 또는 curl 필요)"
    fi
}

# 성능 보고서 생성
generate_performance_report() {
    log_info "성능 보고서 생성 중..."
    
    local report_file="performance_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "=================================="
        echo "Blacklist 시스템 성능 보고서"
        echo "생성일시: $(date)"
        echo "=================================="
        echo
        
        echo "=== 시스템 개요 ==="
        kubectl get deployment,hpa,svc -n "$NAMESPACE"
        echo
        
        echo "=== 리소스 사용량 ==="
        kubectl top pods -n "$NAMESPACE" 2>/dev/null || echo "metrics-server 정보 없음"
        echo
        
        echo "=== 최근 이벤트 ==="
        kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' | tail -10
        echo
        
        echo "=== 최적화 제안 ==="
        generate_optimization_recommendations
        
    } > "$report_file"
    
    log_info "성능 보고서가 $report_file에 저장되었습니다"
}

# 도움말 출력
show_help() {
    cat << EOF
Blacklist 시스템 성능 최적화 스크립트

사용법: $0 [명령어]

명령어:
    apply           성능 최적화 설정 적용
    status          현재 성능 상태 확인
    monitor         실시간 성능 모니터링 시작
    loadtest        부하 테스트 실행
    report          성능 보고서 생성
    recommendations 최적화 제안 생성
    help            이 도움말 출력

환경 변수:
    BLACKLIST_NAMESPACE     대상 네임스페이스 (기본값: blacklist)
    MONITORING_INTERVAL     모니터링 간격(초) (기본값: 30)

예시:
    $0 apply                # 성능 최적화 설정 적용
    $0 status               # 현재 상태 확인
    $0 monitor              # 실시간 모니터링
    MONITORING_INTERVAL=10 $0 monitor  # 10초 간격 모니터링

EOF
}

# 메인 함수
main() {
    case "${1:-help}" in
        "apply")
            apply_performance_optimizations
            ;;
        "status")
            check_performance_status
            ;;
        "monitor")
            start_performance_monitoring
            ;;
        "loadtest")
            run_load_test
            ;;
        "report")
            generate_performance_report
            ;;
        "recommendations")
            generate_optimization_recommendations
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            log_error "알 수 없는 명령어: $1"
            show_help
            exit 1
            ;;
    esac
}

# 필수 도구 확인
check_requirements() {
    local required_tools=("kubectl" "jq" "bc")
    local missing_tools=()
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_tools+=("$tool")
        fi
    done
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "다음 도구들이 필요합니다: ${missing_tools[*]}"
        log_info "설치 방법:"
        for tool in "${missing_tools[@]}"; do
            case "$tool" in
                "kubectl")
                    echo "  - kubectl: https://kubernetes.io/docs/tasks/tools/"
                    ;;
                "jq")
                    echo "  - jq: apt-get install jq 또는 brew install jq"
                    ;;
                "bc")
                    echo "  - bc: apt-get install bc 또는 brew install bc"
                    ;;
            esac
        done
        exit 1
    fi
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    check_requirements
    main "$@"
fi