#!/bin/bash
# Docker Run Script for Blacklist (Standalone without Docker Compose)
# Version: 1.0.40

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
IMAGE_NAME="registry.jclee.me/blacklist:latest"
CONTAINER_NAME="blacklist"
PORT="32542:2542"
NETWORK="blacklist-network"

echo -e "${GREEN}🚀 Starting Blacklist Container (Standalone)${NC}"
echo "================================"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi

# Create network if not exists
echo -e "${YELLOW}📌 Creating network...${NC}"
docker network create ${NETWORK} 2>/dev/null || echo "Network already exists"

# Stop existing container if running
if docker ps -a | grep -q ${CONTAINER_NAME}; then
    echo -e "${YELLOW}🔄 Stopping existing container...${NC}"
    docker stop ${CONTAINER_NAME} 2>/dev/null || true
    docker rm ${CONTAINER_NAME} 2>/dev/null || true
fi

# Pull latest image
echo -e "${YELLOW}📦 Pulling latest image...${NC}"
docker pull ${IMAGE_NAME}

# Run PostgreSQL if not running
if ! docker ps | grep -q "postgres"; then
    echo -e "${YELLOW}🐘 Starting PostgreSQL...${NC}"
    docker run -d \
        --name postgres \
        --network ${NETWORK} \
        -e POSTGRES_DB=blacklist \
        -e POSTGRES_USER=postgres \
        -e POSTGRES_PASSWORD=postgres \
        -p 5432:5432 \
        --restart unless-stopped \
        postgres:15-alpine
fi

# Run Redis if not running
if ! docker ps | grep -q "redis"; then
    echo -e "${YELLOW}📮 Starting Redis...${NC}"
    docker run -d \
        --name redis \
        --network ${NETWORK} \
        -p 6379:6379 \
        --restart unless-stopped \
        redis:7-alpine redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
fi

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 5

# Run the main application
echo -e "${YELLOW}🚀 Starting Blacklist application...${NC}"
docker run -d \
    --name ${CONTAINER_NAME} \
    --network ${NETWORK} \
    -p ${PORT} \
    -e DATABASE_URL=postgresql://postgres:postgres@postgres:5432/blacklist \
    -e REDIS_URL=redis://redis:6379/0 \
    -e FLASK_ENV=production \
    -e COLLECTION_ENABLED=true \
    -e FORCE_DISABLE_COLLECTION=false \
    -v blacklist-data:/app/instance \
    -v $(pwd)/data:/app/data \
    --restart unless-stopped \
    --label "com.centurylinklabs.watchtower.enable=true" \
    ${IMAGE_NAME}

# Check if container started successfully
sleep 3
if docker ps | grep -q ${CONTAINER_NAME}; then
    echo -e "${GREEN}✅ Blacklist container started successfully${NC}"
    echo ""
    echo "📊 Container Status:"
    docker ps --filter "name=${CONTAINER_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    echo -e "${GREEN}🎉 Application is running!${NC}"
    echo "- URL: http://localhost:32542"
    echo "- Health: http://localhost:32542/health"
    echo "- Logs: docker logs -f ${CONTAINER_NAME}"
    echo ""
    echo "📝 Useful Commands:"
    echo "  docker logs -f ${CONTAINER_NAME}     # View logs"
    echo "  docker restart ${CONTAINER_NAME}      # Restart"
    echo "  docker stop ${CONTAINER_NAME}         # Stop"
    echo "  docker exec -it ${CONTAINER_NAME} sh  # Shell access"
else
    echo -e "${RED}❌ Failed to start container${NC}"
    echo "Check logs: docker logs ${CONTAINER_NAME}"
    exit 1
fi