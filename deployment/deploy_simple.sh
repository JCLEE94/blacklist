#!/bin/bash
# Simple deployment script without registry

set -e
PROJECT_NAME=${1:-blacklist}
VERSION_TAG=$(date +%Y%m%d-%H%M%S)

echo "🚀 Starting simple deployment for $PROJECT_NAME..."

# Build Docker image
echo "📦 Building Docker image..."
docker build -t $PROJECT_NAME:latest .

# Save image to tar file
echo "💾 Saving Docker image to tar file..."
docker save $PROJECT_NAME:latest > $PROJECT_NAME-latest.tar

# Copy files to remote server
echo "📤 Copying to remote server..."
scp -P 1111 $PROJECT_NAME-latest.tar docker@192.168.50.215:~/app/$PROJECT_NAME/
scp -P 1111 docker-compose.yml docker@192.168.50.215:~/app/$PROJECT_NAME/

# Deploy on remote server
echo "🚀 Deploying on remote server..."
ssh -p 1111 docker@192.168.50.215 "
  cd ~/app/$PROJECT_NAME
  
  echo '🛑 Stopping existing containers...'
  docker-compose down || true
  
  echo '📥 Loading new image...'
  docker load < $PROJECT_NAME-latest.tar
  
  echo '🚀 Starting new containers...'
  docker-compose up -d
  
  echo '⏳ Waiting for startup...'
  sleep 10
  
  echo '📋 Container status:'
  docker-compose ps
  
  echo '📄 Recent logs:'
  docker-compose logs --tail=30
"

# Clean up local tar file
rm -f $PROJECT_NAME-latest.tar

echo "✅ Deployment completed!"
echo "🌐 Service should be available at: http://192.168.50.215:2541"

# Health check
echo "🔍 Checking health..."
sleep 5
if curl -f http://192.168.50.215:2541/health; then
  echo "✅ Service is healthy!"
else
  echo "⚠️ Health check failed, checking logs..."
  ssh -p 1111 docker@192.168.50.215 "cd ~/app/$PROJECT_NAME && docker-compose logs --tail=50"
fi