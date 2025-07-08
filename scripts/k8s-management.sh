#!/bin/bash

echo "🚀 Kubernetes 관리 스크립트 (ArgoCD GitOps)"
echo "============================================"
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# 기본 설정
NAMESPACE="blacklist"
ARGOCD_SERVER="argo.jclee.me"
REGISTRY="registry.jclee.me"
IMAGE_NAME="blacklist"

# Cloudflare Tunnel 기본 설정
ENABLE_CLOUDFLARED="${ENABLE_CLOUDFLARED:-true}"
CLOUDFLARE_TUNNEL_TOKEN="${CLOUDFLARE_TUNNEL_TOKEN:-}"
CLOUDFLARE_HOSTNAME="${CLOUDFLARE_HOSTNAME:-blacklist.jclee.me}"
CF_API_TOKEN="${CF_API_TOKEN:-}"

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
    echo "사용법: $0 <command> [options]"
    echo ""
    echo "명령어:"
    echo "  init        - 초기 설정 (네임스페이스, 시크릿, ArgoCD 앱)"
    echo "  deploy      - GitOps 배포 (ArgoCD 동기화)"
    echo "  status      - 배포 상태 확인"
    echo "  logs        - 애플리케이션 로그 확인"
    echo "  rollback    - 이전 버전으로 롤백"
    echo "  cleanup     - 리소스 정리"
    echo "  sync        - ArgoCD 수동 동기화"
    echo "  restart     - 애플리케이션 재시작"
    echo ""
    echo "옵션:"
    echo "  --tag TAG   - 특정 이미지 태그 지정"
    echo "  --force     - 강제 실행"
    echo "  --dry-run   - 실제 실행 없이 명령어만 출력"
    echo ""
    echo "예시:"
    echo "  $0 init"
    echo "  $0 deploy --tag v1.2.3"
    echo "  $0 status"
    echo "  $0 rollback"
}

check_prerequisites() {
    print_step "사전 요구사항 확인 중..."
    
    # kubectl 확인
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl이 설치되지 않았습니다."
        exit 1
    fi
    
    # argocd CLI 확인
    if ! command -v argocd &> /dev/null; then
        print_warning "ArgoCD CLI가 설치되지 않았습니다. 설치를 진행합니다..."
        install_argocd_cli
    fi
    
    # Kubernetes 클러스터 연결 확인
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Kubernetes 클러스터에 연결할 수 없습니다."
        exit 1
    fi
    
    print_success "사전 요구사항 확인 완료"
}

install_argocd_cli() {
    print_step "ArgoCD CLI 설치 중..."
    
    curl -sSL -o /tmp/argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
    sudo install -m 555 /tmp/argocd-linux-amd64 /usr/local/bin/argocd
    rm /tmp/argocd-linux-amd64
    
    if command -v argocd &> /dev/null; then
        print_success "ArgoCD CLI 설치 완료"
    else
        print_error "ArgoCD CLI 설치 실패"
        exit 1
    fi
}

init_deployment() {
    print_step "초기 배포 설정 중..."
    
    # 네임스페이스 생성
    print_step "네임스페이스 생성 중..."
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # Docker Registry 시크릿 생성
    print_step "Docker Registry 시크릿 설정 중..."
    if ! kubectl get secret regcred -n $NAMESPACE &> /dev/null; then
        if [ -z "$REGISTRY_USERNAME" ] || [ -z "$REGISTRY_PASSWORD" ]; then
            print_warning "Registry 인증 정보가 설정되지 않았습니다. 기본값을 사용합니다."
            REGISTRY_USERNAME="qws9411"
            REGISTRY_PASSWORD="bingogo1"
        fi
        
        kubectl create secret docker-registry regcred \
            --docker-server=$REGISTRY \
            --docker-username="$REGISTRY_USERNAME" \
            --docker-password="$REGISTRY_PASSWORD" \
            -n $NAMESPACE
        print_success "Registry 시크릿 생성 완료"
    else
        print_success "Registry 시크릿이 이미 존재합니다"
    fi
    
    # 애플리케이션 시크릿 생성
    print_step "애플리케이션 시크릿 설정 중..."
    if ! kubectl get secret blacklist-secret -n $NAMESPACE &> /dev/null; then
        kubectl create secret generic blacklist-secret \
            --from-literal=REGTECH_USERNAME="nextrade" \
            --from-literal=REGTECH_PASSWORD="Sprtmxm1@3" \
            --from-literal=SECUDIUM_USERNAME="nextrade" \
            --from-literal=SECUDIUM_PASSWORD="Sprtmxm1@3" \
            --from-literal=SECRET_KEY="k8s-secret-key-$(date +%s)" \
            -n $NAMESPACE
        print_success "애플리케이션 시크릿 생성 완료"
    else
        print_success "애플리케이션 시크릿이 이미 존재합니다"
    fi
    
    # Kubernetes 매니페스트 적용
    print_step "Kubernetes 매니페스트 적용 중..."
    kubectl apply -k k8s/
    
    # ArgoCD 애플리케이션 생성
    setup_argocd_application
    
    # Cloudflare Tunnel 설정 (선택적)
    if [ "${ENABLE_CLOUDFLARED:-true}" = "true" ]; then
        print_step "Cloudflare Tunnel 설정 중..."
        if [ -f "scripts/setup/install-cloudflared.sh" ]; then
            # DNS 먼저 설정
            if [ -f "scripts/setup/cloudflare-dns-setup.sh" ]; then
                print_step "Cloudflare DNS 설정 중..."
                export CF_API_TOKEN
                bash scripts/setup/cloudflare-dns-setup.sh setup
            fi
            
            # Tunnel 설치
            bash scripts/setup/install-cloudflared.sh all
            print_success "Cloudflare Tunnel 설정 완료"
        else
            print_warning "Cloudflare Tunnel 설치 스크립트를 찾을 수 없습니다"
        fi
    fi
    
    print_success "초기 배포 설정 완료"
}

