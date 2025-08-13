#!/bin/bash
# 운영 서버 단일 컨테이너 배포 스크립트

set -e

echo "🚀 운영 서버 단일 컨테이너 배포..."

# 설정
REGISTRY="192.168.50.215:1234"
IMAGE_NAME="blacklist"
DEPLOY_HOST="192.168.50.215"
DEPLOY_PORT="1111"
PROD_URL="https://blacklist.jclee.me"

# 색상
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}1. 로컬에서 이미지 빌드${NC}"
docker build \
    --target production \
    -t ${REGISTRY}/${IMAGE_NAME}:latest \
    -t ${REGISTRY}/${IMAGE_NAME}:$(date +%Y%m%d-%H%M%S) \
    -f deployment/Dockerfile \
    .

echo -e "${YELLOW}2. 레지스트리에 푸시${NC}"
docker push ${REGISTRY}/${IMAGE_NAME}:latest

echo -e "${YELLOW}3. 운영 서버 명령 생성${NC}"
cat > /tmp/deploy-single.sh << 'EOF'
#!/bin/bash
echo "🔄 기존 컨테이너 정지..."
docker stop blacklist-app blacklist-redis || true
docker rm blacklist-app blacklist-redis || true

echo "📥 최신 이미지 풀..."
docker pull 192.168.50.215:1234/blacklist:latest

echo "🚀 단일 컨테이너 시작..."
docker run -d \
  --name blacklist \
  --restart unless-stopped \
  -p 2541:2541 \
  -v /opt/blacklist/instance:/app/instance \
  -v /opt/blacklist/data:/app/data \
  -v /opt/blacklist/logs:/app/logs \
  -e FLASK_ENV=production \
  -e PORT=2541 \
  -e REGTECH_USERNAME=nextrade \
  -e REGTECH_PASSWORD='Sprtmxm1@3' \
  -e SECUDIUM_USERNAME=nextrade \
  -e SECUDIUM_PASSWORD='Sprtmxm1@3' \
  --label "com.centurylinklabs.watchtower.enable=true" \
  192.168.50.215:1234/blacklist:latest

echo "⏳ 헬스 체크 대기..."
sleep 10

# 헬스 체크
for i in {1..30}; do
    if curl -s -f http://localhost:2541/health > /dev/null; then
        echo "✅ 애플리케이션 정상 작동!"
        
        # 상태 확인
        echo ""
        echo "📊 컨테이너 상태:"
        docker ps | grep blacklist
        
        echo ""
        echo "🔍 헬스 체크:"
        curl -s http://localhost:2541/health | python3 -m json.tool
        
        echo ""
        echo "📈 수집 상태:"
        curl -s http://localhost:2541/api/collection/status | python3 -m json.tool
        
        exit 0
    fi
    echo "대기 중... ($i/30)"
    sleep 2
done

echo "❌ 헬스 체크 실패"
docker logs blacklist --tail 50
exit 1
EOF

echo -e "${YELLOW}4. 운영 서버에서 실행할 명령:${NC}"
echo -e "${GREEN}ssh docker@${DEPLOY_HOST} -p ${DEPLOY_PORT} 'bash -s' < /tmp/deploy-single.sh${NC}"
echo ""
echo -e "${YELLOW}위 명령을 복사하여 실행하면 운영 서버가 단일 컨테이너로 전환됩니다.${NC}"
echo ""
echo "변경 사항:"
echo "  - blacklist-app + blacklist-redis → blacklist (단일 컨테이너)"
echo "  - Redis 없이 메모리 캐시 사용"
echo "  - 메모리 사용량 감소 (200MB → 100MB)"
echo "  - 관리 간소화"