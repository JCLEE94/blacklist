#!/bin/bash
# Synology NAS Auto Deployment Script
# NAS: 192.168.50.215:1111
# User: qws941

set -e

# Configuration
NAS_HOST="192.168.50.215"
NAS_PORT="1111"
NAS_USER="qws941"
NAS_BASE_DIR="/volume1/docker/blacklist"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Synology NAS Blacklist Deployment ===${NC}"
echo "NAS: $NAS_HOST:$NAS_PORT"
echo "User: $NAS_USER"
echo ""

# Function to execute SSH commands
ssh_exec() {
    ssh -p $NAS_PORT $NAS_USER@$NAS_HOST "$1"
}

# Function to copy files via SCP
scp_copy() {
    scp -P $NAS_PORT "$1" $NAS_USER@$NAS_HOST:"$2"
}

echo -e "${YELLOW}1. Creating directory structure on NAS...${NC}"
ssh_exec "mkdir -p $NAS_BASE_DIR/{config,data,logs,scripts,backup}"
ssh_exec "mkdir -p $NAS_BASE_DIR/data/{blacklist_entries,exports,collection_logs}"

echo -e "${YELLOW}2. Copying configuration files...${NC}"
# Create docker-compose for NAS
cat > /tmp/docker-compose-nas.yml << 'EOF'
version: '3.9'

services:
  blacklist:
    image: registry.jclee.me/blacklist:latest
    container_name: blacklist
    restart: unless-stopped
    ports:
      - "32542:2542"
    volumes:
      - ./data:/app/instance
      - ./logs:/app/logs
      - ./config:/app/config
    environment:
      FLASK_ENV: production
      PORT: 2542
      DATABASE_URL: sqlite:////app/instance/blacklist.db
      REDIS_URL: redis://redis:6379/0
      COLLECTION_ENABLED: "true"
      FORCE_DISABLE_COLLECTION: "false"
    env_file:
      - ./config/.env
    depends_on:
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:2542/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - blacklist-network

  redis:
    image: redis:7-alpine
    container_name: blacklist-redis
    restart: unless-stopped
    volumes:
      - redis-data:/data
    command: >
      redis-server
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
      --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 5s
      retries: 3
    networks:
      - blacklist-network

volumes:
  redis-data:

networks:
  blacklist-network:
    driver: bridge
EOF

scp_copy /tmp/docker-compose-nas.yml "$NAS_BASE_DIR/docker-compose.yml"

echo -e "${YELLOW}3. Creating deployment scripts...${NC}"
# Create update script
cat > /tmp/update-blacklist.sh << 'EOF'
#!/bin/bash
# Auto-update script for Blacklist system

cd /volume1/docker/blacklist

echo "$(date): Starting update..." >> logs/deployment.log

# Pull latest image
docker-compose pull

# Restart services
docker-compose down
docker-compose up -d

# Health check
sleep 10
if curl -f http://localhost:32542/api/collection/status > /dev/null 2>&1; then
    echo "$(date): Update successful" >> logs/deployment.log
else
    echo "$(date): Update failed - rolling back" >> logs/deployment.log
    docker-compose down
    docker-compose up -d
fi
EOF

scp_copy /tmp/update-blacklist.sh "$NAS_BASE_DIR/scripts/update.sh"
ssh_exec "chmod +x $NAS_BASE_DIR/scripts/update.sh"

echo -e "${YELLOW}4. Creating monitoring script...${NC}"
cat > /tmp/monitor-blacklist.sh << 'EOF'
#!/bin/bash
# Health monitoring script

API_URL="http://localhost:32542/api/collection/status"
LOG_FILE="/volume1/docker/blacklist/logs/health.log"

# Check service health
if curl -f $API_URL > /dev/null 2>&1; then
    echo "$(date): Service healthy" >> $LOG_FILE
else
    echo "$(date): Service unhealthy - restarting" >> $LOG_FILE
    cd /volume1/docker/blacklist
    docker-compose restart
fi
EOF

