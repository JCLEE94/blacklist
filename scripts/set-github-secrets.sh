#!/bin/bash
# GitHub Secrets 설정 스크립트

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
REPO="blacklist-management"

echo "📦 저장소: $REPO"

# Secrets 설정
echo ""
echo "🔐 Secrets 설정 중..."

# REGISTRY_USERNAME
gh secret set REGISTRY_USERNAME --repo "$REPO" --body "qws941"
echo -e "${GREEN}✅ REGISTRY_USERNAME 설정 완료${NC}"

# REGISTRY_PASSWORD
gh secret set REGISTRY_PASSWORD --repo "$REPO" --body "bingogo1l7!"
echo -e "${GREEN}✅ REGISTRY_PASSWORD 설정 완료${NC}"

# DEPLOY_USERNAME
gh secret set DEPLOY_USERNAME --repo "$REPO" --body "docker"
echo -e "${GREEN}✅ DEPLOY_USERNAME 설정 완료${NC}"

# DEPLOY_HOST
gh secret set DEPLOY_HOST --repo "$REPO" --body "192.168.50.215"
echo -e "${GREEN}✅ DEPLOY_HOST 설정 완료${NC}"

# DEPLOY_PORT
gh secret set DEPLOY_PORT --repo "$REPO" --body "1111"
echo -e "${GREEN}✅ DEPLOY_PORT 설정 완료${NC}"

# SSH 키 설정
echo ""
echo -e "${YELLOW}📝 SSH 키 설정이 필요합니다.${NC}"
echo "배포 서버에 접속할 수 있는 SSH 개인키 경로를 입력하세요."
echo "예: ~/.ssh/id_rsa"
read -p "SSH 개인키 경로: " SSH_KEY_PATH

if [ -f "$SSH_KEY_PATH" ]; then
    gh secret set DEPLOY_SSH_KEY --repo "$REPO" < "$SSH_KEY_PATH"
    echo -e "${GREEN}✅ DEPLOY_SSH_KEY 설정 완료${NC}"
else
    echo -e "${RED}❌ SSH 키 파일을 찾을 수 없습니다: $SSH_KEY_PATH${NC}"
    echo "수동으로 설정해주세요:"
    echo "gh secret set DEPLOY_SSH_KEY --repo $REPO < /path/to/ssh/key"
fi

# 선택적 Secrets
echo ""
echo -e "${YELLOW}선택적 Secrets 설정${NC}"

# Grafana 비밀번호
read -p "Grafana 관리자 비밀번호 설정 (Enter로 건너뛰기): " GRAFANA_PASS
if [ ! -z "$GRAFANA_PASS" ]; then
    gh secret set GRAFANA_PASSWORD --repo "$REPO" --body "$GRAFANA_PASS"
    echo -e "${GREEN}✅ GRAFANA_PASSWORD 설정 완료${NC}"
fi

# Slack Webhook
read -p "Slack Webhook URL (Enter로 건너뛰기): " SLACK_URL
if [ ! -z "$SLACK_URL" ]; then
    gh secret set SLACK_WEBHOOK --repo "$REPO" --body "$SLACK_URL"
    echo -e "${GREEN}✅ SLACK_WEBHOOK 설정 완료${NC}"
fi

echo ""
echo -e "${GREEN}✨ GitHub Secrets 설정이 완료되었습니다!${NC}"
echo ""
echo "설정된 Secrets 확인:"
gh secret list --repo "$REPO"

echo ""
echo "다음 단계:"
echo "1. 코드를 GitHub에 푸시"
echo "   git push -u origin main"
echo ""
echo "2. GitHub Actions 실행 확인"
echo "   https://github.com/qws941/$REPO/actions"
echo ""
echo "3. PR을 생성하여 CI/CD 파이프라인 테스트"