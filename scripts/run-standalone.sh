#!/bin/bash
# Complete Standalone Docker Deployment Script
# Zero docker-compose dependencies - each container runs independently
# Version: v1.0.37

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REGISTRY_URL="${REGISTRY_URL:-registry.jclee.me}"
NETWORK_NAME="blacklist-net"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Container configuration
POSTGRES_CONTAINER="blacklist-postgresql"
REDIS_CONTAINER="blacklist-redis"
APP_CONTAINER="blacklist"

# Network configuration
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
REDIS_PORT="${REDIS_PORT:-6379}"
APP_PORT="${APP_PORT:-2542}"

# Database configuration
POSTGRES_DB="${POSTGRES_DB:-blacklist}"
POSTGRES_USER="${POSTGRES_USER:-blacklist_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-blacklist_standalone_password_change_me}"

# Application configuration
SECRET_KEY="${SECRET_KEY:-standalone-secret-key-change-in-production}"
JWT_SECRET_KEY="${JWT_SECRET_KEY:-standalone-jwt-key-change-in-production}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-standalone_admin_change_me}"

# Function to show usage
show_usage() {
    cat << EOF
Blacklist Management System - Standalone Docker Deployment

USAGE:
    $0 [COMMAND] [OPTIONS]

COMMANDS:
    start           Start all standalone containers (PostgreSQL + Redis + App)
    stop            Stop all standalone containers
    restart         Restart all standalone containers
    status          Show status of all containers
    logs            Show logs from all containers
    clean           Stop and remove all containers and network
    app-only        Start only the main application (with SQLite fallback)
    build           Build all standalone Docker images
    push            Push all images to registry
    pull            Pull all images from registry
    backup          Create backup of data
    restore         Restore from backup
    health          Check health of all services
    shell           Open shell in application container
    psql            Connect to PostgreSQL database
    redis-cli       Connect to Redis CLI

OPTIONS:
    --no-postgres   Skip PostgreSQL container (use SQLite)
    --no-redis      Skip Redis container (use memory cache)
    --build         Build images before starting
    --pull          Pull latest images before starting
    --detach        Run in detached mode (default)
    --logs          Show logs after starting
    --registry URL  Use custom registry URL (default: registry.jclee.me)

EXAMPLES:
    $0 start                    # Start all services
    $0 start --no-postgres      # Start with SQLite only
    $0 app-only                 # Start app with SQLite + memory cache
    $0 build && $0 start        # Build and start
    $0 logs app                 # Show app logs
    $0 shell                    # Open app shell

ENVIRONMENT VARIABLES:
    POSTGRES_PASSWORD           Database password
    SECRET_KEY                  Application secret key
    JWT_SECRET_KEY             JWT secret key
    ADMIN_PASSWORD             Admin user password
    REGISTRY_URL               Docker registry URL
    APP_PORT                   Application port (default: 2542)
    POSTGRES_PORT              PostgreSQL port (default: 5432)
    REDIS_PORT                 Redis port (default: 6379)

EOF
}

# Function to check if Docker is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
}

# Function to create Docker network
create_network() {
    if ! docker network inspect "$NETWORK_NAME" &> /dev/null; then
        log_info "Creating Docker network: $NETWORK_NAME"
        docker network create \
            --driver bridge \
            --subnet 172.30.0.0/16 \
            --gateway 172.30.0.1 \
            "$NETWORK_NAME"
        log_success "Network created successfully"
    else
        log_info "Network $NETWORK_NAME already exists"
    fi
}

# Function to remove Docker network
remove_network() {
    if docker network inspect "$NETWORK_NAME" &> /dev/null; then
        log_info "Removing Docker network: $NETWORK_NAME"
        docker network rm "$NETWORK_NAME" || true
    fi
}

