#!/bin/bash

# Integrated Deployment Script
# This script handles the complete deployment process with proper authentication

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGISTRY_URL="registry.jclee.me"
CHARTS_URL="charts.jclee.me"
ARGOCD_URL="argo.jclee.me"
USERNAME="admin"
PASSWORD="bingogo1"

# Docker image settings
IMAGE_NAME="blacklist"
VERSION="${1:-latest}"

echo -e "${BLUE}=== Integrated Deployment Process ===${NC}"

# Function to check command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 1. Test authentication
echo -e "\n${YELLOW}1. Testing authentication...${NC}"
./scripts/test-auth-services.sh

# 2. Build Docker image
echo -e "\n${YELLOW}2. Building Docker image...${NC}"
if [ -f "deployment/Dockerfile" ]; then
    docker build -f deployment/Dockerfile -t $REGISTRY_URL/$IMAGE_NAME:$VERSION .
    echo -e "${GREEN}✓ Docker image built successfully${NC}"
else
    echo -e "${RED}✗ Dockerfile not found${NC}"
    exit 1
fi

# 3. Push Docker image
echo -e "\n${YELLOW}3. Pushing Docker image...${NC}"
echo "$PASSWORD" | docker login $REGISTRY_URL -u $USERNAME --password-stdin

if docker push $REGISTRY_URL/$IMAGE_NAME:$VERSION; then
    echo -e "${GREEN}✓ Docker image pushed successfully${NC}"
    
    # Also tag and push as latest
    docker tag $REGISTRY_URL/$IMAGE_NAME:$VERSION $REGISTRY_URL/$IMAGE_NAME:latest
    docker push $REGISTRY_URL/$IMAGE_NAME:latest
else
    echo -e "${RED}✗ Failed to push Docker image${NC}"
    exit 1
fi

# 4. Package Helm chart
echo -e "\n${YELLOW}4. Packaging Helm chart...${NC}"
if [ -d "helm/blacklist" ]; then
    # Update chart version
    if [ "$VERSION" != "latest" ]; then
        sed -i "s/^version:.*/version: $VERSION/" helm/blacklist/Chart.yaml
        sed -i "s/^appVersion:.*/appVersion: \"$VERSION\"/" helm/blacklist/Chart.yaml
    fi
    
    helm package helm/blacklist --destination /tmp/
    CHART_FILE=$(ls -t /tmp/blacklist-*.tgz | head -1)
    echo -e "${GREEN}✓ Helm chart packaged: $CHART_FILE${NC}"
else
    echo -e "${RED}✗ Helm chart directory not found${NC}"
    exit 1
fi

# 5. Push Helm chart
echo -e "\n${YELLOW}5. Pushing Helm chart...${NC}"
response=$(curl -s -w "\n%{http_code}" \
    --data-binary "@${CHART_FILE}" \
    -u "$USERNAME:$PASSWORD" \
    "https://$CHARTS_URL/api/charts")

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" -eq 201 ] || [ "$http_code" -eq 200 ]; then
    echo -e "${GREEN}✓ Helm chart pushed successfully${NC}"
else
    echo -e "${RED}✗ Failed to push Helm chart. HTTP code: $http_code${NC}"
    echo "Response: $body"
    exit 1
fi

# 6. Update Helm repository
echo -e "\n${YELLOW}6. Updating Helm repository...${NC}"
helm repo add jclee-charts https://$CHARTS_URL --username $USERNAME --password $PASSWORD --force-update
helm repo update jclee-charts

# 7. Deploy with ArgoCD
echo -e "\n${YELLOW}7. Deploying with ArgoCD...${NC}"
if command_exists argocd; then
    # Login to ArgoCD
    argocd login $ARGOCD_URL --username $USERNAME --password $PASSWORD --grpc-web
    
    # Check if app exists
    if argocd app get blacklist >/dev/null 2>&1; then
        echo "Updating existing application..."
        argocd app set blacklist --helm-version $VERSION
        argocd app sync blacklist
    else
        echo "Creating new application..."
        argocd app create blacklist \
            --repo https://$CHARTS_URL \
            --helm-chart blacklist \
            --revision "$VERSION" \
            --dest-server https://kubernetes.default.svc \
            --dest-namespace blacklist \
            --sync-policy automated \
            --helm-set image.repository=$REGISTRY_URL/$IMAGE_NAME \
            --helm-set image.tag=$VERSION
    fi
    
    # Wait for sync
    argocd app wait blacklist --health --timeout 300
    echo -e "${GREEN}✓ Application deployed successfully${NC}"
else
    echo -e "${YELLOW}⚠ ArgoCD CLI not installed. Please deploy manually or install ArgoCD CLI${NC}"
fi

# 8. Verify deployment
echo -e "\n${YELLOW}8. Verifying deployment...${NC}"
if kubectl get deployment blacklist -n blacklist >/dev/null 2>&1; then
    kubectl get all -n blacklist
    echo -e "${GREEN}✓ Deployment verified${NC}"
else
    echo -e "${YELLOW}⚠ Cannot verify deployment. Check manually${NC}"
fi

# Clean up
rm -f $CHART_FILE

echo -e "\n${GREEN}=== Deployment Complete ===${NC}"
echo -e "${BLUE}Summary:${NC}"
echo -e "- Docker Image: $REGISTRY_URL/$IMAGE_NAME:$VERSION"
echo -e "- Helm Chart: blacklist-$VERSION"
echo -e "- Namespace: blacklist"
echo -e "\n${BLUE}Access:${NC}"
echo -e "- Application: http://$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[0].address}'):32452"
echo -e "- ArgoCD: https://$ARGOCD_URL"
echo -e "- Registry: https://$REGISTRY_URL"
echo -e "- Charts: https://$CHARTS_URL"