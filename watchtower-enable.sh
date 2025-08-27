#!/bin/bash
# Watchtower Enable Script for Blacklist
# Standalone Watchtower container for auto-updates
# Version: 1.0.40

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

WATCHTOWER_CONTAINER="watchtower"
NETWORK="blacklist-network"

echo -e "${BLUE}🔄 Watchtower Auto-Update Configuration${NC}"
echo "=========================================="

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi

# Stop existing Watchtower if running
if docker ps -a | grep -q ${WATCHTOWER_CONTAINER}; then
    echo -e "${YELLOW}🛑 Stopping existing Watchtower...${NC}"
    docker stop ${WATCHTOWER_CONTAINER} 2>/dev/null || true
    docker rm ${WATCHTOWER_CONTAINER} 2>/dev/null || true
fi

# Create network if not exists
echo -e "${YELLOW}📌 Creating network...${NC}"
docker network create ${NETWORK} 2>/dev/null || echo "Network already exists"

# Run Watchtower
echo -e "${GREEN}🚀 Starting Watchtower...${NC}"
docker run -d \
    --name ${WATCHTOWER_CONTAINER} \
    --network ${NETWORK} \
    --restart unless-stopped \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /root/.docker/config.json:/config.json:ro \
    -e WATCHTOWER_POLL_INTERVAL=1800 \
    -e WATCHTOWER_LABEL_ENABLE=true \
    -e WATCHTOWER_CLEANUP=true \
    -e WATCHTOWER_INCLUDE_STOPPED=false \
    -e WATCHTOWER_INCLUDE_RESTARTING=true \
    -e WATCHTOWER_ROLLING_RESTART=true \
    -e WATCHTOWER_TIMEOUT=30 \
    -e WATCHTOWER_DEBUG=false \
    containrrr/watchtower:latest \
    --interval 1800 \
    --cleanup \
    --label-enable

# Check status
sleep 2
if docker ps | grep -q ${WATCHTOWER_CONTAINER}; then
    echo -e "${GREEN}✅ Watchtower started successfully${NC}"
    echo ""
    echo "📊 Watchtower Configuration:"
    echo "  - Update interval: 30 minutes (1800 seconds)"
    echo "  - Monitoring: Containers with label 'com.centurylinklabs.watchtower.enable=true'"
    echo "  - Cleanup: Old images will be removed after update"
    echo "  - Rolling restart: Enabled for zero-downtime updates"
    echo ""
    echo "🎯 Monitored Containers:"
    docker ps --filter "label=com.centurylinklabs.watchtower.enable=true" --format "  - {{.Names}} ({{.Image}})"
    echo ""
    echo "📝 Commands:"
    echo "  docker logs -f watchtower         # View Watchtower logs"
    echo "  docker restart watchtower          # Restart Watchtower"
    echo "  docker stop watchtower             # Stop auto-updates"
    echo "  docker start watchtower            # Resume auto-updates"
    echo ""
    echo -e "${GREEN}🎉 Watchtower is now monitoring for updates!${NC}"
else
    echo -e "${RED}❌ Failed to start Watchtower${NC}"
    echo "Check logs: docker logs ${WATCHTOWER_CONTAINER}"
    exit 1
fi

# Show first few log lines
echo ""
echo -e "${BLUE}📜 Initial Watchtower logs:${NC}"
docker logs --tail 10 ${WATCHTOWER_CONTAINER}