#!/bin/bash

# MSA 완전 자동화 구축 스크립트 (jclee.me 인프라 최적화)
# 모든 MSA 구성 요소를 자동으로 설정하고 배포합니다

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 로깅 함수
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

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# 진행률 표시
show_progress() {
    local current=$1
    local total=$2
    local description=$3
    local percentage=$((current * 100 / total))
    echo -e "${CYAN}[${current}/${total} - ${percentage}%]${NC} ${description}"
}

# 에러 핸들링
error_exit() {
    log_error "스크립트 실행 중 오류가 발생했습니다: $1"
    exit 1
}

# Ctrl+C 핸들링
trap 'log_warning "스크립트가 중단되었습니다"; exit 1' INT

# 환경변수 로드
load_environment() {
    log_step "환경변수 로드 중..."
    
    if [[ -f .env ]]; then
        source .env
        log_success "환경변수 로드 완료"
    else
        log_warning ".env 파일이 없습니다. 기본값을 사용합니다."
    fi
    
    # jclee.me 인프라 기본값 설정
    export REGISTRY_URL=${REGISTRY_URL:-"https://registry.jclee.me"}
    export CHARTS_URL=${CHARTS_URL:-"https://charts.jclee.me"}
    export ARGOCD_SERVER=${ARGOCD_SERVER:-"argo.jclee.me"}
    export K8S_CLUSTER=${K8S_CLUSTER:-"k8s.jclee.me"}
    export NAMESPACE=${NAMESPACE:-"microservices"}
    export APP_NAME=${APP_NAME:-"blacklist"}
    
    # 인증 정보 (Base64 인코딩: admin:bingogo1)
    export REGISTRY_AUTH=${REGISTRY_AUTH:-"YWRtaW46YmluZ29nbzE="}
    export CHARTS_AUTH=${CHARTS_AUTH:-"YWRtaW46YmluZ29nbzE="}
    export ARGOCD_AUTH=${ARGOCD_AUTH:-"YWRtaW46YmluZ29nbzE="}
    
    log_info "환경변수 설정 완료:"
    log_info "  Registry: $REGISTRY_URL"
    log_info "  Charts: $CHARTS_URL"
    log_info "  ArgoCD: $ARGOCD_SERVER"
    log_info "  Namespace: $NAMESPACE"
}

# 필수 도구 확인
check_prerequisites() {
    log_step "필수 도구 확인 중..."
    
    local tools=("docker" "kubectl" "helm" "git")
    local missing_tools=()
    
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "다음 도구들이 설치되지 않았습니다: ${missing_tools[*]}"
        log_info "설치 가이드:"
        for tool in "${missing_tools[@]}"; do
            case $tool in
                docker)
                    log_info "  Docker: https://docs.docker.com/get-docker/"
                    ;;
                kubectl)
                    log_info "  kubectl: https://kubernetes.io/docs/tasks/tools/"
                    ;;
                helm)
                    log_info "  Helm: https://helm.sh/docs/intro/install/"
                    ;;
                git)
                    log_info "  Git: https://git-scm.com/downloads"
                    ;;
            esac
        done
        error_exit "필수 도구가 누락되었습니다"
    fi
    
    log_success "모든 필수 도구가 설치되어 있습니다"
}

# Kubernetes 클러스터 연결 확인
check_kubernetes_connection() {
    log_step "Kubernetes 클러스터 연결 확인 중..."
    
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Kubernetes 클러스터에 연결할 수 없습니다"
        log_info "다음 명령으로 클러스터 설정을 확인하세요:"
        log_info "  kubectl config view"
        log_info "  kubectl config get-contexts"
        error_exit "Kubernetes 연결 실패"
    fi
    
    local cluster_info=$(kubectl cluster-info | head -1)
    log_success "Kubernetes 클러스터 연결 성공: $cluster_info"
}

# 네임스페이스 및 리소스 생성
create_namespace_and_resources() {
    log_step "Kubernetes 네임스페이스 및 리소스 생성 중..."
    
    # 네임스페이스 생성
    kubectl apply -f k8s/msa/namespace.yaml
    log_success "네임스페이스 '$NAMESPACE' 생성 완료"
    
    # Registry Secret 생성
    kubectl create secret docker-registry jclee-registry-secret \
        --docker-server="$REGISTRY_URL" \
        --docker-username="admin" \
        --docker-password="bingogo1" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    log_success "Registry Secret 생성 완료"
    
    # 애플리케이션 Secret 생성 (REGTECH, SECUDIUM 인증 정보)
    kubectl create secret generic blacklist-secrets \
        --from-literal=regtech-username="admin" \
        --from-literal=regtech-password="bingogo1" \
        --from-literal=secudium-username="admin" \
        --from-literal=secudium-password="bingogo1" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    log_success "애플리케이션 Secret 생성 완료"
}

