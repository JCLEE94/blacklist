#!/bin/bash

# Create Docker Registry Secret for all namespaces
# This script creates registry authentication secrets

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="registry.jclee.me"
USERNAME="admin"
PASSWORD="bingogo1"
EMAIL="admin@jclee.me"

echo -e "${BLUE}=== Creating Registry Secrets ===${NC}"

# Namespaces to create secrets in
NAMESPACES=(
    "blacklist"
    "blacklist-dev"
    "blacklist-staging"
    "default"
)

# Create secret in each namespace
for NAMESPACE in "${NAMESPACES[@]}"; do
    echo -e "\n${YELLOW}Creating secret in namespace: $NAMESPACE${NC}"
    
    # Create namespace if it doesn't exist
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # Create registry secret
    kubectl create secret docker-registry regcred \
        --docker-server=$REGISTRY \
        --docker-username=$USERNAME \
        --docker-password=$PASSWORD \
        --docker-email=$EMAIL \
        -n $NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    
    echo -e "${GREEN}✓ Secret 'regcred' created in namespace '$NAMESPACE'${NC}"
done

# Verify secrets
echo -e "\n${YELLOW}Verifying secrets...${NC}"
for NAMESPACE in "${NAMESPACES[@]}"; do
    if kubectl get secret regcred -n $NAMESPACE >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Secret exists in namespace: $NAMESPACE${NC}"
    else
        echo -e "${RED}✗ Secret missing in namespace: $NAMESPACE${NC}"
    fi
done

echo -e "\n${GREEN}=== Registry Secrets Created ===${NC}"
echo -e "${BLUE}Registry: $REGISTRY${NC}"
echo -e "${BLUE}Username: $USERNAME${NC}"
echo -e "\nTo use in deployment:"
echo -e "  imagePullSecrets:"
echo -e "    - name: regcred"