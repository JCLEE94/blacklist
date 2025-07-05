#!/bin/bash
# Fix ArgoCD Application Configuration

set -e

echo "🔧 Fixing ArgoCD Application Configuration..."

# ArgoCD 서버 정보
ARGOCD_SERVER="argo.jclee.me"
APP_NAME="blacklist"
NAMESPACE="blacklist"
REPO_URL="https://github.com/JCLEE94/blacklist.git"
K8S_PATH="k8s"

# 색상 코드
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ArgoCD 인증
echo -e "${YELLOW}Logging in to ArgoCD...${NC}"
argocd login $ARGOCD_SERVER \
  --username admin \
  --password bingogo1 \
  --insecure \
  --grpc-web

# 기존 앱 삭제 (있는 경우)
echo -e "${YELLOW}Checking existing application...${NC}"
if argocd app get $APP_NAME --grpc-web >/dev/null 2>&1; then
    echo -e "${YELLOW}Deleting existing application...${NC}"
    argocd app delete $APP_NAME --grpc-web --yes
    sleep 5
fi

# 새 ArgoCD 애플리케이션 생성
echo -e "${GREEN}Creating new ArgoCD application...${NC}"
argocd app create $APP_NAME \
  --repo $REPO_URL \
  --path $K8S_PATH \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace $NAMESPACE \
  --sync-policy automated \
  --sync-option CreateNamespace=true \
  --sync-option PrunePropagationPolicy=foreground \
  --self-heal \
  --auto-prune \
  --grpc-web

# 초기 동기화
echo -e "${GREEN}Syncing application...${NC}"
argocd app sync $APP_NAME --grpc-web

# 상태 확인
echo -e "${GREEN}Checking application status...${NC}"
argocd app get $APP_NAME --grpc-web

# Image Updater 어노테이션 추가
echo -e "${GREEN}Adding Image Updater annotations...${NC}"
kubectl patch application $APP_NAME -n argocd --type merge -p '
{
  "metadata": {
    "annotations": {
      "argocd-image-updater.argoproj.io/image-list": "blacklist=registry.jclee.me/blacklist:latest",
      "argocd-image-updater.argoproj.io/blacklist.update-strategy": "latest",
      "argocd-image-updater.argoproj.io/blacklist.pull-secret": "pullsecret:blacklist/regcred",
      "argocd-image-updater.argoproj.io/write-back-method": "git",
      "argocd-image-updater.argoproj.io/git-branch": "main"
    }
  }
}'

echo -e "${GREEN}✅ ArgoCD application fixed successfully!${NC}"
echo -e "${GREEN}Application URL: https://argo.jclee.me/applications/$APP_NAME${NC}"