# Docker 이미지 빌드 및 푸시
build_and_push_image() {
    log_step "Docker 이미지 빌드 및 푸시 중..."
    
    local image_tag=$(date +'%Y%m%d')-$(git rev-parse --short HEAD)
    local full_image="registry.jclee.me/jclee/$APP_NAME:$image_tag"
    
    # Docker 로그인
    echo "bingogo1" | docker login registry.jclee.me --username admin --password-stdin
    
    # 이미지 빌드
    docker build -f deployment/Dockerfile -t "$full_image" .
    docker tag "$full_image" "registry.jclee.me/jclee/$APP_NAME:latest"
    
    # 이미지 푸시
    docker push "$full_image"
    docker push "registry.jclee.me/jclee/$APP_NAME:latest"
    
    log_success "Docker 이미지 빌드 및 푸시 완료: $full_image"
    echo "$image_tag" > .last_image_tag
}

# Helm Chart 검증 및 패키징
validate_and_package_helm() {
    log_step "Helm Chart 검증 및 패키징 중..."
    
    # Chart 검증
    helm lint charts/blacklist/
    helm template blacklist charts/blacklist/ --debug --dry-run > /dev/null
    log_success "Helm Chart 검증 완료"
    
    # Chart 패키징
    cd charts
    helm package blacklist/
    
    # ChartMuseum에 푸시 (선택사항)
    if command -v curl &> /dev/null; then
        local chart_file=$(ls blacklist-*.tgz | head -1)
        if [[ -n "$chart_file" ]]; then
            curl -u "admin:bingogo1" \
                --data-binary "@$chart_file" \
                "$CHARTS_URL/api/charts" || log_warning "ChartMuseum 푸시 실패 (선택사항)"
        fi
    fi
    
    cd ..
    log_success "Helm Chart 패키징 완료"
}

# ArgoCD 설치 및 설정
setup_argocd() {
    log_step "ArgoCD 설치 및 설정 중..."
    
    # ArgoCD 네임스페이스 확인/생성
    if ! kubectl get namespace argocd &> /dev/null; then
        kubectl create namespace argocd
        log_info "ArgoCD 네임스페이스 생성"
    fi
    
    # ArgoCD 설치 확인
    if ! kubectl get deployment argocd-server -n argocd &> /dev/null; then
        log_info "ArgoCD 설치 중... (시간이 소요될 수 있습니다)"
        kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
        
        # ArgoCD 준비 대기
        kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd
        log_success "ArgoCD 설치 완료"
    else
        log_info "ArgoCD가 이미 설치되어 있습니다"
    fi
    
    # ArgoCD CLI 설치
    if ! command -v argocd &> /dev/null; then
        log_info "ArgoCD CLI 설치 중..."
        curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
        sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd
        rm argocd-linux-amd64
        log_success "ArgoCD CLI 설치 완료"
    fi
}

# ArgoCD Application 배포
deploy_argocd_application() {
    log_step "ArgoCD Application 배포 중..."
    
    # ArgoCD Application 적용
    kubectl apply -f k8s/msa/argocd-application.yaml
    log_success "ArgoCD Application 설정 완료"
    
    # ArgoCD 로그인 (포트 포워딩 사용)
    kubectl port-forward svc/argocd-server -n argocd 8443:443 &
    local port_forward_pid=$!
    sleep 5
    
    # ArgoCD 초기 비밀번호 획득
    local initial_password=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
    
    # ArgoCD 로그인 시도
    if argocd login localhost:8443 --username admin --password "$initial_password" --insecure; then
        log_success "ArgoCD 로그인 성공"
        
        # 애플리케이션 동기화
        argocd app sync blacklist-msa --grpc-web --insecure
        log_success "ArgoCD 애플리케이션 동기화 완료"
    else
        log_warning "ArgoCD 로그인 실패 - 수동으로 웹 UI를 통해 설정하세요"
        log_info "ArgoCD 웹 UI: https://localhost:8443"
        log_info "초기 비밀번호: $initial_password"
    fi
    
    # 포트 포워딩 종료
    kill $port_forward_pid 2>/dev/null || true
}

