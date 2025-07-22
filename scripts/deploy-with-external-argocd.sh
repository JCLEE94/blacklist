#!/bin/bash

# Deploy Application using External ArgoCD
# This script deploys the application to argo.jclee.me

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ARGOCD_SERVER="argo.jclee.me"
ARGOCD_USERNAME="admin"
ARGOCD_PASSWORD="bingogo1"
APP_NAME="blacklist"
CHART_VERSION="${1:-latest}"

echo -e "${BLUE}=== Deploying to External ArgoCD ===${NC}"

# Check if argocd CLI is installed
if ! command -v argocd >/dev/null 2>&1; then
    echo -e "${RED}Error: argocd CLI is not installed${NC}"
    echo "Install from: https://argo-cd.readthedocs.io/en/stable/cli_installation/"
    exit 1
fi

# 1. Login to ArgoCD
echo -e "\n${YELLOW}1. Logging in to ArgoCD...${NC}"
argocd login $ARGOCD_SERVER \
    --username $ARGOCD_USERNAME \
    --password $ARGOCD_PASSWORD \
    --grpc-web

# 2. Check if application exists
echo -e "\n${YELLOW}2. Checking application status...${NC}"
if argocd app get $APP_NAME >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Application exists${NC}"
    
    # Update application
    echo -e "\n${YELLOW}3. Updating application...${NC}"
    if [ "$CHART_VERSION" != "latest" ]; then
        argocd app set $APP_NAME --helm-version $CHART_VERSION
    fi
    
    # Sync application
    echo -e "\n${YELLOW}4. Syncing application...${NC}"
    argocd app sync $APP_NAME --prune
else
    echo -e "${YELLOW}⚠ Application not found. Creating...${NC}"
    
    # Create new application
    argocd app create $APP_NAME \
        --repo https://charts.jclee.me \
        --helm-chart blacklist \
        --revision "$CHART_VERSION" \
        --dest-server https://kubernetes.default.svc \
        --dest-namespace blacklist \
        --sync-policy automated \
        --sync-option CreateNamespace=true \
        --sync-option PrunePropagationPolicy=foreground \
        --helm-set image.repository=registry.jclee.me/blacklist \
        --helm-set image.tag=latest \
        --helm-set service.type=NodePort \
        --helm-set service.nodePort=32452
fi

# 5. Wait for sync to complete
echo -e "\n${YELLOW}5. Waiting for sync to complete...${NC}"
argocd app wait $APP_NAME --health --timeout 300

# 6. Get application details
echo -e "\n${YELLOW}6. Application details:${NC}"
argocd app get $APP_NAME

# 7. Check deployment status
echo -e "\n${YELLOW}7. Kubernetes deployment status:${NC}"
kubectl get all -n blacklist

echo -e "\n${GREEN}=== Deployment Complete ===${NC}"
echo -e "${BLUE}Application URL: http://$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[0].address}'):32452${NC}"
echo -e "${BLUE}ArgoCD Dashboard: https://$ARGOCD_SERVER${NC}"
echo -e "\n${BLUE}To monitor:${NC}"
echo -e "  argocd app get $APP_NAME --refresh"
echo -e "  kubectl logs -f deployment/blacklist -n blacklist"