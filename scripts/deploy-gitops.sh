#!/bin/bash
# deploy-gitops.sh - GitOps deployment script with App of Apps pattern
# Usage: ./deploy-gitops.sh [production|staging|development|all] [--setup-secrets]

set -e

ENVIRONMENT=${1:-production}
SETUP_SECRETS=${2:-}

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 환경별 네임스페이스 매핑
get_namespace() {
    case "$1" in
        production)
            echo "blacklist"
            ;;
        staging)
            echo "blacklist-staging"
            ;;
        development)
            echo "blacklist-dev"
            ;;
        *)
            echo "blacklist"
            ;;
    esac
}

# ArgoCD CLI 설치 확인
check_argocd_cli() {
    if ! command -v argocd &> /dev/null; then
        log_error "ArgoCD CLI not found. Please install it first."
        log_info "Installation: curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64"
        exit 1
    fi
}

# ArgoCD 서버 연결 확인
check_argocd_connection() {
    log_info "Checking ArgoCD server connection..."
    
    if ! argocd version --grpc-web &> /dev/null; then
        log_warning "ArgoCD server not accessible. Trying to connect..."
        
        # Port forward를 백그라운드에서 실행
        kubectl port-forward svc/argocd-server -n argocd 8080:443 &
        local pf_pid=$!
        
        # 잠시 대기
        sleep 5
        
        # ArgoCD 로그인 시도
        if ! argocd login localhost:8080 --grpc-web --insecure --username admin --password $(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d) &> /dev/null; then
            log_error "Failed to connect to ArgoCD server"
            kill $pf_pid 2>/dev/null || true
            exit 1
        fi
        
        # Port forward 종료
        kill $pf_pid 2>/dev/null || true
    fi
    
    log_success "ArgoCD server connection established"
}

# Secrets 설정
setup_secrets() {
    if [ "$SETUP_SECRETS" = "--setup-secrets" ]; then
        log_info "Setting up secrets for environment: $ENVIRONMENT"
        
        if [ -f "./scripts/setup-multienv-secrets.sh" ]; then
            ./scripts/setup-multienv-secrets.sh "$ENVIRONMENT"
        else
            log_warning "Multi-environment secrets script not found, using legacy script"
            if [ -f "./scripts/setup-all-secrets.sh" ]; then
                ./scripts/setup-all-secrets.sh
            else
                log_error "No secrets setup script found"
                exit 1
            fi
        fi
    fi
}

# App of Apps 배포
deploy_app_of_apps() {
    log_info "Deploying App of Apps pattern..."
    
    # App of Apps 애플리케이션 배포
    kubectl apply -f argocd/app-of-apps.yaml
    
    # ArgoCD Project 확인/생성
    if ! argocd proj get blacklist-project --grpc-web &> /dev/null; then
        log_info "Creating ArgoCD project: blacklist-project"
        kubectl apply -f argocd/application.yaml
    fi
    
    log_success "App of Apps deployed successfully"
}

# 개별 환경 배포
deploy_environment() {
    local env=$1
    local namespace=$(get_namespace $env)
    local app_name="blacklist-$env"
    
    log_info "Deploying $env environment to namespace: $namespace"
    
    # 네임스페이스 생성
    kubectl create namespace $namespace --dry-run=client -o yaml | kubectl apply -f -
    
    # 환경별 애플리케이션 배포
    kubectl apply -f argocd/environments/$env.yaml
    
    # ArgoCD 동기화
    if command -v argocd &> /dev/null; then
        log_info "Synchronizing ArgoCD application: $app_name"
        argocd app sync $app_name --grpc-web || log_warning "ArgoCD sync failed, but will retry automatically"
        
        # Health check 대기
        log_info "Waiting for application to be healthy..."
        argocd app wait $app_name --health --grpc-web --timeout 300 || log_warning "Health check timeout, but deployment may still be in progress"
    fi
    
    log_success "$env environment deployed successfully"
}

# 배포 상태 확인
check_deployment_status() {
    local env=$1
    local namespace=$(get_namespace $env)
    
    log_info "Checking deployment status for $env environment in namespace: $namespace"
    
    # Pod 상태 확인
    echo "Pods in namespace $namespace:"
    kubectl get pods -n $namespace -o wide
    
    # Service 상태 확인
    echo "Services in namespace $namespace:"
    kubectl get svc -n $namespace
    
    # Ingress 상태 확인 (있는 경우)
    if kubectl get ingress -n $namespace &> /dev/null; then
        echo "Ingress in namespace $namespace:"
        kubectl get ingress -n $namespace
    fi
    
    # ArgoCD 애플리케이션 상태 확인
    if command -v argocd &> /dev/null; then
        echo "ArgoCD application status:"
        argocd app get blacklist-$env --grpc-web
    fi
}

# 로그 확인
show_logs() {
    local env=$1
    local namespace=$(get_namespace $env)
    
    log_info "Showing logs for $env environment in namespace: $namespace"
    
    # 최근 로그 확인
    kubectl logs -n $namespace -l app=blacklist --tail=100
}

# 메인 실행 로직
main() {
    log_info "Starting GitOps deployment for: $ENVIRONMENT"
    
    # 사전 확인
    check_argocd_cli
    check_argocd_connection
    
    # Secrets 설정
    setup_secrets
    
    case "$ENVIRONMENT" in
        production)
            deploy_app_of_apps
            deploy_environment production
            check_deployment_status production
            ;;
        staging)
            deploy_app_of_apps
            deploy_environment staging
            check_deployment_status staging
            ;;
        development)
            deploy_app_of_apps
            deploy_environment development
            check_deployment_status development
            ;;
        all)
            deploy_app_of_apps
            deploy_environment production
            deploy_environment staging
            deploy_environment development
            
            log_info "Checking all environments status..."
            check_deployment_status production
            check_deployment_status staging
            check_deployment_status development
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT"
            log_info "Usage: $0 [production|staging|development|all] [--setup-secrets]"
            exit 1
            ;;
    esac
    
    echo ""
    log_success "🎉 GitOps deployment completed!"
    echo ""
    log_info "Access your applications:"
    echo "- Production: kubectl port-forward svc/blacklist -n blacklist 8080:80"
    echo "- Staging: kubectl port-forward svc/blacklist -n blacklist-staging 8080:80"
    echo "- Development: kubectl port-forward svc/blacklist -n blacklist-dev 8080:80"
    echo ""
    log_info "Monitor with ArgoCD:"
    echo "- ArgoCD UI: kubectl port-forward svc/argocd-server -n argocd 8080:443"
    echo "- CLI: argocd app list --grpc-web"
}

# 스크립트 실행
main "$@"