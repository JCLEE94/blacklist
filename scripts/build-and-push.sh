#!/bin/bash

# Direct push to registry.jclee.me with Watchtower automatic deployment
# Version: v1.3.4
# Registry: registry.jclee.me (admin/bingogo1)

set -e

echo "🚀 registry.jclee.me 직접 푸시 및 Watchtower 자동 배포 시작..."

# Configuration
REGISTRY="registry.jclee.me"
REGISTRY_USER="admin"
REGISTRY_PASS="bingogo1"
IMAGE_NAME="blacklist"
DOCKERFILE="build/docker/Dockerfile"

# Version management
VERSION=$(cat config/VERSION 2>/dev/null | head -1 || echo "1.3.4")
GIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "no-git")
TIMESTAMP=$(date +%Y%m%d%H%M%S)
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

echo "📋 빌드 정보:"
echo "  - 버전: v${VERSION}"
echo "  - Git Hash: ${GIT_HASH}"
echo "  - 빌드 시간: ${BUILD_DATE}"
echo "  - 레지스트리: ${REGISTRY}"

# 1. Registry 로그인
echo "🔐 registry.jclee.me 로그인 중..."
echo "${REGISTRY_PASS}" | docker login ${REGISTRY} -u ${REGISTRY_USER} --password-stdin

# 2. Main blacklist image 빌드
echo "📦 메인 애플리케이션 이미지 빌드 중..."
docker build \
  --build-arg BUILD_DATE="${BUILD_DATE}" \
  --build-arg VCS_REF="${GIT_HASH}" \
  --build-arg VERSION="v${VERSION}" \
  -f ${DOCKERFILE} \
  -t ${REGISTRY}/${IMAGE_NAME}:latest \
  -t ${REGISTRY}/${IMAGE_NAME}:v${VERSION} \
  -t ${REGISTRY}/${IMAGE_NAME}:${GIT_HASH} \
  .

# 3. Redis image 빌드 (이미 있는 경우 스킵)
echo "📦 Redis 이미지 빌드 중..."
docker build \
  -f docker/redis/Dockerfile \
  -t ${REGISTRY}/${IMAGE_NAME}-redis:latest \
  -t ${REGISTRY}/${IMAGE_NAME}-redis:v${VERSION} \
  .

# 4. PostgreSQL image 빌드 (이미 있는 경우 스킵)
echo "📦 PostgreSQL 이미지 빌드 중..."
docker build \
  -f docker/postgresql/Dockerfile \
  -t ${REGISTRY}/${IMAGE_NAME}-postgresql:latest \
  -t ${REGISTRY}/${IMAGE_NAME}-postgresql:v${VERSION} \
  .

# 5. 모든 이미지 푸시
echo "📤 registry.jclee.me로 푸시 중..."

# Main application
docker push ${REGISTRY}/${IMAGE_NAME}:latest
docker push ${REGISTRY}/${IMAGE_NAME}:v${VERSION}
docker push ${REGISTRY}/${IMAGE_NAME}:${GIT_HASH}

# Redis
docker push ${REGISTRY}/${IMAGE_NAME}-redis:latest
docker push ${REGISTRY}/${IMAGE_NAME}-redis:v${VERSION}

# PostgreSQL
docker push ${REGISTRY}/${IMAGE_NAME}-postgresql:latest
docker push ${REGISTRY}/${IMAGE_NAME}-postgresql:v${VERSION}

echo "✅ 성공적으로 푸시됨:"
echo "  - ${REGISTRY}/${IMAGE_NAME}:latest"
echo "  - ${REGISTRY}/${IMAGE_NAME}:v${VERSION}"
echo "  - ${REGISTRY}/${IMAGE_NAME}:${GIT_HASH}"
echo "  - ${REGISTRY}/${IMAGE_NAME}-redis:latest"
echo "  - ${REGISTRY}/${IMAGE_NAME}-postgresql:latest"

# 6. Watchtower 자동 배포 대기
echo "⏳ Watchtower 자동 배포 대기 중 (최대 5분)..."
echo "   💡 Watchtower가 자동으로 새 이미지를 감지하고 배포합니다"

# 간접적인 헬스체크 (운영서버 직접 접근 불가)
echo "📋 배포 모니터링 안내:"
echo "  1. Watchtower 로그 확인: docker logs watchtower -f"
echo "  2. 컨테이너 상태 확인: docker ps | grep blacklist"
echo "  3. 헬스체크 (간접): curl https://blacklist.jclee.me/health"
echo "  4. 애플리케이션 로그: docker logs blacklist -f"

# K8s 매니페스트 생성 (배포는 하지 않음)
echo "📜 K8s 매니페스트 생성 중..."
mkdir -p k8s-manifests

cat > k8s-manifests/deployment-v${VERSION}.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blacklist
  namespace: blacklist
  labels:
    app: blacklist
    version: v${VERSION}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: blacklist
  template:
    metadata:
      labels:
        app: blacklist
        version: v${VERSION}
    spec:
      containers:
      - name: blacklist
        image: ${REGISTRY}/${IMAGE_NAME}:v${VERSION}
        ports:
        - containerPort: 2542
        env:
        - name: VERSION
          value: "v${VERSION}"
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 2542
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 2542
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: blacklist-service
  namespace: blacklist
spec:
  selector:
    app: blacklist
  ports:
  - port: 80
    targetPort: 2542
  type: ClusterIP
EOF

echo "📋 K8s 매니페스트 생성 완료: k8s-manifests/deployment-v${VERSION}.yaml"
echo "   💡 이 매니페스트는 별도로 배포해야 합니다"

echo ""
echo "🎉 registry.jclee.me 직접 푸시 완료!"
echo "📋 주요 정보:"
echo "  ✅ 이미지 빌드: 완료"
echo "  ✅ registry.jclee.me 푸시: 완료"
echo "  ⏳ Watchtower 자동 배포: 진행 중"
echo "  📜 K8s 매니페스트: 생성 완료 (수동 배포 필요)"
echo ""
echo "🔗 확인 방법:"
echo "  - 라이브 시스템: https://blacklist.jclee.me/"
echo "  - 헬스체크: https://blacklist.jclee.me/health"
echo "  - 버전 확인: https://blacklist.jclee.me/api/version"