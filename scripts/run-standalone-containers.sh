#!/bin/bash

# Standalone Container Runner for Blacklist Service
# Runs PostgreSQL, Redis, and Application containers independently without docker-compose

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load network configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_ROOT/config/standalone-network.env"

if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
    echo -e "${GREEN}✓ Network configuration loaded from $CONFIG_FILE${NC}"
else
    echo -e "${YELLOW}⚠ Network configuration not found. Creating default network...${NC}"
    "$SCRIPT_DIR/setup-standalone-network.sh" create
    source "$CONFIG_FILE"
fi

# Container configurations
POSTGRES_CONTAINER="blacklist-postgresql-standalone"
REDIS_CONTAINER="blacklist-redis-standalone"
APP_CONTAINER="blacklist-app-standalone"

POSTGRES_IMAGE="blacklist-postgresql:standalone"
REDIS_IMAGE="blacklist-redis:standalone"
APP_IMAGE="blacklist-app:standalone"

# Build images if needed
build_images() {
    echo -e "${BLUE}=== Building Container Images ===${NC}"
    
    cd "$PROJECT_ROOT"
    
    echo -e "${YELLOW}Building PostgreSQL image...${NC}"
    docker build -f docker/postgresql/Dockerfile -t "$POSTGRES_IMAGE" .
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ PostgreSQL image built successfully${NC}"
    else
        echo -e "${RED}✗ Failed to build PostgreSQL image${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Building Redis image...${NC}"
    docker build -f docker/redis/Dockerfile -t "$REDIS_IMAGE" .
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Redis image built successfully${NC}"
    else
        echo -e "${RED}✗ Failed to build Redis image${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Building Application image...${NC}"
    docker build -f docker/application/Dockerfile -t "$APP_IMAGE" .
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Application image built successfully${NC}"
    else
        echo -e "${RED}✗ Failed to build Application image${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ All images built successfully${NC}"
}

# Start PostgreSQL container
start_postgresql() {
    echo -e "${YELLOW}Starting PostgreSQL container...${NC}"
    
    # Remove existing container if it exists
    docker stop "$POSTGRES_CONTAINER" 2>/dev/null || true
    docker rm "$POSTGRES_CONTAINER" 2>/dev/null || true
    
    docker run -d \
        --name "$POSTGRES_CONTAINER" \
        --network="$NETWORK_NAME" \
        --ip="$POSTGRES_IP" \
        -e POSTGRES_DB=blacklist \
        -e POSTGRES_USER=blacklist_user \
        -e POSTGRES_PASSWORD=blacklist_standalone_password_change_me \
        -v blacklist-postgres-data:/var/lib/postgresql/data \
        --restart=unless-stopped \
        "$POSTGRES_IMAGE"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ PostgreSQL container started at $POSTGRES_IP${NC}"
    else
        echo -e "${RED}✗ Failed to start PostgreSQL container${NC}"
        return 1
    fi
}

# Start Redis container
start_redis() {
    echo -e "${YELLOW}Starting Redis container...${NC}"
    
    # Remove existing container if it exists
    docker stop "$REDIS_CONTAINER" 2>/dev/null || true
    docker rm "$REDIS_CONTAINER" 2>/dev/null || true
    
    docker run -d \
        --name "$REDIS_CONTAINER" \
        --network="$NETWORK_NAME" \
        --ip="$REDIS_IP" \
        -v blacklist-redis-data:/data \
        --restart=unless-stopped \
        "$REDIS_IMAGE"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Redis container started at $REDIS_IP${NC}"
    else
        echo -e "${RED}✗ Failed to start Redis container${NC}"
        return 1
    fi
}

