#!/bin/bash
# Synology NAS deployment script

set -e
PROJECT_NAME=${1:-blacklist}
VERSION_TAG=$(date +%Y%m%d-%H%M%S)

# Deployment configuration
DEPLOY_USER=docker
DEPLOY_HOST=192.168.50.215
DEPLOY_PORT=1111
DEPLOY_BASE_PATH=~/app
DOCKER_CMD="/usr/local/bin/docker"
DOCKER_COMPOSE_CMD="/usr/local/bin/docker-compose"

echo "🚀 Starting Synology NAS deployment to $DEPLOY_HOST:$DEPLOY_PORT..."

# Build Docker image
echo "📦 Building Docker image..."
docker build -t $PROJECT_NAME:latest .

# Save image to tar file (compressed)
echo "💾 Saving Docker image to tar file (compressed)..."
docker save $PROJECT_NAME:latest | gzip > $PROJECT_NAME-deploy.tar.gz
echo "Image size: $(du -h $PROJECT_NAME-deploy.tar.gz | cut -f1)"

# Create deployment directory on remote
echo "📁 Creating deployment directory on remote..."
ssh -p $DEPLOY_PORT $DEPLOY_USER@$DEPLOY_HOST "mkdir -p $DEPLOY_BASE_PATH/$PROJECT_NAME"

# Copy files to remote server
echo "📤 Copying files to remote server..."
scp -P $DEPLOY_PORT $PROJECT_NAME-deploy.tar.gz $DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_BASE_PATH/$PROJECT_NAME/
scp -P $DEPLOY_PORT docker-compose.yml $DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_BASE_PATH/$PROJECT_NAME/

# Create necessary directories
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
  export PATH=/usr/local/bin:\$PATH
  
  echo '🛑 Stopping existing containers...'
  $DOCKER_CMD stop blacklist-app blacklist-redis 2>/dev/null || true
  $DOCKER_CMD rm blacklist-app blacklist-redis 2>/dev/null || true
  
  echo '📥 Loading new image...'
  gunzip -c $PROJECT_NAME-deploy.tar.gz | $DOCKER_CMD load
  
  echo '🔗 Creating network...'
  $DOCKER_CMD network create blacklist-network 2>/dev/null || true
  
  echo '🚀 Starting Redis...'
  $DOCKER_CMD run -d \
    --name blacklist-redis \
    --network blacklist-network \
    --restart unless-stopped \
    redis:7-alpine
  
  echo '🚀 Starting application...'
  $DOCKER_CMD run -d \
    --name blacklist-app \
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
  
  echo '⏳ Waiting for startup...'
  sleep 15
  
  echo '📋 Container status:'
  $DOCKER_CMD ps | grep blacklist || echo 'No containers found'
  
  echo '📄 Application logs:'
  $DOCKER_CMD logs blacklist-app --tail=20
  
  # Clean up compressed image
  rm -f $PROJECT_NAME-deploy.tar.gz
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
    echo "📊 Quick stats:"
    curl -s http://$DEPLOY_HOST:2541/api/stats 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'  Total IPs: {data.get(\"database\", {}).get(\"total_ips\", 0)}'); print(f'  Active IPs: {data.get(\"active_ips\", 0)}')" || true
    break
  else
    echo "Attempt $i/10 - waiting for service..."
    sleep 3
  fi
done

echo "🎉 Synology NAS deployment complete!"