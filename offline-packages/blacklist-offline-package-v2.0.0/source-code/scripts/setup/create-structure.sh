#!/bin/bash
# create-structure.sh - GitOps 템플릿 기반 전체 폴더 구조 생성

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

# 기본 설정
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
CREATE_APP_REPO="${CREATE_APP_REPO:-false}"
CREATE_CONFIG_REPO="${CREATE_CONFIG_REPO:-true}"

echo "=========================================="
echo "GitOps Directory Structure Creator"
echo "=========================================="
echo ""

# Application Repository 구조 생성 (선택사항)
if [ "$CREATE_APP_REPO" = "true" ]; then
    log_info "Creating Application Repository structure..."
    
    # app-backend 디렉토리 구조
    mkdir -p app-backend/{src,tests,docs}
    mkdir -p app-backend/.github/workflows
    mkdir -p app-backend/deployment
    
    # 기본 파일 생성
    touch app-backend/.dockerignore
    touch app-backend/requirements.txt
    touch app-backend/README.md
    
    # Dockerfile 생성
    cat > app-backend/Dockerfile <<'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8541

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8541", "--timeout", "120", "main:application"]
EOF
    
    log_info "Application repository structure created"
fi

# Configuration Repository 구조 생성
if [ "$CREATE_CONFIG_REPO" = "true" ]; then
    log_info "Creating Configuration Repository structure..."
    
    # 이미 존재하는 k8s 디렉토리 확인
    if [ -d "k8s" ]; then
        log_warn "k8s directory already exists. Updating structure..."
    fi
    
    # base 디렉토리 구조
    mkdir -p k8s/base
    
    # overlays 디렉토리 구조
    for env in dev staging production; do
        mkdir -p k8s/overlays/$env
    done
    
    # ArgoCD applications 디렉토리
    mkdir -p k8s/argocd/applications
    
    # templates 디렉토리
    mkdir -p templates
    
    log_info "Configuration repository structure created/updated"
fi

# Scripts 디렉토리 구조
log_info "Creating scripts directory structure..."
mkdir -p scripts/{setup,deploy,backup,monitoring}

# 스크립트 파일 생성
SCRIPTS=(
    "scripts/setup/setup-cluster.sh"
    "scripts/setup/setup-argocd.sh"
    "scripts/setup/create-secrets.sh"
    "scripts/setup/create-structure.sh"
    "scripts/deploy/emergency-rollback.sh"
    "scripts/monitoring/check-status.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ ! -f "$script" ]; then
        touch "$script"
        chmod +x "$script"
        log_info "Created script: $script"
    fi
done

# .env.example 파일 생성
log_info "Creating environment template files..."
cat > .env.example <<'EOF'
# Kubernetes Configuration
K8S_TOKEN=<K8S_BEARER_TOKEN>
K8S_CLUSTER=https://k8s.jclee.me:443

# Registry Configuration
REGISTRY_URL=registry.jclee.me
REGISTRY_USER=admin
REGISTRY_PASS=<REGISTRY_PASSWORD>

# SSH Configuration
SSH_USER=jclee
SSH_PASS=<SSH_PASSWORD>

# GitHub Configuration
GITHUB_ORG=JCLEE94
GITHUB_TOKEN=<GITHUB_PERSONAL_ACCESS_TOKEN>

# Application Configuration
APP_NAME=blacklist

# Environment-specific settings
PROD_DB_URL=<PRODUCTION_DATABASE_URL>
PROD_REDIS_URL=redis://redis-prod:6379/0

STAGE_DB_URL=<STAGING_DATABASE_URL>
STAGE_REDIS_URL=redis://redis-staging:6379/0

DEV_DB_URL=sqlite:///app/instance/blacklist-dev.db
DEV_REDIS_URL=redis://redis-dev:6379/0

# External Service Credentials
REGTECH_USERNAME=nextrade
REGTECH_PASSWORD=<REGTECH_PASSWORD>
SECUDIUM_USERNAME=nextrade
SECUDIUM_PASSWORD=<SECUDIUM_PASSWORD>
EOF

# .gitignore 업데이트
log_info "Updating .gitignore..."
cat >> .gitignore <<'EOF'

# GitOps secrets
.env.secret
.env.secrets
*.secret
*-secret.yaml
*-secrets.yaml

# Temporary files
*.tmp
*.bak
*.swp

# Generated files
k8s/overlays/*/.env.secret
EOF

# README 템플릿 생성
log_info "Creating README templates..."
cat > k8s/README-GITOPS.md <<'EOF'
# Kubernetes GitOps Configuration

This directory contains Kubernetes manifests organized for GitOps deployment.

## Directory Structure

```
k8s/
├── base/                  # Base Kubernetes resources
├── overlays/              # Environment-specific configurations
│   ├── dev/              # Development environment
│   ├── staging/          # Staging environment
│   └── production/       # Production environment
└── argocd/               # ArgoCD application definitions
    └── applications/     # ArgoCD Application manifests
```

## Usage

1. Apply base configuration:
   ```bash
   kubectl apply -k k8s/base
   ```

2. Apply environment-specific configuration:
   ```bash
   kubectl apply -k k8s/overlays/production
   ```

3. Deploy with ArgoCD:
   ```bash
   kubectl apply -f k8s/argocd/applications/
   ```

## Environment Variables

Each environment requires a `.env.secret` file with sensitive configuration.
See `.env.example` for required variables.
EOF

# 디렉토리 구조 표시
echo ""
log_info "Directory structure created successfully!"
echo ""
log_info "Project structure:"

# tree 명령어가 있으면 사용, 없으면 find 사용
if command -v tree &> /dev/null; then
    tree -L 3 k8s scripts templates 2>/dev/null || true
else
    log_info "k8s directory:"
    find k8s -type d -maxdepth 3 | sort
    echo ""
    log_info "scripts directory:"
    find scripts -type d -maxdepth 2 | sort
fi

echo ""
echo "=========================================="
log_info "Setup Instructions:"
echo "=========================================="
echo "1. Copy .env.example to .env and fill in values"
echo "2. Run ./scripts/setup/setup-cluster.sh"
echo "3. Run ./scripts/setup/setup-argocd.sh"
echo "4. Run ./scripts/setup/create-secrets.sh"
echo "5. Deploy applications with ArgoCD"
echo ""