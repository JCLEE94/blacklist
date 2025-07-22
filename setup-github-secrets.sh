#!/bin/bash

echo "🔐 GitHub Secrets 설정 스크립트"
echo "==============================="

# GitHub CLI 확인
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh)가 설치되지 않았습니다."
    echo "설치 방법: https://cli.github.com/"
    exit 1
fi

# 인증 상태 확인
if ! gh auth status &> /dev/null; then
    echo "❌ GitHub CLI 인증이 필요합니다."
    echo "인증 명령어: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI 인증 완료"

# Secrets 설정
echo ""
echo "🔧 GitHub Secrets 설정 중..."

# Docker Registry 설정
echo "📦 Docker Registry Secrets..."
gh secret set DOCKER_REGISTRY_USER -b "admin"
gh secret set DOCKER_REGISTRY_PASS -b "bingogo1"

# Helm Repository 설정
echo "📊 Helm Repository Secrets..."
gh secret set HELM_REPO_USERNAME -b "admin"
gh secret set HELM_REPO_PASSWORD -b "bingogo1"

# 추가 레지스트리 설정 (백업용)
echo "🔄 Additional Registry Secrets..."
gh secret set REGISTRY_USERNAME -b "admin"
gh secret set REGISTRY_PASSWORD -b "bingogo1"

echo ""
echo "✅ 모든 GitHub Secrets 설정 완료!"
echo ""
echo "설정된 Secrets:"
echo "- DOCKER_REGISTRY_USER: admin"
echo "- DOCKER_REGISTRY_PASS: ••••••••"
echo "- HELM_REPO_USERNAME: admin" 
echo "- HELM_REPO_PASSWORD: ••••••••"
echo "- REGISTRY_USERNAME: admin"
echo "- REGISTRY_PASSWORD: ••••••••"
echo ""
echo "🚀 이제 main 브랜치에 푸시하여 GitOps 파이프라인을 실행할 수 있습니다!"

# Secrets 확인
echo ""
echo "🔍 설정된 Secrets 확인:"
gh secret list