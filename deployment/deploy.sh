#!/bin/bash
# deploy.sh - Production deployment script for blacklist system

set -e
PROJECT_NAME=${1:-blacklist}
TZ=Asia/Seoul
BUILD_TIME=$(date +"%Y-%m-%d %H:%M:%S KST")
VERSION_TAG=$(date +%Y%m%d-%H%M%S)

# Environment variables
DOCKER_REGISTRY_URL="registry.jclee.me"
DEPLOY_HOST="registry.jclee.me"
DEPLOY_PORT="1112"
DEPLOY_USER="docker"
APP_PORT="2541"

echo "🚀 Starting deployment for $PROJECT_NAME..."

# Clean cache files
echo "🧹 Cleaning cache files..."
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
rm -rf .pytest_cache __pycache__ *.egg-info

# Build Docker image
echo "📦 Building Docker image (no cache)..."
docker build --no-cache --pull --build-arg BUILD_TIME="$BUILD_TIME" -t $PROJECT_NAME:$VERSION_TAG -t $PROJECT_NAME:latest -f deployment/Dockerfile .

# Tag for registry
echo "🏷️ Tagging images..."
docker tag $PROJECT_NAME:latest $DOCKER_REGISTRY_URL/$PROJECT_NAME:latest
docker tag $PROJECT_NAME:$VERSION_TAG $DOCKER_REGISTRY_URL/$PROJECT_NAME:$VERSION_TAG

# Push to registry
echo "📤 Pushing to registry..."
docker push $DOCKER_REGISTRY_URL/$PROJECT_NAME:latest
docker push $DOCKER_REGISTRY_URL/$PROJECT_NAME:$VERSION_TAG

# Deploy to production server
echo "🚀 Deploying to production server..."
ssh -p $DEPLOY_PORT $DEPLOY_USER@$DEPLOY_HOST "
  cd ~/app/$PROJECT_NAME
  
  echo '🛑 Stopping existing containers...'
  docker-compose down -v --remove-orphans || true
  
  echo '🧹 Cleaning up old images...'
  docker images --filter 'reference=$DOCKER_REGISTRY_URL/$PROJECT_NAME' --format '{{.ID}}' | xargs -r docker rmi -f || true
  docker system prune -af --volumes
  
  echo '📥 Pulling latest image...'
  docker-compose pull --ignore-pull-failures
  
  echo '🚀 Starting new containers...'
  docker-compose up -d --force-recreate --renew-anon-volumes
  
  # Wait for startup
  sleep 15
  echo '📋 Container status:'
  docker-compose ps
  echo '📄 Recent logs:'
  docker-compose logs --tail=20
"

# Health check
echo "🔍 Verifying deployment..."
APP_PORT=$(ssh -p $DEPLOY_PORT $DEPLOY_USER@$DEPLOY_HOST "cd ~/app/$PROJECT_NAME && docker-compose port app 2541 2>/dev/null | cut -d: -f2 || echo 2541")

echo "⏳ Waiting for service on port $APP_PORT..."
for i in {1..30}; do
  if curl -f http://$DEPLOY_HOST:$APP_PORT/health >/dev/null 2>&1; then
    echo "✅ Service is healthy!"
    break
  fi
  echo "Attempt $i/30..."
  sleep 3
done

# Final verification
if curl -f http://$DEPLOY_HOST:$APP_PORT/health; then
  echo "✅ Deployment successful! Version: $VERSION_TAG"
  echo "🌐 Service available at: http://$DEPLOY_HOST:$APP_PORT"
  
  # Show final status
  ssh -p $DEPLOY_PORT $DEPLOY_USER@$DEPLOY_HOST "
    cd ~/app/$PROJECT_NAME
    echo 'Container info:'
    docker-compose ps
    echo 'Port usage:'
    ss -tlnp | grep :$APP_PORT || echo 'Port not bound to host'
  "
else
  echo "❌ Deployment failed - health check failed"
  ssh -p $DEPLOY_PORT $DEPLOY_USER@$DEPLOY_HOST "
    cd ~/app/$PROJECT_NAME
    docker-compose logs --tail=100
  "
  exit 1
fi

echo "✅ Deployment completed successfully!"