# Function to start PostgreSQL container
start_postgresql() {
    log_info "Starting PostgreSQL container..."
    
    docker run -d \
        --name "$POSTGRES_CONTAINER" \
        --network "$NETWORK_NAME" \
        --restart unless-stopped \
        -p "${POSTGRES_PORT}:5432" \
        -v blacklist-postgresql-data:/var/lib/postgresql/data \
        -e POSTGRES_DB="$POSTGRES_DB" \
        -e POSTGRES_USER="$POSTGRES_USER" \
        -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
        -e POSTGRES_SHARED_BUFFERS=256MB \
        -e POSTGRES_EFFECTIVE_CACHE_SIZE=1GB \
        -e POSTGRES_MAINTENANCE_WORK_MEM=64MB \
        -e POSTGRES_WORK_MEM=16MB \
        -e POSTGRES_MAX_CONNECTIONS=100 \
        "$REGISTRY_URL/blacklist-postgresql:latest"
    
    log_success "PostgreSQL container started"
    
    # Wait for PostgreSQL to be ready
    log_info "Waiting for PostgreSQL to be ready..."
    for i in {1..30}; do
        if docker exec "$POSTGRES_CONTAINER" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" &> /dev/null; then
            log_success "PostgreSQL is ready"
            break
        fi
        sleep 2
        if [ $i -eq 30 ]; then
            log_error "PostgreSQL failed to start within 60 seconds"
            exit 1
        fi
    done
}

# Function to start Redis container
start_redis() {
    log_info "Starting Redis container..."
    
    docker run -d \
        --name "$REDIS_CONTAINER" \
        --network "$NETWORK_NAME" \
        --restart unless-stopped \
        -p "${REDIS_PORT}:6379" \
        -v blacklist-redis-data:/data \
        -e REDIS_MAXMEMORY=1gb \
        -e REDIS_MAXMEMORY_POLICY=allkeys-lru \
        -e REDIS_APPENDONLY=yes \
        -e REDIS_APPENDFSYNC=everysec \
        "$REGISTRY_URL/blacklist-redis:latest"
    
    log_success "Redis container started"
    
    # Wait for Redis to be ready
    log_info "Waiting for Redis to be ready..."
    for i in {1..15}; do
        if docker exec "$REDIS_CONTAINER" redis-cli ping &> /dev/null; then
            log_success "Redis is ready"
            break
        fi
        sleep 2
        if [ $i -eq 15 ]; then
            log_error "Redis failed to start within 30 seconds"
            exit 1
        fi
    done
}

# Function to start main application container
start_application() {
    local use_postgres="$1"
    local use_redis="$2"
    
    log_info "Starting Blacklist application container..."
    
    # Determine database URL
    local database_url
    if [ "$use_postgres" = "true" ]; then
        database_url="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_CONTAINER}:5432/${POSTGRES_DB}"
    else
        database_url="sqlite:////app/data/blacklist_standalone.db"
    fi
    
    # Determine Redis URL
    local redis_url
    local cache_type
    if [ "$use_redis" = "true" ]; then
        redis_url="redis://${REDIS_CONTAINER}:6379/0"
        cache_type="redis"
    else
        redis_url="redis://localhost:6379/0"
        cache_type="memory"
    fi
    
    docker run -d \
        --name "$APP_CONTAINER" \
        --network "$NETWORK_NAME" \
        --restart unless-stopped \
        -p "${APP_PORT}:2542" \
        -v blacklist-app-data:/app/data \
        -v blacklist-app-logs:/app/logs \
        -e FLASK_ENV=production \
        -e PORT=2542 \
        -e DEBUG=false \
        -e SECRET_KEY="$SECRET_KEY" \
        -e JWT_SECRET_KEY="$JWT_SECRET_KEY" \
        -e DATABASE_URL="$database_url" \
        -e REDIS_URL="$redis_url" \
        -e CACHE_TYPE="$cache_type" \
        -e COLLECTION_ENABLED=false \
        -e FORCE_DISABLE_COLLECTION=true \
        -e RESTART_PROTECTION=true \
        -e JWT_ENABLED=true \
        -e API_KEY_ENABLED=true \
        -e DEFAULT_API_KEY=blk_standalone_default_key_change_me \
        -e ADMIN_USERNAME=admin \
        -e ADMIN_PASSWORD="$ADMIN_PASSWORD" \
        -e GUNICORN_WORKERS=2 \
        -e GUNICORN_THREADS=2 \
        -e LOG_LEVEL=INFO \
        -e ENABLE_V2_API=true \
        -e ENABLE_METRICS=true \
        -e SECURITY_HEADERS_ENABLED=true \
        -e RATE_LIMIT_ENABLED=true \
        "$REGISTRY_URL/blacklist:latest"
    
    log_success "Application container started"
    
    # Wait for application to be ready
    log_info "Waiting for application to be ready..."
    for i in {1..30}; do
        if curl -sf "http://localhost:${APP_PORT}/health" &> /dev/null; then
            log_success "Application is ready"
            break
        fi
        sleep 2
        if [ $i -eq 30 ]; then
            log_error "Application failed to start within 60 seconds"
            exit 1
        fi
    done
}

