#!/bin/bash

# GitHub Container Registry Secret Setup Script
# This script creates Kubernetes secrets for pulling images from GHCR

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== GitHub Container Registry Secret Setup ===${NC}"

# Check if required environment variables are set
if [ -z "$GITHUB_USERNAME" ] || [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${YELLOW}GitHub credentials not found in environment variables.${NC}"
    echo "Please provide your GitHub credentials:"
    
    if [ -z "$GITHUB_USERNAME" ]; then
        read -p "GitHub Username: " GITHUB_USERNAME
    fi
    
    if [ -z "$GITHUB_TOKEN" ]; then
        echo "GitHub Personal Access Token (with read:packages scope):"
        read -s GITHUB_TOKEN
        echo
    fi
fi

# Validate inputs
if [ -z "$GITHUB_USERNAME" ] || [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}Error: GitHub username and token are required${NC}"
    exit 1
fi

# Create namespace if it doesn't exist
echo -e "${YELLOW}Creating namespace if not exists...${NC}"
kubectl create namespace blacklist --dry-run=client -o yaml | kubectl apply -f -

# Delete existing secret if it exists
echo -e "${YELLOW}Removing existing secret if present...${NC}"
kubectl delete secret ghcr-secret -n blacklist --ignore-not-found=true

# Create the secret
echo -e "${GREEN}Creating GHCR pull secret...${NC}"
kubectl create secret docker-registry ghcr-secret \
    --docker-server=ghcr.io \
    --docker-username="$GITHUB_USERNAME" \
    --docker-password="$GITHUB_TOKEN" \
    --docker-email="${GITHUB_EMAIL:-noreply@github.com}" \
    -n blacklist

# Patch default service account to use the secret
echo -e "${GREEN}Patching default service account...${NC}"
kubectl patch serviceaccount default -n blacklist -p '{"imagePullSecrets": [{"name": "ghcr-secret"}]}'

# Verify the secret
echo -e "${GREEN}Verifying secret creation...${NC}"
kubectl get secret ghcr-secret -n blacklist

# Update existing deployments to use the new secret
echo -e "${YELLOW}Updating deployment to use GHCR secret...${NC}"
kubectl patch deployment blacklist -n blacklist --type='json' -p='[
  {
    "op": "replace",
    "path": "/spec/template/spec/imagePullSecrets",
    "value": [{"name": "ghcr-secret"}]
  }
]' || echo "Deployment not found or already updated"

echo -e "${GREEN}✅ GHCR secret setup completed successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Update your deployment manifests to use 'ghcr-secret' instead of 'regcred'"
echo "2. Update image references from 'registry.jclee.me' to 'ghcr.io/YOUR_GITHUB_USERNAME'"
echo "3. Ensure your GitHub token has 'read:packages' and 'write:packages' scopes"
echo ""
echo "To test the secret:"
echo "  kubectl run test-ghcr --rm -it --image=ghcr.io/${GITHUB_USERNAME}/blacklist:latest --restart=Never -- echo 'Success!'"