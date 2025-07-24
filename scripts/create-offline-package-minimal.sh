#!/bin/bash
# 최소 오프라인 패키지 생성 (문서 제외)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 오프라인 배포 패키지 생성 시작..."

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 설정
REGISTRY="${REGISTRY:-registry.jclee.me}"
IMAGE_NAME="${IMAGE_NAME:-blacklist}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
REDIS_IMAGE="redis:7-alpine"
BUSYBOX_IMAGE="busybox"
OUTPUT_DIR="offline-package"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="blacklist-offline-${TIMESTAMP}.tar.gz"

# 출력 디렉토리 생성
echo -e "${BLUE}📁 출력 디렉토리 생성...${NC}"
rm -rf ${OUTPUT_DIR}
mkdir -p ${OUTPUT_DIR}/{images,k8s,src,scripts}

# 1. Docker 이미지 저장
echo -e "${BLUE}🐳 Docker 이미지 저장 중...${NC}"

# Blacklist 이미지
echo "  - ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
docker pull ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} || {
    echo -e "${YELLOW}⚠️  이미지를 pull할 수 없습니다. 로컬 이미지 사용...${NC}"
}
docker save ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} -o ${OUTPUT_DIR}/images/blacklist.tar

# Redis 이미지
echo "  - ${REDIS_IMAGE}"
docker pull ${REDIS_IMAGE}
docker save ${REDIS_IMAGE} -o ${OUTPUT_DIR}/images/redis.tar

# Busybox 이미지
echo "  - ${BUSYBOX_IMAGE}"
docker pull ${BUSYBOX_IMAGE}
docker save ${BUSYBOX_IMAGE} -o ${OUTPUT_DIR}/images/busybox.tar

# 2. 소스코드 복사
echo -e "${BLUE}📦 소스코드 복사 중...${NC}"
rsync -av --exclude='*.pyc' \
          --exclude='__pycache__' \
          --exclude='.git' \
          --exclude='.github' \
          --exclude='instance' \
          --exclude='logs' \
          --exclude='tests' \
          --exclude='*.log' \
          --exclude='.env*' \
          --exclude='data/regtech/*.json' \
          --exclude='node_modules' \
          --exclude='offline-package' \
          --exclude='blacklist-offline-*.tar.gz' \
          --exclude='*.md' \
          --exclude='docs' \
          "${PROJECT_ROOT}/src/" "${OUTPUT_DIR}/src/"

# 필수 파일만 복사
cp "${PROJECT_ROOT}/requirements.txt" "${OUTPUT_DIR}/"
cp "${PROJECT_ROOT}/main.py" "${OUTPUT_DIR}/"
cp "${PROJECT_ROOT}/init_database.py" "${OUTPUT_DIR}/"
cp "${PROJECT_ROOT}/gunicorn_config.py" "${OUTPUT_DIR}/" 2>/dev/null || true

# 3. Kubernetes 매니페스트 복사
echo -e "${BLUE}📋 Kubernetes 매니페스트 복사 중...${NC}"
if [ -d "${PROJECT_ROOT}/k8s-gitops" ]; then
    cp -r "${PROJECT_ROOT}/k8s-gitops/base" "${OUTPUT_DIR}/k8s/"
    cp -r "${PROJECT_ROOT}/k8s-gitops/overlays" "${OUTPUT_DIR}/k8s/"
else
    cp -r "${PROJECT_ROOT}/k8s"/* "${OUTPUT_DIR}/k8s/"
fi

# 4. 설치 스크립트 생성 (단순화)
echo -e "${BLUE}📝 설치 스크립트 생성 중...${NC}"
cat > ${OUTPUT_DIR}/install.sh << 'EOF'
#!/bin/bash
set -e

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAMESPACE="blacklist"

echo "Blacklist 오프라인 설치"
echo "1) Kubernetes"
echo "2) Docker"
echo "3) Python"
read -p "선택: " choice

case $choice in
    1)
        # Docker 이미지 로드
        docker load -i images/blacklist.tar
        docker load -i images/redis.tar
        docker load -i images/busybox.tar
        
        # Kubernetes 배포
        kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
        kubectl apply -k k8s/overlays/prod -n ${NAMESPACE}
        kubectl rollout status deployment/blacklist -n ${NAMESPACE} --timeout=300s
        echo "✅ Kubernetes 배포 완료"
        ;;
    2)
        # Docker 이미지 로드
        docker load -i images/blacklist.tar
        docker load -i images/redis.tar
        
        # 컨테이너 실행
        docker run -d --name blacklist-redis --restart unless-stopped redis:7-alpine
        docker run -d --name blacklist --restart unless-stopped \
            -p 8541:8541 --link blacklist-redis:redis \
            -e REDIS_URL=redis://redis:6379/0 \
            -e FLASK_ENV=production \
            registry.jclee.me/blacklist:latest
        echo "✅ Docker 실행 완료"
        ;;
    3)
        # Python 환경 설정
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        python3 init_database.py
        echo "✅ Python 설치 완료"
        echo "실행: python3 main.py"
        ;;
esac
EOF

chmod +x ${OUTPUT_DIR}/install.sh

# 5. 제거 스크립트
cat > ${OUTPUT_DIR}/uninstall.sh << 'EOF'
#!/bin/bash
kubectl delete -k k8s/ -n blacklist --ignore-not-found=true
kubectl delete namespace blacklist --ignore-not-found=true
docker stop blacklist blacklist-redis 2>/dev/null
docker rm blacklist blacklist-redis 2>/dev/null
echo "✅ 제거 완료"
EOF

chmod +x ${OUTPUT_DIR}/uninstall.sh

# 6. 환경변수 템플릿
cat > ${OUTPUT_DIR}/.env.example << 'EOF'
FLASK_ENV=production
PORT=8541
SECRET_KEY=change-this-secret-key
REGTECH_USERNAME=your-username
REGTECH_PASSWORD=your-password
COLLECTION_ENABLED=false
EOF

# 7. 패키지 생성
echo -e "${BLUE}📦 tar 파일 생성 중...${NC}"
tar -czf ${PACKAGE_NAME} ${OUTPUT_DIR}

# 8. 정리
rm -rf ${OUTPUT_DIR}

# 완료
echo -e "${GREEN}✅ 완료!${NC}"
echo -e "📦 파일: ${YELLOW}${PACKAGE_NAME}${NC}"
echo -e "📏 크기: $(du -h ${PACKAGE_NAME} | cut -f1)"