# Function to stop containers
stop_containers() {
    log_info "Stopping all standalone containers..."
    
    containers=("$APP_CONTAINER" "$REDIS_CONTAINER" "$POSTGRES_CONTAINER")
    
    for container in "${containers[@]}"; do
        if docker ps -q -f name="$container" | grep -q .; then
            log_info "Stopping $container..."
            docker stop "$container" || true
        fi
    done
    
    log_success "All containers stopped"
}

# Function to remove containers
remove_containers() {
    log_info "Removing all standalone containers..."
    
    containers=("$APP_CONTAINER" "$REDIS_CONTAINER" "$POSTGRES_CONTAINER")
    
    for container in "${containers[@]}"; do
        if docker ps -aq -f name="$container" | grep -q .; then
            log_info "Removing $container..."
            docker rm -f "$container" || true
        fi
    done
    
    log_success "All containers removed"
}

# Function to show container status
show_status() {
    log_info "Container Status:"
    echo
    
    containers=("$POSTGRES_CONTAINER" "$REDIS_CONTAINER" "$APP_CONTAINER")
    
    for container in "${containers[@]}"; do
        if docker ps -q -f name="$container" | grep -q .; then
            status=$(docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" -f name="$container")
            echo -e "${GREEN}✓${NC} $status"
        else
            echo -e "${RED}✗${NC} $container - Not running"
        fi
    done
    
    echo
    log_info "Network Status:"
    if docker network inspect "$NETWORK_NAME" &> /dev/null; then
        echo -e "${GREEN}✓${NC} Network $NETWORK_NAME exists"
    else
        echo -e "${RED}✗${NC} Network $NETWORK_NAME not found"
    fi
    
    echo
    log_info "Volume Status:"
    volumes=("blacklist-postgresql-data" "blacklist-redis-data" "blacklist-app-data" "blacklist-app-logs")
    for volume in "${volumes[@]}"; do
        if docker volume inspect "$volume" &> /dev/null; then
            echo -e "${GREEN}✓${NC} Volume $volume exists"
        else
            echo -e "${YELLOW}!${NC} Volume $volume not found"
        fi
    done
}

# Function to show logs
show_logs() {
    local service="$1"
    local follow="$2"
    
    case "$service" in
        "app"|"application")
            container="$APP_CONTAINER"
            ;;
        "postgres"|"postgresql"|"db")
            container="$POSTGRES_CONTAINER"
            ;;
        "redis"|"cache")
            container="$REDIS_CONTAINER"
            ;;
        "")
            log_info "Showing logs from all containers..."
            echo
            log_info "=== Application Logs ==="
            docker logs --tail=50 "$APP_CONTAINER" 2>/dev/null || echo "Application container not running"
            echo
            log_info "=== PostgreSQL Logs ==="
            docker logs --tail=20 "$POSTGRES_CONTAINER" 2>/dev/null || echo "PostgreSQL container not running"
            echo
            log_info "=== Redis Logs ==="
            docker logs --tail=20 "$REDIS_CONTAINER" 2>/dev/null || echo "Redis container not running"
            return
            ;;
        *)
            log_error "Unknown service: $service"
            log_info "Available services: app, postgres, redis"
            exit 1
            ;;
    esac
    
    if [ "$follow" = "true" ]; then
        docker logs -f "$container"
    else
        docker logs --tail=50 "$container"
    fi
}

# Function to check health
check_health() {
    log_info "Checking health of all services..."
    echo
    
    # Check PostgreSQL
    if docker ps -q -f name="$POSTGRES_CONTAINER" | grep -q .; then
        if docker exec "$POSTGRES_CONTAINER" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" &> /dev/null; then
            echo -e "${GREEN}✓${NC} PostgreSQL - Healthy"
        else
            echo -e "${RED}✗${NC} PostgreSQL - Unhealthy"
        fi
    else
        echo -e "${YELLOW}!${NC} PostgreSQL - Not running"
    fi
    
    # Check Redis
    if docker ps -q -f name="$REDIS_CONTAINER" | grep -q .; then
        if docker exec "$REDIS_CONTAINER" redis-cli ping &> /dev/null; then
            echo -e "${GREEN}✓${NC} Redis - Healthy"
        else
            echo -e "${RED}✗${NC} Redis - Unhealthy"
        fi
    else
        echo -e "${YELLOW}!${NC} Redis - Not running"
    fi
    
    # Check Application
    if docker ps -q -f name="$APP_CONTAINER" | grep -q .; then
        if curl -sf "http://localhost:${APP_PORT}/health" &> /dev/null; then
            echo -e "${GREEN}✓${NC} Application - Healthy"
            # Show detailed health info
            log_info "Application health details:"
            curl -s "http://localhost:${APP_PORT}/api/health" | python3 -m json.tool 2>/dev/null || echo "Health endpoint not available"
        else
            echo -e "${RED}✗${NC} Application - Unhealthy"
        fi
    else
        echo -e "${YELLOW}!${NC} Application - Not running"
    fi
}

