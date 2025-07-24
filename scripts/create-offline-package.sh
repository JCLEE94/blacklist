#!/bin/bash
# 로컬에서 오프라인 패키지 생성 스크립트

set -e

echo "🚀 Blacklist 오프라인 패키지 생성 시작..."

# 변수 설정
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
PACKAGE_NAME="blacklist-offline-${TIMESTAMP}"
PACKAGE_DIR="/tmp/${PACKAGE_NAME}"
REGISTRY="${REGISTRY:-registry.jclee.me}"
IMAGE_NAME="${IMAGE_NAME:-blacklist}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# 패키지 디렉토리 생성
echo "📁 패키지 디렉토리 생성: ${PACKAGE_DIR}"
mkdir -p "${PACKAGE_DIR}"/{docker,source,helm,scripts,docs}

# 1. Docker 이미지 내보내기
echo "🐳 Docker 이미지 내보내기..."
FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

# 이미지 확인
if docker images | grep -q "${REGISTRY}/${IMAGE_NAME}"; then
    echo "✅ 이미지 발견: ${FULL_IMAGE}"
else
    echo "📥 이미지 pull 중..."
    docker pull "${FULL_IMAGE}" || {
        echo "❌ 이미지 pull 실패. 로컬 빌드를 시도합니다..."
        docker build -f deployment/Dockerfile -t "${FULL_IMAGE}" .
    }
fi

# 이미지 내보내기
echo "💾 이미지를 tar.gz로 내보내기..."
docker save "${FULL_IMAGE}" | gzip > "${PACKAGE_DIR}/docker/blacklist-image.tar.gz"

# 이미지 정보 저장
cat > "${PACKAGE_DIR}/docker/image-info.txt" << EOF
Image: ${FULL_IMAGE}
Tag: ${IMAGE_TAG}
Registry: ${REGISTRY}
Export Date: $(date -u)
Size: $(du -h "${PACKAGE_DIR}/docker/blacklist-image.tar.gz" | cut -f1)
EOF

# 2. 소스 코드 패키징
echo "📝 소스 코드 패키징..."
tar -czf "${PACKAGE_DIR}/source/blacklist-source.tar.gz" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='instance/*.db' \
    --exclude='data' \
    --exclude='logs' \
    --exclude='venv' \
    --exclude='.env' \
    .

# 주요 설정 파일 복사
cp -r k8s "${PACKAGE_DIR}/source/" 2>/dev/null || echo "k8s 디렉토리 없음"
cp -r charts "${PACKAGE_DIR}/source/" 2>/dev/null || echo "charts 디렉토리 없음"
cp requirements.txt "${PACKAGE_DIR}/source/"
cp .env.example "${PACKAGE_DIR}/source/"
cp CLAUDE.md "${PACKAGE_DIR}/source/" 2>/dev/null || echo "CLAUDE.md 없음"

# 3. Helm 차트 패키징
echo "📊 Helm 차트 패키징..."
if [ -d "charts/blacklist" ]; then
    cp -r charts/blacklist "${PACKAGE_DIR}/helm/"
    
    # 오프라인용 values 생성
    cat > "${PACKAGE_DIR}/helm/values-offline.yaml" << EOF
image:
  repository: blacklist
  tag: "${IMAGE_TAG}"
  pullPolicy: Never

service:
  type: NodePort
  nodePort: 32452

ingress:
  enabled: false

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi
EOF
else
    echo "⚠️ Helm 차트를 찾을 수 없습니다"
fi

# 4. 설치 스크립트 생성
echo "🔧 설치 스크립트 생성..."

# Docker Compose 설치 스크립트
cat > "${PACKAGE_DIR}/scripts/install-docker-compose.sh" << 'SCRIPT'
#!/bin/bash
set -e

echo "🚀 Blacklist Docker Compose 설치 시작..."

# Docker 이미지 로드
echo "📦 Docker 이미지 로딩..."
docker load < ../docker/blacklist-image.tar.gz

# 소스 파일 추출
echo "📂 소스 파일 추출..."
mkdir -p blacklist
tar -xzf ../source/blacklist-source.tar.gz -C blacklist/

cd blacklist

# 환경 설정
echo "⚙️ 환경 설정..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️ .env 파일을 편집하여 설정을 완료하세요"
fi

# 데이터베이스 초기화
echo "🗄️ 데이터베이스 초기화..."
if [ -f init_database.py ]; then
    python3 init_database.py
fi

# Docker Compose 실행
echo "🎯 서비스 시작..."
docker-compose -f deployment/docker-compose.yml up -d

echo "✅ 설치 완료!"
echo "🌐 접속 URL: http://localhost:8541"
echo "📋 상태 확인: docker-compose -f deployment/docker-compose.yml ps"
SCRIPT

# Kubernetes 설치 스크립트
cat > "${PACKAGE_DIR}/scripts/install-kubernetes.sh" << 'SCRIPT'
#!/bin/bash
set -e

echo "🚀 Blacklist Kubernetes 설치 시작..."

# Docker 이미지 로드
echo "📦 Docker 이미지 로딩..."
docker load < ../docker/blacklist-image.tar.gz

# 이미지 태그 변경 (로컬 사용)
docker tag $(docker images --format "{{.Repository}}:{{.Tag}}" | grep blacklist | head -1) blacklist:latest

