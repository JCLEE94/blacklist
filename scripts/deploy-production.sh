#!/bin/bash
# Production Deployment Script with Watchtower
# 프로덕션 환경 자동 배포 스크립트

set -e

# Configuration
REGISTRY="registry.jclee.me"
IMAGE_NAME="blacklist"
TAG="latest"
NAS_HOST="192.168.50.215"
NAS_PORT="1111"
NAS_USER="docker"
NAS_PATH="/volume1/docker/blacklist"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Blacklist Production Deployment ===${NC}"
echo "Registry: $REGISTRY"
echo "Image: $IMAGE_NAME:$TAG"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 1. Build Docker image
echo -e "${YELLOW}1. Building Docker image...${NC}"
if docker build -f docker/Dockerfile -t $REGISTRY/$IMAGE_NAME:$TAG .; then
    print_status "Docker image built successfully"
else
    print_error "Failed to build Docker image"
    exit 1
fi

# 2. Push to registry
echo -e "${YELLOW}2. Pushing to registry...${NC}"
if docker push $REGISTRY/$IMAGE_NAME:$TAG; then
    print_status "Image pushed to registry"
else
    print_error "Failed to push image to registry"
    exit 1
fi

# 3. Update local environment
echo -e "${YELLOW}3. Updating local environment...${NC}"
docker-compose pull
docker-compose down
docker-compose up -d
print_status "Local environment updated"

# 4. Check Watchtower status
echo -e "${YELLOW}4. Checking Watchtower status...${NC}"
if docker ps | grep -q watchtower; then
    print_status "Watchtower is running"
    echo "  Watchtower will automatically update containers within 1 hour"
else
    print_warning "Watchtower is not running"
    echo "  Starting Watchtower..."
    docker-compose up -d watchtower
fi

# 5. Deploy to NAS (if accessible)
echo -e "${YELLOW}5. Deploying to NAS...${NC}"
if ping -c 1 -W 2 $NAS_HOST > /dev/null 2>&1; then
    echo "  NAS is accessible, triggering deployment..."
    
    # Force immediate update on NAS
    if sshpass -p 'bingogo1' ssh -o ConnectTimeout=5 -p $NAS_PORT $NAS_USER@$NAS_HOST \
        "cd $NAS_PATH && /usr/local/bin/docker compose pull && /usr/local/bin/docker compose up -d" 2>/dev/null; then
        print_status "NAS deployment triggered"
    else
        print_warning "Could not deploy to NAS (SSH failed)"
        echo "  Watchtower on NAS will auto-update within its interval"
    fi
else
    print_warning "NAS is not accessible"
    echo "  Watchtower on NAS will auto-update when available"
fi

# 6. Verify deployment
echo -e "${YELLOW}6. Verifying deployment...${NC}"
sleep 5

# Check local health
if curl -s http://localhost:32542/api/collection/status > /dev/null 2>&1; then
    print_status "Local service is healthy"
else
    print_error "Local service health check failed"
fi

# Check NAS health (if accessible)
if ping -c 1 -W 2 $NAS_HOST > /dev/null 2>&1; then
    if curl -s http://$NAS_HOST:32542/api/collection/status > /dev/null 2>&1; then
        print_status "NAS service is healthy"
    else
        print_warning "NAS service health check failed"
    fi
fi

# 7. Display Watchtower logs
echo -e "${YELLOW}7. Recent Watchtower activity:${NC}"
docker logs watchtower --tail 5 2>/dev/null || echo "  No Watchtower logs available"

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "Summary:"
echo "  • Image: $REGISTRY/$IMAGE_NAME:$TAG"
echo "  • Local: http://localhost:32542"
echo "  • NAS: http://$NAS_HOST:32542"
echo "  • Watchtower: Auto-updating every hour"
echo ""
echo "Watchtower will automatically:"
echo "  • Check for new images every hour"
echo "  • Update containers when new images are available"
echo "  • Clean up old images"
echo "  • Send notifications on updates"
echo ""
echo -e "${BLUE}To force immediate update:${NC}"
echo "  Local: docker-compose pull && docker-compose up -d"
echo "  NAS: ssh -p $NAS_PORT $NAS_USER@$NAS_HOST 'cd $NAS_PATH && docker compose pull && docker compose up -d'"