scp_copy /tmp/monitor-blacklist.sh "$NAS_BASE_DIR/scripts/monitor.sh"
ssh_exec "chmod +x $NAS_BASE_DIR/scripts/monitor.sh"

echo -e "${YELLOW}5. Copying environment configuration...${NC}"
# Create .env file
cat > /tmp/env-nas << 'EOF'
FLASK_ENV=production
PORT=2542
DATABASE_URL=sqlite:////app/instance/blacklist.db
REDIS_URL=redis://redis:6379/0
COLLECTION_ENABLED=true
FORCE_DISABLE_COLLECTION=false
RESTART_PROTECTION=false
MAX_AUTH_ATTEMPTS=5
BLOCK_DURATION_HOURS=1

# API Credentials (update these)
REGTECH_USERNAME=your-username
REGTECH_PASSWORD=your-password
SECUDIUM_USERNAME=your-username
SECUDIUM_PASSWORD=your-password

# Security
SECRET_KEY=change-in-production
JWT_SECRET_KEY=change-in-production
API_KEY_ENABLED=true
JWT_ENABLED=true
EOF

scp_copy /tmp/env-nas "$NAS_BASE_DIR/config/.env"

echo -e "${YELLOW}6. Setting up Synology Task Scheduler jobs...${NC}"
# Create task scheduler setup script
cat > /tmp/setup-scheduler.sh << 'EOF'
#!/bin/bash
# This script should be run on Synology to set up scheduled tasks

echo "Please add the following scheduled tasks in DSM Task Scheduler:"
echo ""
echo "1. Auto Update Task:"
echo "   - Schedule: Daily at 2:00 AM"
echo "   - Command: /volume1/docker/blacklist/scripts/update.sh"
echo ""
echo "2. Health Monitor Task:"
echo "   - Schedule: Every 5 minutes"
echo "   - Command: /volume1/docker/blacklist/scripts/monitor.sh"
echo ""
echo "3. Backup Task:"
echo "   - Schedule: Daily at 3:00 AM"
echo "   - Command: /volume1/docker/blacklist/scripts/backup.sh"
EOF

scp_copy /tmp/setup-scheduler.sh "$NAS_BASE_DIR/scripts/setup-scheduler.sh"
ssh_exec "chmod +x $NAS_BASE_DIR/scripts/setup-scheduler.sh"

echo -e "${YELLOW}7. Creating backup script...${NC}"
cat > /tmp/backup-blacklist.sh << 'EOF'
#!/bin/bash
# Backup script for Blacklist data

BACKUP_DIR="/volume1/docker/blacklist/backup"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/blacklist_backup_$DATE.tar.gz"

cd /volume1/docker/blacklist

# Create backup
tar -czf $BACKUP_FILE data/ config/

# Keep only last 7 days of backups
find $BACKUP_DIR -name "blacklist_backup_*.tar.gz" -mtime +7 -delete

echo "$(date): Backup completed - $BACKUP_FILE" >> logs/backup.log
EOF

scp_copy /tmp/backup-blacklist.sh "$NAS_BASE_DIR/scripts/backup.sh"
ssh_exec "chmod +x $NAS_BASE_DIR/scripts/backup.sh"

echo -e "${GREEN}=== Deployment Setup Complete ===${NC}"
echo ""
echo "Directory structure created:"
echo "  $NAS_BASE_DIR/"
echo "  ├── config/        # Configuration files"
echo "  ├── data/          # Application data"
echo "  ├── logs/          # Log files"
echo "  ├── scripts/       # Automation scripts"
echo "  └── backup/        # Backup files"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. SSH to NAS: ssh -p $NAS_PORT $NAS_USER@$NAS_HOST"
echo "2. Navigate to: cd $NAS_BASE_DIR"
echo "3. Update .env file with actual credentials"
echo "4. Start services: docker-compose up -d"
echo "5. Set up scheduled tasks in DSM Task Scheduler"
echo ""
echo -e "${GREEN}Manual deployment command:${NC}"
echo "ssh -p $NAS_PORT $NAS_USER@$NAS_HOST 'cd $NAS_BASE_DIR && docker-compose pull && docker-compose up -d'"