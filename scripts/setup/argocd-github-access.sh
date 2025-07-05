#!/bin/bash
# Setup ArgoCD GitHub Repository Access

set -e

echo "🔐 Setting up ArgoCD GitHub repository access..."

# ArgoCD 서버 정보
ARGOCD_SERVER="argo.jclee.me"
REPO_URL="https://github.com/jclee/blacklist.git"

# 색상 코드
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# GitHub 토큰 확인
if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${YELLOW}GitHub token not found in environment.${NC}"
    echo -e "${YELLOW}Please provide your GitHub Personal Access Token:${NC}"
    read -s GITHUB_TOKEN
fi

# ArgoCD 로그인
echo -e "${YELLOW}Logging in to ArgoCD...${NC}"
argocd login $ARGOCD_SERVER \
  --username admin \
  --password bingogo1 \
  --insecure \
  --grpc-web

# 기존 저장소 자격 증명 확인
echo -e "${YELLOW}Checking existing repository credentials...${NC}"
if argocd repo list --grpc-web | grep -q "$REPO_URL"; then
    echo -e "${YELLOW}Removing existing repository...${NC}"
    argocd repo rm $REPO_URL --grpc-web || true
fi

# GitHub 저장소 추가 (HTTPS with token)
echo -e "${GREEN}Adding GitHub repository with authentication...${NC}"
argocd repo add $REPO_URL \
  --username oauth2 \
  --password $GITHUB_TOKEN \
  --grpc-web

# 저장소 연결 테스트
echo -e "${GREEN}Testing repository connection...${NC}"
if argocd repo list --grpc-web | grep -q "$REPO_URL"; then
    echo -e "${GREEN}✅ Repository successfully added!${NC}"
else
    echo -e "${RED}❌ Failed to add repository${NC}"
    exit 1
fi

# SSH 키 방식 대안 안내
echo -e "${YELLOW}Alternative: SSH Key Setup${NC}"
echo "If HTTPS with token doesn't work, you can use SSH:"
echo "1. Generate SSH key: ssh-keygen -t ed25519 -C 'argocd@jclee.me'"
echo "2. Add public key to GitHub: Settings > SSH and GPG keys"
echo "3. Add repository with SSH URL:"
echo "   argocd repo add git@github.com:jclee/blacklist.git --ssh-private-key-path ~/.ssh/id_ed25519"

echo -e "${GREEN}✅ Repository access configuration completed!${NC}"