# Kubernetes 리소스 적용
echo "🎯 Kubernetes 리소스 적용..."
kubectl create namespace blacklist --dry-run=client -o yaml | kubectl apply -f -

# 소스에서 k8s 매니페스트 적용
if [ -d ../source/k8s ]; then
    kubectl apply -k ../source/k8s/
else
    echo "⚠️ k8s 매니페스트를 찾을 수 없습니다"
fi

echo "⏳ 배포 대기 중..."
kubectl rollout status deployment/blacklist -n blacklist --timeout=300s || true

echo "✅ 설치 완료!"
echo "🌐 서비스 정보:"
kubectl get svc -n blacklist
SCRIPT

# Helm 설치 스크립트
cat > "${PACKAGE_DIR}/scripts/install-helm.sh" << 'SCRIPT'
#!/bin/bash
set -e

echo "🚀 Blacklist Helm 설치 시작..."

# Docker 이미지 로드
echo "📦 Docker 이미지 로딩..."
docker load < ../docker/blacklist-image.tar.gz

# 이미지 태그 변경
docker tag $(docker images --format "{{.Repository}}:{{.Tag}}" | grep blacklist | head -1) blacklist:latest

# Helm 설치
echo "⚙️ Helm 차트 설치..."
helm upgrade --install blacklist ../helm/blacklist \
    -f ../helm/values-offline.yaml \
    --namespace blacklist \
    --create-namespace \
    --wait \
    --timeout 5m

echo "✅ 설치 완료!"
echo "🌐 서비스 정보:"
kubectl get svc -n blacklist
echo "📊 Helm 상태:"
helm status blacklist -n blacklist
SCRIPT

chmod +x "${PACKAGE_DIR}/scripts/"*.sh

# 5. 문서 생성
echo "📚 문서 생성..."
cat > "${PACKAGE_DIR}/docs/INSTALLATION.md" << EOF
# Blacklist 오프라인 설치 가이드

생성 시간: ${TIMESTAMP}

## 📦 패키지 구성

- \`docker/\` - Docker 이미지 (blacklist-image.tar.gz)
- \`source/\` - 소스 코드 및 설정 파일
- \`helm/\` - Helm 차트
- \`scripts/\` - 설치 스크립트
- \`docs/\` - 문서

## 🚀 빠른 시작

### 옵션 1: Docker Compose
\`\`\`bash
cd scripts
./install-docker-compose.sh
\`\`\`

### 옵션 2: Kubernetes
\`\`\`bash
cd scripts
./install-kubernetes.sh
\`\`\`

### 옵션 3: Helm (권장)
\`\`\`bash
cd scripts
./install-helm.sh
\`\`\`

## ⚙️ 환경 설정

설치 전 다음 환경 변수를 설정하세요:

- REGTECH_USERNAME
- REGTECH_PASSWORD
- SECUDIUM_USERNAME
- SECUDIUM_PASSWORD

## 📋 시스템 요구사항

- Docker 20.10+
- Python 3.9+ (Docker Compose 설치 시)
- Kubernetes 1.20+ (K8s/Helm 설치 시)
- 최소 512MB 메모리
- 2GB 저장 공간

## 🔧 문제 해결

### Docker 이미지 로딩 실패
\`\`\`bash
gunzip -c docker/blacklist-image.tar.gz | docker load
\`\`\`

### 포트 충돌
기본 포트를 변경하려면 환경 변수 설정:
\`\`\`bash
export PORT=8542
\`\`\`

## 📞 지원

문제 발생 시 CLAUDE.md 파일을 참조하세요.
EOF

# 6. 패키지 정보 생성
echo "📋 패키지 메타데이터 생성..."
cat > "${PACKAGE_DIR}/package-info.json" << EOF
{
  "name": "blacklist-offline-package",
  "version": "${IMAGE_TAG}",
  "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "size": {
    "docker": "$(du -h "${PACKAGE_DIR}/docker/blacklist-image.tar.gz" | cut -f1)",
    "source": "$(du -h "${PACKAGE_DIR}/source/blacklist-source.tar.gz" | cut -f1)",
    "total": "$(du -sh "${PACKAGE_DIR}" | cut -f1)"
  },
  "contents": {
    "docker_image": "${FULL_IMAGE}",
    "installation_methods": ["docker-compose", "kubernetes", "helm"]
  }
}
EOF

# 7. 체크섬 생성
echo "🔐 체크섬 생성..."
cd "${PACKAGE_DIR}"
find . -type f -exec sha256sum {} + > checksums.txt

# 8. 최종 패키지 생성
echo "🗜️ 최종 패키지 압축..."
cd /tmp
tar -czf "${PACKAGE_NAME}.tar.gz" "${PACKAGE_NAME}/"

# 결과 출력
FINAL_SIZE=$(du -h "/tmp/${PACKAGE_NAME}.tar.gz" | cut -f1)
echo ""
echo "✅ 오프라인 패키지 생성 완료!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 패키지 이름: ${PACKAGE_NAME}.tar.gz"
echo "📏 패키지 크기: ${FINAL_SIZE}"
echo "📍 저장 위치: /tmp/${PACKAGE_NAME}.tar.gz"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📥 사용 방법:"
echo "1. tar -xzf ${PACKAGE_NAME}.tar.gz"
echo "2. cd ${PACKAGE_NAME}"
echo "3. cat docs/INSTALLATION.md"