#!/bin/bash

# ArgoCD 배포 스크립트
# charts.jclee.me 리포지토리 기반 GitOps 배포

set -e

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 설정
NAMESPACE="blacklist"
ARGOCD_NAMESPACE="argocd"
APP_NAME="blacklist"
CHARTS_REPO="https://github.com/jclee/charts.git"
ARGOCD_SERVER="${ARGOCD_SERVER:-argo.jclee.me}"

# 함수 정의
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# ArgoCD 설치 확인
check_argocd() {
    log "ArgoCD 설치 상태 확인..."
    
    if ! kubectl get namespace $ARGOCD_NAMESPACE &>/dev/null; then
        error "ArgoCD namespace가 존재하지 않습니다."
        echo "ArgoCD를 먼저 설치하세요:"
        echo "kubectl create namespace argocd"
        echo "kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml"
        exit 1
    fi
    
    if ! kubectl get deployment argocd-server -n $ARGOCD_NAMESPACE &>/dev/null; then
        error "ArgoCD 서버가 설치되지 않았습니다."
        exit 1
    fi
    
    success "ArgoCD가 설치되어 있습니다."
}

# 네임스페이스 생성
create_namespace() {
    log "네임스페이스 생성..."
    
    if kubectl get namespace $NAMESPACE &>/dev/null; then
        warning "네임스페이스 $NAMESPACE가 이미 존재합니다."
    else
        kubectl create namespace $NAMESPACE
        success "네임스페이스 $NAMESPACE를 생성했습니다."
    fi
}

# Registry Secret 생성
create_registry_secret() {
    log "Registry Secret 생성..."
    
    # 기존 시크릿 삭제
    kubectl delete secret regcred -n $NAMESPACE --ignore-not-found=true
    
    # 새 시크릿 생성
    kubectl create secret docker-registry regcred \
        --docker-server=registry.jclee.me \
        --docker-username="${REGISTRY_USERNAME:-admin}" \
        --docker-password="${REGISTRY_PASSWORD:-bingogo1}" \
        -n $NAMESPACE
    
    success "Registry Secret를 생성했습니다."
}

# 애플리케이션 시크릿 생성
create_app_secrets() {
    log "애플리케이션 시크릿 생성..."
    
    # 기존 시크릿 삭제
    kubectl delete secret blacklist-secrets -n $NAMESPACE --ignore-not-found=true
    
    # 새 시크릿 생성
    kubectl create secret generic blacklist-secrets \
        --from-literal=secret-key="${SECRET_KEY:-$(openssl rand -hex 32)}" \
        --from-literal=jwt-secret-key="${JWT_SECRET_KEY:-$(openssl rand -hex 32)}" \
        --from-literal=regtech-username="${REGTECH_USERNAME:-nextrade}" \
        --from-literal=regtech-password="${REGTECH_PASSWORD:-Sprtmxm1@3}" \
        --from-literal=secudium-username="${SECUDIUM_USERNAME:-nextrade}" \
        --from-literal=secudium-password="${SECUDIUM_PASSWORD:-Sprtmxm1@3}" \
        -n $NAMESPACE
    
    success "애플리케이션 시크릿을 생성했습니다."
}

# Charts 리포지토리 연결
setup_charts_repo() {
    log "Charts 리포지토리 연결..."
    
    # 기존 리포지토리 시크릿 삭제
    kubectl delete secret charts-repo-secret -n $ARGOCD_NAMESPACE --ignore-not-found=true
    
    # 새 리포지토리 시크릿 생성
    if [ -n "$CHARTS_REPO_TOKEN" ]; then
        kubectl create secret generic charts-repo-secret \
            --from-literal=type=git \
            --from-literal=url=$CHARTS_REPO \
            --from-literal=password="$CHARTS_REPO_TOKEN" \
            --from-literal=username="$CHARTS_REPO_USERNAME" \
            -n $ARGOCD_NAMESPACE
        
        kubectl label secret charts-repo-secret \
            argocd.argoproj.io/secret-type=repository \
            -n $ARGOCD_NAMESPACE
        
        success "Charts 리포지토리 시크릿을 생성했습니다."
    else
        warning "CHARTS_REPO_TOKEN이 설정되지 않았습니다. 공개 리포지토리로 연결합니다."
    fi
}

# ArgoCD 애플리케이션 생성
create_argocd_app() {
    log "ArgoCD 애플리케이션 생성..."
    
    # 기존 애플리케이션 삭제
    kubectl delete application $APP_NAME -n $ARGOCD_NAMESPACE --ignore-not-found=true
    
    # 애플리케이션 생성
    kubectl apply -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: $APP_NAME
  namespace: $ARGOCD_NAMESPACE
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: $CHARTS_REPO
    targetRevision: HEAD
    path: charts/blacklist
    helm:
      valueFiles:
        - values.yaml
      parameters:
        - name: image.repository
          value: "registry.jclee.me/blacklist"
        - name: image.tag
          value: "latest"
        - name: replicaCount
          value: "3"
        - name: environment
          value: "production"
  destination:
    server: https://kubernetes.default.svc
    namespace: $NAMESPACE
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
      - PruneLast=true
      - RespectIgnoreDifferences=true
      - ApplyOutOfSyncOnly=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
  revisionHistoryLimit: 10
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas
    - group: ""
      kind: Secret
      jsonPointers:
        - /data
EOF
    
    success "ArgoCD 애플리케이션을 생성했습니다."
}

