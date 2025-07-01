#\!/bin/bash
# Environment-based deployment script

set -euo pipefail

ENVIRONMENT=${1:-production}
ENV_FILE=".env.${ENVIRONMENT}"

echo "🚀 Deploying Blacklist Management System"
echo "Environment: $ENVIRONMENT"

# Check if environment file exists
if [ \! -f "$ENV_FILE" ]; then
    echo "❌ Environment file not found: $ENV_FILE"
    echo "Available environments:"
    ls -1 .env.* 2>/dev/null  < /dev/null |  sed 's/.env./  - /' || echo "  No environment files found"
    exit 1
fi

echo "📁 Using environment file: $ENV_FILE"

# Load environment variables
export $(grep -v '^#' "$ENV_FILE" | grep -v '^$' | xargs)

echo "🔍 Configuration:"
echo "  Registry: $DOCKER_REGISTRY"
echo "  Image: $IMAGE_NAME:$IMAGE_TAG"
echo "  Container: $CONTAINER_NAME"
echo "  Port: $HOST_PORT -> $CONTAINER_PORT"
echo "  Volumes:"
echo "    Instance: $VOLUME_INSTANCE_PATH"
echo "    Data: $VOLUME_DATA_PATH"
echo "    Logs: $VOLUME_LOGS_PATH"

# Choose appropriate compose file
COMPOSE_FILE="docker-compose.single.yml"
if [ -n "${VOLUME_INSTANCE_PATH:-}" ] && [ -n "${VOLUME_DATA_PATH:-}" ] && [ -n "${VOLUME_LOGS_PATH:-}" ]; then
    echo "📁 Using bind mounts (host paths specified)"
    COMPOSE_FILE="docker-compose.bind.yml"
    # Create host directories for bind mounts
    echo "📁 Creating host directories..."
    mkdir -p "$VOLUME_INSTANCE_PATH" "$VOLUME_DATA_PATH" "$VOLUME_LOGS_PATH"
else
    echo "🗄️  Using Docker volumes (no host paths)"
    COMPOSE_FILE="docker-compose.single.yml"
fi

echo "📄 Using compose file: $COMPOSE_FILE"

# Stop existing container
echo "🛑 Stopping existing containers..."
docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down || echo "No existing containers to stop"

# Pull latest image
echo "📥 Pulling latest image..."
docker pull "${DOCKER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

# Start new container
echo "🚀 Starting container..."
docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

# Wait for container to be ready
echo "⏳ Waiting for container to be ready..."
sleep 10

# Health check
echo "🔍 Performing health check..."
HEALTH_URL="http://localhost:${HOST_PORT}${HEALTH_ENDPOINT}"
for i in {1..10}; do
    if curl -f -s "$HEALTH_URL" > /dev/null 2>&1; then
        echo "✅ Container is healthy and ready\!"
        break
    fi
    echo "⏳ Waiting for health check... ($i/10)"
    sleep 5
done

# Show status
echo "📊 Container status:"
docker ps --filter name="$CONTAINER_NAME"

echo "🎉 Deployment completed successfully\!"
echo "🌐 Access: http://localhost:$HOST_PORT"
