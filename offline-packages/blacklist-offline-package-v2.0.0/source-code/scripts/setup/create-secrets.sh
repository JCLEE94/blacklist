#!/bin/bash
# 비밀 정보 생성 스크립트
# GitOps 템플릿 기반 Secret 생성

set -e

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 환경별 기본값 설정
set_defaults() {
    # Production
    PROD_DB_URL="${PROD_DB_URL:-sqlite:///app/instance/blacklist.db}"
    PROD_REDIS_URL="${PROD_REDIS_URL:-redis://redis-prod:6379/0}"
    PROD_JWT_SECRET="${PROD_JWT_SECRET:-$(openssl rand -base64 32)}"
    PROD_API_KEY="${PROD_API_KEY:-$(openssl rand -hex 32)}"
    PROD_SECRET_KEY="${PROD_SECRET_KEY:-$(openssl rand -base64 32)}"
    
    # Staging
    STAGE_DB_URL="${STAGE_DB_URL:-sqlite:///app/instance/blacklist-staging.db}"
    STAGE_REDIS_URL="${STAGE_REDIS_URL:-redis://redis-staging:6379/0}"
    STAGE_JWT_SECRET="${STAGE_JWT_SECRET:-$(openssl rand -base64 32)}"
    STAGE_API_KEY="${STAGE_API_KEY:-$(openssl rand -hex 32)}"
    STAGE_SECRET_KEY="${STAGE_SECRET_KEY:-$(openssl rand -base64 32)}"
    
    # Development
    DEV_DB_URL="${DEV_DB_URL:-sqlite:///app/instance/blacklist-dev.db}"
    DEV_REDIS_URL="${DEV_REDIS_URL:-redis://redis-dev:6379/0}"
    DEV_JWT_SECRET="${DEV_JWT_SECRET:-dev-jwt-secret-key}"
    DEV_API_KEY="${DEV_API_KEY:-dev-api-key}"
    DEV_SECRET_KEY="${DEV_SECRET_KEY:-dev-secret-key}"
    
    # REGTECH/SECUDIUM 인증 정보
    REGTECH_USERNAME="${REGTECH_USERNAME:-nextrade}"
    REGTECH_PASSWORD="${REGTECH_PASSWORD:-Sprtmxm1@3}"
    SECUDIUM_USERNAME="${SECUDIUM_USERNAME:-nextrade}"
    SECUDIUM_PASSWORD="${SECUDIUM_PASSWORD:-Sprtmxm1@3}"
}

# Secret 생성 함수
create_secret() {
    local namespace=$1
    local secret_name=$2
    shift 2
    
    log_info "Creating secret '$secret_name' in namespace '$namespace'..."
    
    kubectl create secret generic $secret_name \
        "$@" \
        --namespace=$namespace \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_info "Secret '$secret_name' created/updated in namespace '$namespace'"
}

