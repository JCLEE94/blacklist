#!/bin/bash

# Complete GitOps Setup with Helm
# This script sets up the entire GitOps pipeline with Helm charts

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Complete GitOps Setup with Helm ===${NC}"

# Check if using external ArgoCD
if [ "$1" == "--external" ]; then
    USE_EXTERNAL_ARGOCD=true
    echo -e "${YELLOW}Using external ArgoCD at argo.jclee.me${NC}"
fi

# Step 0: Create Registry Secrets
echo -e "
${YELLOW}Step 0: Creating registry secrets...${NC}"
./scripts/create-registry-secret.sh

# Step 1: Setup ArgoCD
echo -e "
${YELLOW}Step 1: Setting up ArgoCD...${NC}"
if [ "$USE_EXTERNAL_ARGOCD" == "true" ]; then
    ./scripts/setup-gitops-external.sh
else
    ./scripts/setup-gitops.sh
fi

# Step 2: Install ArgoCD Image Updater
echo -e "\n${YELLOW}Step 2: Installing ArgoCD Image Updater...${NC}"
./scripts/install-image-updater.sh

# Step 3: Package and push Helm chart
echo -e "\n${YELLOW}Step 3: Packaging and pushing Helm chart...${NC}"
./scripts/helm-package-push.sh

# Step 4: Configure Helm repository in ArgoCD
echo -e "\n${YELLOW}Step 4: Configuring Helm repository in ArgoCD...${NC}"
./scripts/setup-helm-repo-argocd.sh

# Step 5: Verify GitOps setup
echo -e "\n${YELLOW}Step 5: Verifying GitOps setup...${NC}"
./scripts/verify-gitops.sh

echo -e "\n${GREEN}=== Complete GitOps Setup Finished ===${NC}"
echo -e "${BLUE}Summary:${NC}"
echo -e "✓ ArgoCD installed and configured"
echo -e "✓ ArgoCD Image Updater installed"
echo -e "✓ Helm chart packaged and pushed to charts.jclee.me"
echo -e "✓ ArgoCD configured to use Helm repository"
echo -e "✓ Application deployed via GitOps"
echo -e "\n${BLUE}Next steps:${NC}"
echo -e "1. Commit and push changes to trigger CI/CD"
echo -e "2. CI/CD will build Docker image → push to registry.jclee.me"
echo -e "3. CI/CD will package Helm chart → push to charts.jclee.me"
echo -e "4. ArgoCD Image Updater will detect new image and update deployment"
echo -e "5. Monitor deployment: argocd app get blacklist"