# Function to build all images
build_images() {
    log_info "Building all standalone Docker images..."
    
    # Build main application
    log_info "Building main application image..."
    docker build -f "$PROJECT_ROOT/Dockerfile.standalone" -t "$REGISTRY_URL/blacklist:standalone" "$PROJECT_ROOT"
    
    # Build PostgreSQL
    log_info "Building PostgreSQL image..."
    docker build -f "$PROJECT_ROOT/build/docker/postgresql/Dockerfile.standalone" -t "$REGISTRY_URL/blacklist-postgresql:standalone" "$PROJECT_ROOT/build/docker/postgresql"
    
    # Build Redis
    log_info "Building Redis image..."
    docker build -f "$PROJECT_ROOT/build/docker/redis/Dockerfile.standalone" -t "$REGISTRY_URL/blacklist-redis:standalone" "$PROJECT_ROOT/build/docker/redis"
    
    log_success "All images built successfully"
}

# Function to push images
push_images() {
    log_info "Pushing all standalone images to registry..."
    
    images=(
        "$REGISTRY_URL/blacklist:latest"
        "$REGISTRY_URL/blacklist-postgresql:latest"
        "$REGISTRY_URL/blacklist-redis:latest"
    )
    
    for image in "${images[@]}"; do
        log_info "Pushing $image..."
        docker push "$image"
    done
    
    log_success "All images pushed successfully"
}

# Function to pull images
pull_images() {
    log_info "Pulling all standalone images from registry..."
    
    images=(
        "$REGISTRY_URL/blacklist:latest"
        "$REGISTRY_URL/blacklist-postgresql:latest"
        "$REGISTRY_URL/blacklist-redis:latest"
    )
    
    for image in "${images[@]}"; do
        log_info "Pulling $image..."
        docker pull "$image"
    done
    
    log_success "All images pulled successfully"
}

# Function to create backup
create_backup() {
    local backup_dir="/tmp/blacklist-standalone-backup-$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    log_info "Creating backup at $backup_dir..."
    
    # Backup PostgreSQL data
    if docker ps -q -f name="$POSTGRES_CONTAINER" | grep -q .; then
        log_info "Backing up PostgreSQL data..."
        docker exec "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$backup_dir/postgres_dump.sql"
    fi
    
    # Backup Redis data
    if docker ps -q -f name="$REDIS_CONTAINER" | grep -q .; then
        log_info "Backing up Redis data..."
        docker exec "$REDIS_CONTAINER" redis-cli --rdb /data/backup.rdb
        docker cp "$REDIS_CONTAINER:/data/backup.rdb" "$backup_dir/redis_dump.rdb"
    fi
    
    # Backup application data
    if docker volume inspect blacklist-app-data &> /dev/null; then
        log_info "Backing up application data..."
        docker run --rm -v blacklist-app-data:/data -v "$backup_dir:/backup" alpine tar -czf /backup/app_data.tar.gz -C /data .
    fi
    
    log_success "Backup created at $backup_dir"
}

# Function to open shell
open_shell() {
    if docker ps -q -f name="$APP_CONTAINER" | grep -q .; then
        log_info "Opening shell in application container..."
        docker exec -it "$APP_CONTAINER" /bin/bash
    else
        log_error "Application container is not running"
        exit 1
    fi
}

# Function to connect to PostgreSQL
connect_psql() {
    if docker ps -q -f name="$POSTGRES_CONTAINER" | grep -q .; then
        log_info "Connecting to PostgreSQL..."
        docker exec -it "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
    else
        log_error "PostgreSQL container is not running"
        exit 1
    fi
}

