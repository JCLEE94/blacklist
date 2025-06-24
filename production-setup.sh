#!/bin/bash
set -euo pipefail

# Production Server Setup Script for Blacklist Application
# This script sets up the production environment on registry.jclee.me

echo "🚀 Setting up Blacklist production environment..."

# Create application directory
APP_DIR="$HOME/app/blacklist"
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# Create docker-compose.yml for production
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  app:
    image: registry.jclee.me/blacklist:latest
    container_name: blacklist-app
    ports:
      - "2541:2541"
    environment:
      - PORT=2541
      - TZ=Asia/Seoul
      - FLASK_ENV=production
      - REDIS_URL=redis://redis:6379/0
      - REGTECH_USERNAME=${REGTECH_USERNAME:-nextrade}
      - REGTECH_PASSWORD=${REGTECH_PASSWORD:-Sprtmxm1@3}
      - SECUDIUM_USERNAME=${SECUDIUM_USERNAME:-nextrade}
      - SECUDIUM_PASSWORD=${SECUDIUM_PASSWORD:-Sprtmxm1@3}
    volumes:
      - ./instance:/app/instance
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - redis
    restart: unless-stopped
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
    networks:
      - blacklist-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:2541/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  redis:
    image: redis:7-alpine
    container_name: blacklist-redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - blacklist-network
    restart: unless-stopped
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  watchtower:
    image: containrrr/watchtower
    container_name: blacklist-watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - WATCHTOWER_POLL_INTERVAL=30
      - WATCHTOWER_CLEANUP=true
      - WATCHTOWER_INCLUDE_STOPPED=true
      - WATCHTOWER_INCLUDE_RESTARTING=true
      - WATCHTOWER_LABEL_ENABLE=true
      - WATCHTOWER_ROLLING_RESTART=true
      - TZ=Asia/Seoul
    command: --interval 30 --cleanup --label-enable
    restart: unless-stopped
    networks:
      - blacklist-network

networks:
  blacklist-network:
    driver: bridge

volumes:
  redis_data:
    driver: local
EOF

# Create required directories
mkdir -p instance data logs

# Create .env file
cat > .env << 'EOF'
# Production Environment Variables
REGTECH_USERNAME=nextrade
REGTECH_PASSWORD=Sprtmxm1@3
SECUDIUM_USERNAME=nextrade
SECUDIUM_PASSWORD=Sprtmxm1@3
PORT=2541
FLASK_ENV=production
TZ=Asia/Seoul
EOF

# Login to registry
echo "🔐 Logging in to private registry..."
echo "bingogo1l7!" | docker login registry.jclee.me -u qws941 --password-stdin

# Pull initial image
echo "📥 Pulling initial application image..."
docker pull registry.jclee.me/blacklist:latest

# Start services
echo "🚀 Starting production services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 60

# Health check
echo "🔍 Running health check..."
for i in {1..10}; do
  if curl -f http://localhost:2541/health > /dev/null 2>&1; then
    echo "✅ Application is healthy!"
    break
  else
    echo "⏳ Waiting for application to be ready... ($i/10)"
    sleep 10
  fi
done

# Show status
echo "📊 Service status:"
docker-compose ps

echo "✅ Production setup completed!"
echo "🌐 Application should be available at: http://registry.jclee.me:2541"
echo "🔄 Watchtower will automatically update the application when new images are pushed"