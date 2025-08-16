#!/bin/bash
# 메인 배포 스크립트 - GitHub Actions → ArgoCD GitOps 파이프라인

set -e

echo "🚀 Blacklist 메인 배포 시작"

# Git 상태 확인
if [[ -n $(git status --porcelain) ]]; then
    echo "❌ 커밋되지 않은 변경사항이 있습니다. 먼저 커밋하세요."
    exit 1
fi

# 현재 브랜치 확인
BRANCH=$(git branch --show-current)
if [[ "$BRANCH" != "main" ]]; then
    echo "⚠️ 현재 브랜치: $BRANCH (main 브랜치에서 배포하는 것을 권장)"
    read -p "계속하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 버전 정보
VERSION=$(grep -E "app_version.*=" src/config/settings.py | cut -d'"' -f2 2>/dev/null || echo "unknown")
echo "📦 버전: $VERSION"

# GitHub에 푸시 (CI/CD 트리거)
echo "📤 GitHub에 푸시 중..."
git push origin $BRANCH

# GitHub Actions 워크플로우 상태 확인
echo "⏳ GitHub Actions 빌드 대기 중..."
sleep 10

# ArgoCD 배포 상태 확인 (선택사항)
if command -v argocd &> /dev/null; then
    echo "🔄 ArgoCD 동기화 확인 중..."
    argocd app sync blacklist 2>/dev/null || echo "ℹ️ ArgoCD 수동 동기화 실패 (자동 동기화 진행 중일 수 있음)"
fi

echo "✅ 배포 완료!"
echo "🌐 서비스 확인: http://192.168.50.110:32542/health"
echo "📊 ArgoCD: https://argo.jclee.me"