#!/bin/bash

# Build and push Docker image to registry.jclee.me

set -e

echo "🚀 Building and pushing Docker image to registry.jclee.me..."

# Configuration
REGISTRY="registry.jclee.me"
IMAGE_NAME="blacklist"
DOCKERFILE="deployment/Dockerfile"

# Get current git hash for tagging
GIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "no-git")
TIMESTAMP=$(date +%Y%m%d%H%M%S)

# Build the image
echo "📦 Building Docker image..."
docker build -f ${DOCKERFILE} -t ${REGISTRY}/${IMAGE_NAME}:latest .

# Tag with multiple tags
echo "🏷️  Tagging image..."
docker tag ${REGISTRY}/${IMAGE_NAME}:latest ${REGISTRY}/${IMAGE_NAME}:${GIT_HASH}
docker tag ${REGISTRY}/${IMAGE_NAME}:latest ${REGISTRY}/${IMAGE_NAME}:${TIMESTAMP}

# Push all tags
echo "📤 Pushing to registry..."
docker push ${REGISTRY}/${IMAGE_NAME}:latest
docker push ${REGISTRY}/${IMAGE_NAME}:${GIT_HASH}
docker push ${REGISTRY}/${IMAGE_NAME}:${TIMESTAMP}

echo "✅ Successfully pushed:"
echo "  - ${REGISTRY}/${IMAGE_NAME}:latest"
echo "  - ${REGISTRY}/${IMAGE_NAME}:${GIT_HASH}"
echo "  - ${REGISTRY}/${IMAGE_NAME}:${TIMESTAMP}"

# Trigger ArgoCD sync
echo "🔄 Triggering ArgoCD sync..."
argocd app sync blacklist --grpc-web --insecure || echo "ArgoCD sync failed, please check manually"

echo "🎉 Build and deployment process completed!"