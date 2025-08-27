#!/bin/bash
# Enable Watchtower for Blacklist Auto-Update
# Version: 1.0.40

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Watchtower 자동 업데이트 설정${NC}"
echo "================================"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker가 설치되어 있지 않습니다${NC}"
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose가 설치되어 있지 않습니다${NC}"
    exit 1
fi

# Create network if not exists
echo -e "${YELLOW}📌 네트워크 생성 중...${NC}"
docker network create blacklist-network 2>/dev/null || echo "네트워크가 이미 존재합니다"

# Start Watchtower
echo -e "${YELLOW}🔄 Watchtower 시작 중...${NC}"
docker-compose -f docker-compose.watchtower.yml up -d

# Check status
if docker ps | grep -q blacklist-watchtower; then
    echo -e "${GREEN}✅ Watchtower가 성공적으로 시작되었습니다${NC}"
    echo ""
    echo "📊 상태 확인:"
    docker ps --filter "name=blacklist-watchtower" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
    echo ""
    echo -e "${GREEN}설정 완료!${NC}"
    echo "- 업데이트 주기: 30분"
    echo "- 모니터링 대상: registry.jclee.me/blacklist:latest"
    echo "- 자동 정리: 활성화"
    echo ""
    echo "📝 유용한 명령어:"
    echo "  docker logs -f blacklist-watchtower  # 로그 확인"
    echo "  docker-compose -f docker-compose.watchtower.yml down  # Watchtower 중지"
    echo "  ./scripts/manage-watchtower.sh status  # 상태 확인"
else
    echo -e "${RED}❌ Watchtower 시작 실패${NC}"
    echo "로그를 확인하세요: docker-compose -f docker-compose.watchtower.yml logs"
    exit 1
fi