# Start Application container
start_application() {
    echo -e "${YELLOW}Starting Application container...${NC}"
    
    # Remove existing container if it exists
    docker stop "$APP_CONTAINER" 2>/dev/null || true
    docker rm "$APP_CONTAINER" 2>/dev/null || true
    
    docker run -d \
        --name "$APP_CONTAINER" \
        --network="$NETWORK_NAME" \
        --ip="$APP_IP" \
        -p 2542:2542 \
        -e DATABASE_URL="postgresql://blacklist_user:blacklist_standalone_password_change_me@$POSTGRES_IP:5432/blacklist" \
        -e REDIS_URL="redis://$REDIS_IP:6379/0" \
        -e FLASK_ENV=production \
        -e PORT=2542 \
        -e COLLECTION_ENABLED=true \
        -e FORCE_DISABLE_COLLECTION=false \
        -v blacklist-app-data:/app/data \
        -v blacklist-app-logs:/app/logs \
        --restart=unless-stopped \
        "$APP_IMAGE"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Application container started at $APP_IP (port 2542)${NC}"
    else
        echo -e "${RED}✗ Failed to start Application container${NC}"
        return 1
    fi
}

# Wait for services to be ready
wait_for_services() {
    echo -e "${BLUE}=== Waiting for Services ===${NC}"
    
    # Wait for PostgreSQL
    echo -e "${YELLOW}Waiting for PostgreSQL...${NC}"
    for i in {1..30}; do
        if docker exec "$POSTGRES_CONTAINER" pg_isready -U blacklist_user -d blacklist > /dev/null 2>&1; then
            echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
            break
        fi
        if [ $i -eq 30 ]; then
            echo -e "${RED}✗ PostgreSQL failed to start within 30 seconds${NC}"
            return 1
        fi
        sleep 1
    done
    
    # Wait for Redis
    echo -e "${YELLOW}Waiting for Redis...${NC}"
    for i in {1..20}; do
        if docker exec "$REDIS_CONTAINER" redis-cli ping | grep -q PONG; then
            echo -e "${GREEN}✓ Redis is ready${NC}"
            break
        fi
        if [ $i -eq 20 ]; then
            echo -e "${RED}✗ Redis failed to start within 20 seconds${NC}"
            return 1
        fi
        sleep 1
    done
    
    # Wait for Application
    echo -e "${YELLOW}Waiting for Application...${NC}"
    for i in {1..60}; do
        if curl -f -s http://localhost:2542/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Application is ready${NC}"
            break
        fi
        if [ $i -eq 60 ]; then
            echo -e "${RED}✗ Application failed to start within 60 seconds${NC}"
            return 1
        fi
        sleep 1
    done
}

# Stop all containers
stop_containers() {
    echo -e "${YELLOW}Stopping all containers...${NC}"
    
    docker stop "$APP_CONTAINER" 2>/dev/null || true
    docker stop "$REDIS_CONTAINER" 2>/dev/null || true
    docker stop "$POSTGRES_CONTAINER" 2>/dev/null || true
    
    echo -e "${GREEN}✓ All containers stopped${NC}"
}

# Remove all containers
remove_containers() {
    echo -e "${YELLOW}Removing all containers...${NC}"
    
    stop_containers
    
    docker rm "$APP_CONTAINER" 2>/dev/null || true
    docker rm "$REDIS_CONTAINER" 2>/dev/null || true
    docker rm "$POSTGRES_CONTAINER" 2>/dev/null || true
    
    echo -e "${GREEN}✓ All containers removed${NC}"
}

# Show container status
show_status() {
    echo -e "${BLUE}=== Container Status ===${NC}"
    
    containers=("$POSTGRES_CONTAINER" "$REDIS_CONTAINER" "$APP_CONTAINER")
    for container in "${containers[@]}"; do
        if docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -q "$container"; then
            echo -e "${GREEN}✓ $container: Running${NC}"
            docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "$container"
        elif docker ps -a --format "table {{.Names}}\t{{.Status}}" | grep -q "$container"; then
            echo -e "${RED}✗ $container: Stopped${NC}"
            docker ps -a --format "table {{.Names}}\t{{.Status}}" | grep "$container"
        else
            echo -e "${YELLOW}⚠ $container: Not found${NC}"
        fi
    done
    
    echo ""
    echo -e "${BLUE}=== Service URLs ===${NC}"
    echo "Application: http://localhost:2542"
    echo "Health Check: http://localhost:2542/health"
    echo "Dashboard: http://localhost:2542/dashboard"
}

