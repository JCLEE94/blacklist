#!/bin/bash

# Redis Standalone Container Runner
# Builds and runs Redis container independently

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

CONTAINER_NAME="blacklist-redis-standalone"
IMAGE_NAME="blacklist-redis:standalone"
NETWORK_NAME="blacklist-standalone"
CONTAINER_IP="172.25.0.20"

# Build Redis image
build() {
    echo -e "${YELLOW}Building Redis image...${NC}"
    cd "$PROJECT_ROOT"
    docker build -f docker/redis/Dockerfile -t "$IMAGE_NAME" .
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Redis image built successfully${NC}"
    else
        echo -e "${RED}✗ Failed to build Redis image${NC}"
        exit 1
    fi
}

# Start Redis container
start() {
    echo -e "${YELLOW}Starting Redis container...${NC}"
    
    # Create network if it doesn't exist
    if ! docker network ls | grep -q "$NETWORK_NAME"; then
        echo -e "${YELLOW}Creating network $NETWORK_NAME...${NC}"
        docker network create --subnet=172.25.0.0/16 "$NETWORK_NAME"
    fi
    
    # Stop and remove existing container
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    
    # Start container
    docker run -d \
        --name "$CONTAINER_NAME" \
        --network="$NETWORK_NAME" \
        --ip="$CONTAINER_IP" \
        -p 6379:6379 \
        -v blacklist-redis-data:/data \
        --restart=unless-stopped \
        "$IMAGE_NAME"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Redis container started${NC}"
        echo -e "Container: $CONTAINER_NAME"
        echo -e "IP: $CONTAINER_IP"
        echo -e "Port: 6379"
    else
        echo -e "${RED}✗ Failed to start Redis container${NC}"
        exit 1
    fi
}

# Stop container
stop() {
    echo -e "${YELLOW}Stopping Redis container...${NC}"
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    echo -e "${GREEN}✓ Redis container stopped${NC}"
}

# Remove container
remove() {
    echo -e "${YELLOW}Removing Redis container...${NC}"
    stop
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    echo -e "${GREEN}✓ Redis container removed${NC}"
}

# Show status
status() {
    echo -e "${BLUE}=== Redis Container Status ===${NC}"
    if docker ps | grep -q "$CONTAINER_NAME"; then
        echo -e "${GREEN}✓ Container: Running${NC}"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "$CONTAINER_NAME"
        
        # Test connection
        if docker exec "$CONTAINER_NAME" redis-cli ping | grep -q PONG; then
            echo -e "${GREEN}✓ Redis: Ready${NC}"
        else
            echo -e "${RED}✗ Redis: Not ready${NC}"
        fi
    else
        echo -e "${RED}✗ Container: Not running${NC}"
    fi
}

# Show logs
logs() {
    docker logs -f "$CONTAINER_NAME"
}

# Health check
health() {
    if docker exec "$CONTAINER_NAME" redis-cli ping | grep -q PONG; then
        echo -e "${GREEN}✓ Redis is healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Redis is not healthy${NC}"
        return 1
    fi
}

case "${1:-help}" in
    build) build ;;
    start) build && start ;;
    stop) stop ;;
    remove) remove ;;
    status) status ;;
    logs) logs ;;
    health) health ;;
    *)
        echo "Redis Standalone Container"
        echo "Usage: $0 {build|start|stop|remove|status|logs|health}"
        echo ""
        echo "Commands:"
        echo "  build   - Build Redis image"
        echo "  start   - Build and start container"
        echo "  stop    - Stop container"
        echo "  remove  - Stop and remove container"
        echo "  status  - Show container status"
        echo "  logs    - Show container logs"
        echo "  health  - Check Redis health"
        ;;
esac