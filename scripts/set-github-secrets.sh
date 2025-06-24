#!/bin/bash
# GitHub Secrets 설정 스크립트
# 환경 변수에서 값을 읽어 GitHub 리포지토리에 설정

set -e

echo "🔐 GitHub Secrets 설정을 시작합니다..."

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# GitHub CLI 확인
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ GitHub CLI가 설치되어 있지 않습니다.${NC}"
    echo "설치: https://cli.github.com/"
    exit 1
fi

# 인증 확인
if ! gh auth status &> /dev/null; then
    echo -e "${RED}❌ GitHub 로그인이 필요합니다.${NC}"
    gh auth login
fi

# 저장소 설정
REPO="${GITHUB_REPOSITORY:-qws941/blacklist}"

echo "📦 저장소: $REPO"

# 필수 환경 변수 확인
if [ -z "$REGISTRY_USERNAME" ] || [ -z "$REGISTRY_PASSWORD" ]; then
    echo -e "${RED}❌ Error: 필수 환경 변수가 설정되지 않았습니다.${NC}"
    echo ""
    echo "💡 사용법:"
    echo "   export REGISTRY_USERNAME=your-username"
    echo "   export REGISTRY_PASSWORD=your-password"
    echo "   $0"
    echo ""
    echo "또는:"
    echo "   REGISTRY_USERNAME=username REGISTRY_PASSWORD=password $0"
    exit 1
fi

# Secrets 설정
echo ""
echo "🔐 Secrets 설정 중..."

# Private Registry 인증
gh secret set REGISTRY_USERNAME --repo "$REPO" --body "$REGISTRY_USERNAME"
echo -e "${GREEN}✅ REGISTRY_USERNAME 설정 완료${NC}"

gh secret set REGISTRY_PASSWORD --repo "$REPO" --body "$REGISTRY_PASSWORD"
echo -e "${GREEN}✅ REGISTRY_PASSWORD 설정 완료${NC}"

# SSH 키 설정 (선택사항)
if [ -f ~/.ssh/deploy_key ]; then
    gh secret set DEPLOY_SSH_KEY --repo "$REPO" < ~/.ssh/deploy_key
    echo -e "${GREEN}✅ DEPLOY_SSH_KEY 설정 완료${NC}"
elif [ -f ~/.ssh/id_rsa ]; then
    echo -e "${YELLOW}⚠️  ~/.ssh/deploy_key가 없어 ~/.ssh/id_rsa를 사용합니다.${NC}"
    read -p "계속하시겠습니까? (y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        gh secret set DEPLOY_SSH_KEY --repo "$REPO" < ~/.ssh/id_rsa
        echo -e "${GREEN}✅ DEPLOY_SSH_KEY 설정 완료${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  SSH 키가 없습니다. SSH 배포가 필요한 경우 나중에 설정하세요.${NC}"
fi

# 선택적 Secrets
echo ""
echo -e "${YELLOW}선택적 Secrets 설정${NC}"

# 외부 서비스 인증 정보
if [ -n "$REGTECH_USERNAME" ] && [ -n "$REGTECH_PASSWORD" ]; then
    gh secret set REGTECH_USERNAME --repo "$REPO" --body "$REGTECH_USERNAME"
    gh secret set REGTECH_PASSWORD --repo "$REPO" --body "$REGTECH_PASSWORD"
    echo -e "${GREEN}✅ REGTECH credentials 설정 완료${NC}"
fi

if [ -n "$SECUDIUM_USERNAME" ] && [ -n "$SECUDIUM_PASSWORD" ]; then
    gh secret set SECUDIUM_USERNAME --repo "$REPO" --body "$SECUDIUM_USERNAME"
    gh secret set SECUDIUM_PASSWORD --repo "$REPO" --body "$SECUDIUM_PASSWORD"
    echo -e "${GREEN}✅ SECUDIUM credentials 설정 완료${NC}"
fi

# Slack Webhook
if [ -n "$SLACK_WEBHOOK" ]; then
    gh secret set SLACK_WEBHOOK --repo "$REPO" --body "$SLACK_WEBHOOK"
    echo -e "${GREEN}✅ SLACK_WEBHOOK 설정 완료${NC}"
fi

echo ""
echo -e "${GREEN}✨ GitHub Secrets 설정이 완료되었습니다!${NC}"
echo ""
echo "설정된 Secrets 확인:"
gh secret list --repo "$REPO"

echo ""
echo "GitHub Variables 설정 (선택사항):"
echo "  gh variable set DOCKER_REGISTRY --repo $REPO --body 'registry.jclee.me'"
echo "  gh variable set APP_PORT --repo $REPO --body '2541'"
echo ""
echo "다음 단계:"
echo "1. 코드를 GitHub에 푸시"
echo "   git push"
echo ""
echo "2. GitHub Actions 실행 확인"
echo "   https://github.com/$REPO/actions"