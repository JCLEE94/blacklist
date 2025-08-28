#!/bin/bash
# Redis 커스텀 이미지 빌드 및 푸시 스크립트
# registry.jclee.me/qws941/blacklist-redis

set -e

# 설정
REGISTRY="registry.jclee.me"
NAMESPACE="jclee94"
IMAGE_NAME="blacklist-redis"
VERSION=${1:-"latest"}
FULL_TAG="${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:${VERSION}"

# 컬러 출력
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐳 Building Custom Redis Image${NC}"
echo -e "${BLUE}Registry: ${REGISTRY}${NC}"
echo -e "${BLUE}Image: ${FULL_TAG}${NC}"
echo "============================================"

# 1. 디렉토리 이동
cd "$(dirname "$0")/.."
REDIS_DIR="docker/redis"

if [ ! -d "$REDIS_DIR" ]; then
    echo -e "${RED}❌ Redis directory not found: $REDIS_DIR${NC}"
    exit 1
fi

echo -e "${YELLOW}📁 Working directory: $(pwd)${NC}"
echo -e "${YELLOW}🔧 Redis config: $REDIS_DIR${NC}"

# 2. 레지스트리 로그인 확인
echo -e "${BLUE}🔐 Checking registry authentication...${NC}"
if ! docker info | grep -q "$REGISTRY"; then
    echo -e "${YELLOW}⚠️ Not logged in to $REGISTRY, attempting login...${NC}"
    docker login $REGISTRY
fi

# 3. 이미지 빌드
echo -e "${BLUE}🔨 Building Redis image...${NC}"
docker build \
    -t "$FULL_TAG" \
    -t "${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:latest" \
    -f "$REDIS_DIR/Dockerfile" \
    "$REDIS_DIR"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Build successful!${NC}"
else
    echo -e "${RED}❌ Build failed!${NC}"
    exit 1
fi

# 4. 이미지 정보 출력
echo -e "${BLUE}📊 Image information:${NC}"
docker images | grep "${NAMESPACE}/${IMAGE_NAME}" | head -5

# 5. 이미지 푸시
echo -e "${BLUE}🚀 Pushing to registry...${NC}"
docker push "$FULL_TAG"

if [ "$VERSION" != "latest" ]; then
    echo -e "${BLUE}🚀 Pushing latest tag...${NC}"
    docker push "${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:latest"
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Push successful!${NC}"
else
    echo -e "${RED}❌ Push failed!${NC}"
    exit 1
fi

# 6. 로컬 정리 (선택사항)
read -p "Remove local images? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}🧹 Cleaning up local images...${NC}"
    docker rmi "$FULL_TAG" || true
    if [ "$VERSION" != "latest" ]; then
        docker rmi "${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:latest" || true
    fi
fi

echo -e "${GREEN}🎉 Redis image build and push completed!${NC}"
echo -e "${GREEN}📦 Image: ${FULL_TAG}${NC}"
echo -e "${BLUE}💡 Usage: docker pull ${FULL_TAG}${NC}"