# 배포 상태 확인
check_deployment_status() {
    log_step "배포 상태 확인 중..."
    
    # Pod 상태 확인
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        local ready_pods=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=blacklist --no-headers | grep -c "Running" || echo "0")
        local total_pods=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=blacklist --no-headers | wc -l)
        
        if [[ $ready_pods -gt 0 ]] && [[ $ready_pods -eq $total_pods ]]; then
            log_success "모든 Pod가 실행 중입니다 ($ready_pods/$total_pods)"
            break
        else
            log_info "Pod 상태 확인 중... ($ready_pods/$total_pods) - 시도 $attempt/$max_attempts"
            sleep 10
            ((attempt++))
        fi
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        log_warning "일부 Pod가 아직 준비되지 않았습니다"
        kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=blacklist
    fi
    
    # 서비스 상태 확인
    local service_ip=$(kubectl get svc blacklist -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [[ -n "$service_ip" ]]; then
        log_success "LoadBalancer IP: $service_ip"
    else
        local nodeport=$(kubectl get svc blacklist -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "")
        if [[ -n "$nodeport" ]]; then
            log_success "NodePort: $nodeport"
            log_info "서비스 접속: http://localhost:$nodeport"
        fi
    fi
}

# 모니터링 설정
setup_monitoring() {
    log_step "모니터링 설정 중..."
    
    # ServiceMonitor 적용 (Prometheus Operator가 설치된 경우)
    if kubectl get crd servicemonitors.monitoring.coreos.com &> /dev/null; then
        kubectl apply -f - <<EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: blacklist-metrics
  namespace: $NAMESPACE
  labels:
    app.kubernetes.io/name: blacklist
    infrastructure: jclee.me
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: blacklist
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
EOF
        log_success "ServiceMonitor 생성 완료"
    else
        log_warning "Prometheus Operator가 설치되지 않아 ServiceMonitor를 생략합니다"
    fi
    
    # 헬스 체크 스크립트 생성
    cat > health-check.sh <<'EOF'
#!/bin/bash
# MSA 헬스 체크 스크립트

NAMESPACE=${NAMESPACE:-microservices}
SERVICE_NAME=${SERVICE_NAME:-blacklist}

echo "=== MSA 상태 확인 ==="

# Pod 상태
echo "📦 Pod 상태:"
kubectl get pods -n $NAMESPACE -l app.kubernetes.io/name=$SERVICE_NAME

# 서비스 상태
echo -e "\n🌐 서비스 상태:"
kubectl get svc -n $NAMESPACE -l app.kubernetes.io/name=$SERVICE_NAME

# HPA 상태
echo -e "\n📊 HPA 상태:"
kubectl get hpa -n $NAMESPACE

# ArgoCD 상태
echo -e "\n🚀 ArgoCD 애플리케이션 상태:"
if command -v argocd &> /dev/null; then
    argocd app get blacklist-msa --grpc-web 2>/dev/null || echo "ArgoCD 연결 실패"
fi

# 헬스 체크
echo -e "\n🏥 서비스 헬스 체크:"
NODEPORT=$(kubectl get svc $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null)
if [[ -n "$NODEPORT" ]]; then
    if curl -f -s http://localhost:$NODEPORT/health > /dev/null; then
        echo "✅ 서비스 정상"
        curl -s http://localhost:$NODEPORT/health | jq . 2>/dev/null || curl -s http://localhost:$NODEPORT/health
    else
        echo "❌ 서비스 응답 없음"
    fi
else
    echo "❓ NodePort를 찾을 수 없습니다"
fi
EOF
    
    chmod +x health-check.sh
    log_success "헬스 체크 스크립트 생성 완료: ./health-check.sh"
}