setup_argocd_application() {
    print_argocd "ArgoCD 애플리케이션 설정 중..."
    
    # ArgoCD 애플리케이션 적용
    if [ -f "k8s/argocd-app-clean.yaml" ]; then
        kubectl apply -f k8s/argocd-app-clean.yaml
        print_argocd "ArgoCD 애플리케이션 매니페스트 적용 완료"
    else
        print_warning "ArgoCD 애플리케이션 매니페스트를 찾을 수 없습니다"
    fi
}

deploy_application() {
    print_step "GitOps 배포 시작..."
    
    # ArgoCD 동기화
    print_argocd "ArgoCD 동기화 실행 중..."
    
    if [ "$DRY_RUN" = "true" ]; then
        echo "argocd app sync blacklist --grpc-web"
        return 0
    fi
    
    # ArgoCD 로그인 확인 (선택사항)
    if ! argocd app get blacklist --grpc-web &> /dev/null; then
        print_warning "ArgoCD 인증이 필요합니다. 수동으로 로그인하세요:"
        echo "argocd login $ARGOCD_SERVER --username admin --grpc-web"
    fi
    
    # 애플리케이션 동기화
    argocd app sync blacklist --grpc-web --timeout 300 || print_warning "ArgoCD 동기화 완료 (일부 경고 있을 수 있음)"
    
    # 배포 상태 대기
    print_step "배포 완료 대기 중..."
    kubectl rollout status deployment/blacklist -n $NAMESPACE --timeout=300s
    
    print_success "GitOps 배포 완료"
}

check_status() {
    print_step "배포 상태 확인 중..."
    
    echo ""
    echo "=== ArgoCD 애플리케이션 상태 ==="
    if argocd app get blacklist --grpc-web &> /dev/null; then
        argocd app get blacklist --grpc-web | grep -E "(Health Status|Sync Status|Last Sync)"
    else
        print_warning "ArgoCD 연결 불가. 수동 로그인 필요"
    fi
    
    echo ""
    echo "=== Kubernetes 리소스 상태 ==="
    kubectl get all -n $NAMESPACE
    
    echo ""
    echo "=== Pod 상세 상태 ==="
    kubectl get pods -n $NAMESPACE -o wide
    
    echo ""
    echo "=== 서비스 엔드포인트 ==="
    local node_port=$(kubectl get svc blacklist -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "N/A")
    local cluster_ip=$(kubectl get svc blacklist -n $NAMESPACE -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "N/A")
    
    echo "ClusterIP: $cluster_ip:2541"
    echo "NodePort: <node-ip>:$node_port"
    
    # Health Check
    echo ""
    echo "=== Health Check ==="
    if [ "$node_port" != "N/A" ]; then
        if curl -s --connect-timeout 5 "http://localhost:$node_port/health" > /dev/null 2>&1; then
            print_success "애플리케이션 Health Check 성공"
        else
            print_warning "애플리케이션 Health Check 실패"
        fi
    fi
}

show_logs() {
    print_step "애플리케이션 로그 확인 중..."
    
    if kubectl get deployment blacklist -n $NAMESPACE &> /dev/null; then
        echo "최근 로그 (마지막 50줄):"
        kubectl logs -n $NAMESPACE deployment/blacklist --tail=50
        
        echo ""
        echo "실시간 로그를 보려면 다음 명령어를 사용하세요:"
        echo "kubectl logs -f deployment/blacklist -n $NAMESPACE"
    else
        print_error "blacklist 배포를 찾을 수 없습니다"
    fi
}

