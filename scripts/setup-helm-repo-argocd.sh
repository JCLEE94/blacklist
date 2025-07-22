#!/bin/bash

# Setup Helm Repository in ArgoCD
# This script configures ArgoCD to use charts.jclee.me

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Setup Helm Repository in ArgoCD ===${NC}"

# Configuration
CHART_REPO_URL="https://charts.jclee.me"
CHART_REPO_NAME="jclee-charts"
ARGOCD_NAMESPACE="argocd"

# Check prerequisites
if ! command -v argocd >/dev/null 2>&1; then
    echo -e "${RED}Error: argocd CLI is not installed${NC}"
    exit 1
fi

if ! kubectl get namespace $ARGOCD_NAMESPACE >/dev/null 2>&1; then
    echo -e "${RED}Error: ArgoCD is not installed${NC}"
    exit 1
fi

# 1. Port forward to ArgoCD server
echo -e "\n${YELLOW}1. Setting up ArgoCD access...${NC}"
kubectl port-forward svc/argocd-server -n $ARGOCD_NAMESPACE 8082:443 >/dev/null 2>&1 &
PF_PID=$!
sleep 5

# 2. Login to ArgoCD
echo -e "\n${YELLOW}2. Logging in to ArgoCD...${NC}"
ARGOCD_PASSWORD=$(kubectl -n $ARGOCD_NAMESPACE get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
argocd login localhost:8082 --username admin --password "$ARGOCD_PASSWORD" --insecure

# 3. Add Helm repository to ArgoCD
echo -e "\n${YELLOW}3. Adding Helm repository to ArgoCD...${NC}"

# Create repository secret for charts.jclee.me
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: charts-jclee-me
  namespace: $ARGOCD_NAMESPACE
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: helm
  url: $CHART_REPO_URL
  name: $CHART_REPO_NAME
  username: admin
  password: bingogo1
EOF

echo -e "${GREEN}✓ Helm repository secret created${NC}"

# 4. Verify repository is added
echo -e "\n${YELLOW}4. Verifying repository...${NC}"
sleep 3  # Give ArgoCD time to process the secret

if argocd repo list | grep -q "$CHART_REPO_URL"; then
    echo -e "${GREEN}✓ Repository added successfully${NC}"
    argocd repo list | grep "$CHART_REPO_URL"
else
    echo -e "${YELLOW}⚠ Repository may take a moment to appear${NC}"
fi

# 5. Test helm chart availability
echo -e "\n${YELLOW}5. Testing Helm chart availability...${NC}"
helm repo add $CHART_REPO_NAME $CHART_REPO_URL --username admin --password bingogo1
helm repo update
helm search repo $CHART_REPO_NAME/blacklist

# 6. Create ArgoCD application using Helm chart
echo -e "\n${YELLOW}6. Creating ArgoCD application from Helm chart...${NC}"
kubectl apply -f k8s-gitops/argocd/blacklist-app-chartrepo.yaml

# 7. Sync application
echo -e "\n${YELLOW}7. Syncing application...${NC}"
argocd app sync blacklist

# 8. Check application status
echo -e "\n${YELLOW}8. Application status:${NC}"
argocd app get blacklist

# Clean up port forward
kill $PF_PID 2>/dev/null

echo -e "\n${GREEN}=== Setup Complete ===${NC}"
echo -e "${BLUE}Helm repository configured in ArgoCD${NC}"
echo -e "Repository URL: $CHART_REPO_URL"
echo -e "Application will now deploy from Helm charts"