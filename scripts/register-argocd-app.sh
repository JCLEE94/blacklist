#!/bin/bash
# ArgoCD Application Registration Script
# Consolidated and optimized version

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== ArgoCD Application Registration ===${NC}"

# Configuration
ARGOCD_SERVER="argo.jclee.me"
ARGOCD_NAMESPACE="argocd"
APP_NAME="blacklist"
APP_NAMESPACE="blacklist"
REPO_URL="https://github.com/JCLEE94/blacklist"
HELM_PATH="chart/blacklist"

# Check if ArgoCD CLI is installed
if ! command -v argocd &> /dev/null; then
    echo -e "${RED}Error: ArgoCD CLI is not installed${NC}"
    echo "Please install ArgoCD CLI first: https://argo-cd.readthedocs.io/en/stable/cli_installation/"
    exit 1
fi

# Login to ArgoCD (if not already logged in)
echo -e "${YELLOW}Checking ArgoCD login status...${NC}"
if ! argocd account get-user-info --server "$ARGOCD_SERVER" &> /dev/null; then
    echo -e "${YELLOW}Please login to ArgoCD:${NC}"
    argocd login "$ARGOCD_SERVER"
fi

# Check if application already exists
if argocd app get "$APP_NAME" --server "$ARGOCD_SERVER" &> /dev/null; then
    echo -e "${YELLOW}Application '$APP_NAME' already exists. Updating...${NC}"
    
    # Delete existing app
    echo -e "${YELLOW}Removing existing application...${NC}"
    argocd app delete "$APP_NAME" --server "$ARGOCD_SERVER" --yes || true
    
    # Wait for deletion
    sleep 5
fi

# Create ArgoCD application
echo -e "${GREEN}Creating ArgoCD application...${NC}"
argocd app create "$APP_NAME" \
    --server "$ARGOCD_SERVER" \
    --repo "$REPO_URL" \
    --path "$HELM_PATH" \
    --dest-server https://kubernetes.default.svc \
    --dest-namespace "$APP_NAMESPACE" \
    --helm-set image.repository=registry.jclee.me/jclee94/blacklist \
    --helm-set image.tag=latest \
    --helm-set image.pullPolicy=Always \
    --values values.yaml \
    --values values-production.yaml \
    --sync-policy automated \
    --auto-prune \
    --self-heal \
    --sync-option CreateNamespace=true \
    --sync-option PrunePropagationPolicy=foreground \
    --sync-option PruneLast=true \
    --revision-history-limit 3

# Set sync retry
echo -e "${GREEN}Setting sync retry policy...${NC}"
argocd app set "$APP_NAME" \
    --server "$ARGOCD_SERVER" \
    --sync-retry-limit 5 \
    --sync-retry-backoff-duration 5s \
    --sync-retry-backoff-factor 2 \
    --sync-retry-backoff-max-duration 3m

# Add finalizer
echo -e "${GREEN}Adding finalizer...${NC}"
kubectl patch app "$APP_NAME" -n "$ARGOCD_NAMESPACE" \
    --type json \
    -p='[{"op": "add", "path": "/metadata/finalizers", "value": ["resources-finalizer.argocd.argoproj.io"]}]' \
    2>/dev/null || true

# Sync application
echo -e "${GREEN}Syncing application...${NC}"
argocd app sync "$APP_NAME" --server "$ARGOCD_SERVER"

# Wait for sync
echo -e "${YELLOW}Waiting for application to be healthy...${NC}"
argocd app wait "$APP_NAME" \
    --server "$ARGOCD_SERVER" \
    --timeout 300 \
    --health \
    --sync

# Get application status
echo -e "${GREEN}Application Status:${NC}"
argocd app get "$APP_NAME" --server "$ARGOCD_SERVER"

# Show application URL
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo -e "Application URL: ${GREEN}https://blacklist.jclee.me${NC}"
echo -e "ArgoCD URL: ${GREEN}https://$ARGOCD_SERVER/applications/$APP_NAME${NC}"

# Health check
echo -e "${YELLOW}Performing health check...${NC}"
sleep 10
if curl -s -o /dev/null -w "%{http_code}" https://blacklist.jclee.me/health | grep -q "200"; then
    echo -e "${GREEN}✓ Application is healthy${NC}"
else
    echo -e "${YELLOW}⚠ Application may still be starting up. Check manually.${NC}"
fi

echo -e "${GREEN}=== Registration Complete ===${NC}"