rollback_deployment() {
    print_step "이전 버전으로 롤백 중..."
    
    if [ "$DRY_RUN" = "true" ]; then
        echo "kubectl rollout undo deployment/blacklist -n $NAMESPACE"
        echo "argocd app rollback blacklist --grpc-web"
        return 0
    fi
    
    # ArgoCD를 통한 롤백
    print_argocd "ArgoCD 롤백 실행 중..."
    if argocd app rollback blacklist --grpc-web; then
        print_success "ArgoCD 롤백 완료"
    else
        print_warning "ArgoCD 롤백 실패. Kubernetes 직접 롤백을 시도합니다."
        kubectl rollout undo deployment/blacklist -n $NAMESPACE
    fi
    
    # 롤백 상태 확인
    kubectl rollout status deployment/blacklist -n $NAMESPACE --timeout=300s
    print_success "롤백 완료"
}

cleanup_resources() {
    print_step "리소스 정리 중..."
    
    echo -e "${RED}경고: 이 작업은 모든 blacklist 리소스를 삭제합니다.${NC}"
    read -p "계속하시겠습니까? (y/N): " confirm
    
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        echo "정리 작업이 취소되었습니다."
        exit 0
    fi
    
    if [ "$DRY_RUN" = "true" ]; then
        echo "kubectl delete namespace $NAMESPACE"
        echo "argocd app delete blacklist --grpc-web"
        return 0
    fi
    
    # ArgoCD 애플리케이션 삭제
    print_argocd "ArgoCD 애플리케이션 삭제 중..."
    argocd app delete blacklist --grpc-web --cascade || print_warning "ArgoCD 애플리케이션 삭제 실패 또는 없음"
    
    # Kubernetes 리소스 삭제
    print_step "Kubernetes 리소스 삭제 중..."
    kubectl delete namespace $NAMESPACE --timeout=300s
    
    print_success "리소스 정리 완료"
}

sync_argocd() {
    print_argocd "ArgoCD 수동 동기화 실행 중..."
    
    if [ "$DRY_RUN" = "true" ]; then
        echo "argocd app sync blacklist --grpc-web --prune"
        return 0
    fi
    
    argocd app sync blacklist --grpc-web --prune --timeout 300
    print_argocd "ArgoCD 동기화 완료"
}

restart_application() {
    print_step "애플리케이션 재시작 중..."
    
    if [ "$DRY_RUN" = "true" ]; then
        echo "kubectl rollout restart deployment/blacklist -n $NAMESPACE"
        return 0
    fi
    
    kubectl rollout restart deployment/blacklist -n $NAMESPACE
    kubectl rollout status deployment/blacklist -n $NAMESPACE --timeout=300s
    print_success "애플리케이션 재시작 완료"
}

# 메인 실행 로직
main() {
    # 인자 파싱
    COMMAND=""
    IMAGE_TAG=""
    FORCE="false"
    DRY_RUN="false"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --tag)
                IMAGE_TAG="$2"
                shift 2
                ;;
            --force)
                FORCE="true"
                shift
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            init|deploy|status|logs|rollback|cleanup|sync|restart)
                COMMAND="$1"
                shift
                ;;
            *)
                print_error "알 수 없는 옵션: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # 명령어가 지정되지 않은 경우
    if [ -z "$COMMAND" ]; then
        print_error "명령어를 지정해주세요."
        show_usage
        exit 1
    fi
    
    # 사전 요구사항 확인 (cleanup 제외)
    if [ "$COMMAND" != "cleanup" ]; then
        check_prerequisites
    fi
    
    # 설정 출력
    if [ "$DRY_RUN" = "true" ]; then
        print_warning "DRY RUN 모드 - 실제 실행 없음"
    fi
    
    echo ""
    print_step "실행 정보:"
    echo "  명령어: $COMMAND"
    echo "  네임스페이스: $NAMESPACE"
    echo "  ArgoCD 서버: $ARGOCD_SERVER"
    if [ -n "$IMAGE_TAG" ]; then
        echo "  이미지 태그: $IMAGE_TAG"
    fi
    echo ""
    
    # 명령어 실행
    case $COMMAND in
        init)
            init_deployment
            ;;
        deploy)
            deploy_application
            ;;
        status)
            check_status
            ;;
        logs)
            show_logs
            ;;
        rollback)
            rollback_deployment
            ;;
        cleanup)
            cleanup_resources
            ;;
        sync)
            sync_argocd
            ;;
        restart)
            restart_application
            ;;
        *)
            print_error "지원하지 않는 명령어: $COMMAND"
            show_usage
            exit 1
            ;;
    esac
    
    echo ""
    print_success "작업 완료!"
}

main "$@"