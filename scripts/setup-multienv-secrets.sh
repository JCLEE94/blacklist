#!/bin/bash
# setup-multienv-secrets.sh - Multi-environment secrets management
# Usage: ./setup-multienv-secrets.sh [production|staging|development|all]

set -e

ENVIRONMENT=${1:-production}

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

# 환경별 설정값 가져오기
get_env_config() {
    local env=$1
    
    case "$env" in
        production)
            echo "LOG_LEVEL=warning"
            echo "FLASK_ENV=production"
            echo "COLLECTION_ENABLED=true"
            echo "REDIS_URL=redis://redis:6379/0"
            echo "PORT=2541"
            echo "SECURE_COOKIES=true"
            ;;
        staging)
            echo "LOG_LEVEL=info"
            echo "FLASK_ENV=staging"
            echo "COLLECTION_ENABLED=false"
            echo "REDIS_URL=redis://redis-staging:6379/0"
            echo "PORT=8541"
            echo "SECURE_COOKIES=false"
            ;;
        development)
            echo "LOG_LEVEL=debug"
            echo "FLASK_ENV=development"
            echo "COLLECTION_ENABLED=false"
            echo "REDIS_URL=redis://redis:6379/0"
            echo "PORT=8541"
            echo "SECURE_COOKIES=false"
            ;;
    esac
}

# Registry secret 생성
create_registry_secret() {
    local namespace=$1
    
    if [ -z "$REGISTRY_URL" ] || [ -z "$REGISTRY_USER" ] || [ -z "$REGISTRY_PASS" ]; then
        log_warning "Registry credentials not set, skipping registry secret for $namespace"
        return
    fi
    
    log_info "Creating registry secret for namespace: $namespace"
    
    kubectl create secret docker-registry regcred \
        --docker-server=${REGISTRY_URL} \
        --docker-username=${REGISTRY_USER} \
        --docker-password=${REGISTRY_PASS} \
        --namespace=$namespace \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_success "Registry secret created in namespace: $namespace"
}

# Application secret 생성
create_app_secret() {
    local env=$1
    local namespace=$2
    
    log_info "Creating application secret for $env environment in namespace: $namespace"
    
    # 환경별 기본값 설정
    case "$env" in
        production)
            SECRET_KEY=${SECRET_KEY:-$(openssl rand -hex 32)}
            JWT_SECRET_KEY=${JWT_SECRET_KEY:-$(openssl rand -hex 32)}
            API_SECRET_KEY=${API_SECRET_KEY:-$(openssl rand -hex 32)}
            ;;
        staging)
            SECRET_KEY=${SECRET_KEY:-staging-$(openssl rand -hex 16)}
            JWT_SECRET_KEY=${JWT_SECRET_KEY:-staging-$(openssl rand -hex 16)}
            API_SECRET_KEY=${API_SECRET_KEY:-staging-$(openssl rand -hex 16)}
            ;;
        development)
            SECRET_KEY=${SECRET_KEY:-dev-secret-key-not-for-production}
            JWT_SECRET_KEY=${JWT_SECRET_KEY:-dev-jwt-key-not-for-production}
            API_SECRET_KEY=${API_SECRET_KEY:-dev-api-key-not-for-production}
            ;;
    esac
    
    kubectl create secret generic blacklist-secret \
        --from-literal=REGTECH_USERNAME="${REGTECH_USERNAME:-nextrade}" \
        --from-literal=REGTECH_PASSWORD="${REGTECH_PASSWORD:-Sprtmxm1@3}" \
        --from-literal=SECUDIUM_USERNAME="${SECUDIUM_USERNAME:-nextrade}" \
        --from-literal=SECUDIUM_PASSWORD="${SECUDIUM_PASSWORD:-Sprtmxm1@3}" \
        --from-literal=SECRET_KEY="$SECRET_KEY" \
        --from-literal=JWT_SECRET_KEY="$JWT_SECRET_KEY" \
        --from-literal=API_SECRET_KEY="$API_SECRET_KEY" \
        --namespace=$namespace \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_success "Application secret created for $env environment"
}

# 환경별 ConfigMap 생성
create_config_map() {
    local env=$1
    local namespace=$2
    
    log_info "Creating configuration for $env environment in namespace: $namespace"
    
    # 환경별 설정 가져오기
    local config_lines=($(get_env_config $env))
    local config_args=()
    
    for line in "${config_lines[@]}"; do
        config_args+=(--from-literal="$line")
    done
    
    kubectl create configmap blacklist-config \
        "${config_args[@]}" \
        --namespace=$namespace \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_success "Configuration created for $env environment"
}

# 단일 환경 설정
setup_environment() {
    local env=$1
    local namespace=$(get_namespace $env)
    
    log_info "Setting up $env environment in namespace: $namespace"
    
    # 네임스페이스 생성
    kubectl create namespace $namespace --dry-run=client -o yaml | kubectl apply -f -
    log_success "Namespace created: $namespace"
    
    # Registry secret 생성
    create_registry_secret $namespace
    
    # Application secret 생성
    create_app_secret $env $namespace
    
    # ConfigMap 생성
    create_config_map $env $namespace
    
    log_success "$env environment setup completed"
}

# ArgoCD 관련 설정
setup_argocd() {
    log_info "Setting up ArgoCD secrets and configurations"
    
    # ArgoCD 네임스페이스 생성
    kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
    
    # ArgoCD용 registry secret
    create_registry_secret argocd
    
    # ArgoCD Repository Secret (GitHub 토큰이 있는 경우)
    if [ ! -z "$GITHUB_TOKEN" ]; then
        kubectl create secret generic charts-repo \
            --from-literal=type=git \
            --from-literal=url=https://github.com/jclee/blacklist.git \
            --from-literal=username=not-used \
            --from-literal=password=${GITHUB_TOKEN} \
            --namespace=argocd \
            --dry-run=client -o yaml | kubectl apply -f -
        log_success "ArgoCD repository secret created"
    fi
    
    log_success "ArgoCD setup completed"
}

# 메인 실행 로직
main() {
    log_info "Starting multi-environment secrets setup for: $ENVIRONMENT"
    
    case "$ENVIRONMENT" in
        production)
            setup_environment production
            ;;
        staging)
            setup_environment staging
            ;;
        development)
            setup_environment development
            ;;
        all)
            setup_argocd
            setup_environment production
            setup_environment staging
            setup_environment development
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT"
            log_info "Usage: $0 [production|staging|development|all]"
            exit 1
            ;;
    esac
    
    # ArgoCD 설정 (all이 아닌 경우에도 실행)
    if [ "$ENVIRONMENT" != "all" ]; then
        setup_argocd
    fi
    
    echo ""
    log_success "🎉 Multi-environment secrets setup completed!"
    echo ""
    log_info "Next steps:"
    echo "1. Apply ArgoCD applications: kubectl apply -f argocd/app-of-apps.yaml"
    echo "2. Check ArgoCD UI: kubectl port-forward svc/argocd-server -n argocd 8080:443"
    echo "3. Sync applications: argocd app sync blacklist-$ENVIRONMENT"
    echo "4. Monitor deployments: kubectl get pods -n $(get_namespace $ENVIRONMENT)"
}

# 스크립트 실행
main "$@"