# 최종 결과 출력
print_summary() {
    log_step "배포 완료 요약"
    
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}🎉 MSA 배포가 완료되었습니다! 🎉${NC}"
    echo -e "${GREEN}================================${NC}"
    
    echo -e "\n📋 배포 정보:"
    echo -e "  • 네임스페이스: ${YELLOW}$NAMESPACE${NC}"
    echo -e "  • 애플리케이션: ${YELLOW}$APP_NAME${NC}"
    echo -e "  • Registry: ${YELLOW}$REGISTRY_URL${NC}"
    echo -e "  • ArgoCD: ${YELLOW}https://$ARGOCD_SERVER${NC}"
    
    echo -e "\n🔗 접속 정보:"
    local nodeport=$(kubectl get svc blacklist -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "N/A")
    echo -e "  • 웹 대시보드: ${CYAN}http://localhost:$nodeport${NC}"
    echo -e "  • API 엔드포인트: ${CYAN}http://localhost:$nodeport/api${NC}"
    echo -e "  • 헬스 체크: ${CYAN}http://localhost:$nodeport/health${NC}"
    
    echo -e "\n🛠️ 유용한 명령어:"
    echo -e "  • 상태 확인: ${CYAN}./health-check.sh${NC}"
    echo -e "  • Pod 로그: ${CYAN}kubectl logs -f deployment/blacklist -n $NAMESPACE${NC}"
    echo -e "  • ArgoCD 동기화: ${CYAN}argocd app sync blacklist-msa --grpc-web${NC}"
    echo -e "  • 스케일링: ${CYAN}kubectl scale deployment blacklist --replicas=5 -n $NAMESPACE${NC}"
    
    echo -e "\n📊 모니터링:"
    echo -e "  • Kubernetes 대시보드를 통해 리소스 모니터링"
    echo -e "  • ArgoCD 웹 UI를 통해 GitOps 상태 확인"
    echo -e "  • Prometheus/Grafana를 통해 메트릭 모니터링 (설치된 경우)"
    
    echo -e "\n🔧 문제 해결:"
    echo -e "  • 로그 확인: ${CYAN}kubectl logs -f deployment/blacklist -n $NAMESPACE${NC}"
    echo -e "  • 이벤트 확인: ${CYAN}kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp'${NC}"
    echo -e "  • Pod 상세 정보: ${CYAN}kubectl describe pod -l app.kubernetes.io/name=blacklist -n $NAMESPACE${NC}"
    
    echo -e "\n${GREEN}🚀 MSA 환경이 준비되었습니다!${NC}"
}

# 메인 실행 함수
main() {
    local total_steps=10
    local current_step=0
    
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}🚀 MSA 완전 자동화 구축 시작${NC}"
    echo -e "${BLUE}================================${NC}\n"
    
    show_progress $((++current_step)) $total_steps "환경변수 로드"
    load_environment
    
    show_progress $((++current_step)) $total_steps "필수 도구 확인"
    check_prerequisites
    
    show_progress $((++current_step)) $total_steps "Kubernetes 연결 확인"
    check_kubernetes_connection
    
    show_progress $((++current_step)) $total_steps "네임스페이스 및 리소스 생성"
    create_namespace_and_resources
    
    show_progress $((++current_step)) $total_steps "Docker 이미지 빌드 및 푸시"
    build_and_push_image
    
    show_progress $((++current_step)) $total_steps "Helm Chart 검증 및 패키징"
    validate_and_package_helm
    
    show_progress $((++current_step)) $total_steps "ArgoCD 설치 및 설정"
    setup_argocd
    
    show_progress $((++current_step)) $total_steps "ArgoCD Application 배포"
    deploy_argocd_application
    
    show_progress $((++current_step)) $total_steps "배포 상태 확인"
    check_deployment_status
    
    show_progress $((++current_step)) $total_steps "모니터링 설정"
    setup_monitoring
    
    print_summary
}

# 스크립트 인자 처리
case "${1:-install}" in
    install|setup|deploy)
        main
        ;;
    check|status|health)
        if [[ -f health-check.sh ]]; then
            ./health-check.sh
        else
            log_error "health-check.sh 파일이 없습니다. 먼저 설치를 실행하세요."
        fi
        ;;
    clean|cleanup)
        log_warning "MSA 환경을 정리합니다..."
        kubectl delete namespace "$NAMESPACE" --ignore-not-found=true
        kubectl delete application blacklist-msa -n argocd --ignore-not-found=true
        log_success "정리 완료"
        ;;
    help|--help|-h)
        echo "MSA 완전 자동화 구축 스크립트"
        echo ""
        echo "사용법: $0 [명령어]"
        echo ""
        echo "명령어:"
        echo "  install, setup, deploy  MSA 환경 설치 및 배포 (기본값)"
        echo "  check, status, health   배포 상태 확인"
        echo "  clean, cleanup          MSA 환경 정리"
        echo "  help                    도움말 표시"
        ;;
    *)
        log_error "알 수 없는 명령어: $1"
        log_info "사용법: $0 [install|check|clean|help]"
        exit 1
        ;;
esac