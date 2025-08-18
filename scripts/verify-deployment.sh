#!/bin/bash

# Verify Deployment Script
# Comprehensive verification of the registry.jclee.me deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Verifying registry.jclee.me deployment...${NC}"
echo ""

# Test 1: Registry connectivity
echo -e "${BLUE}1. Testing registry connectivity...${NC}"
if ping -c 1 registry.jclee.me > /dev/null 2>&1; then
    echo -e "   ${GREEN}✅ Registry reachable${NC}"
else
    echo -e "   ${RED}❌ Registry unreachable${NC}"
    exit 1
fi

# Test 2: Docker registry API
echo -e "${BLUE}2. Testing Docker registry API...${NC}"
if curl -s --connect-timeout 10 https://registry.jclee.me/v2/ > /dev/null; then
    echo -e "   ${GREEN}✅ Registry API responding${NC}"
else
    echo -e "   ${RED}❌ Registry API not responding${NC}"
    exit 1
fi

# Test 3: Docker login (if password provided)
echo -e "${BLUE}3. Testing Docker authentication...${NC}"
if [ -n "$REGISTRY_PASSWORD" ]; then
    if echo "$REGISTRY_PASSWORD" | docker login registry.jclee.me -u admin --password-stdin > /dev/null 2>&1; then
        echo -e "   ${GREEN}✅ Docker authentication successful${NC}"
    else
        echo -e "   ${RED}❌ Docker authentication failed${NC}"
        exit 1
    fi
else
    echo -e "   ${YELLOW}⚠️  REGISTRY_PASSWORD not set - skipping auth test${NC}"
fi

# Test 4: Image availability
echo -e "${BLUE}4. Testing image availability...${NC}"
if docker pull registry.jclee.me/jclee94/blacklist:latest > /dev/null 2>&1; then
    echo -e "   ${GREEN}✅ Image pull successful${NC}"
    
    # Get image details
    IMAGE_ID=$(docker images --format "{{.ID}}" registry.jclee.me/jclee94/blacklist:latest | head -1)
    IMAGE_SIZE=$(docker images --format "{{.Size}}" registry.jclee.me/jclee94/blacklist:latest | head -1)
    CREATED=$(docker images --format "{{.CreatedAt}}" registry.jclee.me/jclee94/blacklist:latest | head -1)
    
    echo -e "   ${GREEN}📦 Image ID: $IMAGE_ID${NC}"
    echo -e "   ${GREEN}📏 Size: $IMAGE_SIZE${NC}"
    echo -e "   ${GREEN}🗓️ Created: $CREATED${NC}"
else
    echo -e "   ${YELLOW}⚠️  Image not available (may need to be built)${NC}"
fi

# Test 5: Docker Compose configuration
echo -e "${BLUE}5. Verifying Docker Compose configuration...${NC}"
if [ -f "docker/docker-compose.yml" ]; then
    COMPOSE_IMAGE=$(grep "image:" docker/docker-compose.yml | head -1 | awk '{print $2}')
    if [ "$COMPOSE_IMAGE" = "registry.jclee.me/jclee94/blacklist:latest" ]; then
        echo -e "   ${GREEN}✅ Docker Compose using correct registry${NC}"
    else
        echo -e "   ${RED}❌ Docker Compose using wrong registry: $COMPOSE_IMAGE${NC}"
        exit 1
    fi
else
    echo -e "   ${RED}❌ docker/docker-compose.yml not found${NC}"
    exit 1
fi

# Test 6: Environment configuration
echo -e "${BLUE}6. Checking environment configuration...${NC}"
if [ -f ".env" ]; then
    REGISTRY_URL=$(grep "REGISTRY_URL=" .env | cut -d'=' -f2)
    if [ "$REGISTRY_URL" = "registry.jclee.me" ]; then
        echo -e "   ${GREEN}✅ Environment configured for registry.jclee.me${NC}"
    else
        echo -e "   ${YELLOW}⚠️  Environment registry URL: $REGISTRY_URL${NC}"
    fi
else
    echo -e "   ${YELLOW}⚠️  .env file not found${NC}"
fi

# Test 7: ArgoCD configuration
echo -e "${BLUE}7. Verifying ArgoCD configuration...${NC}"
if [ -f "argocd/application.yaml" ]; then
    ARGOCD_REPO=$(grep "repository:" argocd/application.yaml | awk '{print $2}')
    if [ "$ARGOCD_REPO" = "registry.jclee.me/jclee94/blacklist" ]; then
        echo -e "   ${GREEN}✅ ArgoCD configured for registry.jclee.me${NC}"
    else
        echo -e "   ${RED}❌ ArgoCD using wrong repository: $ARGOCD_REPO${NC}"
    fi
else
    echo -e "   ${YELLOW}⚠️  ArgoCD configuration not found${NC}"
fi

# Test 8: GitHub Actions workflow
echo -e "${BLUE}8. Checking GitHub Actions configuration...${NC}"
if [ -f ".github/workflows/main-deploy.yml" ]; then
    WORKFLOW_REGISTRY=$(grep "REGISTRY:" .github/workflows/main-deploy.yml | awk '{print $2}')
    if [ "$WORKFLOW_REGISTRY" = "registry.jclee.me" ]; then
        echo -e "   ${GREEN}✅ GitHub Actions configured for registry.jclee.me${NC}"
    else
        echo -e "   ${RED}❌ GitHub Actions using wrong registry: $WORKFLOW_REGISTRY${NC}"
    fi
else
    echo -e "   ${YELLOW}⚠️  GitHub Actions workflow not found${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Deployment verification completed!${NC}"
echo ""
echo -e "${BLUE}Summary:${NC}"
echo "  • Registry: registry.jclee.me"
echo "  • Image: jclee94/blacklist:latest"
echo "  • Configuration: Updated for private registry"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Set REGISTRY_PASSWORD: export REGISTRY_PASSWORD=your-password"
echo "  2. Test connectivity: make registry-test"
echo "  3. Build and deploy: make registry-deploy"
echo "  4. Start services: make start"
echo "  5. Verify health: curl http://localhost:32542/health"