# Show logs
show_logs() {
    container="$1"
    case "$container" in
        postgres|postgresql)
            docker logs -f "$POSTGRES_CONTAINER"
            ;;
        redis)
            docker logs -f "$REDIS_CONTAINER"
            ;;
        app|application)
            docker logs -f "$APP_CONTAINER"
            ;;
        all|"")
            echo -e "${BLUE}=== All Container Logs ===${NC}"
            docker logs --tail=20 "$POSTGRES_CONTAINER" 2>&1 | sed 's/^/[POSTGRES] /'
            docker logs --tail=20 "$REDIS_CONTAINER" 2>&1 | sed 's/^/[REDIS] /'
            docker logs --tail=20 "$APP_CONTAINER" 2>&1 | sed 's/^/[APP] /'
            ;;
        *)
            echo "Unknown container: $container"
            echo "Available containers: postgres, redis, app, all"
            exit 1
            ;;
    esac
}

# Health check
health_check() {
    echo -e "${BLUE}=== Health Check ===${NC}"
    
    # Check containers
    echo -e "${YELLOW}Container Health:${NC}"
    for container in "$POSTGRES_CONTAINER" "$REDIS_CONTAINER" "$APP_CONTAINER"; do
        if docker ps | grep -q "$container"; then
            echo -e "  ${GREEN}✓ $container: Running${NC}"
        else
            echo -e "  ${RED}✗ $container: Not running${NC}"
        fi
    done
    
    # Check services
    echo -e "${YELLOW}Service Health:${NC}"
    
    # PostgreSQL
    if docker exec "$POSTGRES_CONTAINER" pg_isready -U blacklist_user -d blacklist > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ PostgreSQL: Ready${NC}"
    else
        echo -e "  ${RED}✗ PostgreSQL: Not ready${NC}"
    fi
    
    # Redis
    if docker exec "$REDIS_CONTAINER" redis-cli ping | grep -q PONG 2>/dev/null; then
        echo -e "  ${GREEN}✓ Redis: Ready${NC}"
    else
        echo -e "  ${RED}✗ Redis: Not ready${NC}"
    fi
    
    # Application
    if curl -f -s http://localhost:2542/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Application: Ready${NC}"
        echo -e "${YELLOW}API Response:${NC}"
        curl -s http://localhost:2542/health | jq . 2>/dev/null || curl -s http://localhost:2542/health
    else
        echo -e "  ${RED}✗ Application: Not ready${NC}"
    fi
}

# Main command handling
case "${1:-help}" in
    start)
        echo -e "${BLUE}=== Starting Blacklist Standalone Services ===${NC}"
        build_images
        start_postgresql
        start_redis
        start_application
        wait_for_services
        show_status
        echo -e "${GREEN}=== All services started successfully ===${NC}"
        ;;
        
    stop)
        stop_containers
        ;;
        
    restart)
        echo -e "${BLUE}=== Restarting Blacklist Standalone Services ===${NC}"
        stop_containers
        sleep 2
        start_postgresql
        start_redis  
        start_application
        wait_for_services
        show_status
        ;;
        
    remove)
        remove_containers
        ;;
        
    build)
        build_images
        ;;
        
    status)
        show_status
        ;;
        
    logs)
        show_logs "$2"
        ;;
        
    health)
        health_check
        ;;
        
    help|*)
        echo "Blacklist Standalone Container Manager"
        echo ""
        echo "Usage: $0 {start|stop|restart|remove|build|status|logs|health}"
        echo ""
        echo "Commands:"
        echo "  start   - Build and start all containers"
        echo "  stop    - Stop all containers"
        echo "  restart - Restart all containers"
        echo "  remove  - Stop and remove all containers"
        echo "  build   - Build all container images"
        echo "  status  - Show container status"
        echo "  logs    - Show logs (logs [postgres|redis|app|all])"
        echo "  health  - Perform health check"
        echo "  help    - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 start              # Start all services"
        echo "  $0 logs app           # Show application logs"
        echo "  $0 health             # Check service health"
        ;;
esac