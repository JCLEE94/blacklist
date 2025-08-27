#!/bin/bash

# Docker Build Test Script with Best Practices
echo "🚀 Docker Build 테스트 시작..."
echo "================================"

# BuildKit 활성화
export DOCKER_BUILDKIT=1
export BUILDKIT_PROGRESS=plain

# Build arguments
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
VERSION="9.0.0"

echo "📦 Build 정보:"
echo "  - Date: $BUILD_DATE"
echo "  - Git Ref: $VCS_REF"
echo "  - Version: $VERSION"
echo ""

# 기존 Dockerfile 빌드 (시간 측정)
echo "🔨 기존 Dockerfile 빌드 중..."
START_TIME=$(date +%s)
docker build \
  --build-arg BUILD_DATE="$BUILD_DATE" \
  --build-arg VCS_REF="$VCS_REF" \
  --build-arg VERSION="8.3.0" \
  -t blacklist:original \
  -f Dockerfile \
  . 2>&1 | tail -20
END_TIME=$(date +%s)
ORIGINAL_TIME=$((END_TIME - START_TIME))

echo ""
echo "✅ 기존 빌드 완료: ${ORIGINAL_TIME}초"
echo ""

# 개선된 Dockerfile 빌드 (시간 측정)
echo "🔨 개선된 Dockerfile 빌드 중..."
START_TIME=$(date +%s)
docker build \
  --build-arg BUILD_DATE="$BUILD_DATE" \
  --build-arg VCS_REF="$VCS_REF" \
  --build-arg VERSION="$VERSION" \
  -t blacklist:improved \
  -f Dockerfile.improved \
  . 2>&1 | tail -20
END_TIME=$(date +%s)
IMPROVED_TIME=$((END_TIME - START_TIME))

echo ""
echo "✅ 개선된 빌드 완료: ${IMPROVED_TIME}초"
echo ""

# 이미지 크기 비교
echo "📊 이미지 크기 비교:"
echo "================================"
docker images | grep blacklist | grep -E "original|improved" | awk '{printf "%-20s %-15s %s\n", $1":"$2, $7$8, $3}'

echo ""
echo "📈 빌드 시간 비교:"
echo "  - 기존: ${ORIGINAL_TIME}초"
echo "  - 개선: ${IMPROVED_TIME}초"

if [ $IMPROVED_TIME -lt $ORIGINAL_TIME ]; then
  SAVED=$((ORIGINAL_TIME - IMPROVED_TIME))
  echo "  ✅ ${SAVED}초 단축!"
fi

echo ""
echo "🔍 보안 스캔 (간단 체크):"
docker run --rm aquasec/trivy image --severity HIGH,CRITICAL blacklist:improved 2>/dev/null | grep Total || echo "Trivy not available"

echo ""
echo "✨ 테스트 완료!"