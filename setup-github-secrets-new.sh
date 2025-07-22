#!/bin/bash
# GitHub Actions Secrets 자동 설정 스크립트
# GitOps 배포 템플릿용 필수 Secrets 구성

set -e

echo "🔐 GitHub Actions Secrets 설정을 시작합니다..."

# 환경 변수 로드
if [ -f .env ]; then
    source .env
    echo "✅ .env 파일에서 환경 변수를 로드했습니다."
else
    echo "❌ .env 파일이 없습니다. .env.example을 복사하여 .env를 생성하세요."
    echo "   cp .env.example .env"
    exit 1
fi

# GitHub CLI 설치 확인
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh)가 설치되어 있지 않습니다."
    echo "   설치: https://cli.github.com/"
    exit 1
fi

# GitHub 인증 확인
if ! gh auth status >/dev/null 2>&1; then
    echo "❌ GitHub CLI에 로그인이 필요합니다."
    echo "   실행: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI 인증 확인 완료"

# Repository 정보 확인
REPO_FULL_NAME=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")
if [ -z "$REPO_FULL_NAME" ]; then
    echo "❌ 현재 디렉토리가 GitHub 저장소가 아니거나 원격 저장소에 연결되어 있지 않습니다."
    exit 1
fi

echo "📦 저장소: $REPO_FULL_NAME"

# === 필수 Secrets 설정 ===
echo ""
echo "🔑 GitHub Secrets 설정 중..."

# Docker Registry 인증
echo "  📦 Docker Registry Secrets..."
gh secret set DOCKER_REGISTRY_USER --body "$DOCKER_REGISTRY_USER" || true
gh secret set DOCKER_REGISTRY_PASS --body "$DOCKER_REGISTRY_PASS" || true
gh secret set REGISTRY_URL --body "$REGISTRY_URL" || true

# Helm Repository 인증
echo "  📊 Helm Repository Secrets..."  
gh secret set HELM_REPO_USERNAME --body "$HELM_REPO_USERNAME" || true
gh secret set HELM_REPO_PASSWORD --body "$HELM_REPO_PASSWORD" || true
gh secret set CHARTS_URL --body "$CHARTS_URL" || true

# Kubernetes 클러스터 인증
echo "  ☸️ Kubernetes Cluster Secrets..."
gh secret set K8S_TOKEN --body "$K8S_TOKEN" || true
gh secret set K8S_CLUSTER --body "$K8S_CLUSTER" || true

# ArgoCD 인증
echo "  🚀 ArgoCD Secrets..."
gh secret set ARGOCD_SERVER --body "$ARGOCD_SERVER" || true
gh secret set ARGOCD_USERNAME --body "$ARGOCD_USERNAME" || true
gh secret set ARGOCD_PASSWORD --body "$ARGOCD_PASSWORD" || true

# 애플리케이션 인증 정보
echo "  🔐 Application Secrets..."
gh secret set REGTECH_USERNAME --body "$REGTECH_USERNAME" || true
gh secret set REGTECH_PASSWORD --body "$REGTECH_PASSWORD" || true
gh secret set SECUDIUM_USERNAME --body "$SECUDIUM_USERNAME" || true
gh secret set SECUDIUM_PASSWORD --body "$SECUDIUM_PASSWORD" || true

# 보안 키들
echo "  🔒 Security Keys..."
gh secret set SECRET_KEY --body "$SECRET_KEY" || true
gh secret set JWT_SECRET_KEY --body "$JWT_SECRET_KEY" || true
gh secret set API_SECRET_KEY --body "$API_SECRET_KEY" || true

# Cloudflare Tunnel (선택사항)
if [ "$ENABLE_CLOUDFLARED" = "true" ]; then
    echo "  ☁️ Cloudflare Tunnel Secrets..."
    gh secret set CLOUDFLARE_TUNNEL_TOKEN --body "$CLOUDFLARE_TUNNEL_TOKEN" || true
    gh secret set CLOUDFLARE_HOSTNAME --body "$CLOUDFLARE_HOSTNAME" || true
fi

# === Repository Variables 설정 ===
echo ""
echo "📝 GitHub Repository Variables 설정 중..."

gh variable set GITHUB_ORG --body "$GITHUB_ORG" || true
gh variable set APP_NAME --body "$APP_NAME" || true
gh variable set APP_NAMESPACE --body "$APP_NAMESPACE" || true
gh variable set NODE_PORT --body "$NODE_PORT" || true
gh variable set ARGOCD_URL --body "$ARGOCD_URL" || true

# === Environments 설정 (선택사항) ===
echo ""
echo "🌍 GitHub Environments 설정 중..."

# Production Environment
gh api repos/$REPO_FULL_NAME/environments/production --method PUT --field wait_timer=0 >/dev/null 2>&1 || true

# Development Environment  
gh api repos/$REPO_FULL_NAME/environments/development --method PUT --field wait_timer=0 >/dev/null 2>&1 || true

echo ""
echo "✅ GitHub Actions Secrets 및 Variables 설정이 완료되었습니다!"
echo ""
echo "📋 설정된 Secrets 목록:"
echo "   - DOCKER_REGISTRY_USER/PASS"
echo "   - REGISTRY_URL"
echo "   - HELM_REPO_USERNAME/PASSWORD" 
echo "   - CHARTS_URL"
echo "   - K8S_TOKEN/CLUSTER"
echo "   - ARGOCD_SERVER/USERNAME/PASSWORD"
echo "   - REGTECH/SECUDIUM USERNAME/PASSWORD"
echo "   - SECRET/JWT/API_SECRET_KEY"

if [ "$ENABLE_CLOUDFLARED" = "true" ]; then
echo "   - CLOUDFLARE_TUNNEL_TOKEN/HOSTNAME"
fi

echo ""
echo "📋 설정된 Variables 목록:"
echo "   - GITHUB_ORG: $GITHUB_ORG"
echo "   - APP_NAME: $APP_NAME"
echo "   - APP_NAMESPACE: $APP_NAMESPACE"
echo "   - NODE_PORT: $NODE_PORT"
echo "   - ARGOCD_URL: $ARGOCD_URL"

echo ""
echo "🚀 이제 GitHub Actions CI/CD 파이프라인을 실행할 수 있습니다!"
echo "   git add . && git commit -m 'feat: add GitOps CI/CD pipeline' && git push"