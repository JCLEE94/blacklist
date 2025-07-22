#!/bin/bash

# Test Authentication for All Services
# This script tests authentication for Docker Registry and ChartMuseum

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGISTRY_URL="https://registry.jclee.me"
CHARTS_URL="https://charts.jclee.me"
USERNAME="admin"
PASSWORD="bingogo1"
BASIC_AUTH="YWRtaW46YmluZ29nbzE="

echo -e "${BLUE}=== Testing Service Authentication ===${NC}"

# Function to check command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
if ! command_exists curl; then
    echo -e "${RED}Error: curl is not installed${NC}"
    exit 1
fi

if ! command_exists jq; then
    echo -e "${YELLOW}Warning: jq is not installed. Output won't be pretty-printed${NC}"
    JQ="cat"
else
    JQ="jq ."
fi

# Test 1: Docker Registry with username/password
echo -e "\n${YELLOW}1. Testing Docker Registry (username/password)...${NC}"
response=$(curl -s -w "\n%{http_code}" -u "$USERNAME:$PASSWORD" "$REGISTRY_URL/v2/_catalog")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" -eq 200 ]; then
    echo -e "${GREEN}✓ Registry authentication successful${NC}"
    echo "Response: $(echo "$body" | $JQ)"
else
    echo -e "${RED}✗ Registry authentication failed. HTTP code: $http_code${NC}"
    echo "Response: $body"
fi

# Test 2: Docker Registry with Basic Auth header
echo -e "\n${YELLOW}2. Testing Docker Registry (Basic Auth header)...${NC}"
response=$(curl -s -w "\n%{http_code}" -H "Authorization: Basic $BASIC_AUTH" "$REGISTRY_URL/v2/_catalog")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" -eq 200 ]; then
    echo -e "${GREEN}✓ Registry Basic Auth header successful${NC}"
    echo "Response: $(echo "$body" | $JQ)"
else
    echo -e "${RED}✗ Registry Basic Auth header failed. HTTP code: $http_code${NC}"
    echo "Response: $body"
fi

# Test 3: ChartMuseum with username/password
echo -e "\n${YELLOW}3. Testing ChartMuseum (username/password)...${NC}"
response=$(curl -s -w "\n%{http_code}" -u "$USERNAME:$PASSWORD" "$CHARTS_URL/api/charts")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" -eq 200 ]; then
    echo -e "${GREEN}✓ ChartMuseum authentication successful${NC}"
    echo "Response: $(echo "$body" | $JQ)"
else
    echo -e "${RED}✗ ChartMuseum authentication failed. HTTP code: $http_code${NC}"
    echo "Response: $body"
fi

# Test 4: ChartMuseum with Basic Auth header
echo -e "\n${YELLOW}4. Testing ChartMuseum (Basic Auth header)...${NC}"
response=$(curl -s -w "\n%{http_code}" -H "Authorization: Basic $BASIC_AUTH" "$CHARTS_URL/api/charts")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" -eq 200 ]; then
    echo -e "${GREEN}✓ ChartMuseum Basic Auth header successful${NC}"
    echo "Response: $(echo "$body" | $JQ)"
else
    echo -e "${RED}✗ ChartMuseum Basic Auth header failed. HTTP code: $http_code${NC}"
    echo "Response: $body"
fi

# Test 5: Docker login
echo -e "\n${YELLOW}5. Testing Docker login...${NC}"
if command_exists docker; then
    if echo "$PASSWORD" | docker login "$REGISTRY_URL" -u "$USERNAME" --password-stdin >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Docker login successful${NC}"
        
        # Test push/pull
        echo -e "\n${YELLOW}6. Testing Docker push/pull...${NC}"
        TEST_IMAGE="$REGISTRY_URL/test/alpine:test-$(date +%s)"
        
        # Pull alpine from Docker Hub
        docker pull alpine:latest >/dev/null 2>&1
        
        # Tag for our registry
        docker tag alpine:latest "$TEST_IMAGE"
        
        # Push to registry
        if docker push "$TEST_IMAGE" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Docker push successful${NC}"
            
            # Remove local image
            docker rmi "$TEST_IMAGE" >/dev/null 2>&1
            
            # Pull from registry
            if docker pull "$TEST_IMAGE" >/dev/null 2>&1; then
                echo -e "${GREEN}✓ Docker pull successful${NC}"
                
                # Clean up
                docker rmi "$TEST_IMAGE" >/dev/null 2>&1
            else
                echo -e "${RED}✗ Docker pull failed${NC}"
            fi
        else
            echo -e "${RED}✗ Docker push failed${NC}"
        fi
    else
        echo -e "${RED}✗ Docker login failed${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Docker not installed, skipping Docker tests${NC}"
fi

# Test 7: List images in registry
echo -e "\n${YELLOW}7. Listing images in registry...${NC}"
response=$(curl -s -u "$USERNAME:$PASSWORD" "$REGISTRY_URL/v2/_catalog")
echo "Repositories: $(echo "$response" | $JQ)"

# Test 8: Helm repository
echo -e "\n${YELLOW}8. Testing Helm repository...${NC}"
if command_exists helm; then
    # Remove existing repo if exists
    helm repo remove jclee-charts 2>/dev/null || true
    
    # Add repository with auth
    if helm repo add jclee-charts "$CHARTS_URL" --username "$USERNAME" --password "$PASSWORD"; then
        echo -e "${GREEN}✓ Helm repository added successfully${NC}"
        
        # Update repository
        if helm repo update jclee-charts; then
            echo -e "${GREEN}✓ Helm repository updated successfully${NC}"
            
            # Search for charts
            echo -e "\n${YELLOW}Available charts:${NC}"
            helm search repo jclee-charts/
        else
            echo -e "${RED}✗ Helm repository update failed${NC}"
        fi
    else
        echo -e "${RED}✗ Failed to add Helm repository${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Helm not installed, skipping Helm tests${NC}"
fi

echo -e "\n${GREEN}=== Authentication Test Complete ===${NC}"
echo -e "${BLUE}Summary:${NC}"
echo -e "- Registry URL: $REGISTRY_URL"
echo -e "- Charts URL: $CHARTS_URL"
echo -e "- Username: $USERNAME"
echo -e "- Basic Auth: Authorization: Basic $BASIC_AUTH"