# 배포 상태 확인
check_deployment() {
    log "배포 상태 확인..."
    
    # ArgoCD 애플리케이션 동기화 기다리기
    echo "ArgoCD 애플리케이션 동기화 대기 중..."
    
    for i in {1..30}; do
        if argocd app get $APP_NAME --grpc-web --server $ARGOCD_SERVER &>/dev/null; then
            break
        fi
        echo "대기 중... ($i/30)"
        sleep 5
    done
    
    # 애플리케이션 상태 확인
    if argocd app get $APP_NAME --grpc-web --server $ARGOCD_SERVER &>/dev/null; then
        success "ArgoCD 애플리케이션이 생성되었습니다."
        
        # 수동 동기화 수행
        log "수동 동기화 수행..."
        argocd app sync $APP_NAME --grpc-web --server $ARGOCD_SERVER
        
        # 동기화 완료 대기
        argocd app wait $APP_NAME --health --grpc-web --server $ARGOCD_SERVER --timeout 300
        
        # 최종 상태 확인
        kubectl get pods -n $NAMESPACE
        kubectl get svc -n $NAMESPACE
        kubectl get ingress -n $NAMESPACE
        
        success "배포가 완료되었습니다!"
    else
        error "ArgoCD 애플리케이션 생성에 실패했습니다."
        exit 1
    fi
}

# 배포 정보 출력
show_deployment_info() {
    log "배포 정보 출력..."
    
    echo ""
    echo "=================================="
    echo "🚀 Blacklist 배포 완료"
    echo "=================================="
    echo ""
    echo "📦 애플리케이션 정보:"
    echo "  - 이름: $APP_NAME"
    echo "  - 네임스페이스: $NAMESPACE"
    echo "  - 차트 리포지토리: $CHARTS_REPO"
    echo ""
    echo "🔗 접속 정보:"
    echo "  - 서비스: https://blacklist.jclee.me"
    echo "  - 헬스체크: https://blacklist.jclee.me/health"
    echo "  - ArgoCD: https://$ARGOCD_SERVER"
    echo ""
    echo "📊 관리 명령어:"
    echo "  # ArgoCD 애플리케이션 상태 확인"
    echo "  argocd app get $APP_NAME --grpc-web --server $ARGOCD_SERVER"
    echo ""
    echo "  # 수동 동기화"
    echo "  argocd app sync $APP_NAME --grpc-web --server $ARGOCD_SERVER"
    echo ""
    echo "  # 파드 상태 확인"
    echo "  kubectl get pods -n $NAMESPACE"
    echo ""
    echo "  # 로그 확인"
    echo "  kubectl logs -f deployment/$APP_NAME -n $NAMESPACE"
    echo ""
    echo "✅ GitOps 배포가 완료되었습니다!"
}

# 메인 실행
main() {
    log "charts.jclee.me 기반 GitOps 배포 시작..."
    
    # 사전 조건 확인
    check_argocd
    
    # 환경 변수 확인
    if [ -z "$CHARTS_REPO_TOKEN" ]; then
        warning "CHARTS_REPO_TOKEN이 설정되지 않았습니다."
    fi
    
    # 배포 실행
    create_namespace
    create_registry_secret
    create_app_secrets
    setup_charts_repo
    create_argocd_app
    check_deployment
    show_deployment_info
    
    success "모든 배포 과정이 완료되었습니다!"
}

# 도움말
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -n, --namespace <namespace>  Set target namespace (default: blacklist)"
    echo "  -s, --server <server>        Set ArgoCD server (default: argo.jclee.me)"
    echo ""
    echo "Environment Variables:"
    echo "  CHARTS_REPO_TOKEN      GitHub token for charts repository"
    echo "  REGISTRY_USERNAME      Registry username (default: admin)"
    echo "  REGISTRY_PASSWORD      Registry password (default: bingogo1)"
    echo "  SECRET_KEY             Flask secret key"
    echo "  JWT_SECRET_KEY         JWT secret key"
    echo "  REGTECH_USERNAME       REGTECH username"
    echo "  REGTECH_PASSWORD       REGTECH password"
    echo "  SECUDIUM_USERNAME      SECUDIUM username"
    echo "  SECUDIUM_PASSWORD      SECUDIUM password"
    echo ""
    echo "Examples:"
    echo "  # 기본 배포"
    echo "  ./scripts/deploy-argocd.sh"
    echo ""
    echo "  # 다른 네임스페이스에 배포"
    echo "  ./scripts/deploy-argocd.sh -n blacklist-staging"
    echo ""
    echo "  # 환경 변수와 함께 배포"
    echo "  CHARTS_REPO_TOKEN=ghp_xxx ./scripts/deploy-argocd.sh"
}

# 명령행 인자 처리
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -s|--server)
            ARGOCD_SERVER="$2"
            shift 2
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi