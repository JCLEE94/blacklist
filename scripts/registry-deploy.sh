#!/bin/bash

# Registry Deploy Script
# Builds and pushes blacklist image to registry.jclee.me

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGISTRY_URL="registry.jclee.me"
IMAGE_NAME="jclee94/blacklist"
FULL_IMAGE="$REGISTRY_URL/$IMAGE_NAME"

echo -e "${BLUE}📦 Building and deploying to registry.jclee.me...${NC}"

# Check if we're in the right directory
if [ ! -f "Dockerfile" ]; then
    echo -e "${RED}❌ Dockerfile not found. Please run from project root.${NC}"
    exit 1
fi

# Check if registry password is set
if [ -z "$REGISTRY_PASSWORD" ]; then
    echo -e "${RED}❌ REGISTRY_PASSWORD environment variable not set${NC}"
    echo "Please set REGISTRY_PASSWORD before running this script"
    exit 1
fi

# Login to registry
echo "🔐 Logging in to registry..."
if echo "$REGISTRY_PASSWORD" | docker login $REGISTRY_URL -u admin --password-stdin; then
    echo -e "${GREEN}✅ Registry login successful${NC}"
else
    echo -e "${RED}❌ Registry login failed${NC}"
    exit 1
fi

# Build image
echo "🔨 Building Docker image..."
if docker build -t $FULL_IMAGE:latest -t $FULL_IMAGE:$(date +%Y.%m.%d)-$(git rev-parse --short HEAD) .; then
    echo -e "${GREEN}✅ Docker build successful${NC}"
else
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
fi

# Push latest tag
echo "📤 Pushing image to registry..."
if docker push $FULL_IMAGE:latest; then
    echo -e "${GREEN}✅ Latest image pushed successfully${NC}"
else
    echo -e "${RED}❌ Image push failed${NC}"
    exit 1
fi

# Push versioned tag
VERSIONED_TAG="$(date +%Y.%m.%d)-$(git rev-parse --short HEAD)"
if docker push $FULL_IMAGE:$VERSIONED_TAG; then
    echo -e "${GREEN}✅ Versioned image ($VERSIONED_TAG) pushed successfully${NC}"
else
    echo -e "${YELLOW}⚠️  Versioned image push failed${NC}"
fi

# Display image information
echo ""
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo -e "${BLUE}Image details:${NC}"
echo "  • Registry: $REGISTRY_URL"
echo "  • Image: $IMAGE_NAME"
echo "  • Latest: $FULL_IMAGE:latest"
echo "  • Versioned: $FULL_IMAGE:$VERSIONED_TAG"
echo ""
echo "Next steps:"
echo "1. Update deployment: docker-compose pull && docker-compose up -d"
echo "2. Check ArgoCD sync: kubectl get applications -n argocd"
echo "3. Verify deployment: curl http://localhost:32542/health"
