#!/bin/bash
# Remote deployment script for 192.168.50.215

set -e
PROJECT_NAME=${1:-blacklist}
VERSION_TAG=$(date +%Y%m%d-%H%M%S)

# Deployment configuration
DEPLOY_USER=docker
DEPLOY_HOST=192.168.50.215
DEPLOY_PORT=1111
DEPLOY_BASE_PATH=/home/docker/app

echo "🚀 Starting remote deployment to $DEPLOY_HOST:$DEPLOY_PORT..."

# Build Docker image
echo "📦 Building Docker image..."
docker build -t $PROJECT_NAME:latest .

# Save image to tar file
echo "💾 Saving Docker image to tar file..."
docker save $PROJECT_NAME:latest | gzip > $PROJECT_NAME-deploy.tar.gz

# Create deployment directory on remote
echo "📁 Creating deployment directory on remote..."
ssh -p $DEPLOY_PORT $DEPLOY_USER@$DEPLOY_HOST "mkdir -p $DEPLOY_BASE_PATH/$PROJECT_NAME"

# Copy files to remote server
echo "📤 Copying files to remote server..."
scp -P $DEPLOY_PORT $PROJECT_NAME-deploy.tar.gz $DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_BASE_PATH/$PROJECT_NAME/
scp -P $DEPLOY_PORT docker-compose.yml $DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_BASE_PATH/$PROJECT_NAME/

# Create necessary directories and copy data
echo "📂 Setting up data directories..."
ssh -p $DEPLOY_PORT $DEPLOY_USER@$DEPLOY_HOST "cd $DEPLOY_BASE_PATH/$PROJECT_NAME && mkdir -p instance data logs"

# Copy instance database if exists
if [ -f "instance/blacklist.db" ]; then
    echo "📊 Copying database..."
    scp -P $DEPLOY_PORT instance/blacklist.db $DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_BASE_PATH/$PROJECT_NAME/instance/
fi

# Deploy on remote server
echo "🚀 Deploying on remote server..."
ssh -p $DEPLOY_PORT $DEPLOY_USER@$DEPLOY_HOST "
  cd $DEPLOY_BASE_PATH/$PROJECT_NAME
  
  echo '🛑 Stopping existing containers...'
  if command -v docker-compose &> /dev/null; then
    docker-compose down || true
  elif command -v docker &> /dev/null; then
    docker stop blacklist-app blacklist-redis || true
    docker rm blacklist-app blacklist-redis || true
  elif command -v podman &> /dev/null; then
    podman stop blacklist-app blacklist-redis || true
    podman rm blacklist-app blacklist-redis || true
  fi
  
  echo '📥 Loading new image...'
  if command -v docker &> /dev/null; then
    docker load < $PROJECT_NAME-deploy.tar.gz
  elif command -v podman &> /dev/null; then
    podman load < $PROJECT_NAME-deploy.tar.gz
  fi
  
  echo '🚀 Starting new containers...'
  if command -v docker-compose &> /dev/null; then
    docker-compose up -d
  elif command -v docker &> /dev/null; then
    # Run without docker-compose
    docker network create blacklist-network || true
    docker run -d --name blacklist-redis --network blacklist-network redis:7-alpine
    docker run -d --name blacklist-app \
      --network blacklist-network \
      -p 2541:2541 \
      -e PORT=2541 \
      -e FLASK_ENV=production \
      -e REDIS_URL=redis://blacklist-redis:6379/0 \
      -e REGTECH_USERNAME=nextrade \
      -e REGTECH_PASSWORD='Sprtmxm1@3' \
      -e SECUDIUM_USERNAME=nextrade \
      -e SECUDIUM_PASSWORD='Sprtmxm1@3' \
      -v \$(pwd)/instance:/app/instance \
      -v \$(pwd)/data:/app/data \
      -v \$(pwd)/logs:/app/logs \
      --restart unless-stopped \
      $PROJECT_NAME:latest
  elif command -v podman &> /dev/null; then
    # Podman deployment
    podman network create blacklist-network || true
    podman run -d --name blacklist-redis --network blacklist-network redis:7-alpine
    podman run -d --name blacklist-app \
      --network blacklist-network \
      -p 2541:2541 \
      -e PORT=2541 \
      -e FLASK_ENV=production \
      -e REDIS_URL=redis://blacklist-redis:6379/0 \
      -e REGTECH_USERNAME=nextrade \
      -e REGTECH_PASSWORD='Sprtmxm1@3' \
      -e SECUDIUM_USERNAME=nextrade \
      -e SECUDIUM_PASSWORD='Sprtmxm1@3' \
      -v \$(pwd)/instance:/app/instance \
      -v \$(pwd)/data:/app/data \
      -v \$(pwd)/logs:/app/logs \
      --restart unless-stopped \
      $PROJECT_NAME:latest
  fi
  
  echo '⏳ Waiting for startup...'
  sleep 15
  
  echo '📋 Container status:'
  if command -v docker &> /dev/null; then
    docker ps | grep blacklist || echo 'No containers found'
  elif command -v podman &> /dev/null; then
    podman ps | grep blacklist || echo 'No containers found'
  fi
"

# Clean up local tar file
rm -f $PROJECT_NAME-deploy.tar.gz

echo "✅ Deployment completed!"
echo "🌐 Service should be available at: http://$DEPLOY_HOST:2541"

# Health check
echo "🔍 Checking health..."
sleep 5
for i in {1..10}; do
  if curl -f http://$DEPLOY_HOST:2541/health 2>/dev/null; then
    echo "✅ Service is healthy!"
    curl -s http://$DEPLOY_HOST:2541/api/stats | python3 -m json.tool | grep -E "(total_ips|active_ips)" || true
    break
  else
    echo "Attempt $i/10 - waiting for service..."
    sleep 3
  fi
done

echo "🎉 Remote deployment complete!"