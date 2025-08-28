#!/bin/bash

# Test Registry Connection Script
# Tests connectivity to registry.jclee.me and authentication

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Testing registry.jclee.me connectivity..."

# Check if environment variables are set
if [ -z "$REGISTRY_PASSWORD" ]; then
    echo -e "${RED}❌ REGISTRY_PASSWORD environment variable not set${NC}"
    echo "Please set REGISTRY_PASSWORD before running this script"
    exit 1
fi

# Test network connectivity
echo "🌐 Testing network connectivity to registry.jclee.me..."
if ping -c 1 registry.jclee.me > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Network connectivity to registry.jclee.me: OK${NC}"
else
    echo -e "${RED}❌ Cannot reach registry.jclee.me${NC}"
    exit 1
fi

# Test HTTP connectivity to registry
echo "🔌 Testing HTTP connectivity to registry..."
if curl -s --connect-timeout 10 https://registry.jclee.me/v2/ > /dev/null; then
    echo -e "${GREEN}✅ HTTP connectivity to registry: OK${NC}"
else
    echo -e "${RED}❌ Cannot connect to registry API${NC}"
    exit 1
fi

# Test Docker login
echo "🔐 Testing Docker login..."
if echo "$REGISTRY_PASSWORD" | docker login registry.jclee.me -u admin --password-stdin > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Docker login successful${NC}"
else
    echo -e "${RED}❌ Docker login failed${NC}"
    echo "Please check your registry credentials"
    exit 1
fi

# Test image pull (if blacklist image exists)
echo "🐳 Testing image pull..."
if docker pull registry.jclee.me/qws941/blacklist:latest > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Image pull successful${NC}"
    
    # Get image info
    IMAGE_ID=$(docker images --format "table {{.ID}}" registry.jclee.me/qws941/blacklist:latest | tail -n 1)
    IMAGE_SIZE=$(docker images --format "table {{.Size}}" registry.jclee.me/qws941/blacklist:latest | tail -n 1)
    echo -e "${GREEN}📦 Image ID: $IMAGE_ID${NC}"
    echo -e "${GREEN}📏 Image Size: $IMAGE_SIZE${NC}"
else
    echo -e "${YELLOW}⚠️  Image pull failed (image may not exist yet)${NC}"
fi

# Test push capability with a test image
echo "📤 Testing push capability..."
echo 'FROM alpine:latest' | docker build -t registry.jclee.me/jclee94/test:latest - > /dev/null 2>&1
if docker push registry.jclee.me/jclee94/test:latest > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Image push successful${NC}"
    
    # Clean up test image
    docker rmi registry.jclee.me/jclee94/test:latest > /dev/null 2>&1
else
    echo -e "${RED}❌ Image push failed${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 All registry tests passed! registry.jclee.me is fully functional.${NC}"
echo ""
echo "Next steps:"
echo "1. Build and push your blacklist image: make docker-build && make docker-push"
echo "2. Update GitHub secrets with REGISTRY_USERNAME and REGISTRY_PASSWORD"
echo "3. Deploy with: docker-compose up -d"
