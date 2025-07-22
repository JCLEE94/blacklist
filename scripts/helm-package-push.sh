#!/bin/bash

# Helm Chart Package and Push Script
# This script packages the Helm chart and pushes it to charts.jclee.me

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CHART_DIR="helm/blacklist"
CHART_REPO_URL="https://charts.jclee.me"
CHART_REPO_NAME="jclee-charts"

echo -e "${BLUE}=== Helm Chart Package and Push ===${NC}"

# Check prerequisites
if ! command -v helm >/dev/null 2>&1; then
    echo -e "${RED}Error: helm is not installed${NC}"
    echo "Install helm from: https://helm.sh/docs/intro/install/"
    exit 1
fi

# 1. Add Helm repository
echo -e "\n${YELLOW}1. Adding Helm repository...${NC}"
helm repo add $CHART_REPO_NAME $CHART_REPO_URL || true
helm repo update

# 2. Lint the chart
echo -e "\n${YELLOW}2. Linting Helm chart...${NC}"
helm lint $CHART_DIR

# 3. Package the chart
echo -e "\n${YELLOW}3. Packaging Helm chart...${NC}"
VERSION=$(grep '^version:' $CHART_DIR/Chart.yaml | awk '{print $2}')
APP_VERSION=$(grep '^appVersion:' $CHART_DIR/Chart.yaml | awk '{print $2}' | tr -d '"')

helm package $CHART_DIR --destination /tmp/
CHART_PACKAGE="/tmp/blacklist-${VERSION}.tgz"

if [ ! -f "$CHART_PACKAGE" ]; then
    echo -e "${RED}Error: Chart package not created${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Chart packaged: $CHART_PACKAGE${NC}"

# 4. Push to chart repository using curl
echo -e "\n${YELLOW}4. Pushing chart to repository...${NC}"

# ChartMuseum API endpoint
PUSH_URL="${CHART_REPO_URL}/api/charts"

# Push the chart
response=$(curl -s -w "\n%{http_code}" \
    --data-binary "@${CHART_PACKAGE}" \
    -u "admin:bingogo1" \
    "${PUSH_URL}")

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" -eq 201 ] || [ "$http_code" -eq 200 ]; then
    echo -e "${GREEN}✓ Chart pushed successfully${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ Failed to push chart. HTTP code: $http_code${NC}"
    echo "Response: $body"
    exit 1
fi

# 5. Update repository index
echo -e "\n${YELLOW}5. Updating repository index...${NC}"
helm repo update $CHART_REPO_NAME

# 6. Verify chart is available
echo -e "\n${YELLOW}6. Verifying chart availability...${NC}"
if helm search repo $CHART_REPO_NAME/blacklist --version $VERSION | grep -q blacklist; then
    echo -e "${GREEN}✓ Chart is available in repository${NC}"
    helm search repo $CHART_REPO_NAME/blacklist --version $VERSION
else
    echo -e "${YELLOW}⚠ Chart may not be immediately available. Try 'helm repo update' again${NC}"
fi

# Clean up
rm -f $CHART_PACKAGE

echo -e "\n${GREEN}=== Chart Push Complete ===${NC}"
echo -e "${BLUE}Chart details:${NC}"
echo -e "  Name: blacklist"
echo -e "  Version: $VERSION"
echo -e "  App Version: $APP_VERSION"
echo -e "  Repository: $CHART_REPO_URL"
echo -e "\n${BLUE}To install the chart:${NC}"
echo -e "  helm install blacklist $CHART_REPO_NAME/blacklist --version $VERSION"