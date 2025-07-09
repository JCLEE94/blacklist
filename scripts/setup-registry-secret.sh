#!/bin/bash

# Registry Secret 설정 스크립트
# Docker config.json을 사용하여 Kubernetes Secret 생성

set -euo pipefail

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 기본값
DOCKER_CONFIG_PATH="${DOCKER_CONFIG_PATH:-$HOME/.docker/config.json}"
SECRET_NAME="${SECRET_NAME:-regcred}"
NAMESPACES="${NAMESPACES:-blacklist blacklist-dev blacklist-staging}"

# 로깅 함수
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

# Docker config 확인
check_docker_config() {
    log "Checking Docker configuration..."
    
    if [ ! -f "$DOCKER_CONFIG_PATH" ]; then
        error "Docker config not found at $DOCKER_CONFIG_PATH"
    fi
    
    # registry.jclee.me 인증 정보 확인
    if ! grep -q "registry.jclee.me" "$DOCKER_CONFIG_PATH"; then
        error "registry.jclee.me not found in Docker config"
    fi
    
    success "Docker config found and valid"
}

# Kubernetes Secret 생성
create_registry_secret() {
    local namespace=$1
    
    log "Creating registry secret in namespace: $namespace"
    
    # 네임스페이스 생성 (없으면)
    kubectl create namespace "$namespace" --dry-run=client -o yaml | kubectl apply -f - &>/dev/null || true
    
    # 기존 Secret 삭제 (있으면)
    kubectl delete secret "$SECRET_NAME" -n "$namespace" --ignore-not-found=true
    
    # Docker config를 사용하여 Secret 생성
    kubectl create secret generic "$SECRET_NAME" \
        --from-file=.dockerconfigjson="$DOCKER_CONFIG_PATH" \
        --type=kubernetes.io/dockerconfigjson \
        -n "$namespace"
    
    success "Registry secret created in namespace: $namespace"
}

# 모든 네임스페이스에 Secret 생성
create_all_secrets() {
    log "Creating registry secrets in all namespaces..."
    
    for namespace in $NAMESPACES; do
        create_registry_secret "$namespace"
    done
}

# Secret 검증
verify_secrets() {
    log "Verifying registry secrets..."
    
    for namespace in $NAMESPACES; do
        if kubectl get secret "$SECRET_NAME" -n "$namespace" &>/dev/null; then
            success "Secret verified in namespace: $namespace"
        else
            warning "Secret not found in namespace: $namespace"
        fi
    done
}

# GitHub Actions Secret 설정 안내
show_github_setup() {
    log "GitHub Actions setup instructions:"
    
    echo
    echo "Add the following secrets to your GitHub repository:"
    echo "  Settings → Secrets and variables → Actions → New repository secret"
    echo
    echo "1. REGISTRY_USERNAME:"
    echo "   Value: _token"
    echo
    echo "2. REGISTRY_PASSWORD:"
    echo "   Value: <your-cloudflare-access-token>"
    echo
    echo "The token can be extracted from the auth field in your Docker config."
    echo "It's the part after '_token:' when base64 decoded."
}

# ArgoCD Secret 설정
setup_argocd_secret() {
    log "Setting up ArgoCD registry secret..."
    
    # ArgoCD가 설치되어 있는지 확인
    if ! kubectl get namespace argocd &>/dev/null; then
        warning "ArgoCD namespace not found, skipping ArgoCD setup"
        return
    fi
    
    # ArgoCD namespace에도 Secret 생성
    create_registry_secret "argocd"
    
    # ArgoCD에 레지스트리 추가
    if command -v argocd &>/dev/null; then
        log "Adding registry to ArgoCD..."
        
        # Docker config에서 auth 추출
        local auth=$(jq -r '.auths."registry.jclee.me".auth' "$DOCKER_CONFIG_PATH")
        local decoded=$(echo "$auth" | base64 -d)
        local username=$(echo "$decoded" | cut -d: -f1)
        local password=$(echo "$decoded" | cut -d: -f2-)
        
        # ArgoCD에 레지스트리 추가
        argocd repo add registry.jclee.me \
            --type helm \
            --name jclee-registry \
            --username "$username" \
            --password "$password" \
            --upsert || warning "Failed to add registry to ArgoCD"
    fi
}

# 메인 실행
main() {
    log "Starting registry secret setup"
    
    # Docker config 확인
    check_docker_config
    
    # 모든 네임스페이스에 Secret 생성
    create_all_secrets
    
    # Secret 검증
    verify_secrets
    
    # ArgoCD 설정
    setup_argocd_secret
    
    # GitHub 설정 안내
    show_github_setup
    
    success "Registry secret setup completed!"
    
    echo
    log "Test the secret with:"
    echo "  kubectl run test-pull --rm -it --image=registry.jclee.me/blacklist:latest -- echo 'Pull successful!'"
}

# 명령행 옵션 처리
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--file)
            DOCKER_CONFIG_PATH="$2"
            shift 2
            ;;
        -s|--secret)
            SECRET_NAME="$2"
            shift 2
            ;;
        -n|--namespaces)
            NAMESPACES="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -f, --file PATH       Path to Docker config.json (default: ~/.docker/config.json)"
            echo "  -s, --secret NAME     Secret name (default: regcred)"
            echo "  -n, --namespaces NS   Space-separated list of namespaces"
            echo "  -h, --help           Show this help message"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# 실행
main