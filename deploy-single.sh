#!/bin/bash
# 단일 컨테이너 배포 스크립트

set -e

echo "🚀 단일 컨테이너 배포 시작..."

# 색상 코드
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 기본값
REGISTRY="192.168.50.215:1234"
IMAGE_NAME="blacklist"
DEPLOY_HOST="192.168.50.215"
DEPLOY_PORT="1111"
TARGET="production"  # production 또는 production-with-redis

# 옵션 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        --with-redis)
            TARGET="production-with-redis"
            shift
            ;;
        --no-redis)
            TARGET="production"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--with-redis|--no-redis]"
            exit 1
            ;;
    esac
done

echo -e "${YELLOW}🔧 빌드 타겟: $TARGET${NC}"

# 1. 기존 컨테이너 정지
echo -e "${YELLOW}📦 기존 컨테이너 정리...${NC}"
docker-compose down || true
docker stop blacklist blacklist-app blacklist-redis || true
docker rm blacklist blacklist-app blacklist-redis || true

# 2. 새 이미지 빌드
echo -e "${YELLOW}🔨 새 이미지 빌드 중...${NC}"
docker build \
    --target $TARGET \
    -t ${REGISTRY}/${IMAGE_NAME}:single-latest \
    -t ${REGISTRY}/${IMAGE_NAME}:single-$(date +%Y%m%d-%H%M%S) \
    -f deployment/Dockerfile.single \
    .

# 3. 레지스트리 푸시
echo -e "${YELLOW}📤 레지스트리에 푸시 중...${NC}"
docker push ${REGISTRY}/${IMAGE_NAME}:single-latest

# 4. 로컬 실행 (docker-compose.single.yml 사용)
echo -e "${YELLOW}🚀 새 컨테이너 시작...${NC}"

# 이미지 태그 업데이트
sed -i "s|image: .*|image: ${REGISTRY}/${IMAGE_NAME}:single-latest|" docker-compose.single.yml

# Redis 환경변수 설정
if [ "$TARGET" = "production-with-redis" ]; then
    echo -e "${GREEN}✅ Redis 내장 모드${NC}"
    # Redis URL을 localhost로 설정
    sed -i 's|# - REDIS_URL=|      - REDIS_URL=redis://localhost:6379/0|' docker-compose.single.yml
else
    echo -e "${GREEN}✅ 메모리 캐시 모드${NC}"
    # Redis URL 주석 처리
    sed -i 's|      - REDIS_URL=|# - REDIS_URL=|' docker-compose.single.yml
fi

# 컨테이너 시작
docker-compose -f docker-compose.single.yml up -d

# 5. 헬스 체크
echo -e "${YELLOW}🔍 헬스 체크 중...${NC}"
sleep 10

for i in {1..30}; do
    if curl -s -f http://localhost:2541/health > /dev/null; then
        echo -e "${GREEN}✅ 애플리케이션이 정상적으로 실행 중입니다!${NC}"
        
        # 상태 정보 출력
        echo -e "\n${YELLOW}📊 시스템 상태:${NC}"
        curl -s http://localhost:2541/api/stats | jq '.' || curl -s http://localhost:2541/api/stats
        
        echo -e "\n${YELLOW}🐳 컨테이너 정보:${NC}"
        docker ps | grep blacklist
        
        echo -e "\n${GREEN}🎉 단일 컨테이너 배포 완료!${NC}"
        echo -e "   - 모드: $TARGET"
        echo -e "   - URL: http://localhost:2541"
        echo -e "   - 로그: docker logs -f blacklist"
        
        exit 0
    fi
    echo "대기 중... ($i/30)"
    sleep 2
done

echo -e "${RED}❌ 헬스 체크 실패${NC}"
docker logs blacklist
exit 1