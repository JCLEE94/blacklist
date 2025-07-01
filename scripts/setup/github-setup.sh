#!/bin/bash

# GitHub 저장소 설정 스크립트
# 사용법: ./scripts/github-setup.sh

set -e

echo "🚀 GitHub 저장소 설정을 시작합니다..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 현재 디렉토리 확인
if [ ! -f "main.py" ]; then
    echo -e "${RED}❌ 프로젝트 루트 디렉토리에서 실행해주세요.${NC}"
    exit 1
fi

# Git 초기화 확인
if [ ! -d ".git" ]; then
    echo "📁 Git 저장소 초기화..."
    git init
fi

# GitHub CLI 설치 확인
if ! command -v gh &> /dev/null; then
    echo -e "${YELLOW}⚠️  GitHub CLI가 설치되어 있지 않습니다.${NC}"
    echo "설치 방법: https://cli.github.com/"
    echo "수동으로 저장소를 생성하고 다음 단계를 진행하세요."
else
    echo "✅ GitHub CLI 확인됨"
    
    # GitHub 로그인 확인
    if ! gh auth status &> /dev/null; then
        echo "🔐 GitHub 로그인이 필요합니다..."
        gh auth login
    fi
    
    # 저장소 생성
    echo "📦 GitHub 저장소 생성..."
    REPO_NAME="blacklist-management"
    
    if gh repo view "$REPO_NAME" &> /dev/null; then
        echo -e "${YELLOW}⚠️  저장소가 이미 존재합니다: $REPO_NAME${NC}"
    else
        gh repo create "$REPO_NAME" \
            --private \
            --description "Enterprise Blacklist Management System with FortiGate Integration" \
            --add-readme=false
        echo -e "${GREEN}✅ 저장소 생성 완료: $REPO_NAME${NC}"
    fi
fi

# 원격 저장소 설정
echo "🔗 원격 저장소 연결..."
REMOTE_URL=$(gh repo view --json sshUrl -q .sshUrl 2>/dev/null || echo "")

if [ -z "$REMOTE_URL" ]; then
    echo -e "${YELLOW}⚠️  원격 저장소 URL을 자동으로 가져올 수 없습니다.${NC}"
    echo "수동으로 설정해주세요: git remote add origin <your-repo-url>"
else
    if git remote get-url origin &> /dev/null; then
        echo "기존 origin 업데이트..."
        git remote set-url origin "$REMOTE_URL"
    else
        git remote add origin "$REMOTE_URL"
    fi
    echo -e "${GREEN}✅ 원격 저장소 연결 완료${NC}"
fi

# GitHub Secrets 설정 안내
echo ""
echo "🔐 GitHub Secrets 설정이 필요합니다:"
echo ""
echo "다음 secrets를 GitHub 저장소 설정에서 추가해주세요:"
echo "  Settings → Secrets and variables → Actions"
echo ""
echo "필수 Secrets:"
echo "  - REGISTRY_USERNAME: Docker 레지스트리 사용자명"
echo "  - REGISTRY_PASSWORD: Docker 레지스트리 비밀번호"
echo "  - DEPLOY_USERNAME: 배포 서버 SSH 사용자명"
echo "  - DEPLOY_SSH_KEY: 배포 서버 SSH 개인키"
echo ""
echo "선택적 Secrets:"
echo "  - SLACK_WEBHOOK: Slack 알림 웹훅 URL"
echo "  - GRAFANA_PASSWORD: Grafana 관리자 비밀번호"
echo ""

# 브랜치 보호 규칙 설정
if command -v gh &> /dev/null; then
    echo "🛡️  브랜치 보호 규칙 설정..."
    
    # main 브랜치 보호
    gh api repos/:owner/:repo/branches/main/protection \
        --method PUT \
        --field required_status_checks='{"strict":true,"contexts":["lint","test"]}' \
        --field enforce_admins=false \
        --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
        --field restrictions=null \
        --field allow_force_pushes=false \
        --field allow_deletions=false \
        2>/dev/null || echo -e "${YELLOW}⚠️  브랜치 보호 규칙 설정 실패 (수동 설정 필요)${NC}"
fi

# 첫 커밋 생성
if [ -z "$(git log --oneline -1 2>/dev/null)" ]; then
    echo "📝 첫 커밋 생성..."
    git add .
    git commit -m "Initial commit: Blacklist Management System

- Flask-based REST API with dependency injection
- Multi-source data collection (REGTECH, SECUDIUM)
- FortiGate External Connector integration
- Docker containerization with CI/CD pipeline
- Comprehensive monitoring and logging"
fi

# 태그 생성
echo "🏷️  초기 버전 태그 생성..."
git tag -a v1.0.0 -m "Initial release" 2>/dev/null || echo "태그가 이미 존재합니다"

# Push
echo "⬆️  코드 푸시..."
git push -u origin main --tags || echo -e "${YELLOW}⚠️  푸시 실패 (인증 확인 필요)${NC}"

echo ""
echo -e "${GREEN}✨ GitHub 설정이 완료되었습니다!${NC}"
echo ""
echo "다음 단계:"
echo "1. GitHub Secrets 설정 완료"
echo "2. 첫 PR 생성으로 CI/CD 파이프라인 테스트"
echo "3. README.md에 배지 추가:"
echo ""
echo "[![Build and Deploy](https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/actions/workflows/build-deploy.yml/badge.svg)](https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/actions/workflows/build-deploy.yml)"
echo "[![Security Scan](https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/security/code-scanning/badge.svg)](https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/security/code-scanning)"
echo ""