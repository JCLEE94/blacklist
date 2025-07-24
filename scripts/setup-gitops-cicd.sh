#!/bin/bash
# GitOps CI/CD 구축 템플릿 - Blacklist Management System
set -e

echo "🚀 Blacklist Management System - GitOps CI/CD 파이프라인 구축"
echo "=============================================================="

# 기존 파일 정리 (선택적)
read -p "기존 CI/CD 설정을 정리하시겠습니까? (y/N): " CLEAN_EXISTING
if [[ "$CLEAN_EXISTING" =~ ^[Yy]$ ]]; then
    echo "🧹 기존 설정 정리 중..."
    rm -rf .github/workflows/old-* || true
    rm -f docker-compose.old.yml .env.old || true
    rm -rf k8s-old/ kubernetes-old/ || true
fi

# GitHub CLI 로그인 체크
echo "📋 GitHub CLI 상태 확인..."
if ! gh auth status >/dev/null 2>&1; then
    echo "⚠ GitHub CLI 로그인이 필요합니다."
    gh auth login
fi

# 프로젝트 설정값 (Blacklist 특화)
GITHUB_ORG="${GITHUB_ORG:-JCLEE94}"
APP_NAME="blacklist"
NAMESPACE="${NAMESPACE:-blacklist}"
NODEPORT="${NODEPORT:-32542}"  # From CLAUDE.md
DEV_PORT="${DEV_PORT:-8541}"   # From CLAUDE.md  
PROD_PORT="${PROD_PORT:-2541}" # From CLAUDE.md

echo "📝 프로젝트 설정:"
echo "   GitHub Org: ${GITHUB_ORG}"
echo "   App Name: ${APP_NAME}"
echo "   Namespace: ${NAMESPACE}"
echo "   NodePort: ${NODEPORT}"
echo "   Dev Port: ${DEV_PORT}"
echo "   Prod Port: ${PROD_PORT}"

# Registry 설정 (기존 CLAUDE.md 정보 사용)
REGISTRY_URL="${REGISTRY_URL:-registry.jclee.me}"
REGISTRY_USERNAME="${REGISTRY_USERNAME:-admin}"
REGISTRY_PASSWORD="${REGISTRY_PASSWORD:-bingogo1}"

# ChartMuseum 설정
CHARTMUSEUM_URL="${CHARTMUSEUM_URL:-https://charts.jclee.me}"
CHARTMUSEUM_USERNAME="${CHARTMUSEUM_USERNAME:-admin}"
CHARTMUSEUM_PASSWORD="${CHARTMUSEUM_PASSWORD:-bingogo1}"

# ArgoCD 설정 (기존 인프라 기반)
ARGOCD_URL="${ARGOCD_URL:-argo.jclee.me}"
ARGOCD_USERNAME="${ARGOCD_USERNAME:-admin}"
ARGOCD_PASSWORD="${ARGOCD_PASSWORD:-bingogo1}"

echo "🔐 GitHub Secrets/Variables 설정 중..."

# GitHub Secrets 설정
gh secret list | grep -q "REGISTRY_URL" || gh secret set REGISTRY_URL -b "${REGISTRY_URL}"
gh secret list | grep -q "REGISTRY_USERNAME" || gh secret set REGISTRY_USERNAME -b "${REGISTRY_USERNAME}"
gh secret list | grep -q "REGISTRY_PASSWORD" || gh secret set REGISTRY_PASSWORD -b "${REGISTRY_PASSWORD}"
gh secret list | grep -q "CHARTMUSEUM_URL" || gh secret set CHARTMUSEUM_URL -b "${CHARTMUSEUM_URL}"
gh secret list | grep -q "CHARTMUSEUM_USERNAME" || gh secret set CHARTMUSEUM_USERNAME -b "${CHARTMUSEUM_USERNAME}"
gh secret list | grep -q "CHARTMUSEUM_PASSWORD" || gh secret set CHARTMUSEUM_PASSWORD -b "${CHARTMUSEUM_PASSWORD}"
gh secret list | grep -q "ARGOCD_URL" || gh secret set ARGOCD_URL -b "${ARGOCD_URL}"
gh secret list | grep -q "ARGOCD_USERNAME" || gh secret set ARGOCD_USERNAME -b "${ARGOCD_USERNAME}"
gh secret list | grep -q "ARGOCD_PASSWORD" || gh secret set ARGOCD_PASSWORD -b "${ARGOCD_PASSWORD}"

# Application Secrets (기존 CLAUDE.md에서)
gh secret list | grep -q "REGTECH_USERNAME" || gh secret set REGTECH_USERNAME -b "nextrade"
gh secret list | grep -q "REGTECH_PASSWORD" || gh secret set REGTECH_PASSWORD -b "Sprtmxm1@3"
gh secret list | grep -q "SECUDIUM_USERNAME" || gh secret set SECUDIUM_USERNAME -b "nextrade"
gh secret list | grep -q "SECUDIUM_PASSWORD" || gh secret set SECUDIUM_PASSWORD -b "Sprtmxm1@3"

# GitHub Variables 설정
gh variable list | grep -q "GITHUB_ORG" || gh variable set GITHUB_ORG -b "${GITHUB_ORG}"
gh variable list | grep -q "APP_NAME" || gh variable set APP_NAME -b "${APP_NAME}"
gh variable list | grep -q "NAMESPACE" || gh variable set NAMESPACE -b "${NAMESPACE}"
gh variable list | grep -q "NODEPORT" || gh variable set NODEPORT -b "${NODEPORT}"
gh variable list | grep -q "DEV_PORT" || gh variable set DEV_PORT -b "${DEV_PORT}"
gh variable list | grep -q "PROD_PORT" || gh variable set PROD_PORT -b "${PROD_PORT}"

echo "✅ GitHub Secrets/Variables 설정 완료"

# 다음 단계 안내
echo ""
echo "🎉 GitOps CI/CD 초기 구성 완료!"
echo "==============================="
echo ""
echo "📋 다음 단계:"
echo "1. Helm Charts 생성: ./scripts/generate-helm-charts.sh"
echo "2. GitHub Actions 워크플로우 생성: ./scripts/create-github-workflow.sh"
echo "3. ArgoCD 애플리케이션 설정: ./scripts/setup-argocd-app.sh"
echo "4. 배포 검증 스크립트 실행: ./scripts/validate-deployment.sh"
echo ""
echo "🚀 준비가 완료되면 다음 명령어로 배포:"
echo "   git add . && git commit -m 'feat: GitOps CI/CD 구성' && git push origin main"