# Function to connect to Redis CLI
connect_redis_cli() {
    if docker ps -q -f name="$REDIS_CONTAINER" | grep -q .; then
        log_info "Connecting to Redis CLI..."
        docker exec -it "$REDIS_CONTAINER" redis-cli
    else
        log_error "Redis container is not running"
        exit 1
    fi
}

# Parse command line arguments
COMMAND=""
USE_POSTGRES="true"
USE_REDIS="true"
BUILD_IMAGES="false"
PULL_IMAGES="false"
SHOW_LOGS="false"
FOLLOW_LOGS="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        start|stop|restart|status|logs|clean|app-only|build|push|pull|backup|restore|health|shell|psql|redis-cli)
            COMMAND="$1"
            shift
            ;;
        --no-postgres)
            USE_POSTGRES="false"
            shift
            ;;
        --no-redis)
            USE_REDIS="false"
            shift
            ;;
        --build)
            BUILD_IMAGES="true"
            shift
            ;;
        --pull)
            PULL_IMAGES="true"
            shift
            ;;
        --logs)
            SHOW_LOGS="true"
            shift
            ;;
        --follow|-f)
            FOLLOW_LOGS="true"
            shift
            ;;
        --registry)
            REGISTRY_URL="$2"
            shift 2
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        app|postgres|postgresql|db|redis|cache)
            if [ "$COMMAND" = "logs" ]; then
                LOG_SERVICE="$1"
            fi
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check if command is provided
if [ -z "$COMMAND" ]; then
    log_error "No command provided"
    show_usage
    exit 1
fi

# Check Docker availability
check_docker

# Execute command
case "$COMMAND" in
    "start")
        log_info "Starting Blacklist Management System in standalone mode..."
        log_info "Configuration:"
        log_info "  - PostgreSQL: $USE_POSTGRES"
        log_info "  - Redis: $USE_REDIS"
        log_info "  - Registry: $REGISTRY_URL"
        log_info "  - App Port: $APP_PORT"
        echo
        
        if [ "$BUILD_IMAGES" = "true" ]; then
            build_images
        fi
        
        if [ "$PULL_IMAGES" = "true" ]; then
            pull_images
        fi
        
        create_network
        
        if [ "$USE_POSTGRES" = "true" ]; then
            start_postgresql
        fi
        
        if [ "$USE_REDIS" = "true" ]; then
            start_redis
        fi
        
        start_application "$USE_POSTGRES" "$USE_REDIS"
        
        echo
        log_success "All services started successfully!"
        log_info "Application available at: http://localhost:${APP_PORT}"
        log_info "Health check: curl http://localhost:${APP_PORT}/health"
        
        if [ "$SHOW_LOGS" = "true" ]; then
            echo
            show_logs "" "$FOLLOW_LOGS"
        fi
        ;;
        
    "stop")
        stop_containers
        ;;
        
    "restart")
        stop_containers
        sleep 2
        create_network
        
        if [ "$USE_POSTGRES" = "true" ]; then
            start_postgresql
        fi
        
        if [ "$USE_REDIS" = "true" ]; then
            start_redis
        fi
        
        start_application "$USE_POSTGRES" "$USE_REDIS"
        log_success "All services restarted successfully!"
        ;;
        
    "status")
        show_status
        ;;
        
    "logs")
        show_logs "$LOG_SERVICE" "$FOLLOW_LOGS"
        ;;
        
    "clean")
        stop_containers
        remove_containers
        remove_network
        log_info "Cleaning up volumes (optional)..."
        log_warning "To remove all data, run: docker volume rm blacklist-postgresql-data blacklist-redis-data blacklist-app-data blacklist-app-logs"
        log_success "Cleanup completed"
        ;;
        
    "app-only")
        log_info "Starting application in standalone mode with SQLite + Memory cache..."
        create_network
        start_application "false" "false"
        log_success "Application started in standalone mode!"
        log_info "Application available at: http://localhost:${APP_PORT}"
        log_info "Database: SQLite"
        log_info "Cache: Memory"
        ;;
        
    "build")
        build_images
        ;;
        
    "push")
        push_images
        ;;
        
    "pull")
        pull_images
        ;;
        
    "backup")
        create_backup
        ;;
        
    "health")
        check_health
        ;;
        
    "shell")
        open_shell
        ;;
        
    "psql")
        connect_psql
        ;;
        
    "redis-cli")
        connect_redis_cli
        ;;
        
    *)
        log_error "Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac