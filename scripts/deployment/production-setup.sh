#!/bin/bash
set -euo pipefail

# Production Server Setup Script for Blacklist Application
# This script sets up the production environment on registry.jclee.me

echo "🚀 Setting up Blacklist production environment..."

# Configuration
REGISTRY="${DOCKER_REGISTRY:-registry.jclee.me}"
APP_DIR="${APP_DIR:-$HOME/app/blacklist}"

# Create application directory
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# Copy docker-compose.yml from deployment directory
if [ -f "$HOME/blacklist/deployment/docker-compose.yml" ]; then
    cp "$HOME/blacklist/deployment/docker-compose.yml" .
else
    echo "⚠️ docker-compose.yml not found in deployment directory"
    echo "📝 Creating default docker-compose.yml..."
    
    # Create minimal docker-compose.yml
    cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  app:
    image: ${DOCKER_REGISTRY:-registry.jclee.me}/${IMAGE_NAME:-blacklist}:${IMAGE_TAG:-latest}
    container_name: ${CONTAINER_NAME:-blacklist-app}
    ports:
      - "${APP_PORT:-2541}:${APP_PORT:-2541}"
    environment:
      - PORT=${APP_PORT:-2541}
      - HOST=0.0.0.0
      - TZ=${TZ:-Asia/Seoul}
      - FLASK_ENV=${FLASK_ENV:-production}
      - REDIS_URL=redis://redis:6379/0
      - REGTECH_USERNAME=${REGTECH_USERNAME}
      - REGTECH_PASSWORD=${REGTECH_PASSWORD}
      - SECUDIUM_USERNAME=${SECUDIUM_USERNAME}
      - SECUDIUM_PASSWORD=${SECUDIUM_PASSWORD}
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
      test: ["CMD", "curl", "-f", "http://localhost:${APP_PORT:-2541}/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  redis:
    image: redis:7-alpine
    container_name: ${REDIS_CONTAINER_NAME:-blacklist-redis}
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

networks:
  blacklist-network:
    driver: bridge

volumes:
  redis_data:
    driver: local
EOF
fi

# Create required directories
mkdir -p instance data logs

# Create .env file from example if not exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << 'EOF'
# Production Environment Variables
DOCKER_REGISTRY=registry.jclee.me
IMAGE_NAME=blacklist
IMAGE_TAG=latest
APP_PORT=2541
FLASK_ENV=production
TZ=Asia/Seoul

# Credentials (update with actual values)
REGTECH_USERNAME=${REGTECH_USERNAME}
REGTECH_PASSWORD=${REGTECH_PASSWORD}
SECUDIUM_USERNAME=${SECUDIUM_USERNAME}
SECUDIUM_PASSWORD=${SECUDIUM_PASSWORD}
EOF
else
    echo "✅ Using existing .env file"
fi

# Login to registry
echo "🔐 Logging in to private registry..."
if [ -n "${REGISTRY_PASSWORD}" ]; then
    echo "${REGISTRY_PASSWORD}" | docker login "${REGISTRY}" -u "${REGISTRY_USERNAME:-qws941}" --password-stdin
else
    echo "⚠️ REGISTRY_PASSWORD not set. Please login manually with: docker login ${REGISTRY}"
fi

# Pull initial image
echo "📥 Pulling initial application image..."
docker pull "${REGISTRY}/${IMAGE_NAME:-blacklist}:${IMAGE_TAG:-latest}"

# Start services
echo "🚀 Starting production services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 60

# Health check
echo "🔍 Running health check..."
APP_PORT="${APP_PORT:-2541}"
for i in {1..10}; do
  if curl -f http://localhost:${APP_PORT}/health > /dev/null 2>&1; then
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
echo "🌐 Application should be available at: http://${REGISTRY}:${APP_PORT}"
echo "🔄 Watchtower will automatically update the application when new images are pushed"

# Create Watchtower configuration if needed
if [ ! -f "$APP_DIR/docker-compose.watchtower.yml" ]; then
    cat > docker-compose.watchtower.yml << 'EOF'
version: '3.8'

services:
  watchtower:
    image: containrrr/watchtower
    container_name: watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - WATCHTOWER_POLL_INTERVAL=${WATCHTOWER_POLL_INTERVAL:-30}
      - WATCHTOWER_CLEANUP=true
      - WATCHTOWER_INCLUDE_STOPPED=true
      - WATCHTOWER_INCLUDE_RESTARTING=true
      - WATCHTOWER_LABEL_ENABLE=true
      - WATCHTOWER_ROLLING_RESTART=true
      - TZ=${TZ:-Asia/Seoul}
    command: --interval ${WATCHTOWER_POLL_INTERVAL:-30} --cleanup --label-enable
    restart: unless-stopped
EOF
    echo "📝 Created Watchtower configuration"
    echo "🚀 To start Watchtower: docker-compose -f docker-compose.watchtower.yml up -d"
fi