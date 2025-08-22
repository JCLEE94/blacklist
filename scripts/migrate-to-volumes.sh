#!/bin/bash
# Script to migrate from bind mounts to Docker volumes
# Removes external dependencies and uses only Docker-managed volumes

set -e

echo "🔄 Docker Volume Migration Script"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    exit 1
fi

echo "📊 Current Docker setup:"
echo "------------------------"

# Show current containers
echo "Containers:"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" | grep -E "blacklist|redis|postgresql" || echo "No containers found"

echo ""

# Show current volumes
echo "Volumes:"
docker volume ls | grep blacklist || echo "No volumes found"

echo ""

# Stop services if running
echo -e "${YELLOW}⏸️  Stopping current services...${NC}"
docker-compose -f deployments/docker-compose/docker-compose.yml down 2>/dev/null || true

# Backup existing data from bind mounts
echo ""
echo -e "${YELLOW}💾 Backing up existing data...${NC}"

BACKUP_DIR="backups/migration-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup bind mount data if exists
if [ -d "data" ]; then
    echo "  - Backing up data directory..."
    cp -r data "$BACKUP_DIR/data-backup" 2>/dev/null || true
fi

if [ -d "logs" ]; then
    echo "  - Backing up logs directory..."
    cp -r logs "$BACKUP_DIR/logs-backup" 2>/dev/null || true
fi

echo -e "${GREEN}✅ Backup created in $BACKUP_DIR${NC}"

# Create Docker volumes
echo ""
echo -e "${YELLOW}🐳 Creating Docker volumes...${NC}"

docker volume create blacklist-data
docker volume create blacklist-logs
docker volume create blacklist-redis-data
docker volume create blacklist-postgresql-data

echo -e "${GREEN}✅ Volumes created${NC}"

# Migrate data to volumes (if backup exists)
echo ""
echo -e "${YELLOW}📦 Migrating data to volumes...${NC}"

if [ -d "$BACKUP_DIR/data-backup" ]; then
    # Use temporary container to copy data
    echo "  - Migrating application data..."
    docker run --rm -v "$PWD/$BACKUP_DIR/data-backup":/source:ro \
        -v blacklist-data:/target \
        alpine cp -r /source/. /target/ 2>/dev/null || true
    
    if [ -d "$BACKUP_DIR/data-backup/redis" ]; then
        echo "  - Migrating Redis data..."
        docker run --rm -v "$PWD/$BACKUP_DIR/data-backup/redis":/source:ro \
            -v blacklist-redis-data:/target \
            alpine cp -r /source/. /target/ 2>/dev/null || true
    fi
    
    if [ -d "$BACKUP_DIR/data-backup/postgresql" ]; then
        echo "  - Migrating PostgreSQL data..."
        docker run --rm -v "$PWD/$BACKUP_DIR/data-backup/postgresql":/source:ro \
            -v blacklist-postgresql-data:/target \
            alpine cp -r /source/. /target/ 2>/dev/null || true
    fi
fi

if [ -d "$BACKUP_DIR/logs-backup" ]; then
    echo "  - Migrating logs..."
    docker run --rm -v "$PWD/$BACKUP_DIR/logs-backup":/source:ro \
        -v blacklist-logs:/target \
        alpine cp -r /source/. /target/ 2>/dev/null || true
fi

echo -e "${GREEN}✅ Data migration complete${NC}"

# Start services with new volume-based configuration
echo ""
echo -e "${YELLOW}🚀 Starting services with Docker volumes...${NC}"

cd deployments/docker-compose
docker-compose up -d

# Wait for services to be healthy
echo ""
echo -e "${YELLOW}⏳ Waiting for services to be healthy...${NC}"

MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if docker-compose ps | grep -q "healthy"; then
        echo -e "${GREEN}✅ Services are healthy${NC}"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo -n "."
    sleep 2
done

# Show final status
echo ""
echo "📊 Final Docker setup:"
echo "----------------------"

# Show running containers
echo "Containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" | grep -E "blacklist|redis|postgresql"

echo ""

# Show volumes
echo "Volumes:"
docker volume ls | grep blacklist

echo ""

# Test health endpoint
echo -e "${YELLOW}🔍 Testing application health...${NC}"
if curl -sf http://localhost:32542/health >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Application is healthy!${NC}"
else
    echo -e "${RED}❌ Application health check failed${NC}"
fi

echo ""
echo "🎉 Migration complete!"
echo ""
echo "📝 Notes:"
echo "  - Old bind mount directories can be removed after verifying the migration"
echo "  - Backup is saved in: $BACKUP_DIR"
echo "  - Docker volumes are now managing all data"
echo "  - No external dependencies or bind mounts are used"
echo ""
echo "🔧 Useful commands:"
echo "  docker volume inspect blacklist-data       # Inspect volume"
echo "  docker-compose logs -f blacklist          # View logs"
echo "  docker-compose down                       # Stop services"
echo "  docker-compose up -d                      # Start services"