# 메인 실행
main() {
    log_info "Starting secrets creation..."
    
    # 기본값 설정
    set_defaults
    
    # Production secrets
    log_info "Creating Production secrets..."
    create_secret "blacklist" "blacklist-secret" \
        --from-literal=DATABASE_URL="${PROD_DB_URL}" \
        --from-literal=REDIS_URL="${PROD_REDIS_URL}" \
        --from-literal=JWT_SECRET_KEY="${PROD_JWT_SECRET}" \
        --from-literal=API_KEY="${PROD_API_KEY}" \
        --from-literal=SECRET_KEY="${PROD_SECRET_KEY}" \
        --from-literal=REGTECH_USERNAME="${REGTECH_USERNAME}" \
        --from-literal=REGTECH_PASSWORD="${REGTECH_PASSWORD}" \
        --from-literal=SECUDIUM_USERNAME="${SECUDIUM_USERNAME}" \
        --from-literal=SECUDIUM_PASSWORD="${SECUDIUM_PASSWORD}"
    
    # Staging secrets
    log_info "Creating Staging secrets..."
    create_secret "blacklist-staging" "blacklist-secret" \
        --from-literal=DATABASE_URL="${STAGE_DB_URL}" \
        --from-literal=REDIS_URL="${STAGE_REDIS_URL}" \
        --from-literal=JWT_SECRET_KEY="${STAGE_JWT_SECRET}" \
        --from-literal=API_KEY="${STAGE_API_KEY}" \
        --from-literal=SECRET_KEY="${STAGE_SECRET_KEY}" \
        --from-literal=REGTECH_USERNAME="${REGTECH_USERNAME}" \
        --from-literal=REGTECH_PASSWORD="${REGTECH_PASSWORD}" \
        --from-literal=SECUDIUM_USERNAME="${SECUDIUM_USERNAME}" \
        --from-literal=SECUDIUM_PASSWORD="${SECUDIUM_PASSWORD}"
    
    # Development secrets
    log_info "Creating Development secrets..."
    create_secret "blacklist-dev" "blacklist-secret" \
        --from-literal=DATABASE_URL="${DEV_DB_URL}" \
        --from-literal=REDIS_URL="${DEV_REDIS_URL}" \
        --from-literal=JWT_SECRET_KEY="${DEV_JWT_SECRET}" \
        --from-literal=API_KEY="${DEV_API_KEY}" \
        --from-literal=SECRET_KEY="${DEV_SECRET_KEY}" \
        --from-literal=REGTECH_USERNAME="${REGTECH_USERNAME}" \
        --from-literal=REGTECH_PASSWORD="${REGTECH_PASSWORD}" \
        --from-literal=SECUDIUM_USERNAME="${SECUDIUM_USERNAME}" \
        --from-literal=SECUDIUM_PASSWORD="${SECUDIUM_PASSWORD}"
    
    # GitHub Secret for ArgoCD (if GITHUB_TOKEN is set)
    if [ -n "$GITHUB_TOKEN" ]; then
        log_info "Creating GitHub credentials secret for ArgoCD..."
        create_secret "argocd" "github-creds" \
            --from-literal=type=git \
            --from-literal=url=https://github.com/JCLEE94/blacklist \
            --from-literal=username=not-used \
            --from-literal=password="${GITHUB_TOKEN}"
    else
        log_warn "GITHUB_TOKEN not set. Skipping GitHub credentials secret."
        log_warn "Set GITHUB_TOKEN environment variable and re-run if you need ArgoCD to access private repos."
    fi
    
    # Secret 생성 확인
    echo ""
    log_info "Secrets created successfully!"
    echo ""
    log_info "Verifying secrets:"
    echo ""
    
    for ns in blacklist blacklist-staging blacklist-dev; do
        echo "Namespace: $ns"
        kubectl get secrets -n $ns | grep blacklist-secret || log_warn "No blacklist-secret found in $ns"
        echo ""
    done
    
    # 생성된 값 저장 (옵션)
    if [ "$SAVE_GENERATED_SECRETS" = "true" ]; then
        log_info "Saving generated secrets to .env.secrets file..."
        cat > .env.secrets <<EOF
# Generated secrets - $(date)
# IMPORTANT: Keep this file secure and do not commit to version control!

# Production
PROD_DB_URL=$PROD_DB_URL
PROD_REDIS_URL=$PROD_REDIS_URL
PROD_JWT_SECRET=$PROD_JWT_SECRET
PROD_API_KEY=$PROD_API_KEY
PROD_SECRET_KEY=$PROD_SECRET_KEY

# Staging
STAGE_DB_URL=$STAGE_DB_URL
STAGE_REDIS_URL=$STAGE_REDIS_URL
STAGE_JWT_SECRET=$STAGE_JWT_SECRET
STAGE_API_KEY=$STAGE_API_KEY
STAGE_SECRET_KEY=$STAGE_SECRET_KEY

# Development
DEV_DB_URL=$DEV_DB_URL
DEV_REDIS_URL=$DEV_REDIS_URL
DEV_JWT_SECRET=$DEV_JWT_SECRET
DEV_API_KEY=$DEV_API_KEY
DEV_SECRET_KEY=$DEV_SECRET_KEY

# External Services
REGTECH_USERNAME=$REGTECH_USERNAME
REGTECH_PASSWORD=$REGTECH_PASSWORD
SECUDIUM_USERNAME=$SECUDIUM_USERNAME
SECUDIUM_PASSWORD=$SECUDIUM_PASSWORD
EOF
        chmod 600 .env.secrets
        log_info "Secrets saved to .env.secrets (mode 600)"
    fi
}

# 스크립트 실행
main "$@"