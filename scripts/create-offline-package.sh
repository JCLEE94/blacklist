#!/bin/bash

# 오프라인 배포 패키지 생성 스크립트
# Docker 이미지와 Kubernetes 매니페스트를 tar 파일로 패키징

set -e

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

# CI/CD에서 IMAGE_TAG가 전달되면 사용, 아니면 timestamp 사용
if [ -n "$IMAGE_TAG" ] && [ "$IMAGE_TAG" != "latest" ]; then
    PACKAGE_NAME="blacklist-offline-${IMAGE_TAG}.tar.gz"
else
    PACKAGE_NAME="blacklist-offline-${TIMESTAMP}.tar.gz"
fi

# 출력 디렉토리 생성
echo -e "${BLUE}📁 출력 디렉토리 생성...${NC}"
rm -rf ${OUTPUT_DIR}
mkdir -p ${OUTPUT_DIR}/{images,k8s,scripts}

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

# Busybox 이미지 (init container용)
echo "  - ${BUSYBOX_IMAGE}"
docker pull ${BUSYBOX_IMAGE}
docker save ${BUSYBOX_IMAGE} -o ${OUTPUT_DIR}/images/busybox.tar

# 2. Kubernetes 매니페스트 복사
echo -e "${BLUE}📋 Kubernetes 매니페스트 복사 중...${NC}"
cp -r k8s/* ${OUTPUT_DIR}/k8s/

# 3. 설치 스크립트 생성
echo -e "${BLUE}📝 설치 스크립트 생성 중...${NC}"

cat > ${OUTPUT_DIR}/install.sh << 'EOF'
#!/bin/bash

# 오프라인 설치 스크립트

set -e

echo "🚀 Blacklist 오프라인 설치 시작..."

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 1. Docker 이미지 로드
echo -e "${BLUE}🐳 Docker 이미지 로드 중...${NC}"
docker load -i images/blacklist.tar
docker load -i images/redis.tar
docker load -i images/busybox.tar

echo -e "${GREEN}✅ Docker 이미지 로드 완료${NC}"

# 2. Kubernetes 배포
echo -e "${BLUE}☸️  Kubernetes 배포 중...${NC}"

# 네임스페이스 생성
kubectl create namespace blacklist --dry-run=client -o yaml | kubectl apply -f -

# Kustomize로 배포
kubectl apply -k k8s/

echo -e "${GREEN}✅ Kubernetes 배포 완료${NC}"

# 3. 배포 상태 확인
echo -e "${BLUE}📊 배포 상태 확인...${NC}"
kubectl get pods -n blacklist
kubectl get svc -n blacklist

echo ""
echo -e "${GREEN}🎉 설치 완료!${NC}"
echo ""
echo "접속 방법:"
echo "- NodePort: http://<노드IP>:32452"
echo "- Port Forward: kubectl port-forward -n blacklist svc/blacklist 8541:2541"
echo ""
echo "상태 확인:"
echo "- kubectl get pods -n blacklist"
echo "- kubectl logs -n blacklist deployment/blacklist"
EOF

chmod +x ${OUTPUT_DIR}/install.sh

# 4. 제거 스크립트 생성
cat > ${OUTPUT_DIR}/uninstall.sh << 'EOF'
#!/bin/bash

# 오프라인 제거 스크립트

echo "🗑️  Blacklist 제거 중..."

# Kubernetes 리소스 제거
kubectl delete -k k8s/ --ignore-not-found=true

# 네임스페이스 제거
kubectl delete namespace blacklist --ignore-not-found=true

echo "✅ 제거 완료"
EOF

chmod +x ${OUTPUT_DIR}/uninstall.sh

# 5. README 생성
cat > ${OUTPUT_DIR}/README.md << EOF
# Blacklist 오프라인 배포 패키지

## 패키지 정보
- 생성일시: $(date)
- 버전: $(git describe --tags --always 2>/dev/null || echo "unknown")
- 커밋: $(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

## 포함된 Docker 이미지
- ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
- ${REDIS_IMAGE}
- ${BUSYBOX_IMAGE}

## 설치 방법
\`\`\`bash
# 1. tar 파일 압축 해제
tar -xzf ${PACKAGE_NAME}
cd offline-package

# 2. 설치 스크립트 실행
./install.sh
\`\`\`

## 제거 방법
\`\`\`bash
./uninstall.sh
\`\`\`

## 수동 설치
\`\`\`bash
# Docker 이미지 로드
docker load -i images/blacklist.tar
docker load -i images/redis.tar
docker load -i images/busybox.tar

# Kubernetes 배포
kubectl apply -k k8s/
\`\`\`

## 환경 변수 설정
필요한 경우 k8s/configmap.yaml과 k8s/secret.yaml을 수정하세요:
- REGTECH_USERNAME/PASSWORD
- SECUDIUM_USERNAME/PASSWORD
- 기타 설정

## 접속 방법
- NodePort: http://<노드IP>:32452
- Port Forward: kubectl port-forward -n blacklist svc/blacklist 8541:2541
EOF

# 6. 패키지 생성
echo -e "${BLUE}📦 tar 파일 생성 중...${NC}"
tar -czf ${PACKAGE_NAME} ${OUTPUT_DIR}

# 7. 정리
echo -e "${BLUE}🧹 임시 파일 정리 중...${NC}"
rm -rf ${OUTPUT_DIR}

# 8. 완료
echo ""
echo -e "${GREEN}✅ 오프라인 패키지 생성 완료!${NC}"
echo -e "📦 파일명: ${YELLOW}${PACKAGE_NAME}${NC}"
echo -e "📏 크기: $(du -h ${PACKAGE_NAME} | cut -f1)"
echo ""
echo "사용 방법:"
echo "1. 오프라인 환경으로 파일 전송"
echo "2. tar -xzf ${PACKAGE_NAME}"
echo "3. cd offline-package && ./install.sh"